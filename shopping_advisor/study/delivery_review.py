"""The delivery review: a scoped, digest-bound re-check at one delivery event.

R13 stage 10. The delivery record (stage 7) makes current advice a structural
condition: an event is ``permitted``, ``blocked`` or ``not_in_scope`` from the
frozen reference and the governed observations, and nothing a reviewer writes
can lift a block. What the record cannot do is judge -- whether the declared
age bound is adequate for *this* purchase, whether the governed observations
still apply to the buyer's marketplace and variant, whether the statement
handed over says no more than the event permits -- or attest what no check can
establish: that the reference was the clock honestly read and that the brief's
declared scope is true (INTAKE §9).

INTAKE §8 sets the shape. A previously issued report does not stay current;
reusing it for a later purchase is a new delivery event, and if the policy
passes, the new **delivery binding** is reviewed as a scoped re-check. It must
not require re-writing the semantic findings for an analysis whose inputs,
decisions and report bytes have not moved -- otherwise every re-delivery of an
unchanged study costs a full human review. So the delivery record and the
session snapshot are bound *here*, per event, and never into the final
semantic review's basis (:mod:`inventory`).

**One review per event.** A review names the event by position and canonical
digest, the report bytes, the semantic review it relies on with its status,
and the session and intake-review snapshots when the bundle holds them. A
later event is a new assessment and needs its own review; the earlier one
stays bound to the earlier event.

**Three checks and an attestation.** ``freshness`` (is the declared age bound
adequate for advice issued at this reference, and are the right observations
governed), ``applicability`` (do the governed observations and the declared
scope still fit this buyer's marketplace, region and variant), and
``conclusion_presentation`` (does the delivered statement claim no more than
the event permits). A completed review names its reviewer and records
findings. Approval additionally requires the deliverer to attest, by name,
that the reference was read honestly and that the declared scope is true;
an attestation is a signed statement, not a proof, and the record says so.

**What consumes it.** ``study delivery-review-template`` writes a pending
review bound to the latest event; ``study review-delivery`` attaches one after
checking its bindings. ``verify`` reports a review whose bindings do not hold.
``validate-report`` fails a bundle whose latest event carries a failed review
and, under ``--require-review``, requires a passing one for a permitted
current-advice event; a historical study is asked for nothing. ``resume``
reports the state. The review enters neither ``study_id`` nor the report.
"""

import json
from pathlib import Path

from ..provenance import sha256_file, sha256_text

#: The shape of ``delivery-review.json``. Tracked by the maintenance gate.
DELIVERY_REVIEW_VERSION = 1
RECORD = 'delivery-review.json'

CHECKS = ('freshness', 'applicability', 'conclusion_presentation')
QUESTIONS = {
    'freshness': 'Is the declared age bound adequate for advice issued at this '
                 'reference, and does the event govern the observations the buyer '
                 'would act on?',
    'applicability': 'Do the governed observations and the declared scope still '
                     'fit this buyer: marketplace, delivery region, variant and '
                     'pack identity?',
    'conclusion_presentation': 'Does the statement handed over at this event claim '
                               'no more than the event permits, and is a withheld '
                               'recommendation still withheld?',
}
#: What the deliverer attests. Neither can be checked by software (INTAKE §9).
ATTESTED = ('reference_read_honestly', 'declaration_true')

PENDING, PASS, FAIL = 'pending', 'pass', 'fail'
STATUSES = (PENDING, PASS, FAIL)

LIMITS = (
    'An attestation is a statement signed by name, not a proof: it records who '
    'vouched for the reference and the declared scope, and it does not make '
    'either true.',
    'This review binds one delivery event. A later delivery is a new event and '
    'needs its own review; nothing here carries forward.',
)


class DeliveryReviewError(ValueError):
    """The review cannot be produced, or does not hold as written."""


def _fail(where, message):
    raise DeliveryReviewError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly these fields: {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected nonempty text' if not empty else 'expected text')


def _sha(value, where, empty=False):
    if value == '' and empty:
        return
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        _fail(where, 'expected a SHA-256 digest')


def digest(data):
    """Canonical JSON content digest, independent of path and whitespace."""
    try:
        return sha256_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise DeliveryReviewError(f'a review must be finite JSON data: {exc}') from exc


# ---------------------------------------------------------------------------
# What a review binds, recomputed from the bundle
# ---------------------------------------------------------------------------

def binding(directory, position=None):
    """The facts a review of event ``position`` binds, read from the bundle.

    ``position`` defaults to the latest event. Raises when the bundle holds no
    delivery record or no such event: there is nothing to review.
    """
    from . import audit, delivery, intake_review, session
    from .inventory import REPORT, REVIEW
    directory = Path(directory)
    path = directory / delivery.RECORD
    if not path.is_file():
        raise DeliveryReviewError(f'{directory}: no {delivery.RECORD}; deliver the study '
                                  f'before reviewing a delivery')
    events = delivery.read(path)['events']
    if position is None:
        position = len(events) - 1
    if not isinstance(position, int) or isinstance(position, bool) \
            or position < 0 or position >= len(events):
        raise DeliveryReviewError(f'{directory}: no delivery event {position!r}; the record '
                                  f'holds {len(events)}')
    event = events[position]
    review_path = directory / REVIEW
    try:
        semantic = json.loads(review_path.read_text(encoding='utf-8'))
        semantic_status = audit.review_status(semantic)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DeliveryReviewError(f'{review_path}: unreadable semantic review ({exc})') from exc
    session_path = directory / session.SNAPSHOT
    intake_path = directory / intake_review.SNAPSHOT
    return {
        'event': position,
        'reference': event['reference'],
        'current_advice': event['current_advice'],
        'event_sha256': digest(event),
        'report_sha256': sha256_file(directory / REPORT),
        'semantic_review': {'status': semantic_status, 'sha256': sha256_file(review_path)},
        'session_sha256': sha256_file(session_path) if session_path.is_file() else '',
        'intake_review_sha256': sha256_file(intake_path) if intake_path.is_file() else '',
    }


def template(directory, position=None):
    """A pending review bound to one event of this bundle."""
    return {
        'delivery_review_version': DELIVERY_REVIEW_VERSION,
        **binding(directory, position),
        'reviewer': '',
        'checks': {name: {'status': PENDING, 'findings': ''} for name in CHECKS},
        'attestation': {'by': '', **{name: None for name in ATTESTED}, 'statement': ''},
        'unresolved_limits': [],
        'limits': list(LIMITS),
    }


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

def check_shape(review):
    """Well formed, and complete where it claims to be. Binding needs the bundle."""
    _object(review, 'delivery_review_version event reference current_advice event_sha256 '
                    'report_sha256 semantic_review session_sha256 intake_review_sha256 '
                    'reviewer checks attestation unresolved_limits limits', 'delivery review')
    if type(review['delivery_review_version']) is not int \
            or review['delivery_review_version'] != DELIVERY_REVIEW_VERSION:
        _fail('delivery_review_version', f'unsupported version; expected {DELIVERY_REVIEW_VERSION}')
    if type(review['event']) is not int or review['event'] < 0:
        _fail('event', 'expected a non-negative event position')
    _text(review['reference'], 'reference')
    _text(review['current_advice'], 'current_advice')
    _sha(review['event_sha256'], 'event_sha256')
    _sha(review['report_sha256'], 'report_sha256')
    _object(review['semantic_review'], 'status sha256', 'semantic_review')
    if review['semantic_review']['status'] not in STATUSES:
        _fail('semantic_review.status', 'expected one of: ' + ', '.join(STATUSES))
    _sha(review['semantic_review']['sha256'], 'semantic_review.sha256')
    _sha(review['session_sha256'], 'session_sha256', empty=True)
    _sha(review['intake_review_sha256'], 'intake_review_sha256', empty=True)
    _text(review['reviewer'], 'reviewer', empty=True)
    if not isinstance(review['checks'], dict) or set(review['checks']) != set(CHECKS):
        _fail('checks', 'expected exactly: ' + ', '.join(CHECKS))
    completed = False
    for name in CHECKS:
        item = review['checks'][name]
        _object(item, 'status findings', 'checks.' + name)
        if item['status'] not in STATUSES:
            _fail('checks.' + name, 'expected one of: ' + ', '.join(STATUSES))
        _text(item['findings'], f'checks.{name}.findings', empty=True)
        if item['status'] != PENDING:
            completed = True
            if not review['reviewer'].strip() or not item['findings'].strip():
                _fail('checks.' + name, 'a completed check needs a reviewer and findings, '
                                        'not a bare approval')
        elif item['findings'].strip():
            _fail('checks.' + name, 'a pending check records nothing')
    attestation = review['attestation']
    _object(attestation, 'by ' + ' '.join(ATTESTED) + ' statement', 'attestation')
    _text(attestation['by'], 'attestation.by', empty=True)
    _text(attestation['statement'], 'attestation.statement', empty=True)
    for name in ATTESTED:
        if attestation[name] is not None and not isinstance(attestation[name], bool):
            _fail('attestation.' + name, 'expected true, false or null')
    if completed:
        if not attestation['by'].strip() or any(attestation[n] is None for n in ATTESTED):
            _fail('attestation', 'a completed review records who delivered it and whether '
                                 'the reference was read honestly and the declared scope '
                                 'is true; null is not an answer')
    if status(review) == PASS and not all(attestation[n] is True for n in ATTESTED):
        _fail('attestation', 'a passing delivery review needs both attestations true: a '
                             'delivery nobody will vouch for is not approved')
    if not isinstance(review['unresolved_limits'], list) \
            or any(not isinstance(v, str) for v in review['unresolved_limits']):
        _fail('unresolved_limits', 'expected a list of text')
    if review['limits'] != list(LIMITS):
        _fail('limits', 'the recorded limits are this contract\'s, not the reviewer\'s')
    return review


def check_binding(review, directory):
    """Does this review bind an event this bundle holds, as it stands now?"""
    live = binding(directory, review['event'])
    moved = [key for key, value in live.items() if review[key] != value]
    if moved:
        _fail(', '.join(moved), f'do(es) not match delivery event {review["event"]} of this bundle '
                                f'as it stands: the review is superseded and its findings are not '
                                f'this event\'s')
    return review


def status(review):
    """One word: ``fail`` > ``pending`` > ``pass``."""
    statuses = [item['status'] for item in review['checks'].values()]
    return FAIL if FAIL in statuses else (PENDING if PENDING in statuses else PASS)


def read(path):
    """Read and shape-check one review file. Binding needs the bundle."""
    try:
        return check_shape(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise DeliveryReviewError(f'{path}: {exc}') from exc


def load(path, directory):
    """Read one review file and check it against the bundle."""
    review = read(path)
    try:
        return check_binding(review, directory)
    except DeliveryReviewError as exc:
        raise DeliveryReviewError(f'{path}: {exc}') from exc


# ---------------------------------------------------------------------------
# The record inside the bundle: one review per reviewed event
# ---------------------------------------------------------------------------

def empty():
    return {'delivery_review_version': DELIVERY_REVIEW_VERSION, 'reviews': []}


def read_record(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise DeliveryReviewError(f'{path}: {exc}') from exc
    if not isinstance(data, dict) or set(data) != {'delivery_review_version', 'reviews'}:
        raise DeliveryReviewError('a delivery review record has delivery_review_version and reviews')
    if data['delivery_review_version'] != DELIVERY_REVIEW_VERSION:
        raise DeliveryReviewError(f'unsupported delivery_review_version; expected '
                                  f'{DELIVERY_REVIEW_VERSION}')
    if not isinstance(data['reviews'], list) or not data['reviews']:
        raise DeliveryReviewError('a delivery review record holds at least one review')
    positions = []
    for review in data['reviews']:
        check_shape(review)
        if review['event'] in positions:
            raise DeliveryReviewError(f'two reviews of delivery event {review["event"]}: '
                                      f'attach a replacement, do not duplicate')
        positions.append(review['event'])
    return data


def for_event(record, position):
    """The review of event ``position``, or ``None``."""
    return next((r for r in record['reviews'] if r['event'] == position), None)


def attach(record, review):
    """``record`` with ``review`` in place of any earlier review of its event."""
    record['reviews'] = [r for r in record['reviews'] if r['event'] != review['event']]
    record['reviews'].append(review)
    record['reviews'].sort(key=lambda r: r['event'])
    return record


def check(record, directory):
    """Every review in the record binds its event as this bundle stands now."""
    for review in record['reviews']:
        try:
            check_binding(review, directory)
        except DeliveryReviewError as exc:
            raise DeliveryReviewError(f'review of delivery event {review["event"]}: {exc}') from exc
