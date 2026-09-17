"""The delivery record: current buying advice as a structural condition.

R13 stage 7. Two different questions need two references, and until now the
study had one. ``analyse()`` measures every observation against the brief's
``as_of`` -- the date the study is *about* -- and that is right for a
historical comparison and useless as a guard: a block computed on a date the
brief's author supplies is self-certifying and will block nothing, forever.
The measurement is in INTAKE §1: five decisive observations thirty-two days
old, the declared policy seven days, and the recommendation standing under a
banner that said it was not current buying advice.

This module adds the second reference and keeps it out of the analysis.

**The scope is declared, not inferred.** A brief says ``freshness.scope =
"current_advice"`` or ``"historical"``; a brief that says nothing is
historical, because the conservative reading of silence is that nobody claimed
this was current. Fresh dates do not turn a regression fixture into buying
evidence: the committed pasta examples pass any age calculation at the date
they were built and are historical because their briefs do not say otherwise.

**The reference comes from the delivery event, not the brief.** ``study
deliver`` reads the execution clock -- or an operator-declared instant, and
says which -- freezes it in ``delivery.json``, and assesses the *governed*
observations against it: the shortlisted and ranked candidates, which are the
decisive comparison inputs, and not an excluded record nobody would act on.
Replay recomputes every event from its frozen reference and never reads
today's clock, so the maintenance gate does not start failing with the passage
of time.

**Current advice is permitted, blocked or not in scope.** Under a
current-advice scope a governed observation older than the policy, an undated
or future-dated one, a reference that precedes ``as_of``, or a withheld
recommendation blocks current advice. ``validate-report`` refuses a
current-advice study without a passing delivery record, and a completed
semantic review does not waive that: the block is structural. A historical
study is delivered as what it is, with its reference date, at any clock.

The record does not enter ``study_id`` (INTAKE §8): the analysis is the same
analysis whenever it is delivered. What the record cannot do is prove the
clock was honest. It prevents silent backdating inside the declared workflow;
it does not establish that an operator who supplied a reference supplied a
true one, and every event says where its reference came from.
"""

import datetime as _dt
import json
from pathlib import Path

from ..provenance import sha256_file

#: The shape of ``delivery.json``. Tracked by the maintenance gate.
DELIVERY_VERSION = 1
RECORD = 'delivery.json'

HISTORICAL = 'historical'
CURRENT_ADVICE = 'current_advice'
SCOPES = (HISTORICAL, CURRENT_ADVICE)

PERMITTED = 'permitted'
BLOCKED = 'blocked'
NOT_IN_SCOPE = 'not_in_scope'

EXECUTION_CLOCK = 'execution_clock'
DECLARED = 'declared'

#: The candidate decisions whose observations the policy governs.
GOVERNED = ('shortlisted', 'ranked')

LIMITS = (
    'The execution clock is not a trusted time service: this record prevents '
    'silent backdating inside the declared workflow and does not prove that a '
    'supplied reference is true.',
    'Ages are whole UTC calendar days between the observation and the '
    'reference. An observation without a parseable timestamp, or dated after '
    'the reference, is unknown, which is not the same as current.',
    'Session consumption and interruption facts travel in the session snapshot '
    'beside this record; the attestation of this event is in the delivery review '
    'bound to it. None of them proves the clock or the declared scope true.',
)


class DeliveryError(ValueError):
    """The record cannot be produced or does not hold as written."""


def parse_reference(text):
    """An ISO 8601 instant with an explicit offset, normalised to UTC seconds."""
    if not isinstance(text, str) or not text.strip():
        raise DeliveryError('a delivery reference is an ISO 8601 instant')
    try:
        moment = _dt.datetime.fromisoformat(text.strip())
    except ValueError as exc:
        raise DeliveryError(f'{text!r}: not an ISO 8601 instant') from exc
    if moment.tzinfo is None:
        raise DeliveryError(f'{text!r}: a delivery reference needs an explicit '
                            f'time zone offset; a naive instant is ambiguous')
    return moment.astimezone(_dt.timezone.utc).replace(microsecond=0).isoformat()


def scope_of(brief_data):
    """``(scope, source)`` from a persisted brief; silence is historical."""
    declared = (brief_data.get('freshness') or {}).get('scope') or ''
    if declared:
        if declared not in SCOPES:
            raise DeliveryError(f'unknown scope {declared!r}')
        return declared, 'brief'
    return HISTORICAL, 'undeclared'


def age_days(fetched_at, reference):
    """Whole UTC days from an observation to the reference; ``None`` if unknown."""
    if not fetched_at:
        return None
    try:
        observed = _dt.datetime.fromisoformat(fetched_at)
        moment = _dt.datetime.fromisoformat(reference)
    except ValueError:
        return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=_dt.timezone.utc)
    days = (moment.astimezone(_dt.timezone.utc).date()
            - observed.astimezone(_dt.timezone.utc).date()).days
    return days if days >= 0 else None


def assess(brief_data, ranking_data, candidates, study_id, report_sha256,
           reference, source, supplied=''):
    """One delivery event, as data. Pure: the reference is an argument."""
    reference = parse_reference(reference)
    if source not in (EXECUTION_CLOCK, DECLARED):
        raise DeliveryError(f'unknown reference source {source!r}')
    scope, scope_source = scope_of(brief_data)
    freshness = brief_data.get('freshness') or {}
    as_of, policy = freshness.get('as_of') or '', freshness.get('price_max_age_days')
    outcome = ranking_data['outcome']['code']
    stop = ranking_data.get('stop') or ''

    governed = []
    for entry in candidates:
        if entry['decision'] not in GOVERNED:
            continue
        age = age_days(entry['fetched_at'], reference)
        governed.append({'asin': entry['asin'], 'decision': entry['decision'],
                         'rank': entry['rank'], 'fetched_at': entry['fetched_at'],
                         'age_days': age,
                         'stale': (policy is not None and age is not None
                                   and age > policy)})
    stale = [g['asin'] for g in governed if g['stale']]
    undated = [g['asin'] for g in governed if g['age_days'] is None]
    counts = {'governed': len(governed), 'stale': len(stale), 'undated': len(undated)}

    blockers = []
    if scope == CURRENT_ADVICE:
        if policy is None:
            blockers.append('the brief declares no age policy; current advice '
                            'needs one with a stated rationale')
        if as_of and reference[:10] < as_of:
            blockers.append(f'the delivery reference {reference} precedes the '
                            f'brief\'s as_of {as_of}: the dates are inconsistent')
        if stale:
            blockers.append(f'{len(stale)} of {len(governed)} governed observation(s) '
                            f'are older than {policy} day(s) at the delivery '
                            f'reference: {", ".join(stale)}')
        if undated:
            blockers.append(f'{len(undated)} governed observation(s) are undated or '
                            f'dated after the reference, so their age is unknown: '
                            f'{", ".join(undated)}')
        if stop:
            blockers.append(f'the recommendation is withheld ({stop}); a bounded '
                            f'finding is not current buying advice')
        status = BLOCKED if blockers else PERMITTED
    else:
        status = NOT_IN_SCOPE

    where = ('the brief declares no scope, so this study is delivered as'
             if scope_source == 'undeclared' else 'the brief declares') \
        if scope == HISTORICAL else 'the brief declares current-advice scope'
    if status == NOT_IN_SCOPE:
        statement = (f'Historical comparison as of {as_of or "an unstated date"}; '
                     f'not current buying advice, however recent the observations '
                     f'are: {where} a historical comparison. Delivered at '
                     f'{reference}, when {counts["stale"]} of {counts["governed"]} '
                     f'governed observation(s) exceeded the declared policy.')
    elif status == PERMITTED:
        statement = (f'Current buying advice is permitted at {reference}: {where}, '
                     f'and all {counts["governed"]} governed observation(s) are '
                     f'within {policy} day(s) of it. This permission is for this '
                     f'delivery event; a later delivery is a new assessment.')
    else:
        statement = (f'No current purchasing recommendation at {reference}: '
                     + '; '.join(blockers) + '. A separately scoped historical '
                     f'comparison as of {as_of or "an unstated date"} may be '
                     f'delivered instead, with that reference date stated.')
    return {
        'reference': reference, 'reference_source': source,
        'reference_as_supplied': supplied or reference, 'time_zone': 'UTC',
        'study_id': study_id, 'report_sha256': report_sha256,
        'scope': scope, 'scope_source': scope_source,
        'as_of': as_of, 'price_max_age_days': policy,
        'rationale': freshness.get('note') or '',
        'analytical_outcome': outcome, 'stop': stop,
        'governed': governed, 'counts': counts, 'blockers': blockers,
        'current_advice': status, 'statement': statement, 'limits': list(LIMITS),
    }


def empty():
    return {'delivery_version': DELIVERY_VERSION, 'events': []}


def latest(record):
    return record['events'][-1] if record and record.get('events') else None


def read(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise DeliveryError(f'{path}: {exc}') from exc
    check_shape(data)
    return data


def check_shape(record):
    if not isinstance(record, dict) or set(record) != {'delivery_version', 'events'}:
        raise DeliveryError('a delivery record has delivery_version and events')
    if record['delivery_version'] != DELIVERY_VERSION:
        raise DeliveryError(f'unsupported delivery_version; expected {DELIVERY_VERSION}')
    if not isinstance(record['events'], list) or not record['events']:
        raise DeliveryError('a delivery record holds at least one event')
    for event in record['events']:
        if not isinstance(event, dict) or event.get('current_advice') not in (
                PERMITTED, BLOCKED, NOT_IN_SCOPE):
            raise DeliveryError('every delivery event records a current-advice status')


def _bundle_inputs(directory):
    from ..run import read_jsonl
    from . import bundle
    directory = Path(directory)
    brief_data = json.loads((directory / bundle.BRIEF).read_text(encoding='utf-8'))
    ranking_data = json.loads((directory / bundle.RANKING).read_text(encoding='utf-8'))
    manifest = bundle.load_manifest(directory)
    return (brief_data, ranking_data, list(read_jsonl(directory / bundle.CANDIDATES)),
            manifest['study_id'], sha256_file(directory / bundle.REPORT))


def assess_bundle(directory, reference, source, supplied=''):
    """The event a delivery of this bundle at ``reference`` produces."""
    return assess(*_bundle_inputs(directory), reference, source, supplied)


def check(record, directory):
    """Every event re-derives from its own frozen reference and this bundle.

    Never reads the clock. A record whose events do not reproduce, or whose
    report digest is not this report's, does not hold.
    """
    check_shape(record)
    inputs = _bundle_inputs(directory)
    report_sha256 = inputs[-1]
    for position, event in enumerate(record['events']):
        if event.get('report_sha256') != report_sha256:
            raise DeliveryError(f'delivery event {position} belongs to different '
                                f'report bytes: the report changed after delivery')
        expected = assess(*inputs, event.get('reference'), event.get('reference_source'),
                          event.get('reference_as_supplied', ''))
        if expected != event:
            moved = sorted(k for k in set(expected) | set(event)
                           if expected.get(k) != event.get(k))
            raise DeliveryError(f'delivery event {position} does not re-derive from '
                                f'its frozen reference: {", ".join(moved)} moved')
