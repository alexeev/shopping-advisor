"""Deterministic claim checks and a separate, digest-bound semantic review.

The validator checks declared support, not the truth of arbitrary prose. External
claims render through fixed scope labels; a reviewer checks citation meaning.
Retained excerpts are embedded UTF-8 text, so bundles need no private paths.
"""
import json
from pathlib import Path

from ..provenance import sha256_text, sha256_file

LEDGER_VERSION = 1
AUDIT_VERSION = 1
REVIEW_VERSION = 1
REVIEW_CHECKS = ('citation_support', 'variant_applicability', 'user_priorities',
                 'coverage_and_limits')
SCOPES = ('historical', 'current_batch', 'vendor_declaration', 'review_sample',
          'access_limit')


class AuditError(ValueError):
    pass


def pointer(document, path):
    """Resolve a JSON Pointer; never evaluate an expression or import a name."""
    if not isinstance(path, str) or not path.startswith('/'):
        raise AuditError(f'invalid JSON pointer: {path!r}')
    try:
        for token in path[1:].split('/'):
            token = token.replace('~1', '/').replace('~0', '~')
            document = document[int(token)] if isinstance(document, list) else document[token]
        return document
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise AuditError(f'unresolved field: {path}') from exc


def empty():
    return {'ledger_version': LEDGER_VERSION, 'observations': [], 'claims': []}


def read(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        check_ledger(data)
        return data
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise AuditError(f'{path}: {exc}') from exc


def check_ledger(data):
    if not isinstance(data, dict) or type(data.get('ledger_version')) is not int or data.get('ledger_version') != LEDGER_VERSION:
        raise AuditError(f'unsupported ledger_version; expected {LEDGER_VERSION}')
    if set(data) - {'ledger_version', 'observations', 'claims'}:
        raise AuditError('unknown ledger fields')
    rows = data.get('observations')
    if not isinstance(rows, list) or not isinstance(data.get('claims', []), list):
        raise AuditError('observations and claims must be lists')
    ids = set()
    required = {'id', 'source_id', 'source_class', 'publisher', 'title', 'url',
                'published', 'retrieved', 'locator', 'snapshot', 'claim',
                'excerpt', 'units', 'representation', 'verification', 'product',
                'match_status', 'limits', 'conflicts', 'supersedes'}
    for row in rows:
        if not isinstance(row, dict) or required - row.keys():
            raise AuditError('observation missing required metadata')
        if not isinstance(row['id'], str) or not row['id'] or row['id'] in ids:
            raise AuditError('observation IDs must be unique nonempty strings')
        ids.add(row['id'])
        if any(not isinstance(row[key], str) or not row[key].strip() for key in ('source_id', 'publisher', 'title', 'locator', 'claim')):
            raise AuditError('observation needs source identity, locator and claim')
        for key in required - {'snapshot', 'product', 'limits', 'conflicts', 'supersedes'}:
            if not isinstance(row[key], str):
                raise AuditError(f'{row["id"]}.{key}: expected text')
        for key in ('limits', 'conflicts', 'supersedes'):
            if not isinstance(row[key], list) or any(not isinstance(v, str) for v in row[key]):
                raise AuditError(f'{row["id"]}.{key}: expected list of text')
        if row['source_class'] not in ('independent_test', 'manufacturer', 'seller', 'buyer_sample', 'secondary'):
            raise AuditError('unsupported source_class')
        if row['verification'] not in ('verified', 'unverified', 'legacy_unverified', 'indirect'):
            raise AuditError('unsupported source verification')
        if row['match_status'] not in ('checked', 'unresolved', 'mismatch'):
            raise AuditError('unsupported match_status')
        if row['representation'] not in ('quotation', 'interpretation'):
            raise AuditError('unsupported representation')
        product = row['product']
        if not isinstance(product, dict) or set(product) != {'brand', 'model', 'variant', 'batch', 'geography'} or any(not isinstance(v, str) for v in product.values()):
            raise AuditError('product needs brand/model/variant/batch/geography (empty means unknown)')
        snap = row['snapshot']
        if not isinstance(snap, dict):
            raise AuditError('snapshot must be a table')
        if snap.get('status') == 'retained':
            if not isinstance(snap.get('text'), str) or sha256_text(snap['text']) != snap.get('sha256'):
                raise AuditError(f'{row["id"]}: retained text digest mismatch')
            if row['representation'] == 'quotation' and row['claim'] != row['excerpt']:
                raise AuditError('quotation claim must equal its retained excerpt')
            if not row['excerpt'] or row['excerpt'] not in snap['text']:
                raise AuditError(f'{row["id"]}: excerpt absent from retained text')
        elif snap.get('status') != 'unavailable' or not snap.get('reason'):
            raise AuditError('snapshot needs retained text/digest or unavailable reason')
        if row['verification'] == 'verified':
            import datetime
            for key in ('published', 'retrieved'):
                try:
                    datetime.date.fromisoformat(row[key])
                except ValueError as exc:
                    raise AuditError(f'verified source needs ISO {key} date') from exc
            if not row['url'].startswith(('https://', 'http://')) or not row['locator']:
                raise AuditError('verified source needs URL and precise locator')
    for row in rows:
        if any(link not in ids or link == row['id'] for link in row['conflicts'] + row['supersedes']):
            raise AuditError(f'{row["id"]}: unresolved or self conflict/supersession link')


def check_claims(ledger, records, as_of=None):
    """Reject overreach even when a citation resolves and has valid bytes."""
    check_ledger(ledger)
    observations = {row['id']: row for row in ledger['observations']}
    seen = set()
    for claim in ledger.get('claims', []):
        if not isinstance(claim, dict) or set(claim) != {'id', 'observation', 'scope', 'statement', 'listing', 'match'}:
            raise AuditError('claim needs id/observation/scope/statement/listing/match')
        if not isinstance(claim['id'], str) or not claim['id'] or claim['id'] in seen:
            raise AuditError('duplicate or empty claim id')
        seen.add(claim['id'])
        obs = observations.get(claim['observation'])
        if obs is None:
            raise AuditError(f'{claim["id"]}: absent evidence')
        scope = claim['scope']
        if scope not in SCOPES:
            raise AuditError('unsupported claim scope (sample frequency is not population frequency)')
        expected = obs['snapshot'].get('reason') if scope == 'access_limit' else obs['claim']
        if claim['statement'] != expected:
            raise AuditError(f'{claim["id"]}: fabricated or different statement')
        if scope == 'current_batch' and (not as_of or obs['published'] > as_of):
            raise AuditError('current batch claim needs an as-of date at or after publication')
        if scope == 'access_limit':
            if obs['snapshot']['status'] != 'unavailable':
                raise AuditError('access limit requires unavailable snapshot')
            continue
        if obs['verification'] != 'verified' or obs['snapshot']['status'] != 'retained':
            raise AuditError(f'{claim["id"]}: unverified or unavailable support')
        permitted = {'manufacturer': 'vendor_declaration', 'seller': 'vendor_declaration',
                     'buyer_sample': 'review_sample', 'secondary': 'historical'}
        if obs['source_class'] in permitted and scope != permitted[obs['source_class']]:
            raise AuditError('vendor assertion/sample/secondary source cannot establish this scope')
        if scope in ('vendor_declaration', 'review_sample') and obs['source_class'] not in (
                ('manufacturer', 'seller') if scope == 'vendor_declaration' else ('buyer_sample',)):
            raise AuditError('scope does not match source class')
        conflicts = set(obs['conflicts']) | {o['id'] for o in observations.values() if obs['id'] in o['conflicts']}
        superseded = any(obs['id'] in o['supersedes'] for o in observations.values())
        if scope == 'current_batch' and (conflicts or superseded):
            raise AuditError('conflicting or superseded evidence cannot decide current batch')
        if scope == 'historical' and not claim['listing']:
            continue  # A dated source finding, with no assertion about a listing.
        if obs['match_status'] != 'checked':
            raise AuditError('listing match unresolved')
        record = records.get(claim['listing'])
        if record is None:
            raise AuditError('wrong or absent marketplace listing')
        needed = {'brand', 'model', 'variant', 'geography'}
        if scope == 'current_batch':
            needed.add('batch')
        if not isinstance(claim['match'], dict) or set(claim['match']) != needed:
            raise AuditError('match must name identity fields, including batch for current conclusions')
        for field in needed:
            value = obs['product'][field]
            if not value or pointer(record, claim['match'][field]) != value:
                raise AuditError(f'{claim["id"]}: wrong or unknown {field}')


def index(result, cards, ledger):
    """Claim -> decision field -> retained input/card; computations replay in analyse."""
    claims = []
    for n, claim in enumerate(result['claims']):
        claims.append(dict(claim, support={'artifact': 'ranking.json',
            'pointer': f'/claims/{n}', 'computation': 'study.analysis._claims',
            'inputs': 'manifest.json#/inputs',
            'input_claims': ['best_value', 'runner_up_value'] if claim['id'] == 'margin' else []}))
    for n, card in enumerate(cards):
        if card.get('score'):
            claims.append({'id': f'score-{n}', 'value': card['score'],
                           'support': {'artifact': 'cards.jsonl', 'row': n,
                                       'pointer': '/score', 'computation': 'basmati-score-v2',
                                       'inputs': 'manifest.json#/inputs'}})
    return {'audit_version': AUDIT_VERSION, 'method': {
        'ranking': 'single-axis-v1', 'axis': result['constraints']['axis'],
        'score_shortlist': False}, 'claims': claims,
        'external_claims': ledger.get('claims', []),
        'decision_support': {'artifact': 'candidates.jsonl',
                             'inputs': 'manifest.json#/inputs'},
        'listing_support': [{'listing': f'{c.get("marketplace")}:{c["asin"]}',
            'artifact': 'cards.jsonl', 'row': n, 'axis': result['constraints']['axis']['key'],
            'required_claims': result['constraints']['require_claims']}
            for n, c in enumerate(cards)],
        'framing': 'historical' if result['freshness']['stale_ranked'] or
                   not result['freshness']['assessed'] or result['freshness']['undated']
                   else 'as_of_brief'}


def render(ledger):
    lines = ['\n## External evidence audit\n',
             'Scope labels describe what the source supports. Source verification '
             'and product matching are recorded assessments; semantic review is separate.\n']
    for claim in ledger.get('claims', []):
        obs = next(o for o in ledger['observations'] if o['id'] == claim['observation'])
        lines += [f'- [{claim["id"]}] **{claim["scope"]}**, {obs["publisher"]}, '
                  f'{obs["published"] or "date unknown"}: {claim["statement"]} '
                  f'(ledger.json observation `{obs["id"]}`, {obs["locator"]}).']
    for obs in ledger['observations']:
        lines += [f'- Observation `{obs["id"]}`: {obs["verification"]}; '
                  f'match {obs["match_status"]}; {obs["snapshot"]["status"]}. '
                  + ' '.join(obs['limits']) + f' Conflicts: {obs["conflicts"]}; '
                  f'supersedes: {obs["supersedes"]}.']
    if ledger['observations']:
        lines += ['\nTo reproduce external claims, also pass `--evidence <bundle>/ledger.json` to `study run`.']
    return '\n'.join(lines) + '\n'


def validation_result(review):
    return {'audit_version': AUDIT_VERSION, 'deterministic': 'pass',
            'semantic': review_status(review),
            'checks': ['ledger_schema', 'source_digests', 'claim_scope',
                       'listing_applicability', 'decision_replay'],
            'limits': ['Semantic citation support and priorities require a separate review.']}


def review_status(review):
    statuses = [item['status'] for item in review['checks'].values()]
    return 'fail' if 'fail' in statuses else ('pending' if 'pending' in statuses else 'pass')


def review_basis(directory):
    names = ('brief.json', 'ranking.json', 'candidates.jsonl', 'cards.jsonl',
             'ledger.json', 'claim-index.json')
    return {name: sha256_file(Path(directory) / name) for name in names}


def review_template(directory):
    return {'review_version': REVIEW_VERSION, 'report_sha256': sha256_file(Path(directory) / 'report.md'),
            'basis': review_basis(directory), 'reviewer': '', 'checks': {k: {'status': 'pending', 'findings': ''} for k in REVIEW_CHECKS},
            'unresolved_limits': []}


def check_review(review, directory, required=False):
    if not isinstance(review, dict) or review.get('review_version') != REVIEW_VERSION:
        raise AuditError('unsupported semantic review version')
    if review.get('report_sha256') != sha256_file(Path(directory) / 'report.md'):
        raise AuditError('semantic review belongs to different report bytes')
    if not isinstance(review.get('checks'), dict) or set(review['checks']) != set(REVIEW_CHECKS) or not isinstance(review.get('unresolved_limits'), list):
        raise AuditError('semantic review needs checklist and unresolved limits')
    if any(item.get('status') != 'pending' for item in review['checks'].values() if isinstance(item, dict)) and review.get('basis') != review_basis(directory):
        raise AuditError('semantic review belongs to different evidence/decision bytes')
    if not isinstance(review.get('reviewer'), str) or any(not isinstance(v, str) for v in review['unresolved_limits']):
        raise AuditError('reviewer and unresolved limits must be text')
    for item in review['checks'].values():
        if not isinstance(item, dict) or item.get('status') not in ('pending', 'pass', 'fail'):
            raise AuditError('invalid semantic review check')
        if item['status'] != 'pending' and (not review.get('reviewer') or not isinstance(item.get('findings'), str) or not item['findings'].strip()):
            raise AuditError('completed review needs reviewer and findings, not a bare approval')
        if required and item['status'] != 'pass':
            raise AuditError('semantic review incomplete or failed')
