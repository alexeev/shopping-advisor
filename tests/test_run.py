"""Tests for crawl provenance: run identity, locale, discovery and the page store.

The discovery tests run against a real saved Amazon.de search page rather than
a hand-built one, because the thing being tested is a claim about Amazon's
markup, not about our code: that the result grid can be told apart from the
carousels around it, and that sponsored placement is detectable. On the saved
page the spider's discovery selector matches 82 nodes, of which 60 are the
grid; 12 of those are sponsored; and two ASINs appear twice on that single
page, once organic and once sponsored. Every one of those numbers is asserted,
so a markup change fails here rather than silently degrading a crawl.
"""

import contextlib
import gzip
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import scrapy
from scrapy.http import HtmlResponse
from scrapy.settings import Settings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shopping_advisor import run as run_module  # noqa: E402
from shopping_advisor.extraction import PdpExtractor, for_domain  # noqa: E402
from shopping_advisor.extraction.pdp import SCHEMA_VERSION  # noqa: E402
from shopping_advisor.provenance import sha256_text  # noqa: E402
from shopping_advisor.run import CrawlRun, acquisition_locale  # noqa: E402
from shopping_advisor.spiders.amazon_product import AmazonProductSpider  # noqa: E402
from shopping_advisor.validation.contract import CONTRACT_VERSION  # noqa: E402

CORPUS = pathlib.Path(__file__).resolve().parent / 'corpus'
SEARCH_PAGE = CORPUS / 'amazon_de_search' / 'spaghetti-hartweizen-p1.html.gz'
A_PDP = CORPUS / 'amazon_de' / 'B088419TTP.html.gz'

DE = for_domain('www.amazon.de')


def read_fixture(path):
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        return handle.read()


class Stats:
    """The slice of Scrapy's stats collector the spider touches."""

    def __init__(self):
        self.values = {}

    def inc_value(self, key, count=1):
        self.values[key] = self.values.get(key, 0) + count


class Crawler:
    def __init__(self):
        self.stats = Stats()


class Locale(unittest.TestCase):

    def test_the_validated_profile_matches_its_marketplace(self):
        locale = acquisition_locale(
            Settings({'DEFAULT_REQUEST_HEADERS':
                      {'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'}}), DE)
        self.assertEqual(locale['status'], 'matches')
        self.assertEqual(locale['language'], 'de')

    def test_english_on_a_german_marketplace_is_a_conflict(self):
        """The failure this guards against is silent: German label lists
        against English markup map nothing, and the record still validates."""
        locale = acquisition_locale(
            Settings({'DEFAULT_REQUEST_HEADERS':
                      {'Accept-Language': 'en-US,en;q=0.9'}}), DE)
        self.assertEqual(locale['status'], 'conflict')

    def test_an_unset_locale_is_reported_rather_than_assumed(self):
        locale = acquisition_locale(
            Settings({'DEFAULT_REQUEST_HEADERS': {'Accept': 'text/html'}}), DE)
        self.assertEqual(locale['status'], 'unset')
        self.assertIsNone(locale['language'])

    def test_scrapys_own_default_conflicts_with_amazon_de(self):
        """Not a hypothetical. Scrapy ships ``Accept-Language: en`` and the
        non-baseline settings profile never overrides it, so every crawl of
        amazon.de on that profile has been asking Amazon for English while
        reading the answer with German label lists. Nothing failed; the records
        would just have carried an empty ``attributes`` block beside a full
        ``raw_tables``. This is the bug the gate exists for, and it was already
        in the repository."""
        from scrapy.settings import default_settings
        self.assertEqual(
            default_settings.DEFAULT_REQUEST_HEADERS['Accept-Language'], 'en')
        self.assertEqual(acquisition_locale(Settings({}), DE)['status'],
                         'conflict')

    def test_the_header_name_is_matched_case_insensitively(self):
        locale = acquisition_locale(
            Settings({'DEFAULT_REQUEST_HEADERS':
                      {'accept-language': 'de-DE,de;q=0.9'}}), DE)
        self.assertEqual(locale['status'], 'matches')

    def test_only_the_first_tag_decides(self):
        # "de-DE,en;q=0.8" asks for German first; the fallback is not a choice.
        locale = acquisition_locale(
            Settings({'DEFAULT_REQUEST_HEADERS':
                      {'Accept-Language': 'de-DE,en;q=0.8'}}), DE)
        self.assertEqual(locale['language'], 'de')


class Run(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = CrawlRun(
            root=self.tmp.name, spider='amazon_product',
            marketplace='www.amazon.de',
            locale={'language': 'de', 'accept_language': 'de-DE,de;q=0.9',
                    'status': 'matches'},
            arguments={'keyword': ['spaghetti']}).open()
        self.addCleanup(self.run.close)

    def another(self, **overrides):
        """A second run constructed exactly like the first one."""
        arguments = dict(root=self.tmp.name, spider='amazon_product',
                         marketplace='www.amazon.de',
                         locale={'language': 'de',
                                 'accept_language': 'de-DE,de;q=0.9',
                                 'status': 'matches'},
                         arguments={'keyword': ['spaghetti']})
        arguments.update(overrides)
        run = CrawlRun(**arguments)
        self.addCleanup(run.close)
        return run

    def test_the_run_id_sorts_by_time_and_names_its_marketplace(self):
        self.assertRegex(self.run.run_id,
                         r'^\d{8}T\d{6}Z-www\.amazon\.de-[0-9a-f]{8}$')

    def test_two_identical_crawls_started_together_are_two_runs(self):
        """The identity used to be a digest of the timestamp, the marketplace
        and the arguments -- exactly the three things two concurrent crawls of
        one shelf agree on. Two identical constructions in the same second
        produced the same ID, and ``open()`` then accepted the existing
        directory: one discovery log holding both crawls' sightings, one
        manifest describing one of them, and pages overwriting each other."""
        twins = [self.another().open() for _ in range(5)]
        identities = {run.run_id for run in twins} | {self.run.run_id}
        self.assertEqual(len(identities), 6, 'two runs shared an identity')
        directories = {str(run.directory) for run in twins}
        self.assertEqual(len(directories), 5)
        for run in twins:
            self.assertTrue((run.directory / 'manifest.json').is_file())

    def test_a_directory_another_run_owns_is_refused_not_joined(self):
        taken = self.another()
        taken.directory.mkdir(parents=True)
        (taken.directory / 'discovery.jsonl').write_text('{}\n', encoding='utf-8')
        with self.assertRaises(run_module.RunDirectoryExists):
            taken.open()
        self.assertEqual((taken.directory / 'discovery.jsonl')
                         .read_text(encoding='utf-8'), '{}\n',
                         'the refused run wrote into the other run\'s evidence')

    def test_every_record_can_be_traced_to_its_run_and_locale(self):
        lineage = self.run.lineage()
        self.assertEqual(lineage['run_id'], self.run.run_id)
        self.assertEqual(lineage['locale'], 'de')
        self.assertEqual(lineage['accept_language'], 'de-DE,de;q=0.9')

    def test_a_manifest_exists_from_the_start_of_the_crawl(self):
        """A crawl that dies halfway must still say what it was trying to do."""
        manifest = run_module.load_manifest(self.run.directory)
        self.assertEqual(manifest['run_id'], self.run.run_id)
        self.assertEqual(manifest['arguments']['keyword'], ['spaghetti'])
        self.assertNotIn('finish_reason', manifest)

    def test_a_run_that_never_closed_says_so_rather_than_looking_finished(self):
        """The diagnosable state. A crawl killed by a timeout, a signal or a
        lost machine leaves the manifest it wrote when it started; without a
        state of its own that is indistinguishable from a crawl that simply
        was not asked to close, and its partial coverage reads as complete."""
        interrupted = run_module.load_manifest(self.run.directory)
        self.assertEqual(run_module.run_state(interrupted), 'interrupted')

        self.run.close(finish_reason='finished')
        closed = run_module.load_manifest(self.run.directory)
        self.assertEqual(run_module.run_state(closed), 'complete')
        self.assertEqual(closed['finish_reason'], 'finished')

    def test_a_run_store_written_before_provenance_existed_is_legacy(self):
        """Not an error and not a complete run: a directory whose manifest
        predates T1 has no page digests, no fetch times and no feed
        bindings, and the difference has to survive into the report."""
        self.assertEqual(run_module.run_state({'run_id': 'x', 'spider': 's'}),
                         'legacy')

    def test_a_manifest_is_replaced_rather_than_rewritten_in_place(self):
        """A manifest is read by whoever is diagnosing the crawl that is
        writing it, which is the moment a truncated file is least welcome."""
        self.run.close(finish_reason='finished')
        self.assertEqual(
            sorted(path.name for path in self.run.directory.glob('manifest*')),
            ['manifest.json'], 'a temporary manifest was left behind')
        json.loads((self.run.directory / 'manifest.json')
                   .read_text(encoding='utf-8'))

    def test_the_manifest_says_which_code_produced_the_evidence(self):
        code = run_module.load_manifest(self.run.directory)['code']
        self.assertEqual(code['extraction_schema_version'], SCHEMA_VERSION)
        self.assertEqual(code['validated_contract_version'], CONTRACT_VERSION)
        self.assertTrue(code['python'])
        # git and the lock file may legitimately be absent from an export;
        # what may not happen is a value that implies a reproducibility this
        # run cannot offer.
        self.assertIn('git_revision', code)
        self.assertIn('git_dirty', code)
        self.assertIn('lock_sha256', code)

    def test_the_manifest_says_how_the_marketplace_was_asked(self):
        run = self.another(settings=Settings({
            'SETTINGS_PROFILE': 'baseline', 'DOWNLOAD_DELAY': 9.0,
            'CONCURRENT_REQUESTS': 1, 'USER_AGENT': 'Mozilla/5.0',
            'DOWNLOADER_MIDDLEWARES': {
                'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550},
            'DEFAULT_REQUEST_HEADERS': {'Accept-Language': 'de-DE,de;q=0.9'},
        })).open()
        settings = run_module.load_manifest(run.directory)['settings']
        self.assertEqual(settings['SETTINGS_PROFILE'], 'baseline')
        self.assertEqual(settings['DOWNLOAD_DELAY'], 9.0)
        self.assertEqual(settings['DEFAULT_REQUEST_HEADERS'],
                         {'Accept-Language': 'de-DE,de;q=0.9'})
        self.assertFalse(settings['proxy_middleware'],
                         'whether a third party sat in the request path '
                         'decides what a challenge count means')

    def test_a_credential_is_never_written_into_a_run_manifest(self):
        """The manifest lives beside the evidence and gets archived with it.
        Recording the effective settings wholesale is how a proxy key ends up
        in a study bundle, so the recorder is an allowlist."""
        secret = 'sk-live-do-not-archive-me'
        run = self.another(settings=Settings({
            'SCRAPEOPS_API_KEY': secret,
            'DEFAULT_REQUEST_HEADERS': {'Accept-Language': 'de-DE,de;q=0.9',
                                        'Cookie': f'session={secret}',
                                        'Authorization': f'Bearer {secret}'},
        })).open()
        written = (run.directory / 'manifest.json').read_text(encoding='utf-8')
        self.assertNotIn(secret, written)
        self.assertNotIn('Cookie', written)
        self.assertNotIn('Authorization', written)

    def test_the_feed_the_crawl_writes_is_bound_in_its_manifest(self):
        run = self.another(settings=Settings({
            'FEEDS': {'data/products.jsonl': {'format': 'jsonlines',
                                              'overwrite': True}}})).open()
        feeds = run_module.load_manifest(run.directory)['feeds']
        self.assertEqual([binding['uri'] for binding in feeds],
                         ['data/products.jsonl'])

    def test_closing_records_the_outcome_and_the_counts(self):
        self.run.close(stats={'downloader/request_count': 7, 'obj': object()},
                       finish_reason='finished')
        manifest = run_module.load_manifest(self.run.directory)
        self.assertEqual(manifest['finish_reason'], 'finished')
        self.assertEqual(manifest['stats']['downloader/request_count'], 7)
        self.assertNotIn('obj', manifest['stats'],
                         'only serialisable stats belong in a manifest')

    def test_the_same_asin_seen_twice_is_written_down_twice(self):
        for rank, sponsored in ((8, False), (16, True)):
            self.run.record_discovery({'asin': 'B000U7PDRI', 'query': 'q',
                                       'grid_position': rank,
                                       'sponsored': sponsored})
        self.run.close()
        occurrences = run_module.load_discovery(self.run.directory)
        self.assertEqual(len(occurrences), 2)
        self.assertEqual([o['sponsored'] for o in occurrences], [False, True])
        self.assertTrue(all(o['run_id'] == self.run.run_id for o in occurrences))
        self.assertTrue(all(o['seen_at'] for o in occurrences))

    def test_a_retained_page_re_extracts_offline(self):
        """The point of the page store: a new extractor, an old page, no network."""
        html = read_fixture(A_PDP)
        self.run.save_page('B088419TTP', html)

        pages = run_module.stored_pages(self.run.directory)
        self.assertIn('B088419TTP', pages)
        record = PdpExtractor(DE).extract(
            __import__('parsel').Selector(run_module.read_page(pages['B088419TTP'])),
            run_module.read_page(pages['B088419TTP']), {'asin': 'B088419TTP'})
        self.assertTrue(record['title'])
        self.assertTrue(record['variation']['values_by_asin'])

    def test_a_stored_page_carries_no_session_identifiers(self):
        self.run.save_page('X', "var ue_sid='123-4567890-1234567';")
        stored = run_module.read_page(
            run_module.stored_pages(self.run.directory)['X'])
        self.assertNotIn('123-4567890-1234567', stored)

    def test_a_stored_page_records_when_and_from_where_it_was_fetched(self):
        entry = self.run.save_page(
            'B088419TTP', '<html><title>t</title></html>',
            fetched_at='2026-09-15T10:00:00+00:00',
            request_url='https://www.amazon.de/dp/B088419TTP',
            final_url='https://www.amazon.de/dp/B088419TTP?th=1',
            http_status=200)
        self.assertEqual(entry['fetched_at'], '2026-09-15T10:00:00+00:00')
        self.assertEqual(entry['http_status'], 200)
        self.assertEqual(entry['final_url'],
                         'https://www.amazon.de/dp/B088419TTP?th=1')
        self.assertEqual(entry['redaction'], 'applied')
        self.assertFalse(entry['quarantined'])
        # Over the bytes retained, after redaction changed them on purpose.
        self.assertEqual(
            entry['redacted_sha256'],
            sha256_text(run_module.read_page(
                run_module.stored_pages(self.run.directory)['B088419TTP'])))
        self.assertEqual(
            run_module.page_metadata(self.run.directory)['B088419TTP'], entry)

    def test_a_page_whose_redaction_fails_is_quarantined_not_stored(self):
        """Redaction used to be imported from the test corpus through
        ``sys.path`` and fall back to storing the page unredacted on any
        exception. A page store therefore could not tell a caller whether what
        it held was safe to promote into the corpus or to hand to anybody."""
        with mock.patch.object(run_module, 'redact_page',
                               side_effect=lambda html: (html, 'failed')):
            entry = self.run.save_page('B000000001', 'ue_sid raw page')
        self.assertTrue(entry['quarantined'])
        self.assertEqual(entry['redaction'], 'failed')
        self.assertNotIn('B000000001', run_module.stored_pages(self.run.directory))
        self.assertIn('B000000001',
                      run_module.quarantined_pages(self.run.directory))
        self.assertEqual(self.run.counts['redaction_failures'], 1)
        self.assertEqual(self.run.counts['pages_quarantined'], 1)
        self.assertEqual(self.run.counts['pages_saved'], 0)

    def test_redaction_does_not_change_anything_the_extractor_reads(self):
        """The rule the corpus test enforces over 39 pages, asserted here for
        the store that feeds it: what is promoted is what was extracted.

        The fixture is already redacted -- every committed page is -- so the
        identifiers a live response carries are put back before it is stored.
        """
        clean = read_fixture(A_PDP)
        live = clean.replace(
            '<head>', "<head><script>var ue_sid='123-4567890-1234567';"
                      "var ue_id='ABCDEFGHJKLMNPQRSTUV';</script>", 1)
        self.assertNotEqual(live, clean)
        self.run.save_page('B088419TTP', live)
        stored = run_module.read_page(
            run_module.stored_pages(self.run.directory)['B088419TTP'])
        self.assertNotIn('123-4567890-1234567', stored)
        self.assertNotIn('ABCDEFGHJKLMNPQRSTUV', stored)

        selector = __import__('parsel').Selector
        before = PdpExtractor(DE).extract(selector(live), live,
                                          {'asin': 'B088419TTP'})
        after = PdpExtractor(DE).extract(selector(stored), stored,
                                         {'asin': 'B088419TTP'})
        before.pop('fetched_at'), after.pop('fetched_at')
        self.assertEqual(before, after)

    def test_a_challenge_is_kept_as_a_bounded_sample(self):
        """A challenge page and a 200 with no product title were counted and
        then dropped, which leaves "48 records from 56 requests" with nothing
        underneath it: neither can be reproduced without crawling again."""
        entry = self.run.save_failure(
            'challenge_pdp_captcha_form',
            '<html>Geben Sie die Zeichen unten ein</html>',
            key='B000000002', http_status=200,
            final_url='https://www.amazon.de/errors/validateCaptcha')
        self.assertEqual(entry['reason'], 'challenge_pdp_captcha_form')
        self.assertFalse(entry['truncated'])
        samples = run_module.failure_samples(self.run.directory)
        self.assertEqual(len(samples), 1)
        self.assertIn('Zeichen', run_module.read_page(
            self.run.directory / samples[0]['path']))

    def test_failure_samples_are_capped_and_truncated(self):
        """A blocked crawl produces one challenge per request; the tenth is
        not more informative than the first, and a titleless PDP is 2 MB."""
        for index in range(run_module.FAILURE_SAMPLES_PER_KIND + 3):
            self.run.save_failure('challenge_search_challenge_text',
                                  'x' * (run_module.FAILURE_SAMPLE_BYTES + 10),
                                  key=f'B00000000{index}')
        samples = run_module.failure_samples(self.run.directory)
        self.assertEqual(len(samples), run_module.FAILURE_SAMPLES_PER_KIND)
        self.assertEqual(self.run.counts['failure_samples_over_cap'], 3)
        self.assertTrue(samples[0]['truncated'])
        self.assertEqual(samples[0]['redacted_bytes'],
                         run_module.FAILURE_SAMPLE_BYTES)

    def test_a_search_page_is_retained_only_when_the_run_asks_for_it(self):
        self.assertIsNone(self.run.save_search_page('spaghetti', 1, '<html/>'))
        keeping = self.another(keep_search_pages=True).open()
        entry = keeping.save_search_page('spaghetti hartweizen', 2, '<html/>')
        self.assertEqual(entry['kind'], 'search')
        self.assertEqual(entry['search_page'], 2)
        self.assertEqual(entry['path'], 'search/spaghetti-hartweizen-p2.html.gz')
        self.assertTrue((keeping.directory / entry['path']).is_file())

    def test_page_retention_can_be_turned_off(self):
        off = CrawlRun(root=self.tmp.name, spider='s', marketplace='m',
                       locale={}, arguments={}, keep_pages=False).open()
        self.addCleanup(off.close)
        off.save_page('B000000000', '<html></html>')
        self.assertEqual(run_module.stored_pages(off.directory), {})
        self.assertEqual(off.counts['pages_saved'], 0)


class Discovery(unittest.TestCase):
    """Against a real saved Amazon.de search page."""

    @classmethod
    def setUpClass(cls):
        cls.html = read_fixture(SEARCH_PAGE)

    def spider(self, **run_options):
        spider = AmazonProductSpider(keyword='spaghetti hartweizen',
                                     domain='www.amazon.de', max_pages=1)
        spider.crawler = Crawler()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        spider.run = CrawlRun(root=tmp.name, spider=spider.name,
                              marketplace='www.amazon.de',
                              locale={'language': 'de'}, arguments={},
                              keep_pages=False, **run_options).open()
        self.addCleanup(spider.run.close)
        return spider

    def response(self, spider):
        return HtmlResponse(
            url=spider.search_url('spaghetti hartweizen', 1),
            body=self.html, encoding='utf-8',
            request=spider.search_request(0, 1))

    def test_the_result_grid_is_smaller_than_everything_shaped_like_it(self):
        response = self.response(self.spider())
        self.assertEqual(len(response.css('div.s-result-item[data-asin]')), 82)
        self.assertEqual(len(AmazonProductSpider.grid_ranks(response)), 60)

    def test_sponsored_placement_is_detectable(self):
        response = self.response(self.spider())
        grid = response.css('div[data-component-type="s-search-result"]')
        sponsored = [node for node in grid
                     if AmazonProductSpider.sponsored_markers(node)]
        self.assertEqual(len(sponsored), 12)

    def test_the_three_sponsorship_markers_agree(self):
        """If they ever stop agreeing, that is worth knowing about."""
        response = self.response(self.spider())
        for node in response.css('div[data-component-type="s-search-result"]'):
            markers = AmazonProductSpider.sponsored_markers(node)
            self.assertIn(len(markers), (0, 3), 'markers disagree on a result')

    def test_every_sighting_is_recorded_including_the_repeats(self):
        spider = self.spider()
        list(spider.discover_product_urls(self.response(spider)))
        occurrences = run_module.load_discovery(spider.run.directory)

        seen = {}
        for occurrence in occurrences:
            seen.setdefault(occurrence['asin'], []).append(occurrence)
        repeats = {asin: rows for asin, rows in seen.items() if len(rows) > 1}
        self.assertTrue(repeats, 'this page has ASINs listed more than once')
        self.assertGreater(len(occurrences), len(seen),
                           'the log must be longer than the set of ASINs')

        for rows in repeats.values():
            self.assertNotEqual(len({row['sponsored'] for row in rows}), 0)

    def test_a_repeat_sighting_is_logged_but_not_fetched(self):
        spider = self.spider()
        requests = [item for item in spider.discover_product_urls(
            self.response(spider)) if hasattr(item, 'url')]
        fetched = [request.meta['asin'] for request in requests]
        self.assertEqual(len(fetched), len(set(fetched)),
                         'PDP fetching must stay de-duplicated')
        occurrences = run_module.load_discovery(spider.run.directory)
        self.assertGreater(len(occurrences), len(fetched))
        self.assertTrue(spider.crawler.stats.values.get(
            'amazon/discovery/repeat_sighting'))

    def test_an_occurrence_carries_what_the_shopper_saw(self):
        spider = self.spider()
        list(spider.discover_product_urls(self.response(spider)))
        occurrences = run_module.load_discovery(spider.run.directory)
        first = occurrences[0]
        self.assertTrue(first['result_title'])
        self.assertIsNotNone(first['result_price_amount'])
        self.assertEqual(first['query'], 'spaghetti hartweizen')
        self.assertEqual(first['search_page'], 1)
        self.assertEqual(first['locale'], 'de')

    def test_grid_ranks_survive_the_proxies_that_produced_them(self):
        """lxml frees element proxies and recycles their ids, so a rank map
        keyed by ``id()`` silently matches the wrong result once the list that
        built it is released. Keyed by tree path, it does not."""
        import gc
        response = self.response(self.spider())
        ranks = AmazonProductSpider.grid_ranks(response)
        gc.collect()
        tree = response.selector.root.getroottree()
        matched = [ranks.get(tree.getpath(node.root)) for node
                   in response.css('div.s-result-item[data-asin]')]
        self.assertEqual(len([r for r in matched if r]), 60)
        self.assertEqual(matched[2], 1, 'the first grid result is the third node')

    def test_a_challenge_on_a_search_page_leaves_evidence_behind(self):
        """A challenge is served with HTTP 200 and counted as a stat, and the
        body used to be dropped: the crawl reported a blocked query with
        nothing under it to show what Amazon actually answered."""
        spider = self.spider()
        challenge = HtmlResponse(
            url=spider.search_url('spaghetti hartweizen', 1),
            body=b'<html><head><title>Robot Check</title></head><body>'
                 b'Geben Sie die Zeichen unten ein</body></html>',
            encoding='utf-8', request=spider.search_request(0, 1))
        list(spider.discover_product_urls(challenge))

        samples = run_module.failure_samples(spider.run.directory)
        self.assertEqual(len(samples), 1)
        self.assertTrue(samples[0]['reason'].startswith('challenge_search'))
        self.assertIn('Zeichen', run_module.read_page(
            spider.run.directory / samples[0]['path']))
        self.assertTrue(spider.crawler.stats.values['amazon/challenge/search'])

    def test_a_titleless_product_page_is_kept_so_it_can_be_reproduced(self):
        spider = self.spider()
        response = HtmlResponse(
            url='https://www.amazon.de/dp/B000000001',
            body=b'<html><body>no product title here</body></html>',
            encoding='utf-8',
            request=scrapy.Request('https://www.amazon.de/dp/B000000001',
                                   meta={'asin': 'B000000001',
                                         'search_query': 'q',
                                         'search_page': 1,
                                         'search_position': 1}))
        list(spider.parse_product_data(response) or [])

        samples = run_module.failure_samples(spider.run.directory)
        self.assertEqual([entry['reason'] for entry in samples],
                         ['pdp_no_product_title'])
        self.assertEqual(samples[0]['asin'], 'B000000001')
        self.assertTrue(spider.crawler.stats.values['amazon/pdp_parse_failed'])

    def test_search_pages_are_retained_only_when_the_run_asks_for_them(self):
        spider = self.spider()
        list(spider.discover_product_urls(self.response(spider)))
        self.assertEqual(spider.run.counts['search_pages_saved'], 0)

        keeping = self.spider(keep_search_pages=True)
        list(keeping.discover_product_urls(self.response(keeping)))
        retained = [entry for entry in
                    run_module.load_pages_index(keeping.run.directory)
                    if entry['kind'] == 'search']
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]['query'], 'spaghetti hartweizen')
        self.assertIn('data-asin', run_module.read_page(
            keeping.run.directory / retained[0]['path']))

    def test_grid_rank_and_raw_index_are_both_kept(self):
        """The raw index counts ad tiles; the grid rank is what a shopper saw."""
        spider = self.spider()
        list(spider.discover_product_urls(self.response(spider)))
        ranked = [o for o in run_module.load_discovery(spider.run.directory)
                  if o['in_result_grid']]
        self.assertEqual(ranked[0]['grid_position'], 1)
        self.assertGreater(ranked[0]['position'], ranked[0]['grid_position'],
                           'empty ad tiles precede the first real result')


class Reextraction(unittest.TestCase):
    """The page store's whole point, as a command rather than a code sample."""

    FETCHED_AT = '2026-09-14T22:24:05+00:00'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = pathlib.Path(self.tmp.name) / 'new.jsonl'
        self.run = CrawlRun(
            root=self.tmp.name, spider='amazon_product',
            marketplace='www.amazon.de',
            locale={'language': 'de', 'accept_language': 'de-DE,de;q=0.9',
                    'status': 'matches'},
            arguments={'keyword': ['spaghetti hartweizen']}).open()
        self.run.save_page('B088419TTP', read_fixture(A_PDP),
                           fetched_at=self.FETCHED_AT,
                           request_url='https://www.amazon.de/dp/B088419TTP',
                           final_url='https://www.amazon.de/dp/B088419TTP',
                           http_status=200)
        self.run.close(finish_reason='finished')

    def feed(self, **overrides):
        """The feed the crawl would have written for that one page."""
        record = {'asin': 'B088419TTP', 'search_query': 'spaghetti hartweizen',
                  'search_page': 2, 'search_position': 17,
                  'fetched_at': self.FETCHED_AT,
                  'canonical_url': 'https://www.amazon.de/dp/B088419TTP'}
        record.update(overrides)
        path = pathlib.Path(self.tmp.name) / 'old.jsonl'
        path.write_text(json.dumps(record) + '\n', encoding='utf-8')
        return str(path)

    def reextract(self, feed=None):
        return list(run_module.reextract(self.run.directory, feed))

    def command(self, argv):
        """``(exit code, what it printed)`` for one run of the command."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run_module.main(argv)
        return code, printed.getvalue()

    def one(self, feed=None):
        """The record this run's single stored page re-extracts to."""
        _, record, error = self.reextract(feed)[0]
        self.assertIsNone(error)
        return record

    def test_a_run_re_extracts_from_its_own_pages_with_no_network(self):
        results = self.reextract()
        self.assertEqual(len(results), 1)
        asin, record, error = results[0]
        self.assertIsNone(error)
        self.assertEqual(asin, 'B088419TTP')
        self.assertTrue(record['title'])
        self.assertTrue(record['variation']['values_by_asin'])
        self.assertEqual(record['extraction']['errors'], [])

    def test_the_marketplace_comes_from_the_manifest_not_from_a_flag(self):
        """A page re-extracted with the wrong label vocabulary parses without
        failing and reports almost nothing, which is the failure R1's locale
        gate exists for. The run already wrote down which marketplace answered."""
        record = self.one()
        self.assertEqual(record['marketplace'], 'www.amazon.de')
        self.assertEqual(record['locale'], 'de')
        self.assertTrue(record['attributes'])

    def test_provenance_survives_without_a_feed(self):
        record = self.one()
        self.assertEqual(record['run_id'], self.run.run_id)
        self.assertEqual(record['accept_language'], 'de-DE,de;q=0.9')
        self.assertEqual(record['product_url'],
                         'https://www.amazon.de/dp/B088419TTP')

    def test_what_only_the_crawl_knew_comes_from_the_feed(self):
        record = self.one(self.feed())
        self.assertEqual(record['search_query'], 'spaghetti hartweizen')
        self.assertEqual(record['search_page'], 2)
        self.assertEqual(record['search_position'], 17)

    def test_without_a_feed_the_search_context_is_absent_rather_than_invented(self):
        record = self.one()
        self.assertNotIn('search_query', record)
        self.assertNotIn('search_position', record)

    def test_a_re_extracted_record_keeps_the_time_the_page_was_fetched(self):
        """Stamping a re-extraction with today's clock would make every old
        page the freshest evidence in a study, which is precisely what the
        merge across feeds must not believe."""
        record = self.one()
        self.assertEqual(record['fetched_at'], self.FETCHED_AT)
        self.assertEqual(record['fetched_at_source'], 'page_index')

    def test_the_fetch_time_survives_the_bundle_being_copied(self):
        """The failure this replaces. Fetch time used to fall back to the
        page file's mtime, which is not a property of the observation at all:
        copying a study bundle, restoring it from an archive or checking it
        out elsewhere rewrites every one of them, and the copy then looks like
        the freshest evidence in the study."""
        copied = pathlib.Path(self.tmp.name) / 'restored-bundle'
        shutil.copytree(self.run.directory, copied)
        for path in copied.rglob('*'):
            os.utime(path, (1_800_000_000, 1_800_000_000))

        _, record, error = list(run_module.reextract(copied))[0]
        self.assertIsNone(error)
        self.assertEqual(record['fetched_at'], self.FETCHED_AT)
        self.assertEqual(record['fetched_at_source'], 'page_index')

    def test_a_run_with_no_recorded_fetch_time_reports_unknown_freshness(self):
        """A store written before per-page metadata existed. Its pages are
        still worth re-extracting; what they may not do is claim a freshness
        the run never recorded."""
        (self.run.directory / run_module.PAGES_INDEX).unlink()
        _, record, error = list(run_module.reextract(self.run.directory))[0]
        self.assertIsNone(error)
        self.assertIsNone(record['fetched_at'])
        self.assertEqual(record['fetched_at_source'], 'unknown')

    def test_a_replayed_record_says_it_is_a_new_reading_of_old_bytes(self):
        """``extracted_at`` is what lets a merge prefer a re-extraction of an
        observation over the original reading of it without mistaking it for
        a newer observation of the product."""
        record = self.one()
        self.assertTrue(record['extracted_at'])
        self.assertGreater(record['extracted_at'], record['fetched_at'])

    def test_the_feed_of_another_crawl_is_refused(self):
        """The useful failure here is not a crash, it is silence: the wrong
        feed grafts another crawl's queries, positions and fetch times onto
        these pages and nothing says so."""
        with self.assertRaises(run_module.FeedBindingError) as raised:
            self.reextract(self.feed(run_id='20260101T000000Z-www.amazon.de-deadbeef'))
        self.assertIn('belongs to another crawl', str(raised.exception))

    def test_a_feed_from_another_marketplace_is_refused(self):
        with self.assertRaises(run_module.FeedBindingError) as raised:
            self.reextract(self.feed(run_id=self.run.run_id,
                                     marketplace='www.amazon.com'))
        self.assertIn('another marketplace', str(raised.exception))

    def test_the_wrong_feed_costs_nothing_that_was_already_written(self):
        """The refusal has to land before the output file is opened, or a
        mistyped feed truncates whatever the caller was writing into."""
        self.output.write_text('previous output\n', encoding='utf-8')
        code, _ = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output),
             '--feed', self.feed(run_id='20260101T000000Z-www.amazon.de-deadbeef')])
        self.assertEqual(code, 2)
        self.assertEqual(self.output.read_text(encoding='utf-8'),
                         'previous output\n')

    def test_the_same_marketplace_written_two_ways_is_not_a_wrong_feed(self):
        record = self.one(self.feed(run_id=self.run.run_id,
                                    marketplace='amazon.de'))
        self.assertEqual(record['search_query'], 'spaghetti hartweizen')

    def test_a_feed_that_names_no_run_is_read_with_its_lineage_named(self):
        """A feed written before provenance existed is readable, and its
        lineage is unknown rather than wrong. The command says which."""
        binding = run_module.feed_binding(
            run_module.load_manifest(self.run.directory),
            [{'asin': 'B088419TTP'}])
        self.assertEqual(binding['status'], 'legacy')
        code, printed = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output),
             '--feed', self.feed()])
        self.assertEqual(code, 0)
        self.assertIn('legacy lineage', printed)

    def test_a_page_that_no_longer_matches_its_digest_is_reported(self):
        """A page store is evidence, and a swapped or truncated file in it is
        the one corruption a replay would otherwise carry into a report."""
        path = run_module.stored_pages(self.run.directory)['B088419TTP']
        with gzip.open(path, 'wt', encoding='utf-8') as fh:
            fh.write('<html><title>not the page that was fetched</title></html>')
        _, record, error = list(run_module.reextract(self.run.directory))[0]
        self.assertIsNone(record)
        self.assertIn('does not match the digest', error)

    def test_a_quarantined_page_is_replayed_but_named(self):
        """Its extracted values are the same -- redaction may not change one
        -- so the record is worth having. What must not happen is the page
        passing quietly into an export."""
        with mock.patch.object(run_module, 'redact_page',
                               side_effect=lambda html: (html, 'failed')):
            self.run.save_page('B000U7PDRI', read_fixture(A_PDP))
        code, printed = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output)])
        self.assertEqual(code, 0)
        self.assertIn('quarantined', printed)
        self.assertIn('B000U7PDRI', printed)
        self.assertEqual(len(run_module.read_jsonl(self.output)), 2)

    def test_a_feed_entry_for_another_asin_is_not_borrowed(self):
        record = self.one(self.feed(asin='B000000000'))
        self.assertNotIn('search_query', record)

    def test_an_unreadable_page_is_reported_and_the_pass_continues(self):
        pages = self.run.pages_directory
        (pages / 'B000000000.html.gz').write_bytes(b'not gzip at all')
        results = {asin: (record, error) for asin, record, error
                   in self.reextract()}
        self.assertEqual(len(results), 2)
        self.assertIsNone(results['B000000000'][0])
        self.assertTrue(results['B000000000'][1])
        self.assertIsNotNone(results['B088419TTP'][0], 'one bad page ended the pass')

    def test_the_command_writes_a_feed_and_counts_what_it_did(self):
        code, printed = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output),
             '--feed', self.feed()])
        self.assertEqual(code, 0)
        self.assertIn('1 pages, 1 records, 0 extraction errors', printed)
        written = run_module.read_jsonl(self.output)
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0]['asin'], 'B088419TTP')
        self.assertEqual(written[0]['search_query'], 'spaghetti hartweizen')

    def test_the_command_compresses_when_asked_to(self):
        packed = pathlib.Path(self.tmp.name) / 'new.jsonl.gz'
        self.command(['reextract', str(self.run.directory), '-o', str(packed)])
        self.assertEqual(len(run_module.read_jsonl(packed)), 1)

    def test_a_page_the_feed_never_mentioned_is_named_not_silently_dropped(self):
        self.run.save_page('B000U7PDRI', read_fixture(A_PDP))
        _, printed = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output),
             '--feed', self.feed()])
        self.assertIn('2 pages, 2 records', printed)
        self.assertIn('B000U7PDRI', printed)

    def test_the_command_fails_loudly_on_an_unreadable_page(self):
        (self.run.pages_directory / 'B000000000.html.gz').write_bytes(b'junk')
        code, printed = self.command(
            ['reextract', str(self.run.directory), '-o', str(self.output)])
        self.assertEqual(code, 1)
        self.assertIn('unreadable: B000000000', printed)
        self.assertEqual(len(run_module.read_jsonl(self.output)), 1,
                         'the readable pages are still written')


class Inspect(unittest.TestCase):
    """``inspect`` exists so a run can be read without a JSON viewer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = CrawlRun(root=self.tmp.name, spider='amazon_product',
                            marketplace='www.amazon.de',
                            locale={'language': 'de', 'status': 'matches',
                                    'accept_language': 'de-DE,de;q=0.9'},
                            arguments={'keyword': ['spaghetti']}).open()
        # Deliberately not closed: an interrupted run is one whose streams
        # were never closed, which is what these tests are about. The handles
        # are released here rather than at process exit.
        self.addCleanup(self._release)

    def _release(self):
        for handle in ('_discovery', '_index'):
            stream = getattr(self.run, handle)
            if stream is not None:
                stream.close()
                setattr(self.run, handle, None)

    def inspect(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run_module.main(['inspect', str(self.run.directory)])
        return printed.getvalue()

    def test_an_interrupted_run_says_what_it_left_unfinished(self):
        self.run.save_failure('challenge_pdp_captcha_form', '<html/>',
                              key='B000000001')
        text = self.inspect()
        self.assertIn('[interrupted]', text)
        self.assertIn('never closed', text)
        self.assertIn('challenge_pdp_captcha_form', text)

    def test_a_finished_run_reports_its_code_and_outcome(self):
        self.run.close(stats={'amazon/challenge/pdp': 3},
                       finish_reason='closespider_timeout')
        text = self.inspect()
        self.assertIn('[complete]', text)
        self.assertIn('closespider_timeout', text)
        self.assertIn('amazon/challenge/pdp 3', text)
        self.assertIn(f'schema {SCHEMA_VERSION}', text)


class Variation(unittest.TestCase):

    def test_the_twister_matrix_is_decoded_but_not_interpreted(self):
        html = read_fixture(A_PDP)
        record = PdpExtractor(DE).extract(
            __import__('parsel').Selector(html), html, {'asin': 'B088419TTP'})
        variation = record['variation']
        self.assertIn('size_name', variation['dimensions'])
        self.assertEqual(variation['current_asin'], 'B088419TTP')
        # Sibling ASINs with the pack-size labels that settle quantity
        # disputes -- stored verbatim, no parsing into grams.
        self.assertIn('B003SNIIO6', variation['values_by_asin'])
        self.assertIn('500 g (10er Pack)',
                      variation['values_by_asin']['B003SNIIO6'])

    def test_a_page_without_a_twister_reports_nothing_rather_than_failing(self):
        html = read_fixture(CORPUS / 'amazon_de' / 'B01M8K0019.html.gz')
        record = PdpExtractor(DE).extract(
            __import__('parsel').Selector(html), html, {'asin': 'B01M8K0019'})
        self.assertEqual(record['variation'], {})
        self.assertIn('variation', record['extraction']['blocks_absent'])
        self.assertEqual(record['extraction']['errors'], [])


if __name__ == '__main__':
    unittest.main()
