"""Declared source ledger: external documents mapped to listings by assertion.

Bucket F of the powerbank postmortem (HISTORY, 2026-09-19), built on
2026-11-24 for a review whose decisive facts -- an operating temperature, a
vehicle approval number -- stood in manufacturer datasheets and on no listing.

A bounded review of an unsupported category has no study bundle, so the T3
evidence ledger (``audit``), which binds claims to a study's cards, cannot
hold its sources. This ledger can: it needs feeds and nothing else.

What it does, and all it does:

* a **source** is a manufacturer datasheet, a certificate or a safety notice,
  recorded with where it was read, the **model string it names**, verbatim,
  and the statements quoted from it;
* a **mapping** is the operator's assertion that a source concerns a listing,
  with the model string the operator quotes from the *record*;
* the tool checks that the quote occurs in the record field the mapping names,
  and reports each listing x kind as ``checked``, ``declared``,
  ``nothing_found`` or ``not_looked_up``.

It never infers a match. Automatic model matching was rejected against
counterexamples (``PB763`` against ``PB763 v2``, ROADMAP's rejected table):
the record's string and the source's string are printed side by side, and
whether they are the same string is reported, not decided. ``checked`` says a
string was found where the operator said it was. It does not say the source
applies, and nothing here renders a product as safe, compliant or suitable.
"""
import datetime
import json
from pathlib import Path

from ..provenance import sha256_text
from .audit import AuditError, pointer

SOURCE_LEDGER_VERSION = 1
KINDS = ('manufacturer_datasheet', 'certificate', 'safety_notice')
#: What a statement quoted from each kind is, in the words a report may use.
#: A datasheet is the maker speaking about its own product.
STATEMENT_LABELS = {'manufacturer_datasheet': 'vendor declaration',
                    'certificate': "certifier's record",
                    'safety_notice': 'notice'}
STATUSES = ('checked', 'declared', 'nothing_found', 'not_looked_up')
NOTE = ('A mapping is the operator\'s declared assertion that a source concerns a '
        'listing. "checked" means the quoted model string occurs in the record field '
        'named; it does not mean the source applies to the listing. Nothing here says '
        'a product is safe, compliant or suitable.')


class SourceError(ValueError):
    pass


def _fail(where, message):
    raise SourceError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly the fields {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected text' if empty else 'expected non-empty text')


def _date(value, where, empty=False):
    _text(value, where, empty)
    if value:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            _fail(where, 'expected an ISO date')


def check(data):
    """Structural validity. Says nothing about any record."""
    if not isinstance(data, dict) or type(data.get('source_ledger_version')) is not int \
            or data['source_ledger_version'] != SOURCE_LEDGER_VERSION:
        raise SourceError(f'unsupported source_ledger_version; expected {SOURCE_LEDGER_VERSION}')
    _object(data, 'source_ledger_version id marketplace listings kinds sources mappings lookups',
            'source ledger')
    _text(data['id'], 'id')
    _text(data['marketplace'], 'marketplace')
    for key in ('listings', 'kinds', 'sources', 'mappings', 'lookups'):
        if not isinstance(data[key], list):
            _fail(key, 'expected a list')
    listings = data['listings']
    for listing in listings:
        _text(listing, 'listings')
        if not listing.startswith(data['marketplace'] + ':'):
            _fail('listings', f'{listing!r} is not a listing of {data["marketplace"]}')
    if len(set(listings)) != len(listings) or not listings:
        _fail('listings', 'name each listing in scope once, and at least one')
    kinds = data['kinds']
    if not kinds or len(set(kinds)) != len(kinds) or any(kind not in KINDS for kind in kinds):
        _fail('kinds', f'expected distinct kinds from: {", ".join(KINDS)}')

    sources = {}
    for row in data['sources']:
        where = f'source {row.get("id") if isinstance(row, dict) else row!r}'
        _object(row, 'id kind publisher title url published retrieved locator model snapshot '
                     'statements limits', where)
        _text(row['id'], where)
        if row['id'] in sources:
            _fail(where, 'duplicate source id')
        if row['kind'] not in kinds:
            _fail(where, 'kind is not among the ledger\'s declared kinds')
        for key in ('publisher', 'title', 'locator', 'model'):
            _text(row[key], f'{where}.{key}')
        if not row['url'].startswith(('https://', 'http://')):
            _fail(where, 'a source needs the URL it was read at')
        _date(row['published'], f'{where}.published', empty=True)
        _date(row['retrieved'], f'{where}.retrieved')
        if not isinstance(row['limits'], list) or any(not isinstance(v, str) for v in row['limits']):
            _fail(where, 'limits is a list of text')
        snapshot = row['snapshot']
        if not isinstance(snapshot, dict):
            _fail(where, 'snapshot must be a table')
        retained = snapshot.get('status') == 'retained'
        if retained:
            _object(snapshot, 'status text sha256', f'{where}.snapshot')
            if not isinstance(snapshot['text'], str) or sha256_text(snapshot['text']) != snapshot['sha256']:
                _fail(where, 'retained text digest mismatch')
            if row['model'] not in snapshot['text']:
                _fail(where, 'the model string is absent from the retained text')
        elif snapshot.get('status') == 'unavailable':
            _object(snapshot, 'status reason', f'{where}.snapshot')
            _text(snapshot['reason'], f'{where}.snapshot.reason')
        else:
            _fail(where, 'snapshot needs retained text and digest, or unavailable with a reason')
        if not isinstance(row['statements'], list):
            _fail(where, 'statements is a list')
        seen = set()
        for statement in row['statements']:
            _object(statement, 'id subject quote', f'{where}.statements')
            for key in ('id', 'subject', 'quote'):
                _text(statement[key], f'{where}.statements.{key}')
            if statement['id'] in seen:
                _fail(where, f'duplicate statement id {statement["id"]!r}')
            seen.add(statement['id'])
            if retained and statement['quote'] not in snapshot['text']:
                _fail(where, f'statement {statement["id"]!r} is absent from the retained text')
        sources[row['id']] = row

    pairs, covered, ids = set(), set(), set()
    for row in data['mappings']:
        where = f'mapping {row.get("id") if isinstance(row, dict) else row!r}'
        _object(row, 'id source listing quote field basis', where)
        _text(row['id'], where)
        if row['id'] in ids:
            _fail(where, 'duplicate mapping id')
        ids.add(row['id'])
        if row['source'] not in sources:
            _fail(where, 'names no recorded source')
        if row['listing'] not in listings:
            _fail(where, 'names a listing outside the ledger\'s scope')
        if (row['source'], row['listing']) in pairs:
            _fail(where, 'this source is already mapped to this listing')
        pairs.add((row['source'], row['listing']))
        covered.add((row['listing'], sources[row['source']]['kind']))
        _text(row['quote'], f'{where}.quote')
        _text(row['field'], f'{where}.field', empty=True)
        _text(row['basis'], f'{where}.basis', empty=True)
        if row['field'] and not row['field'].startswith('/'):
            _fail(where, 'field is a JSON pointer into the record, or empty')
        if not row['field'] and not row['basis'].strip():
            _fail(where, 'a mapping with no record field to check states its basis')

    looked = set()
    for row in data['lookups']:
        where = f'lookup {row.get("listing") if isinstance(row, dict) else row!r}'
        _object(row, 'listing kind where retrieved', where)
        if row['listing'] not in listings:
            _fail(where, 'names a listing outside the ledger\'s scope')
        if row['kind'] not in kinds:
            _fail(where, 'kind is not among the ledger\'s declared kinds')
        _text(row['where'], f'{where}.where')
        _date(row['retrieved'], f'{where}.retrieved')
        key = (row['listing'], row['kind'])
        if key in looked:
            _fail(where, 'one lookup per listing and kind')
        if key in covered:
            _fail(where, 'a lookup that found nothing contradicts a mapping of the same kind')
        looked.add(key)
    return data


def load(path):
    try:
        return check(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f'{path}: {exc}') from exc


def assess(ledger, records):
    """Every listing x kind in scope, with its status; ``records`` is ``{listing: record}``.

    A finding is a declaration the records contradict: a listing that is in no
    feed, a field that does not resolve, a quote that is not in the field.
    """
    check(ledger)
    sources = {row['id']: row for row in ledger['sources']}
    lookups = {(row['listing'], row['kind']): row for row in ledger['lookups']}
    rows, findings = [], []
    for listing in ledger['listings']:
        record = records.get(listing)
        if record is None:
            findings.append({'code': 'listing_absent', 'listing': listing,
                             'message': f'{listing}: no record in the feeds given'})
        for kind in ledger['kinds']:
            mapped = [m for m in ledger['mappings']
                      if m['listing'] == listing and sources[m['source']]['kind'] == kind]
            for mapping in mapped:
                source = sources[mapping['source']]
                status = 'declared'
                if mapping['field'] and record is not None:
                    try:
                        value = pointer(record, mapping['field'])
                    except AuditError:
                        value = None
                    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                        findings.append({'code': 'field_unresolved', 'listing': listing,
                                         'message': f'{mapping["id"]}: {mapping["field"]} is not a '
                                                    f'text or number field of the record'})
                    elif mapping['quote'] not in str(value):
                        findings.append({'code': 'quote_absent', 'listing': listing,
                                         'message': f'{mapping["id"]}: {mapping["quote"]!r} does not '
                                                    f'occur in {mapping["field"]}'})
                    else:
                        status = 'checked'
                rows.append({
                    'listing': listing, 'kind': kind, 'status': status,
                    'mapping': mapping['id'], 'source': source['id'],
                    'record_quote': mapping['quote'], 'record_field': mapping['field'],
                    'source_model': source['model'],
                    'same_string': mapping['quote'] == source['model'],
                    'basis': mapping['basis'], 'publisher': source['publisher'],
                    'url': source['url'], 'locator': source['locator'],
                    'retrieved': source['retrieved'],
                    'snapshot': source['snapshot']['status'],
                    'statement_label': STATEMENT_LABELS[kind],
                    'statements': source['statements'], 'limits': source['limits']})
            if not mapped:
                lookup = lookups.get((listing, kind))
                rows.append({'listing': listing, 'kind': kind,
                             'status': 'nothing_found' if lookup else 'not_looked_up',
                             'where': lookup['where'] if lookup else '',
                             'retrieved': lookup['retrieved'] if lookup else ''})
    counts = {status: sum(row['status'] == status for row in rows) for status in STATUSES}
    return {'source_ledger_version': SOURCE_LEDGER_VERSION, 'id': ledger['id'],
            'note': NOTE, 'rows': rows, 'counts': counts, 'findings': findings}


def render(result):
    lines = [f'{result["id"]}: declared source ledger v{result["source_ledger_version"]}; '
             + ', '.join(f'{result["counts"][s]} {s}' for s in STATUSES), NOTE]
    for row in result['rows']:
        head = f'  {row["listing"]:<28}{row["kind"]:<24}{row["status"]}'
        if 'mapping' not in row:
            lines.append(head + (f': {row["where"]} ({row["retrieved"]})' if row['where'] else ''))
            continue
        same = 'the same string' if row['same_string'] else 'NOT the same string'
        where = f'record {row["record_field"]}' if row['record_field'] else f'no record field; {row["basis"]}'
        lines.append(f'{head}: record names {row["record_quote"]!r} ({where}); source names '
                     f'{row["source_model"]!r} -- {same}')
        lines.append(f'      {row["publisher"]}, {row["locator"]}, read {row["retrieved"]}, '
                     f'text {row["snapshot"]}: {row["url"]}')
        for statement in row['statements']:
            lines.append(f'      {row["statement_label"]} [{statement["subject"]}]: '
                         f'"{statement["quote"]}"')
        for limit in row['limits']:
            lines.append(f'      limit: {limit}')
    for finding in result['findings']:
        lines.append(f'  FINDING {finding["code"]}: {finding["message"]}')
    return '\n'.join(lines)
