"""The adaptation record: one bounded engineering operation inside a study.

R15. A study may find that the repository lacks what the question needs -- a
category, a parser, a comparison method -- and the agent may close that gap
as engineering. What separates that from an agent rewriting its own tools is
a record that binds the gap, the patch, the checks, the review and the
adoption to the study that needed them, so that another reader can replay the
decision from the files and the study's identity says which method produced
it. This module is that record's contract and nothing else: it runs nothing,
patches nothing and adopts nothing. :mod:`trial` captures patches and executes
checks; :mod:`session` accounts for the seconds; :mod:`bundle` binds the record
into the study and its ``study_id``.

Four rules shape the record.

**The patch is the record, not a pointer to it.** Every added or modified
file travels in full inside the record, with its digest; a deleted file is
named. A commit in a disposable worktree reconstructs nothing once the
worktree is gone, and a dirty flag reproduces no code (ROADMAP R15). The
``descriptor_sha256`` -- base revision, patch digest, resulting tree digest,
lock digest, the method versions the patch moved -- is what enters the study
identity when the record is bound, so the same inputs under a different method
are a different study.

**The review binds the bytes it read and stays out of the method digest.** A
completed review names the patch digest and the digest of the checks it saw;
a patch edited afterwards supersedes it. The descriptor does not include the
review, so approval cannot be part of what it approves.

**Adoption is a decision, recorded once, by a role.** ``accepted`` needs a
passing review; ``rejected``, ``withdrawn``, ``interrupted`` and
``budget_exhausted`` are outcomes in their own right and keep the record.
Nothing here turns a failed check into success.

**The state machine is the session ledger's.** The engineering action in the
ledger already knows ``planned``, ``authorised``, ``running``, ``completed``,
``interrupted`` and ``abandoned``; the record adds the checks, the review and
the adoption the ledger lacks, and names the action it accounts against.
"""

import base64
import json
import re

from ..provenance import sha256_text

#: The shape of the record. Tracked by the maintenance gate as ``adaptation_record``.
ADAPTATION_VERSION = 1
#: The record's name inside a study bundle.
RECORD = 'adaptation.json'

LAYERS = ('category', 'extraction', 'validation', 'analysis', 'acquisition',
          'evidence', 'method')
#: Who enforces the execution boundary the checks ran under.
BOUNDARIES = ('kernel', 'harness-only')
DECISIONS = ('pending', 'accepted', 'rejected', 'withdrawn', 'interrupted',
             'budget_exhausted')
FILE_STATES = ('added', 'modified', 'deleted')
VERDICTS = ('pending', 'pass', 'fail', 'limited')
PREDECESSORS = ('plan_session', 'adaptation')

SLUG = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
SHA = re.compile('[a-f0-9]{64}')
INSTANT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)')


class AdaptationError(ValueError):
    """An invalid record, or a binding that does not hold."""


def _fail(where, message):
    raise AdaptationError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly these fields: {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected nonempty text' if not empty else 'expected text')


def _enum(value, choices, where):
    if value not in choices:
        _fail(where, 'expected one of: ' + ', '.join(choices))


def _sha(value, where, empty=False):
    if value == '' and empty:
        return
    if not isinstance(value, str) or not SHA.fullmatch(value):
        _fail(where, 'expected a SHA-256 digest')


def _count(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        _fail(where, f'expected an integer of at least {minimum}')


def _instant(value, where, empty=True):
    if value == '' and empty:
        return
    if not isinstance(value, str) or not INSTANT.fullmatch(value):
        _fail(where, 'expected an ISO 8601 instant with an offset')


def _bool(value, where):
    if type(value) is not bool:
        _fail(where, 'expected true or false')


def _list(value, where):
    if not isinstance(value, list):
        _fail(where, 'expected a list')
    return value


def digest(data):
    """Canonical JSON content digest, independent of path and whitespace."""
    try:
        return sha256_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise AdaptationError(f'record must be finite JSON data: {exc}') from exc


# ---------------------------------------------------------------------------
# The patch archive
# ---------------------------------------------------------------------------

def file_content(entry):
    """The bytes an added or modified file carries; ``b''`` for a deleted one."""
    if entry['status'] == 'deleted':
        return b''
    if entry['content'] is not None:
        return entry['content'].encode('utf-8')
    try:
        return base64.b64decode(entry['content_base64'], validate=True)
    except (ValueError, TypeError) as exc:
        _fail(entry['path'], f'content_base64 is not base64: {exc}')


def file_entry(path, status, data=b''):
    """One archive entry: text when the bytes are UTF-8, base64 otherwise."""
    entry = {'path': path, 'status': status, 'sha256': '', 'content': None,
             'content_base64': ''}
    if status == 'deleted':
        return entry
    entry['sha256'] = _sha256_bytes(data)
    try:
        text = data.decode('utf-8')
        if text.encode('utf-8') == data:
            entry['content'] = text
            return entry
    except UnicodeDecodeError:
        pass
    entry['content_base64'] = base64.b64encode(data).decode('ascii')
    return entry


def _sha256_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def patch_digest(files):
    """Digest over every file's path, status and content digest, in path order."""
    rows = sorted(({'path': f['path'], 'status': f['status'], 'sha256': f['sha256']}
                   for f in files), key=lambda row: row['path'])
    return digest(rows)


def descriptor(record):
    """The method identity: what code, exactly, produced a study bound to this.

    Excludes the review and the adoption on purpose: approval is a judgement
    about the method and cannot be part of it without a digest cycle.
    """
    return digest({
        'base_revision': record['base']['git_revision'],
        'base_tree_sha256': record['base']['tree_sha256'],
        'patch_sha256': record['patch']['sha256'],
        'result_tree_sha256': record['result_tree_sha256'],
        'lock_sha256': record['lock_sha256'],
        'method_versions': record['method_versions'],
    })


def checks_digest(record):
    """What a review saw: the checks list as it stood."""
    return digest(record['checks'])


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

FIELDS = ('adaptation_version id layer hypothesis origin predecessor budget base '
          'patch result_tree_sha256 lock_sha256 method_versions evaluator inspection '
          'runner checks attempts consumption semantic_diff review adoption rollback '
          'descriptor_sha256')


def check(data):
    """Validate a record and its internal bindings. Reads nothing else."""
    _object(data, FIELDS, 'record')
    if type(data['adaptation_version']) is not int or data['adaptation_version'] != ADAPTATION_VERSION:
        _fail('adaptation_version', f'unsupported version; expected {ADAPTATION_VERSION}')
    if not isinstance(data['id'], str) or not SLUG.fullmatch(data['id']):
        _fail('id', 'expected a slug')
    _enum(data['layer'], LAYERS, 'layer')
    _text(data['hypothesis'], 'hypothesis')

    origin = data['origin']
    _object(origin, 'plan_id plan_revision plan_sha256 session_id action_id', 'origin')
    _text(origin['plan_id'], 'origin.plan_id', empty=True)
    if origin['plan_id']:
        _count(origin['plan_revision'], 'origin.plan_revision', 1)
        _sha(origin['plan_sha256'], 'origin.plan_sha256')
    elif origin['plan_revision'] != 0 or origin['plan_sha256'] != '':
        _fail('origin', 'without a plan, plan_revision is 0 and plan_sha256 is empty')
    _text(origin['session_id'], 'origin.session_id')
    _text(origin['action_id'], 'origin.action_id')

    if data['predecessor'] is not None:
        _object(data['predecessor'], 'kind ref sha256', 'predecessor')
        _enum(data['predecessor']['kind'], PREDECESSORS, 'predecessor.kind')
        _text(data['predecessor']['ref'], 'predecessor.ref')
        _sha(data['predecessor']['sha256'], 'predecessor.sha256')

    _object(data['budget'], 'seconds attempts', 'budget')
    _count(data['budget']['seconds'], 'budget.seconds', 1)
    _count(data['budget']['attempts'], 'budget.attempts', 1)

    _object(data['base'], 'git_revision tree_sha256', 'base')
    _text(data['base']['git_revision'], 'base.git_revision', empty=True)
    _sha(data['base']['tree_sha256'], 'base.tree_sha256', empty=True)

    patch = data['patch']
    _object(patch, 'sha256 files', 'patch')
    files = _list(patch['files'], 'patch.files')
    seen = set()
    for entry in files:
        _object(entry, 'path status sha256 content content_base64', 'patch.files[]')
        _text(entry['path'], 'patch.files[].path')
        if entry['path'].startswith('/') or '..' in entry['path'].split('/'):
            _fail(entry['path'], 'patch paths are relative to the tree and never climb out of it')
        if entry['path'] in seen:
            _fail(entry['path'], 'a file appears once in a patch')
        seen.add(entry['path'])
        _enum(entry['status'], FILE_STATES, f'{entry["path"]}.status')
        if entry['status'] == 'deleted':
            if entry['sha256'] != '' or entry['content'] is not None or entry['content_base64'] != '':
                _fail(entry['path'], 'a deleted file carries no content and no digest')
            continue
        _sha(entry['sha256'], f'{entry["path"]}.sha256')
        if (entry['content'] is None) == (entry['content_base64'] == ''):
            _fail(entry['path'], 'an added or modified file carries its content, as text or as base64')
        if entry['content'] is not None and not isinstance(entry['content'], str):
            _fail(entry['path'], 'content is text')
        if _sha256_bytes(file_content(entry)) != entry['sha256']:
            _fail(entry['path'], 'the content does not match its recorded digest')
    if files:
        _sha(patch['sha256'], 'patch.sha256')
        if patch['sha256'] != patch_digest(files):
            _fail('patch.sha256', 'does not match the files it lists')
    elif patch['sha256'] != '':
        _fail('patch.sha256', 'an empty patch has no digest')

    _sha(data['result_tree_sha256'], 'result_tree_sha256', empty=True)
    _sha(data['lock_sha256'], 'lock_sha256', empty=True)
    if not isinstance(data['method_versions'], dict):
        _fail('method_versions', 'expected a table of capability key -> version')
    for key, version in data['method_versions'].items():
        if not isinstance(key, str) or not SLUG.fullmatch(key):
            _fail('method_versions', f'{key!r} is not a capability key')
        _count(version, f'method_versions.{key}', 1)

    evaluator = data['evaluator']
    _object(evaluator, 'files base_sha256 frozen', 'evaluator')
    for path in _list(evaluator['files'], 'evaluator.files'):
        _text(path, 'evaluator.files[]')
    _sha(evaluator['base_sha256'], 'evaluator.base_sha256', empty=True)
    if evaluator['frozen'] is not None:
        _bool(evaluator['frozen'], 'evaluator.frozen')

    inspection = data['inspection']
    if inspection is not None:
        _object(inspection, 'paths flags findings', 'inspection')
        for path in _list(inspection['paths'], 'inspection.paths'):
            _text(path, 'inspection.paths[]')
        if not isinstance(inspection['flags'], dict):
            _fail('inspection.flags', 'expected a table of flag -> list of locations')
        for flag, where in inspection['flags'].items():
            _enum(flag, INSPECTION_FLAGS, 'inspection.flags')
            for item in _list(where, f'inspection.flags.{flag}'):
                _text(item, f'inspection.flags.{flag}[]')
        for finding in _list(inspection['findings'], 'inspection.findings'):
            _text(finding, 'inspection.findings[]')

    runner = data['runner']
    _object(runner, 'boundary profile_sha256 interpreter tmpdir timeout_seconds exception', 'runner')
    if runner['boundary'] is not None:
        _enum(runner['boundary'], BOUNDARIES, 'runner.boundary')
    _sha(runner['profile_sha256'], 'runner.profile_sha256', empty=True)
    _text(runner['interpreter'], 'runner.interpreter', empty=True)
    _text(runner['tmpdir'], 'runner.tmpdir', empty=True)
    if runner['timeout_seconds'] is not None:
        _count(runner['timeout_seconds'], 'runner.timeout_seconds', 1)
    _text(runner['exception'], 'runner.exception', empty=True)
    if runner['boundary'] == 'harness-only' and not runner['exception'].strip():
        _fail('runner.exception', 'a harness-only boundary is an exception the maintainer '
                                  'recorded; name the ledger revision or message that did')

    checks = _list(data['checks'], 'checks')
    for index, item in enumerate(checks):
        where = f'checks[{index}]'
        _object(item, 'command started_at finished_at seconds exit timed_out output_sha256 '
                      'output_path summary boundary', where)
        for word in _list(item['command'], where + '.command'):
            _text(word, where + '.command[]')
        _instant(item['started_at'], where + '.started_at', empty=False)
        _instant(item['finished_at'], where + '.finished_at', empty=False)
        if not isinstance(item['seconds'], (int, float)) or isinstance(item['seconds'], bool) \
                or item['seconds'] < 0:
            _fail(where + '.seconds', 'expected a non-negative number')
        if item['exit'] is not None and type(item['exit']) is not int:
            _fail(where + '.exit', 'expected an integer exit status, or null when killed')
        _bool(item['timed_out'], where + '.timed_out')
        if item['timed_out'] and item['exit'] is not None:
            _fail(where, 'a timed-out check has no exit status: it was killed, and it has no pass')
        _sha(item['output_sha256'], where + '.output_sha256', empty=True)
        _text(item['output_path'], where + '.output_path', empty=True)
        _text(item['summary'], where + '.summary', empty=True)
        _enum(item['boundary'], BOUNDARIES, where + '.boundary')
    _count(data['attempts'], 'attempts')
    if data['attempts'] > data['budget']['attempts']:
        _fail('attempts', f'{data["attempts"]} exceed the budget of {data["budget"]["attempts"]}: '
                          f'exhaustion stops new work, it does not extend the envelope')

    consumption = data['consumption']
    _object(consumption, 'seconds attempts', 'consumption')
    if consumption['seconds'] is not None and (
            not isinstance(consumption['seconds'], (int, float)) or isinstance(consumption['seconds'], bool)
            or consumption['seconds'] < 0):
        _fail('consumption.seconds', 'expected a non-negative number, or null when unknown')
    _count(consumption['attempts'], 'consumption.attempts')
    if consumption['attempts'] != data['attempts']:
        _fail('consumption.attempts', 'counts the attempts recorded above, once each')

    if data['semantic_diff'] is not None:
        _object(data['semantic_diff'], 'examples summary', 'semantic_diff')
        for row in _list(data['semantic_diff']['examples'], 'semantic_diff.examples'):
            _object(row, 'name before after', 'semantic_diff.examples[]')
            _text(row['name'], 'semantic_diff.examples[].name')
        _text(data['semantic_diff']['summary'], 'semantic_diff.summary')

    review = data['review']
    _object(review, 'reviewer verdict findings patch_sha256 checks_sha256', 'review')
    _enum(review['verdict'], VERDICTS, 'review.verdict')
    for finding in _list(review['findings'], 'review.findings'):
        _text(finding, 'review.findings[]')
    if review['verdict'] == 'pending':
        if review['reviewer'] or review['findings'] or review['patch_sha256'] or review['checks_sha256']:
            _fail('review', 'a pending review records nothing')
    else:
        _text(review['reviewer'], 'review.reviewer')
        if not review['findings']:
            _fail('review.findings', 'a completed review names its findings, never a bare verdict')
        _sha(review['patch_sha256'], 'review.patch_sha256')
        _sha(review['checks_sha256'], 'review.checks_sha256')
        if review['patch_sha256'] != patch['sha256']:
            _fail('review.patch_sha256', 'the review read another patch than this record holds: '
                                         'a patch edited after review supersedes the review')
        if review['checks_sha256'] != checks_digest(data):
            _fail('review.checks_sha256', 'the review saw other checks than this record holds: '
                                          'checks run after review are not what it reviewed')

    adoption = data['adoption']
    _object(adoption, 'decision decided by reason', 'adoption')
    _enum(adoption['decision'], DECISIONS, 'adoption.decision')
    if adoption['decision'] == 'pending':
        if adoption['decided'] or adoption['by'] or adoption['reason']:
            _fail('adoption', 'a pending adoption records nothing')
    else:
        _instant(adoption['decided'], 'adoption.decided', empty=False)
        _text(adoption['by'], 'adoption.by')
        _text(adoption['reason'], 'adoption.reason')
    if adoption['decision'] == 'accepted':
        if review['verdict'] != 'pass':
            _fail('adoption', 'accepted needs a passing review; a check that exited 0 is not one')
        if not files:
            _fail('adoption', 'nothing was patched, so nothing is adopted')
        if not checks or checks[-1]['timed_out'] or checks[-1]['exit'] != 0:
            _fail('adoption', 'accepted needs a last check that finished and passed; a timed-out '
                              'or failing check is not turned into success by a decision')
        if evaluator['frozen'] is not True:
            _fail('adoption', 'accepted needs the evaluator set proven frozen against the base revision')

    rollback = data['rollback']
    _object(rollback, 'instructions demonstrated demonstrated_at', 'rollback')
    for line in _list(rollback['instructions'], 'rollback.instructions'):
        _text(line, 'rollback.instructions[]')
    _bool(rollback['demonstrated'], 'rollback.demonstrated')
    _instant(rollback['demonstrated_at'], 'rollback.demonstrated_at')
    if rollback['demonstrated'] != bool(rollback['demonstrated_at']):
        _fail('rollback', 'a demonstrated rollback records when; an undemonstrated one records nothing')

    _sha(data['descriptor_sha256'], 'descriptor_sha256')
    if data['descriptor_sha256'] != descriptor(data):
        _fail('descriptor_sha256', 'does not match the base, patch, tree, lock and method versions '
                                   'this record holds')
    digest(data)
    return data


#: What the static inspection looks for, before anything is imported or run.
INSPECTION_FLAGS = ('import_side_effects', 'network', 'subprocess', 'file_writes',
                    'evaluator', 'contracts', 'dependencies')


def load(path):
    from pathlib import Path
    try:
        return check(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise AdaptationError(f'{path}: {exc}') from exc


def template(identifier, layer, hypothesis, session_id, action_id, budget_seconds,
             budget_attempts, plan=None, predecessor=None):
    """A valid, empty record: a gap named, nothing captured, nothing run."""
    origin = {'plan_id': '', 'plan_revision': 0, 'plan_sha256': '',
              'session_id': session_id, 'action_id': action_id}
    if plan is not None:
        from . import intake
        origin.update(plan_id=plan['id'], plan_revision=plan['revision'],
                      plan_sha256=intake.digest(plan))
        if predecessor is None:
            predecessor = {'kind': 'plan_session', 'ref': f'{plan["id"]}@{plan["revision"]}',
                           'sha256': intake.digest(plan)}
    record = {
        'adaptation_version': ADAPTATION_VERSION,
        'id': identifier, 'layer': layer, 'hypothesis': hypothesis,
        'origin': origin, 'predecessor': predecessor,
        'budget': {'seconds': budget_seconds, 'attempts': budget_attempts},
        'base': {'git_revision': '', 'tree_sha256': ''},
        'patch': {'sha256': '', 'files': []},
        'result_tree_sha256': '', 'lock_sha256': '', 'method_versions': {},
        'evaluator': {'files': [], 'base_sha256': '', 'frozen': None},
        'inspection': None,
        'runner': {'boundary': None, 'profile_sha256': '', 'interpreter': '', 'tmpdir': '',
                   'timeout_seconds': None, 'exception': ''},
        'checks': [], 'attempts': 0,
        'consumption': {'seconds': None, 'attempts': 0},
        'semantic_diff': None,
        'review': {'reviewer': '', 'verdict': 'pending', 'findings': [],
                   'patch_sha256': '', 'checks_sha256': ''},
        'adoption': {'decision': 'pending', 'decided': '', 'by': '', 'reason': ''},
        'rollback': {'instructions': [], 'demonstrated': False, 'demonstrated_at': ''},
        'descriptor_sha256': '',
    }
    record['descriptor_sha256'] = descriptor(record)
    return check(record)


def seal(record):
    """Recompute the derived digests after the record's facts changed."""
    record['patch']['sha256'] = patch_digest(record['patch']['files']) if record['patch']['files'] else ''
    record['consumption']['attempts'] = record['attempts']
    record['descriptor_sha256'] = descriptor(record)
    return check(record)


def binding(record):
    """What a study manifest records about the adaptation it rests on."""
    return {'id': record['id'], 'layer': record['layer'],
            'descriptor_sha256': record['descriptor_sha256'],
            'sha256': digest(record),
            'adoption': record['adoption']['decision'],
            'boundary': record['runner']['boundary']}


def check_binding(record, recorded):
    """Does the manifest's entry name this record, exactly?"""
    expected = binding(record)
    if recorded != expected:
        moved = sorted(k for k in set(expected) | set(recorded or {})
                       if expected.get(k) != (recorded or {}).get(k))
        raise AdaptationError('the manifest names another adaptation than the bundle holds: '
                              + ', '.join(moved) + ' moved')
