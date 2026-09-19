"""The session resource ledger: declared limits, action records, resumption.

R13 stage 8. Per-crawl provenance is a foundation and not session accounting:
a run manifest says what one crawl consumed, and nothing said what a session
had been allowed, what it had spent across probes, retries and interrupted
runs, or what it might still do. This module is that record and the check that
reads it. It is not a scheduler and not a command runner: it authorises or
refuses a *described* action, records what an action *did* from the manifest
the crawl left behind, and says whether retained artifacts support resuming.

Three rules from INTAKE §7 shape every function here.

**Count in the units the environment observes.** A limit is stated in a unit a
run manifest actually reports -- responses, requests, items, seconds, retained
pages, runs -- or is marked an estimate and can then only stop new work, never
enforce a ceiling. A ``strict_ceiling`` is permitted only for a unit Scrapy's
``CLOSESPIDER_*`` settings can close on, and even then the record names the
known overshoot: a page-count closure does not cancel requests in flight, and
an item cap is not a request cap.

**Unknown stays unknown, not zero.** A completed or interrupted action whose
consumption could not be read leaves its limit *unreconciled*, and an
unreconciled limit authorises nothing until the operator records the manifest
or declares the whole allocation consumed. A replay is not new acquisition and
may not claim acquisition units; a resumed action is a new record whose
predecessor's consumption is counted once, on the predecessor.

**A stop preserves what was done and names what it prevents.** Exhaustion
refuses the next action; it deletes no record. Interrupted work is listed as
interrupted, never assumed complete. Engineering is accounted against its own
allowance, never a research one: willingness to investigate products does not
fund development.

**Version 2 (R15) lets engineering run.** A v1 ledger retained engineering as
a proposal -- ``planned`` or ``abandoned``, never authorised -- because no
controlled execution existed. Under v2 an engineering action is authorised,
runs, completes or is interrupted like any other, against an ``engineering``
limit in ``seconds`` -- attempts are the adaptation record's own budget, and
acquisition units stay research's -- and what it did is recorded from its
*adaptation record* (:mod:`adaptation`) rather than from a crawl manifest: the record is linked by path and digest as ``run_manifest``,
its id as ``run_id``, and the consumption source is ``adaptation_record``. A
v1 ledger is still read, and still refuses to execute engineering: the file
says what its author was entitled to, and a newer reader grants nothing more.

Resumption reads the bundle and the ledger and writes nothing. It verifies the
retained artifacts, the active plan revision, consumed and reserved resources,
the predecessors each action depends on and the pending review state, rechecks
delivery freshness at a reference it is given, and either reports the verified
state with the next actions the ledger permits or names the precise missing
dependency. It does not need the conversation that produced any of it.
"""

from datetime import datetime
import json
from pathlib import Path
import re

from ..provenance import sha256_file, sha256_text
from . import delivery

#: The shape of a session ledger and of the bundle snapshot. Tracked by the gate.
SESSION_VERSION = 3
#: Versions this build reads. A v1 ledger keeps v1's rules (engineering is a
#: proposal); a v2 ledger has no ``collections`` unit and no
#: ``builds_on_partial`` field, and a dependent on interrupted work under it
#: is refused as it always was. The file says what its author was entitled
#: to, and a newer reader grants nothing more.
SUPPORTED_VERSIONS = (1, 2, 3)
SNAPSHOT = 'session.json'
DEFAULT_SESSION_ROOT = 'data/sessions'

KINDS = ('inspection', 'probe', 'collection', 'analysis', 'engineering')
#: Kinds that touch the marketplace and therefore spend acquisition units.
LIVE = ('probe', 'collection')
STATES = ('planned', 'authorised', 'running', 'completed', 'interrupted', 'abandoned')
DONE = ('completed', 'interrupted')
LIMIT_KINDS = ('research', 'engineering')
MODES = ('stops_new_work', 'strict_ceiling')
AUTHORITY = ('user_message', 'existing_authorization', 'operator')
CONSUMPTION_SOURCES = ('run_manifest', 'adaptation_record', 'declared', 'assumed_allocation',
                       'unknown')

#: Units a run manifest reports, and where. ``runs`` is one per manifest.
OBSERVED = {
    'requests': ('stats', 'downloader/request_count'),
    'responses': ('stats', 'downloader/response_count'),
    'items': ('stats', 'item_scraped_count'),
    'seconds': ('stats', 'elapsed_time_seconds'),
    'pages_retained': ('counts', 'pages_saved'),
    'runs': None,
    'collections': None,
}
#: Units a ledger may declare only from the version that introduced them.
#: ``collections`` (v3) is one per collection action, consumed when the
#: action is recorded: the powerbank session's "maximum two follow-up crawls"
#: lived in a limit's prose ``scope``, which nothing could count against.
INTRODUCED = {'collections': 3}
#: Units nobody in this environment can measure reliably. Estimates only.
ESTIMATED = ('eur', 'tokens')
#: Units that spend the marketplace's patience rather than this machine's.
ACQUISITION = ('requests', 'responses', 'items', 'pages_retained', 'runs',
               'collections')
#: The closure settings a crawl can enforce a unit with, and what each misses.
ENFORCEABLE = {'responses': 'CLOSESPIDER_PAGECOUNT',
               'items': 'CLOSESPIDER_ITEMCOUNT',
               'seconds': 'CLOSESPIDER_TIMEOUT'}
OVERSHOOT = {
    'responses': 'a page-count closure does not cancel requests already in flight',
    'items': 'an item cap is not a request cap: pages that yield no item are not counted',
    'seconds': 'a timeout closure may leave requests in flight',
}

SLUG = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')


class SessionError(ValueError):
    """An invalid ledger, a refused record, or a resumption that cannot proceed."""


def _fail(where, message):
    raise SessionError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly these fields: {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected nonempty text' if not empty else 'expected text')


def _enum(value, choices, where):
    if value not in choices:
        _fail(where, 'expected one of: ' + ', '.join(choices))


def _amount(value, where, unit):
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or value < 0 or value != value or value in (float('inf'), float('-inf')):
        _fail(where, 'expected a finite non-negative number')
    if unit in ACQUISITION and int(value) != value:
        _fail(where, f'{unit} are counted in whole numbers')


def _instant(value, where, empty=True):
    if value == '' and empty:
        return
    try:
        delivery.parse_reference(value)
    except delivery.DeliveryError as exc:
        _fail(where, str(exc))


def digest(data):
    try:
        return sha256_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise SessionError(f'ledger must be finite JSON data: {exc}') from exc


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

def check(data):
    """Validate a ledger. Reads no manifest, no clock and no bundle."""
    _object(data, 'session_version id revision supersedes plan limits actions', 'ledger')
    if type(data['session_version']) is not int or data['session_version'] not in SUPPORTED_VERSIONS:
        _fail('session_version', 'unsupported version; expected one of '
                                 + ', '.join(str(v) for v in SUPPORTED_VERSIONS))
    if not isinstance(data['id'], str) or not SLUG.fullmatch(data['id']):
        _fail('id', 'expected a slug')
    if type(data['revision']) is not int or data['revision'] < 1:
        _fail('revision', 'expected a positive integer')
    if data['revision'] == 1:
        if data['supersedes'] != '':
            _fail('supersedes', 'the first revision supersedes nothing')
    elif not isinstance(data['supersedes'], str) or not re.fullmatch('[a-f0-9]{64}', data['supersedes']):
        _fail('supersedes', 'a later revision names the previous ledger digest: an '
                            'extension is an explicit budget revision')
    if data['plan'] is not None:
        _object(data['plan'], 'id revision sha256', 'plan')
        _text(data['plan']['id'], 'plan.id')
        if type(data['plan']['revision']) is not int or data['plan']['revision'] < 1:
            _fail('plan.revision', 'expected a positive integer')
        if not re.fullmatch('[a-f0-9]{64}', str(data['plan']['sha256'])):
            _fail('plan.sha256', 'expected a SHA-256 digest')

    limits = _ids(data['limits'], 'limits')
    for limit in limits.values():
        _limit(limit, data)
    actions = _ids(data['actions'], 'actions')
    if set(limits) & set(actions):
        _fail('ledger', 'limit and action ids must be distinct')
    for action in actions.values():
        _action(action, limits, actions, data)
    digest(data)
    return data


def _ids(rows, where):
    if not isinstance(rows, list):
        _fail(where, 'expected a list')
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) \
                or not SLUG.fullmatch(row['id']):
            _fail(where, 'every entry needs a slug id')
        if row['id'] in found:
            _fail(where, 'duplicate id ' + row['id'])
        found[row['id']] = row
    return found


def version(ledger):
    return ledger.get('session_version', 1)


def _limit(limit, ledger):
    name = limit['id']
    _object(limit, 'id kind unit amount measurement mode scope authorization deadline note', name)
    _enum(limit['kind'], LIMIT_KINDS, name + '.kind')
    unit = limit['unit']
    if unit in INTRODUCED and version(ledger) < INTRODUCED[unit]:
        _fail(name, f'{unit} is a session ledger v{INTRODUCED[unit]} unit; this ledger is '
                    f'v{version(ledger)}, and a newer reader grants nothing its author could not declare')
    if unit in OBSERVED:
        if limit['measurement'] != 'observed':
            _fail(name, f'{unit} is a unit the run manifest reports; measurement is observed')
    elif unit in ESTIMATED:
        if limit['measurement'] != 'estimate':
            _fail(name, f'{unit} cannot be measured here; measurement is estimate')
    else:
        _fail(name, f'{unit!r}: not a unit this environment observes '
                    f'({", ".join(OBSERVED)}) or estimates ({", ".join(ESTIMATED)})')
    _amount(limit['amount'], name + '.amount', unit)
    _enum(limit['mode'], MODES, name + '.mode')
    if limit['mode'] == 'strict_ceiling':
        if unit not in ENFORCEABLE:
            _fail(name, f'no mechanism enforces a strict ceiling on {unit}; declare '
                        f'stops_new_work instead of promising a cap nothing can hold')
        if not limit['note'].strip():
            _fail(name, 'a strict ceiling states its known overshoot in note')
    _text(limit['scope'], name + '.scope')
    _text(limit['note'], name + '.note', empty=True)
    if limit['measurement'] == 'estimate' and not limit['note'].strip():
        _fail(name, 'an estimated limit says in note how the estimate is made')
    authorization = limit['authorization']
    _object(authorization, 'source ref text', name + '.authorization')
    _enum(authorization['source'], AUTHORITY, name + '.authorization.source')
    _text(authorization['text'], name + '.authorization.text')
    _text(authorization['ref'], name + '.authorization.ref',
          empty=authorization['source'] != 'user_message')
    _instant(limit['deadline'], name + '.deadline')


ACTION_FIELDS = ('id kind purpose question limit_ids allocation state started_at '
                 'finished_at run_id run_manifest consumption consumption_source '
                 'depends_on resumes replay_of result promotion authorisation')


def _action(action, limits, actions, ledger):
    name = action['id']
    fields = ACTION_FIELDS + (' builds_on_partial' if version(ledger) >= 3 else '')
    _object(action, fields, name)
    kind, state = action['kind'], action['state']
    _enum(kind, KINDS, name + '.kind')
    _enum(state, STATES, name + '.state')
    _text(action['purpose'], name + '.purpose')
    _text(action['question'], name + '.question', empty=kind != 'probe')
    if kind == 'engineering' and state not in ('planned', 'abandoned') and not executes(ledger):
        _fail(name, 'engineering is retained as a proposal under session ledger v1; controlled '
                    'execution needs a v2 ledger (R15)')
    if kind == 'collection' and ledger['plan'] is None:
        _fail(name, 'collection is only what a brief declares: the ledger names its plan')

    if not isinstance(action['limit_ids'], list) or len(set(action['limit_ids'])) != len(action['limit_ids']) \
            or any(i not in limits for i in action['limit_ids']):
        _fail(name, 'limit_ids must name declared limits, once each')
    funded = {}
    for limit_id in action['limit_ids']:
        limit = limits[limit_id]
        if (limit['kind'] == 'engineering') != (kind == 'engineering'):
            _fail(name, f'{limit_id} is a {limit["kind"]} limit; a research allowance does '
                        f'not fund engineering and an engineering allowance does not fund research')
        funded[limit['unit']] = limit_id
    allocation = action['allocation']
    if not isinstance(allocation, dict):
        _fail(name, 'allocation is a table of unit -> amount')
    for unit, amount in allocation.items():
        if unit not in funded:
            _fail(name, f'allocation in {unit} names no declared limit in that unit')
        _amount(amount, f'{name}.allocation.{unit}', unit)
    if 'collections' in allocation and (kind != 'collection' or allocation['collections'] != 1):
        _fail(name, 'a collection action is one collection and allocates exactly 1; '
                    f'a {kind} allocates none')
    live = any(allocation.get(unit, 0) > 0 for unit in ACQUISITION)
    if kind in LIVE and not live:
        _fail(name, f'a {kind} spends the marketplace: allocate a finite, positive '
                    f'amount in an acquisition unit')
    if kind not in LIVE and any(unit in ACQUISITION for unit in allocation):
        _fail(name, f'{kind} touches nothing live and may not allocate acquisition units')
    if kind not in LIVE and kind != 'engineering' and (action['run_id'] or action['run_manifest'] is not None):
        _fail(name, f'{kind} has no crawl run to link')
    if kind == 'engineering' and action['run_manifest'] is not None and state not in DONE:
        _fail(name, 'an adaptation record is linked when the attempt finished, not before')

    for field in ('resumes', 'replay_of'):
        _text(action[field], name + '.' + field, empty=True)
        if action[field] and (action[field] not in actions or action[field] == name):
            _fail(name, f'{field} must name another retained action')
    if action['replay_of'] and kind not in ('analysis', 'inspection'):
        _fail(name, 'a replay recomputes over retained bytes; it is not acquisition')
    if action['resumes']:
        predecessor = actions[action['resumes']]
        if predecessor['state'] != 'interrupted' or predecessor['kind'] != kind:
            _fail(name, 'a resumption continues an interrupted action of the same kind')
    if not isinstance(action['depends_on'], list) or any(
            d not in actions or d == name for d in action['depends_on']):
        _fail(name, 'depends_on must name other retained actions')
    partial = partial_evidence(action)
    if not isinstance(partial, list) or len(set(partial)) != len(partial) \
            or any(d not in action['depends_on'] for d in partial):
        _fail(name, 'builds_on_partial names dependencies, once each: a dependent may build '
                    'on the partial evidence of an interrupted predecessor only when it says so')

    for field in ('started_at', 'finished_at'):
        _instant(action[field], name + '.' + field)
    _text(action['run_id'], name + '.run_id', empty=True)
    if action['run_manifest'] is not None:
        _object(action['run_manifest'], 'path sha256', name + '.run_manifest')
        _text(action['run_manifest']['path'], name + '.run_manifest.path')
        if not re.fullmatch('[a-f0-9]{64}', str(action['run_manifest']['sha256'])):
            _fail(name, 'run_manifest.sha256 must be a SHA-256 digest')
    _enum(action['consumption_source'], CONSUMPTION_SOURCES, name + '.consumption_source')
    if action['consumption_source'] == 'adaptation_record' and kind != 'engineering':
        _fail(name, 'an adaptation record accounts for engineering, nothing else')
    if action['consumption_source'] == 'run_manifest' and kind == 'engineering':
        _fail(name, 'engineering is recorded from its adaptation record, not a crawl manifest')
    consumption = action['consumption']
    if not isinstance(consumption, dict):
        _fail(name, 'consumption is a table of unit -> amount or null')
    if state in DONE:
        if set(consumption) != set(allocation):
            _fail(name, 'a finished action records consumption for every allocated unit, '
                        'null where it is unknown')
        for unit, amount in consumption.items():
            if amount is not None:
                _amount(amount, f'{name}.consumption.{unit}', unit)
        if action['consumption_source'] == 'unknown' and any(v is not None for v in consumption.values()):
            _fail(name, 'a known consumption names its source')
        if action['consumption_source'] == 'assumed_allocation' and consumption != allocation:
            _fail(name, 'assumed_allocation means the whole allocation is counted as spent')
        if not action['started_at']:
            _fail(name, 'a finished action records when it started')
    elif consumption or action['consumption_source'] != 'unknown':
        _fail(name, 'consumption is recorded when an action completes or is interrupted')
    if state == 'planned' and action['authorisation'] != '':
        _fail(name, 'a planned action has not been authorised')
    if state != 'planned':
        _enum(action['authorisation'], ('checked', 'unchecked'), name + '.authorisation')

    if action['result'] is not None:
        _object(action['result'], 'summary next_action', name + '.result')
        _text(action['result']['summary'], name + '.result.summary')
        _text(action['result']['next_action'], name + '.result.next_action')
    if action['promotion'] is not None:
        promotion = action['promotion']
        _object(promotion, 'promoted into changed_criteria supplied_candidates assessment', name + '.promotion')
        for flag in ('promoted', 'changed_criteria', 'supplied_candidates'):
            if type(promotion[flag]) is not bool:
                _fail(name, f'promotion.{flag} must be boolean')
        _enum(promotion['into'], ('none', 'plan_inputs'), name + '.promotion.into')
        if promotion['promoted'] != (promotion['into'] != 'none'):
            _fail(name, 'promoted means promoted into the declared inputs, explicitly')
        _text(promotion['assessment'], name + '.promotion.assessment',
              empty=not (promotion['promoted'] or promotion['changed_criteria']
                         or promotion['supplied_candidates']))
    if kind == 'probe' and state == 'completed':
        if action['result'] is None:
            _fail(name, 'a completed probe records the result that determines the next action')
        if action['promotion'] is None:
            _fail(name, 'a completed probe records whether its evidence was promoted and '
                        'whether seeing it changed the criteria or supplied candidates')
    if kind != 'probe' and action['promotion'] is not None:
        _fail(name, 'promotion is a probe record')


def executes(ledger):
    """May engineering run under this ledger? v1 says no, and its author meant no."""
    return version(ledger) >= 2


def partial_evidence(action):
    """The interrupted predecessors this action declares it builds on (v3; else none)."""
    return action.get('builds_on_partial', [])


def load(path):
    try:
        return check(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise SessionError(f'{path}: {exc}') from exc


# ---------------------------------------------------------------------------
# Recording what an action did, from the manifest the crawl wrote
# ---------------------------------------------------------------------------

def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def run_seconds(manifest):
    """Seconds between the manifest's own ``started_at`` and ``finished_at``.

    The run stamps both instants itself, at whole-second resolution, so a
    closed manifest carries its duration whether or not Scrapy's
    ``elapsed_time_seconds`` reached the stats snapshot. ``None`` for a run
    that never closed, or whose instants do not parse or run backwards:
    unknown is not zero.
    """
    try:
        started = datetime.fromisoformat(manifest.get('started_at') or '')
        finished = datetime.fromisoformat(manifest.get('finished_at') or '')
        seconds = (finished - started).total_seconds()
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return int(seconds) if seconds.is_integer() else seconds


def consumption_from_manifest(manifest, units):
    """``{unit: amount or None}`` read from a run manifest, nothing inferred.

    A manifest without ``stats`` -- a crawl that never closed -- reports every
    stats-backed unit as unknown. Unknown is not zero. ``seconds`` has a
    second witness in the manifest itself: when a closed manifest's stats
    lack ``elapsed_time_seconds`` -- until 2026-09-17 the spider snapshotted
    the stats before CoreStats had written it on the same signal, and a stats
    extension can be switched off -- the run's own ``started_at`` and
    ``finished_at`` say how long it ran. That is still the run manifest
    speaking, not the operator.
    """
    consumption = {}
    for unit in units:
        where = OBSERVED.get(unit)
        if unit in ('runs', 'collections'):
            # One manifest is one run, and a collection action is one crawl,
            # finished or stopped: it is consumed the moment it is recorded.
            consumption[unit] = 1
        elif where is None:
            consumption[unit] = None
        else:
            block, key = where
            value = (manifest.get(block) or {}).get(key)
            if unit == 'seconds' and not _number(value):
                value = run_seconds(manifest)
            consumption[unit] = value if _number(value) else None
    return consumption


def enforced_caps(manifest):
    """Which units this crawl's own settings closed on, and at what."""
    settings = manifest.get('settings') or {}
    caps = {}
    for unit, setting in ENFORCEABLE.items():
        value = settings.get(setting)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            caps[unit] = value
    return caps


def record(ledger, action_id, run_directory=None, *, state='', consumption=None,
           assume_allocation=False, started_at='', finished_at='', result=None,
           promotion=None, adaptation_record=None):
    """Record what ``action_id`` did. Mutates and re-validates the ledger.

    From a run directory the state, timestamps and consumption are read from
    its manifest, and the manifest is linked by path and digest. Without one,
    the operator declares the consumption or -- the conservative choice when a
    run left no readable count -- assumes the whole allocation was spent. A
    completed probe also needs its ``result`` and ``promotion`` record, which
    the contract refuses to leave blank.
    """
    check(ledger)
    action = next((a for a in ledger['actions'] if a['id'] == action_id), None)
    if action is None:
        _fail(action_id, 'no such action')
    if action['state'] in DONE or action['state'] == 'abandoned':
        _fail(action_id, f'already {action["state"]}; a second record would count it twice. '
                         f'Resume it as a new action instead')
    if action['kind'] == 'engineering' and not executes(ledger):
        _fail(action_id, 'engineering is a retained proposal under session ledger v1; nothing here '
                         'executes or records it')
    if action['kind'] != 'engineering' and adaptation_record is not None:
        _fail(action_id, 'an adaptation record accounts for engineering, nothing else')
    units = list(action['allocation'])
    if adaptation_record is not None:
        from . import adaptation
        path = Path(adaptation_record)
        record_data = adaptation.load(path)
        if record_data['origin']['session_id'] != ledger['id'] \
                or record_data['origin']['action_id'] != action_id:
            _fail(action_id, f'the adaptation record {record_data["id"]} accounts against '
                             f'{record_data["origin"]["session_id"]}/{record_data["origin"]["action_id"]}, '
                             f'not this action')
        checks = record_data['checks']
        action['run_id'] = record_data['id']
        action['run_manifest'] = {'path': str(path), 'sha256': sha256_file(path)}
        action['state'] = ('interrupted' if record_data['adoption']['decision'] in ('interrupted',)
                           or (checks and checks[-1]['timed_out'] and
                               record_data['adoption']['decision'] == 'pending')
                           else 'completed')
        action['started_at'] = (checks[0]['started_at'] if checks else '') or started_at or action['started_at']
        action['finished_at'] = (checks[-1]['finished_at'] if checks else '') or finished_at or ''
        measured = {'seconds': record_data['consumption']['seconds']}
        action['consumption'] = {unit: measured.get(unit) for unit in units}
        action['consumption_source'] = 'adaptation_record'
    elif run_directory is not None:
        from ..run import load_manifest, run_state
        if action['kind'] not in LIVE:
            _fail(action_id, f'{action["kind"]} has no crawl run to record from')
        path = Path(run_directory) / 'manifest.json'
        try:
            manifest = load_manifest(run_directory)
        except (OSError, ValueError) as exc:
            _fail(action_id, f'{path}: unreadable run manifest ({exc})')
        action['run_id'] = manifest.get('run_id') or ''
        action['run_manifest'] = {'path': str(path), 'sha256': sha256_file(path)}
        action['state'] = 'completed' if run_state(manifest) == 'complete' else 'interrupted'
        action['started_at'] = manifest.get('started_at') or started_at
        action['finished_at'] = manifest.get('finished_at') or ''
        action['consumption'] = consumption_from_manifest(manifest, units)
        action['consumption_source'] = 'run_manifest'
    else:
        if state not in DONE:
            _fail(action_id, 'without a run manifest, say whether the action completed or '
                             'was interrupted')
        action['state'] = state
        action['started_at'] = started_at or action['started_at']
        action['finished_at'] = finished_at or action['finished_at']
        if assume_allocation:
            action['consumption'] = dict(action['allocation'])
            action['consumption_source'] = 'assumed_allocation'
        elif consumption is not None:
            action['consumption'] = {unit: consumption.get(unit) for unit in units}
            action['consumption_source'] = 'declared'
        else:
            action['consumption'] = {unit: None for unit in units}
            action['consumption_source'] = 'unknown'
    if result is not None:
        action['result'] = result
    if promotion is not None:
        action['promotion'] = promotion
    if action['authorisation'] == '':
        # Honest accounting beats a refusal: a run that happened without the
        # check is recorded, and recorded as unchecked.
        action['authorisation'] = 'unchecked'
    return check(ledger)


# ---------------------------------------------------------------------------
# Reconciliation and the next-action check
# ---------------------------------------------------------------------------

def _limits(ledger, reference=None):
    actions = ledger['actions']
    rows = []
    for limit in ledger['limits']:
        unit = limit['unit']
        consumed, unknown, reserved = 0, [], 0
        for action in actions:
            if limit['id'] not in action['limit_ids']:
                continue
            if action['state'] in DONE:
                amount = action['consumption'].get(unit)
                if amount is None:
                    unknown.append(action['id'])
                else:
                    consumed += amount
            elif action['state'] in ('authorised', 'running'):
                reserved += action['allocation'].get(unit, 0)
        total = None if unknown else consumed
        remaining = None if total is None else limit['amount'] - total - reserved
        deadline_passed = bool(limit['deadline'] and reference
                               and delivery.parse_reference(reference) > limit['deadline'])
        rows.append({
            'id': limit['id'], 'kind': limit['kind'], 'unit': unit,
            'amount': limit['amount'], 'mode': limit['mode'],
            'measurement': limit['measurement'],
            'consumed': total, 'unknown': unknown, 'reserved': reserved,
            'remaining': remaining,
            'exhausted': remaining is not None and remaining <= 0,
            'deadline': limit['deadline'], 'deadline_passed': deadline_passed,
            'overshoot': OVERSHOOT.get(unit, '') if limit['mode'] == 'strict_ceiling' else '',
        })
    return rows


def authorise(ledger, action_id, reference=None):
    """May this planned action proceed? A decision about a description, not a run."""
    check(ledger)
    action = next((a for a in ledger['actions'] if a['id'] == action_id), None)
    if action is None:
        _fail(action_id, 'no such action')
    limits = {row['id']: row for row in _limits(ledger, reference)}
    reasons = []
    if action['state'] != 'planned':
        reasons.append(f'already {action["state"]}; only a planned action is authorised')
    if action['kind'] == 'engineering' and not executes(ledger):
        reasons.append('engineering is retained as a proposal against its allowance under '
                       'session ledger v1; controlled execution and its gates are R15 and need '
                       'a v2 ledger, and planning it authorises none of it')
    partial = []
    for name in action['depends_on']:
        predecessor = next(a for a in ledger['actions'] if a['id'] == name)
        if predecessor['state'] == 'completed':
            continue
        if predecessor['state'] == 'interrupted' and name in partial_evidence(action):
            # The companion to the honest state: a stopped crawl's retained
            # pages are evidence, and a dependent that says it builds on
            # partial evidence may -- once the predecessor's consumption is
            # on record, so the interruption cost something the ledger knows.
            if predecessor['consumption_source'] != 'unknown':
                partial.append(name)
                continue
            reasons.append(f'depends on {name}, which is interrupted and declared as partial '
                           f'evidence, but its consumption is unknown: record its run manifest '
                           f'or assume its allocation before building on it')
            continue
        reasons.append(f'depends on {name}, which is {predecessor["state"]}: '
                       f'interrupted or unfinished work is never assumed complete'
                       + (f'. A dependent that builds on its partial evidence declares '
                          f'{name} in builds_on_partial' if predecessor['state'] == 'interrupted'
                          and version(ledger) >= 3 else ''))
    fits = {}
    for limit_id in action['limit_ids']:
        row = limits[limit_id]
        wanted = action['allocation'].get(row['unit'], 0)
        if row['deadline_passed']:
            reasons.append(f'{limit_id}: the deadline {row["deadline"]} has passed at '
                           f'{reference}; time elapsed during an interruption counts, and an '
                           f'extension is an explicit budget revision')
        if row['remaining'] is None:
            reasons.append(f'{limit_id}: consumption cannot be reconciled; '
                           + ', '.join(row['unknown'])
                           + ' recorded no known consumption. Record the run manifest or '
                             'declare the whole allocation consumed before authorising more')
            continue
        if wanted > row['remaining']:
            reasons.append(f'{limit_id}: {wanted:g} {row["unit"]} asked, {row["remaining"]:g} '
                           f'remaining of {row["amount"]:g} ({row["consumed"]:g} consumed, '
                           f'{row["reserved"]:g} reserved). Exhaustion stops new work; '
                           f'completed evidence stands')
        fits[limit_id] = row['remaining'] - wanted
    return {'action': action_id, 'kind': action['kind'], 'authorised': not reasons,
            'reasons': reasons, 'remaining_after': fits, 'partial_evidence': partial}


def reconcile(ledger, reference=None):
    """Every limit's position, every action's fate, and what is prevented."""
    check(ledger)
    limits = _limits(ledger, reference)
    prevented, permitted, proposals = [], [], []
    for action in ledger['actions']:
        if action['kind'] == 'engineering' and action['state'] == 'planned' and not executes(ledger):
            proposals.append(action['id'])
            continue
        if action['state'] != 'planned':
            continue
        decision = authorise(ledger, action['id'], reference)
        (permitted if decision['authorised'] else prevented).append(decision)
    return {
        'reconciled': all(row['remaining'] is not None for row in limits),
        'limits': limits,
        'actions': [{'id': a['id'], 'kind': a['kind'], 'state': a['state'],
                     'authorisation': a['authorisation'],
                     'consumption_source': a['consumption_source'],
                     'resumes': a['resumes'], 'replay_of': a['replay_of']}
                    for a in ledger['actions']],
        'interrupted': [a['id'] for a in ledger['actions'] if a['state'] == 'interrupted'],
        'permitted': permitted, 'prevented': prevented, 'proposals': proposals,
    }


# ---------------------------------------------------------------------------
# Resumption from retained artifacts, without the conversation
# ---------------------------------------------------------------------------

def resume(directory, ledger=None, reference=None, source=delivery.DECLARED,
           input_root=''):
    """Can work on this study resume from what is on disk, and what next?

    Writes nothing. ``ledger`` is a loaded session ledger; when it is ``None``
    the bundle's own snapshot is used, so a study resumes without the working
    ledger and without the conversation.
    """
    from . import bundle, intake, intake_review, audit
    directory = Path(directory)
    findings = []
    manifest, verification = bundle.verify(directory, input_root)
    if verification:
        findings.append({'code': 'artifacts_not_verified',
                         'message': 'retained artifacts do not verify: '
                                    + '; '.join(f['code'] for f in verification)})
    snapshot = directory / SNAPSHOT
    if ledger is None and snapshot.is_file():
        try:
            ledger = load(snapshot)
        except SessionError as exc:
            findings.append({'code': 'session_invalid', 'message': str(exc)})
    if ledger is None:
        findings.append({'code': 'session_missing',
                         'message': 'no session ledger was given and the bundle holds no '
                                    'snapshot: consumed and reserved resources are unknown, '
                                    'and no new acquisition can be authorised'})

    plan_state = {'bundle': None, 'ledger': None, 'match': None}
    if (directory / intake.SNAPSHOT).is_file():
        try:
            plan = intake.load(directory / intake.SNAPSHOT)
            plan_state['bundle'] = {'id': plan['id'], 'revision': plan['revision'],
                                    'sha256': intake.digest(plan)}
        except intake.PlanError as exc:
            findings.append({'code': 'plan_snapshot_invalid', 'message': str(exc)})
    if ledger is not None:
        plan_state['ledger'] = ledger['plan']
        if plan_state['bundle'] and ledger['plan']:
            plan_state['match'] = plan_state['bundle'] == ledger['plan']
            if not plan_state['match']:
                findings.append({
                    'code': 'plan_revision_mismatch',
                    'message': f'the ledger names plan {ledger["plan"]["id"]} revision '
                               f'{ledger["plan"]["revision"]} ({ledger["plan"]["sha256"][:12]}); '
                               f'the bundle holds revision {plan_state["bundle"]["revision"]} '
                               f'({plan_state["bundle"]["sha256"][:12]}). Revise explicitly '
                               f'before resuming'})

    resources, next_actions = None, []
    if ledger is not None:
        resources = reconcile(ledger, reference)
        if not resources['reconciled']:
            findings.append({
                'code': 'unreconciled_consumption',
                'message': 'consumption unknown on '
                           + ', '.join(sorted({a for row in resources['limits'] for a in row['unknown']}))
                           + ': unknown stays unknown, not zero, and no new acquisition is '
                             'authorised until it is recorded'})
        for action in ledger['actions']:
            link = action['run_manifest']
            if link is None:
                continue
            path = Path(link['path'])
            if not path.is_file():
                findings.append({'code': 'run_manifest_missing',
                                 'message': f'{action["id"]}: its run manifest {path} is missing; '
                                            f'the consumption it recorded cannot be re-read'})
            elif sha256_file(path) != link['sha256']:
                findings.append({'code': 'run_manifest_altered',
                                 'message': f'{action["id"]}: {path} is not the manifest this '
                                            f'action was recorded from'})
        for decision in resources['permitted']:
            next_actions.append({**decision, 'status': 'authorisable'})
        for decision in resources['prevented']:
            next_actions.append({**decision, 'status': 'prevented'})
        for name in resources['proposals']:
            next_actions.append({'action': name, 'kind': 'engineering', 'authorised': False,
                                 'status': 'proposal',
                                 'reasons': ['retained against the engineering allowance; '
                                             'controlled execution is R15']})

    review = None
    if (directory / bundle.REVIEW).is_file():
        try:
            review = audit.review_status(json.loads((directory / bundle.REVIEW).read_text(encoding='utf-8')))
        except (ValueError, KeyError, TypeError):
            review = 'unreadable'
    # The intake-phase review beside the final one: a pending or failed intake
    # review is pending review state, and resumption reports it as such.
    plan_review = None
    if (directory / intake_review.SNAPSHOT).is_file():
        try:
            plan_review = intake_review.status(intake_review.read(directory / intake_review.SNAPSHOT))
        except intake_review.IntakeReviewError:
            plan_review = 'unreadable'

    delivery_state = {'latest': None, 'recheck': None}
    # The delivery review of the latest event, beside the other two reviews.
    delivery_review_state = None
    if not verification:
        record_path = directory / delivery.RECORD
        if record_path.is_file():
            from . import delivery_review
            events = delivery.read(record_path)['events']
            latest = events[-1]
            delivery_state['latest'] = {'reference': latest['reference'],
                                        'current_advice': latest['current_advice']}
            delivery_review_state = 'absent'
            reviews_path = directory / delivery_review.RECORD
            if reviews_path.is_file():
                try:
                    found = delivery_review.for_event(
                        delivery_review.read_record(reviews_path), len(events) - 1)
                    delivery_review_state = delivery_review.status(found) if found else 'absent'
                except delivery_review.DeliveryReviewError:
                    delivery_review_state = 'unreadable'
        if reference:
            event = delivery.assess_bundle(directory, reference, source)
            delivery_state['recheck'] = {
                'reference': event['reference'], 'reference_source': source,
                'scope': event['scope'], 'current_advice': event['current_advice'],
                'statement': event['statement'],
                'note': 'a recheck, not a delivery: issue current advice only through '
                        '`study deliver`, which records the event'}

    return {
        'study_id': manifest.get('study_id'),
        'resumable': not findings,
        'findings': findings,
        'plan': plan_state,
        'resources': resources,
        'interrupted': resources['interrupted'] if resources else [],
        'review': review,
        'intake_review': plan_review,
        'delivery_review': delivery_review_state,
        'delivery': delivery_state,
        'next_actions': next_actions,
        'limits': ['Resumption verifies what is on disk. It cannot recover an action that '
                   'was never recorded, and it does not depend on -- or reconstruct -- the '
                   'conversation that produced the plan.'],
    }
