"""Identity, provenance and the on-disk evidence of one crawl.

A crawl used to leave exactly one artefact: a file of product records, with no
statement of what was asked for, which locale answered, or what was seen and
then discarded. Three consequences, all of which cost a re-crawl to undo:

* **Discovery was destroyed as it happened.** The spider drops an ASIN it has
  already queued before anything about that sighting is written down. One live
  Amazon.de search page carries the same ASIN twice -- once organic at rank 8
  and once sponsored at rank 16 -- and that fact was unrecoverable.
* **The page was thrown away.** Every new field the extractor learns to read
  costs a fresh crawl of pages we already downloaded, which contradicts the
  first thing this project decided about how to treat evidence.
* **Locale was implicit.** It lives in an HTTP header in a settings module,
  while the label vocabulary is chosen separately from the domain. The two can
  disagree with no error at all: an English-locale request to amazon.de leaves
  every German label unmapped and emits an empty ``attributes`` block beside a
  full ``raw_tables``.

So a run owns a directory::

    data/runs/<run_id>/
        manifest.json         what was asked for, by which code, with which
                              settings, which feeds it bound, how it ended
        discovery.jsonl       one line per sighting, before de-duplication
        pages.jsonl           one line per retained artefact: when it was
                              fetched, from which URL, with which status, and
                              the digest of the bytes actually stored
        pages/<ASIN>.html.gz  the page each record was extracted from
        quarantine/<ASIN>.html.gz  a page whose redaction failed
        failures/….html.gz    bounded samples of what went wrong
        search/….html.gz      search responses, when asked for

The product feed is unchanged and still goes wherever ``-O`` points. Nothing
here interprets anything: it records.

Four properties are load-bearing and each replaces something that was merely
probable before (T1):

**A run identity is unique.** It used to be a hash of second-resolution time,
marketplace and arguments, so two identical crawls started in the same second
produced the same ID -- and ``open()`` accepted the existing directory,
appended to its discovery log and overwrote its manifest. The identity now
carries random bytes and the directory is created exclusively.

**A manifest is never half-written.** It is written through a temporary file
and renamed, and it carries its own state, so a crawl killed mid-flight leaves
a readable manifest that says ``running`` instead of a truncated one.

**An observation's time survives being copied.** Re-extraction used to fall
back to the page file's mtime, which any copy, archive or restore rewrites --
so moving a study bundle could make every page in it look freshly fetched.
Fetch time is recorded per page at the moment of the fetch. A run store
written before this existed has no such record, and its pages are reported
with unknown freshness rather than with a filesystem timestamp.

**A stored page says whether it is clean.** Redaction used to be imported from
the test corpus through ``sys.path`` and fall back to storing the unredacted
page on any exception, silently. Failures are now recorded and the page is
quarantined out of the export/promotion path.

Because the pages survive, a finished run re-extracts offline with today's
extractor and no network at all::

    python -m shopping_advisor.run reextract data/runs/<run_id> \
        --feed data/products.jsonl -o data/products.v6.jsonl
"""

import argparse
import datetime as _dt
import gzip
import json
import pathlib
import re
import secrets
import sys

from .jsonl import read_jsonl  # noqa: F401  -- the documented name; the reader lives in .jsonl (R16 review 2)
from .provenance import (RUN_MANIFEST_VERSION, acquisition_settings,
                         code_identity, sha256_text, write_json_atomically)
from .redaction import APPLIED, redact_page

# Written next to the crawl output rather than inside it, so a feed file can
# still be moved, appended to or replaced without losing its provenance.
DEFAULT_RUN_ROOT = 'data/runs'

MANIFEST = 'manifest.json'
DISCOVERY = 'discovery.jsonl'
PAGES_INDEX = 'pages.jsonl'
PAGES = 'pages'
QUARANTINE = 'quarantine'
FAILURES = 'failures'
SEARCH = 'search'

#: A crawl that is still running, or died without closing its manifest.
RUNNING = 'running'
#: A crawl that closed normally. ``finish_reason`` says how.
CLOSED = 'closed'

# How much of a failing response is worth keeping. Challenge pages are a few
# kilobytes; a titleless PDP can be two megabytes, and a study does not need
# a second copy of the whole shelf to reproduce a parse defect.
FAILURE_SAMPLE_BYTES = 256 * 1024
#: Samples kept per failure kind. A blocked crawl produces one challenge page
#: per request, and the tenth is not more informative than the first.
FAILURE_SAMPLES_PER_KIND = 5


class RunDirectoryExists(FileExistsError):
    """Another run already owns this directory, so this one will not use it."""


class FeedBindingError(ValueError):
    """The feed offered for replay is not the feed this run wrote."""


def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def acquisition_locale(settings, marketplace):
    """The locale a crawl actually asks Amazon for, and whether it fits.

    Returns ``{'accept_language', 'language', 'expected_language', 'status'}``.
    ``status`` is one of:

    ``matches``
        The request locale agrees with the marketplace profile's label
        vocabulary. This is the only configuration that has been validated.
    ``unset``
        No ``Accept-Language`` is configured, so Amazon answers in the
        marketplace's own default. On amazon.de that is German, which is what
        we want, but it is luck rather than intent -- hence a warning.
    ``conflict``
        A locale is configured that contradicts the profile. Nothing would
        raise; extraction would quietly under-report. The caller turns this
        into a hard failure.
    """
    headers = settings.getdict('DEFAULT_REQUEST_HEADERS') or {}
    header = ''
    for name, value in headers.items():
        if name.lower() == 'accept-language':
            header = (value or '').strip()
            break

    expected = marketplace.language
    if not header:
        return {'accept_language': '', 'language': None,
                'expected_language': expected, 'status': 'unset'}

    # "de-DE,de;q=0.9,en;q=0.8" -> "de". Only the first, highest-priority tag
    # decides: the rest are fallbacks Amazon may never use.
    primary = re.split(r'[;,]', header)[0].strip().lower()
    language = primary.split('-')[0] or None
    status = 'matches' if language == expected else 'conflict'
    return {'accept_language': header, 'language': language,
            'expected_language': expected, 'status': status}


def declared_feeds(settings):
    """The feed files this crawl was told to write, as bindings.

    Read from Scrapy's ``FEEDS`` -- which is where ``-O data/x.jsonl`` ends up
    -- so the manifest can name the feed a later replay should be given.
    Recorded at the start, not at the end: the feed exporter closes its file
    on ``spider_closed``, and a digest taken while that signal is being
    delivered would be a digest of a file still being written. The spider now
    writes the manifest on ``engine_stopped``, after every ``spider_closed``
    receiver has completed, but the binding stays a declaration made when the
    crawl was asked for, so that a run that never closed still names its feed.
    """
    bindings = []
    for uri, options in (settings.getdict('FEEDS') or {}).items():
        options = options if isinstance(options, dict) else {}
        bindings.append({'uri': str(uri),
                         'format': options.get('format') or '',
                         'overwrite': bool(options.get('overwrite'))})
    return bindings


class CrawlRun:
    """One crawl's identity and its directory of evidence."""

    def __init__(self, root, spider, marketplace, locale, arguments,
                 keep_pages=True, settings=None, keep_search_pages=False):
        self.started_at = _utc_now()
        self.spider = spider
        self.marketplace = marketplace
        self.locale = locale
        self.arguments = dict(arguments)
        self.keep_pages = keep_pages
        self.keep_search_pages = keep_search_pages
        self.settings = acquisition_settings(settings) if settings else {}
        self.feeds = declared_feeds(settings) if settings else []

        # Sortable by time, readable at a glance, and unique because the tail
        # is random rather than derived. The previous digest was taken over
        # the timestamp, marketplace and arguments, which are precisely the
        # things two concurrent crawls of the same shelf have in common.
        stamp = self.started_at.strftime('%Y%m%dT%H%M%SZ')
        self.run_id = f'{stamp}-{marketplace}-{secrets.token_hex(4)}'

        self.directory = pathlib.Path(root) / self.run_id
        self.pages_directory = self.directory / PAGES
        self.quarantine_directory = self.directory / QUARANTINE
        self.counts = {'discovery_occurrences': 0, 'pages_saved': 0,
                       'page_write_errors': 0, 'redaction_failures': 0,
                       'pages_quarantined': 0, 'search_pages_saved': 0,
                       'failure_samples_saved': 0,
                       'failure_samples_over_cap': 0}
        self.state = RUNNING
        self._discovery = None
        self._index = None
        self._failure_counts = {}

    # -- provenance carried on every record --------------------------------

    def lineage(self):
        """The provenance fields every record of this run carries."""
        return {'run_id': self.run_id,
                'locale': self.locale.get('language') or '',
                'accept_language': self.locale.get('accept_language') or ''}

    # -- writing -----------------------------------------------------------

    def open(self):
        """Create this run's directory, exclusively.

        Exclusive because the alternative was measured: two runs sharing a
        directory interleave their discovery logs and overwrite each other's
        manifests and pages, and the surviving manifest describes only one of
        the two crawls that produced the evidence beside it.
        """
        try:
            self.directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise RunDirectoryExists(
                f'{self.directory} already exists: another run owns it. '
                f'Nothing was written.') from exc
        if self.keep_pages:
            self.pages_directory.mkdir(parents=True, exist_ok=True)
        self._discovery = (self.directory / DISCOVERY).open(
            'a', encoding='utf-8')
        self._index = (self.directory / PAGES_INDEX).open('a', encoding='utf-8')
        self.write_manifest()
        return self

    def record_discovery(self, occurrence):
        """Append one sighting, exactly as seen, before any de-duplication."""
        if self._discovery is None:
            return
        line = dict(occurrence)
        line.setdefault('run_id', self.run_id)
        line.setdefault('marketplace', self.marketplace)
        line.setdefault('locale', self.locale.get('language') or '')
        line.setdefault('seen_at', _utc_now().isoformat())
        self._discovery.write(json.dumps(line, ensure_ascii=False) + '\n')
        self._discovery.flush()
        self.counts['discovery_occurrences'] += 1

    def _index_entry(self, entry):
        if self._index is None:
            return entry
        self._index.write(json.dumps(entry, ensure_ascii=False) + '\n')
        self._index.flush()
        return entry

    def _store(self, path, html):
        """Redact, compress, write; return the entry fields that describe it.

        Returns ``None`` when the bytes could not be written at all, which is
        counted rather than raised: one unwritable page must not end a crawl
        that is producing records.
        """
        text, redaction = redact_page(html)
        if redaction != APPLIED:
            self.counts['redaction_failures'] += 1
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(path, 'wt', encoding='utf-8', compresslevel=6) as fh:
                fh.write(text)
        except OSError:
            self.counts['page_write_errors'] += 1
            return None
        return {'path': str(path.relative_to(self.directory)).replace('\\', '/'),
                'redaction': redaction,
                # Over the bytes retained, *after* redaction replaced the
                # session identifiers. It answers "is this the file the
                # manifest describes"; it is not a digest of Amazon's reply.
                'redacted_sha256': sha256_text(text),
                'redacted_bytes': len(text.encode('utf-8'))}

    def save_page(self, asin, html, fetched_at=None, request_url='',
                  final_url='', http_status=None):
        """Store the page a record was extracted from, gzipped, with its
        fetch metadata.

        Redacted on the way in with the same rules the committed corpus uses:
        the identifiers Amazon mints per session and per request have no place
        in a stored page, and the corpus test proves the substitution does not
        change a single extracted value. A page whose redaction *failed* is
        still kept -- it cannot be fetched again -- but it goes to
        ``quarantine/`` and never to ``pages/``, so the export and promotion
        paths cannot pick it up by accident.

        Returns the index entry, whose ``fetched_at`` the caller should put on
        the record too, so the feed and the page agree to the second.
        """
        if not (self.keep_pages and asin and html):
            return None
        stamp = fetched_at or _utc_now().isoformat()
        stored = self._store(self.pages_directory / f'{asin}.html.gz', html)
        if stored is None:
            return None
        if stored['redaction'] != APPLIED:
            # Move it out of the promotable store. Written first and moved
            # after, so a failure between the two leaves the page somewhere
            # rather than nowhere.
            target = self.quarantine_directory / f'{asin}.html.gz'
            target.parent.mkdir(parents=True, exist_ok=True)
            (self.pages_directory / f'{asin}.html.gz').replace(target)
            stored['path'] = f'{QUARANTINE}/{asin}.html.gz'
            self.counts['pages_quarantined'] += 1
        else:
            self.counts['pages_saved'] += 1
        return self._index_entry(dict(
            stored, kind='pdp', asin=asin, marketplace=self.marketplace,
            run_id=self.run_id, fetched_at=stamp,
            request_url=request_url or '', final_url=final_url or '',
            http_status=http_status,
            quarantined=stored['redaction'] != APPLIED))

    def save_search_page(self, query, page, html, fetched_at=None,
                         final_url='', http_status=None):
        """Retain one search response, when the run was asked to.

        Off by default and separate from the PDP store: a search page is the
        only witness to what a query returned and to what was *not* on the
        shelf, but it is also large, and retaining every page of every query
        changes the size of a run store by an order of magnitude.
        """
        if not (self.keep_search_pages and html):
            return None
        slug = re.sub(r'[^a-z0-9]+', '-', str(query).lower()).strip('-')[:48]
        stored = self._store(
            self.directory / SEARCH / f'{slug or "query"}-p{page}.html.gz', html)
        if stored is None:
            return None
        self.counts['search_pages_saved'] += 1
        return self._index_entry(dict(
            stored, kind='search', query=query, search_page=page,
            marketplace=self.marketplace, run_id=self.run_id,
            fetched_at=fetched_at or _utc_now().isoformat(),
            final_url=final_url or '', http_status=http_status,
            quarantined=stored['redaction'] != APPLIED))

    def save_failure(self, reason, html, key='', fetched_at=None,
                     final_url='', http_status=None):
        """Keep a bounded, truncated sample of a response that went wrong.

        A challenge page and a 200 with no product title are both discarded
        before anything is written down, which makes "the crawl returned 48 of
        56" a number with no evidence under it. Samples are capped per reason
        and truncated, because the purpose is to reproduce the defect, not to
        archive the failure.
        """
        seen = self._failure_counts.get(reason, 0)
        if seen >= FAILURE_SAMPLES_PER_KIND:
            self.counts['failure_samples_over_cap'] += 1
            return None
        self._failure_counts[reason] = seen + 1

        body = html or ''
        truncated = len(body) > FAILURE_SAMPLE_BYTES
        name = f'{reason}-{seen + 1:02d}{"-" + key if key else ""}.html.gz'
        stored = self._store(self.directory / FAILURES / name,
                             body[:FAILURE_SAMPLE_BYTES])
        if stored is None:
            return None
        self.counts['failure_samples_saved'] += 1
        return self._index_entry(dict(
            stored, kind='failure', reason=reason, asin=key,
            marketplace=self.marketplace, run_id=self.run_id,
            fetched_at=fetched_at or _utc_now().isoformat(),
            final_url=final_url or '', http_status=http_status,
            truncated=truncated,
            quarantined=stored['redaction'] != APPLIED))

    def manifest(self, stats=None, finish_reason=None):
        """The manifest as data, so a caller can inspect it without a file."""
        manifest = {
            'manifest_version': RUN_MANIFEST_VERSION,
            'run_id': self.run_id,
            'spider': self.spider,
            'marketplace': self.marketplace,
            'started_at': self.started_at.isoformat(),
            'arguments': self.arguments,
            'locale': self.locale,
            'pages_retained': self.keep_pages,
            'search_pages_retained': self.keep_search_pages,
            'state': self.state,
            'code': code_identity(),
            'settings': self.settings,
            'feeds': self.feeds,
            'counts': dict(self.counts),
        }
        if finish_reason is not None:
            manifest['finished_at'] = _utc_now().isoformat()
            manifest['finish_reason'] = finish_reason
        if stats is not None:
            manifest['stats'] = {key: value for key, value in stats.items()
                                 if isinstance(value, (int, float, str, bool))}
        return manifest

    def write_manifest(self, stats=None, finish_reason=None):
        return write_json_atomically(self.directory / MANIFEST,
                                     self.manifest(stats, finish_reason))

    def close(self, stats=None, finish_reason=None):
        for handle in ('_discovery', '_index'):
            stream = getattr(self, handle)
            if stream is not None:
                stream.close()
                setattr(self, handle, None)
        self.state = CLOSED
        if not self.directory.is_dir():
            # A run that never opened -- a refused directory, a locale
            # conflict raised before collection -- has nowhere to write and
            # nothing to say. Closing it is not an error.
            return None
        return self.write_manifest(stats, finish_reason)


# ---------------------------------------------------------------------------
# Reading a run back
# ---------------------------------------------------------------------------

def load_manifest(directory):
    return json.loads((pathlib.Path(directory) / MANIFEST)
                      .read_text(encoding='utf-8'))


def load_discovery(directory):
    path = pathlib.Path(directory) / DISCOVERY
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_pages_index(directory):
    """Every retained artefact this run wrote down, in the order it wrote it.

    Empty for a run store written before the index existed. That is not the
    same as a run that retained nothing, and :func:`page_metadata` keeps the
    difference visible instead of resolving it.
    """
    path = pathlib.Path(directory) / PAGES_INDEX
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def page_metadata(directory):
    """``{asin: entry}`` for the retained product pages of a run."""
    return {entry['asin']: entry for entry in load_pages_index(directory)
            if entry.get('kind') == 'pdp' and entry.get('asin')}


def run_state(manifest):
    """``complete``, ``interrupted`` or ``legacy`` -- what this run left behind.

    ``interrupted`` is the one worth having. A crawl killed by a timeout, a
    signal or a lost machine leaves a manifest that was written when it
    started; before it carried its own state, such a run was indistinguishable
    from one that simply had not been asked to close.
    """
    if not manifest.get('manifest_version'):
        return 'legacy'
    if manifest.get('state') == CLOSED:
        return 'complete'
    return 'interrupted'


def stored_pages(directory):
    """``{asin: path}`` for every page a run retained *and may export*.

    Quarantined pages are deliberately absent: the whole point of quarantine
    is that a caller which iterates the page store never picks one up.
    """
    pages = pathlib.Path(directory) / PAGES
    if not pages.is_dir():
        return {}
    return {path.name[:-len('.html.gz')]: path
            for path in sorted(pages.glob('*.html.gz'))}


def quarantined_pages(directory):
    """``{asin: path}`` for pages whose redaction failed."""
    pages = pathlib.Path(directory) / QUARANTINE
    if not pages.is_dir():
        return {}
    return {path.name[:-len('.html.gz')]: path
            for path in sorted(pages.glob('*.html.gz'))}


def failure_samples(directory):
    """Every retained failure sample, newest last."""
    return [entry for entry in load_pages_index(directory)
            if entry.get('kind') == 'failure']


def read_page(path):
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Binding a feed to the run that wrote it
# ---------------------------------------------------------------------------

def feed_binding(manifest, records):
    """How `records` relate to the run `manifest` describes.

    Replay takes a feed on the command line, and the useful failure is not a
    crash: it is silence. Handing ``reextract`` the feed of a *different*
    crawl produced records that carried this run's pages and that crawl's
    search queries, positions and fetch times, and nothing said so.

    Returns counts plus a ``status``:

    ``bound``
        every record that names a run names this one.
    ``mixed``
        some do. A merged multi-run evidence feed looks like this, and it is
        legitimate -- but its lineage is only partly this run's.
    ``foreign``
        none do, and at least one names another run. This is the wrong feed.
    ``legacy``
        no record names any run: a feed written before provenance existed.
        Readable, with unknown lineage, which is not the same as wrong.
    ``empty``
        no records at all.
    """
    from .extraction.marketplaces import domain_key

    run_id = manifest.get('run_id') or ''
    # Normalised, because 'amazon.de' and 'www.amazon.de' are one marketplace
    # and a feed that writes it the other way is not the wrong feed.
    marketplace = domain_key(manifest.get('marketplace') or '')
    bound = foreign = legacy = other_market = 0
    runs = {}
    for record in records:
        named = record.get('run_id') or ''
        if not named:
            legacy += 1
        elif named == run_id:
            bound += 1
        else:
            foreign += 1
            runs[named] = runs.get(named, 0) + 1
        seen = domain_key(record.get('marketplace') or '')
        if marketplace and seen not in ('', marketplace):
            other_market += 1

    if not records:
        status = 'empty'
    elif bound and not foreign:
        status = 'bound'
    elif bound:
        status = 'mixed'
    elif foreign:
        status = 'foreign'
    else:
        status = 'legacy'
    return {'status': status, 'records': len(records), 'bound': bound,
            'foreign': foreign, 'legacy': legacy,
            'other_marketplace': other_market, 'foreign_runs': runs}


def check_feed_binding(manifest, records, feed):
    """Raise :class:`FeedBindingError` if `feed` is not this run's feed.

    A feed whose records name *no* run is legacy rather than wrong, and one
    that names several is a merged multi-run evidence feed: both are read,
    with their lineage stated. What is refused is a feed that belongs
    somewhere else.
    """
    binding = feed_binding(manifest, records)
    if binding['status'] == 'foreign':
        raise FeedBindingError(
            f'{feed} belongs to another crawl: '
            f'{binding["foreign"]} of {binding["records"]} records name '
            f'{", ".join(sorted(binding["foreign_runs"]))} rather than '
            f'{manifest.get("run_id")}. Pass the feed this run wrote.')
    if binding['other_marketplace']:
        raise FeedBindingError(
            f'{feed} holds {binding["other_marketplace"]} records from '
            f'another marketplace than {manifest.get("marketplace")}.')
    return binding


# ---------------------------------------------------------------------------
# Re-extracting a finished run
# ---------------------------------------------------------------------------

# What a record knows that its page does not. A stored page says everything
# about the product and nothing about the crawl: which query found it, where
# it ranked, when it was fetched. Those come from the feed the crawl wrote,
# and are copied across verbatim rather than guessed at.
CRAWL_FIELDS = ('marketplace', 'asin', 'product_url', 'canonical_url',
                'search_query', 'search_page', 'search_position', 'sponsored',
                'run_id', 'locale', 'accept_language')


def sighting_sponsored(asin, crawled, discovery, seeds=()):
    """Was the search slot that queued this page's fetch a sponsored one?

    ``None`` -- unknown, not false -- for a seeded ASIN, which came from the
    person who named it and not from a search, and for a page no sighting in
    the discovery log explains. Otherwise the sighting that matches the
    record's own query, page and position; failing that, the first sighting
    of the ASIN, which is the one that queued the request. A feed written
    before 2026-09-19 has no ``sponsored`` field, and this is how a replay
    of those runs gets it from the crawl's own log rather than leaving it
    blank.
    """
    crawled = crawled or {}
    seeded = str(crawled.get('search_query') or '').startswith('asin:') \
        or crawled.get('search_page') == 0
    if seeded or (not crawled and asin in seeds):
        return None
    sightings = [o for o in discovery or () if o.get('asin') == asin]
    if crawled:
        exact = [o for o in sightings
                 if (o.get('query'), o.get('search_page'), o.get('position'))
                 == (crawled.get('search_query'), crawled.get('search_page'),
                     crawled.get('search_position'))]
        if exact:
            return bool(exact[0].get('sponsored'))
    if sightings:
        return bool(sightings[0].get('sponsored'))
    return None


def observation_time(entry, crawled):
    """``(fetched_at, source)`` for one replayed page.

    The run's own page index is preferred over the feed because it is written
    at the moment of the fetch, by the code that did it. The feed is the
    fallback, and it agrees to the second by construction.

    There is deliberately no third fallback. Re-extraction used to stamp a
    page with its file's mtime, which is not a property of the observation at
    all: copying a study bundle, restoring it from an archive or checking it
    out somewhere else rewrites every one of them, and a merge across crawls
    would then believe the copy was the freshest evidence in the study. A page
    with no recorded fetch time has **unknown** freshness, and says so.
    """
    if entry and entry.get('fetched_at'):
        return entry['fetched_at'], 'page_index'
    if crawled and crawled.get('fetched_at'):
        return crawled['fetched_at'], 'feed'
    return None, 'unknown'


def _lineage(asin, manifest, crawled, canonical_url, entry, discovery=()):
    """The provenance a re-extracted record carries, best available first."""
    marketplace = manifest.get('marketplace') or ''
    locale = manifest.get('locale') or {}
    fetched_at, source = observation_time(entry, crawled)
    lineage = {
        'marketplace': marketplace,
        'asin': asin,
        'product_url': f'https://{marketplace}/dp/{asin}',
        'canonical_url': canonical_url or f'https://{marketplace}/dp/{asin}',
        'run_id': manifest.get('run_id') or '',
        'locale': locale.get('language') or '',
        'accept_language': locale.get('accept_language') or '',
    }
    # The crawl's own record wins wherever it has something to say: it is the
    # only witness to the search that found this page.
    lineage.update({key: crawled[key] for key in CRAWL_FIELDS
                    if key in (crawled or {})})
    if 'sponsored' not in lineage:
        lineage['sponsored'] = sighting_sponsored(
            asin, crawled, discovery,
            seeds=(manifest.get('arguments') or {}).get('asin') or ())
    lineage['fetched_at'] = fetched_at
    lineage['fetched_at_source'] = source
    # A new reading of old bytes is not a new observation of the product, and
    # a merge has to be able to tell them apart. Absent on a record written by
    # the crawl that fetched it.
    lineage['extracted_at'] = _utc_now().isoformat()
    return lineage


def reextract(directory, feed=None, verify=True, include_quarantined=True):
    """Re-extract every page a run retained, with today's extractor.

    Yields ``(asin, record, error)`` per stored page, in ASIN order, and
    touches no network. ``error`` is a string on the pages that could not be
    read, could not be parsed, or no longer match the digest the run recorded
    for them; ``None`` otherwise. Block-level failures are not errors here --
    the extractor reports those inside the record, in ``extraction.errors``,
    and the record is still worth writing.

    ``feed`` is the JSONL the crawl wrote. It is optional, and supplying it is
    the difference between a record that knows which query found it and one
    that does not. Supplying the *wrong* one raises
    :class:`FeedBindingError` rather than quietly grafting another crawl's
    search context onto these pages.
    """
    from parsel import Selector

    from .extraction import PdpExtractor, for_domain

    directory = pathlib.Path(directory)
    manifest = load_manifest(directory)
    extractor = PdpExtractor(for_domain(manifest['marketplace']))
    records = read_jsonl(feed) if feed else []
    if feed:
        check_feed_binding(manifest, records, feed)
    crawled = {record['asin']: record for record in records
               if record.get('asin')}

    index = page_metadata(directory)
    discovery = load_discovery(directory)
    pages = dict(stored_pages(directory))
    if include_quarantined:
        pages.update(quarantined_pages(directory))

    for asin in sorted(pages):
        path = pages[asin]
        entry = index.get(asin)
        try:
            html = read_page(path)
            if verify and entry and entry.get('redacted_sha256'):
                digest = sha256_text(html)
                if digest != entry['redacted_sha256']:
                    raise ValueError(
                        f'stored page does not match the digest this run '
                        f'recorded for it ({digest[:12]}… != '
                        f'{entry["redacted_sha256"][:12]}…)')
            selector = Selector(html)
            lineage = _lineage(
                asin, manifest, crawled.get(asin),
                selector.css('link[rel=canonical]::attr(href)').get(), entry,
                discovery)
            record = extractor.extract(selector, html, lineage)
        except Exception as exc:  # one unreadable page must not end the pass
            yield asin, None, f'{type(exc).__name__}: {exc}'
        else:
            yield asin, record, None


def reextract_command(args):
    """``reextract <run_dir> -o new.jsonl [--feed old.jsonl]``."""
    manifest = load_manifest(args.run_dir)
    state = run_state(manifest)
    if state != 'complete':
        print(f'  {args.run_dir}: this run is {state}'
              + (' — it has no recorded page metadata, so replayed records '
                 'carry unknown fetch times' if state == 'legacy' else
                 ' — it never closed its manifest, so its coverage is partial'))

    feed = read_jsonl(args.feed) if args.feed else []
    known = {record['asin'] for record in feed if record.get('asin')}
    if args.feed:
        # Checked before the output file is opened: the wrong feed must not
        # cost the caller the file they were writing into.
        binding = check_feed_binding(manifest, feed, args.feed)
        if binding['status'] in ('mixed', 'legacy'):
            print(f'  {args.feed}: {binding["status"]} lineage — '
                  f'{binding["bound"]} of {binding["records"]} records name '
                  f'this run, {binding["legacy"]} name no run at all')

    quarantined = quarantined_pages(args.run_dir)
    if quarantined:
        print(f'  {len(quarantined)} page(s) are quarantined: redaction failed, '
              f'so they must not be exported or promoted — '
              + ', '.join(sorted(quarantined)[:6]))

    opener = gzip.open if args.output.endswith('.gz') else open
    pages = records = block_errors = undated = 0
    failed, unseen = [], []
    with opener(args.output, 'wt', encoding='utf-8') as out:
        for asin, record, error in reextract(args.run_dir, args.feed):
            pages += 1
            if error is not None:
                failed.append(f'{asin} — {error}')
                continue
            records += 1
            block_errors += len(record['extraction']['errors'])
            if record.get('fetched_at_source') == 'unknown':
                undated += 1
            if args.feed and asin not in known:
                unseen.append(asin)
            out.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f'{args.run_dir}: {pages} pages, {records} records, '
          f'{block_errors} extraction errors -> {args.output}')
    if undated:
        print(f'  {undated} record(s) have no recorded fetch time. Their '
              f'freshness is unknown and they must not be read as current.')
    if unseen:
        print(f'  {len(unseen)} pages had no record in {args.feed}, so they '
              f'carry the run\'s provenance but not a search query: '
              + ', '.join(unseen[:6]) + ('…' if len(unseen) > 6 else ''))
    for line in failed[:10]:
        print(f'  unreadable: {line}')
    if len(failed) > 10:
        print(f'  … and {len(failed) - 10} more unreadable pages')
    return 1 if failed else 0


def inspect_command(args):
    """``inspect <run_dir>`` -- what this run did, and what it left unfinished."""
    manifest = load_manifest(args.run_dir)
    state = run_state(manifest)
    code = manifest.get('code') or {}
    print(f'{manifest.get("run_id")}  [{state}]')
    print(f'  spider        {manifest.get("spider")} on '
          f'{manifest.get("marketplace")}')
    print(f'  started       {manifest.get("started_at")}'
          + (f' · finished {manifest["finished_at"]} '
             f'({manifest.get("finish_reason")})'
             if manifest.get('finished_at') else ' · never closed'))
    print(f'  code          {code.get("git_revision") or "unknown revision"}'
          + (' (dirty tree)' if code.get('git_dirty') else '')
          + f' · schema {code.get("extraction_schema_version")}'
            f' · contract {code.get("validated_contract_version")}')
    print(f'  locale        {(manifest.get("locale") or {}).get("status")}'
          f' · {(manifest.get("locale") or {}).get("accept_language") or "unset"}')
    for binding in manifest.get('feeds') or []:
        print(f'  feed          {binding.get("uri")}')
    counts = manifest.get('counts') or {}
    print('  counts        ' + ', '.join(f'{key} {value}' for key, value
                                         in sorted(counts.items())))
    stats = manifest.get('stats') or {}
    challenges = {key: value for key, value in stats.items()
                  if key.startswith('amazon/challenge')
                  or key.startswith('amazon/http_error')
                  or key == 'amazon/pdp_parse_failed'}
    if challenges:
        print('  trouble       ' + ', '.join(f'{key} {value}' for key, value
                                             in sorted(challenges.items())))
    samples = failure_samples(args.run_dir)
    for entry in samples:
        print(f'  failure       {entry.get("reason")} '
              f'{entry.get("asin") or ""} -> {entry.get("path")}'
              + (' (truncated)' if entry.get('truncated') else ''))
    quarantined = quarantined_pages(args.run_dir)
    if quarantined:
        print(f'  quarantined   {len(quarantined)} page(s): redaction failed, '
              f'not exportable')
    if state == 'legacy':
        print('  NOTE          written before run provenance existed: no page '
              'digests, no recorded fetch times, no feed bindings.')
    elif state == 'interrupted':
        print('  NOTE          the manifest was never closed. Treat coverage '
              'as partial and read discovery.jsonl for what was sighted.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='shopping_advisor.run',
        description='Work with the evidence a finished crawl left behind.')
    commands = parser.add_subparsers(dest='command', required=True)

    reextraction = commands.add_parser(
        'reextract', help='re-extract a run\'s retained pages, offline')
    reextraction.add_argument('run_dir', help='data/runs/<run_id>')
    reextraction.add_argument('-o', '--output', required=True,
                              help='JSONL to write; .gz is compressed')
    reextraction.add_argument('--feed', default='',
                              help='the JSONL this run wrote, so the new '
                                   'records keep the search query, position '
                                   'and fetch time only the crawl knew')
    reextraction.set_defaults(handler=reextract_command)

    inspection = commands.add_parser(
        'inspect', help='what a run did, how it ended, and what it retained')
    inspection.add_argument('run_dir', help='data/runs/<run_id>')
    inspection.set_defaults(handler=inspect_command)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except FeedBindingError as exc:
        print(f'{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
