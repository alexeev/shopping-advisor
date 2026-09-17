"""The intake review: a separate, digest-bound semantic pass over a plan revision.

R13 stage 9. The plan contract (stage 5) checks that retained structure is
well formed and that every executable mapping still resolves; the stage gates
(stage 6) enforce what the plan recorded. Neither can tell that the plan is
*right*: that an instruction in the user's words is missing from it, that a
requirement's role is not what those words support, that a control which runs
correctly answers the wrong question -- a purchase budget mapped onto the
per-kilogram cap passes the gates as ``enforced`` -- or that an assumed default
was indefensible. INTAKE §12 calls those the interpretation and
semantic-execution questions and says they are review, not machine-decidable.

This module is that review's record, and the checks that keep it honest.

**It binds what it reviewed.** The review names the plan id, revision and
canonical digest, the digests of the retained user evidence and of the
requirements with their resolved control metadata, the read-back response
status, and the digest of the category's live control catalogue. A review
whose plan digest is not this plan's is superseded and its findings are not
this revision's; a review whose catalogue digest is not the live one was
judging adequacy against other controls. Both refuse rather than carry a
``pass`` forward, because a finding reused across changed inputs is the copied
approval INTAKE §11 forbids.

**It cannot claim what the evidence does not let it see.** Redactions that the
plan itself marked as limiting review, and missing context, are recomputed from
the plan and must be recorded in the review as recorded. While any such limit
stands, the omissions check -- and, for a redaction, the faithfulness check --
cannot be ``pass``: the reviewer records ``limited`` or ``fail``. A review of
the plan alone cannot detect an instruction missing from it (INTAKE §12), and
this artifact does not pretend otherwise.

**A completed check is a finding, not a badge.** Every non-pending check names
the reviewer and records findings. A failed omission points at the retained
user messages that carry the missing instruction; a failed faithfulness,
adequacy, assumption or stage-effect check points at the requirements it
concerns. Those references must resolve in the plan, so a failure is always
something a later reader can go and look at.

**What consumes it.** ``study run --intake-review`` snapshots the review into
the bundle as ``intake-review.json``, digest-listed in the manifest, and
refuses to run a study on a plan revision whose review records a failure: a
recorded blocker at intake is a planning outcome, not authorisation to
proceed through it (INTAKE §5). ``verify`` checks that the snapshot binds the
bundle's own plan and the live catalogue. ``validate-report`` fails a bundle
whose intake review records a failure and, under ``--require-review``,
requires a plan-backed bundle to carry a passing one. ``resume`` reports its
state beside the final review's. It enters neither ``study_id`` nor the report
bytes: approval travels in review artifacts and is checked before delivery,
never rendered into the report it approves (INTAKE §11).

**What rests on it.** Stage 10 moved the final semantic review to v2 so that
it binds this artifact and records the intake findings it rests on: final
approval requires a passing intake review, and a changed intake review
supersedes a completed final one (CONTRACT §14). Findings are not reused
across plan revisions -- the plan digest refuses a review of another revision,
and a revision is re-reviewed.
"""

import json
from pathlib import Path
import re

from ..analysis.category import known
from . import controls, intake

#: The shape of ``intake-review.json``. Tracked by the maintenance gate.
INTAKE_REVIEW_VERSION = 1
SNAPSHOT = 'intake-review.json'

#: The closed check set. INTAKE §11: omissions, faithfulness, adequacy,
#: assumptions and stage effects. A review with another key set is not one.
CHECKS = ('omissions', 'faithfulness', 'adequacy', 'assumptions', 'stage_effects')

PENDING = 'pending'
PASS = 'pass'
FAIL = 'fail'
#: Could not be established from the retained evidence. Not a pass.
LIMITED = 'limited'
STATUSES = (PENDING, PASS, FAIL, LIMITED)

#: A failure here concerns recorded requirements and must name them.
REQUIREMENT_CHECKS = ('faithfulness', 'adequacy', 'assumptions', 'stage_effects')
#: A failure here is an instruction the plan lacks; it must point at the
#: retained user messages that carry it.
EVIDENCE_CHECKS = ('omissions',)

#: What each review limit forbids the reviewer to claim. A redaction removed
#: wording, so neither completeness nor the reading of retained wording can be
#: established; missing context removes whole messages, so only completeness
#: is in doubt.
BLOCKED_BY = {'redaction': ('omissions', 'faithfulness'),
              'missing_context': ('omissions',)}

#: Not stored in the artifact -- a wording change is not a new question -- but
#: printed with the template so the reviewer answers the contract's questions.
QUESTIONS = {
    'omissions': ('Does every instruction in the retained user messages that bears on '
                  'the purchase appear as a requirement, or as context marked '
                  'non-operative, and is nothing decisive missing?'),
    'faithfulness': ('Is each requirement\'s statement, role, decisiveness and settlement '
                     'what the user\'s words support, does the quoted wording support it, '
                     'and is nothing the agent introduced presented as the user\'s?'),
    'adequacy': ('Does each resolved control answer the requirement it is mapped to, and '
                 'is each unsupported disposition a genuine absence of an executable '
                 'method rather than missing evidence?'),
    'assumptions': ('Does each assumed or delegated requirement rest on a defensible '
                    'default with its rationale and if-wrong consequence recorded, and '
                    'does no indefensible default proceed on disclosure alone?'),
    'stage_effects': ('Are the stage effects recorded for each operative requirement the '
                      'ones its meaning implies, distinct per stage, neither read as a '
                      'universal ban nor applied only at the last stage?'),
}


class IntakeReviewError(ValueError):
    """The review does not hold as written, or does not belong to this plan."""


def _fail(where, message):
    raise IntakeReviewError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly these fields: {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected nonempty text' if not empty else 'expected text')


def _sha(value, where, empty=False):
    if empty and value == '':
        return
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        _fail(where, 'expected a SHA-256 digest')


def _ids(value, available, where):
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        _fail(where, 'expected a list of ids')
    if len(set(value)) != len(value) or set(value) - set(available):
        _fail(where, 'duplicate or unresolved references')


def digest(data):
    """Canonical JSON content digest, independent of path and whitespace."""
    try:
        return intake.digest(data)
    except intake.PlanError as exc:
        raise IntakeReviewError(str(exc)) from exc


# ---------------------------------------------------------------------------
# What the review binds, recomputed from the plan
# ---------------------------------------------------------------------------

def catalogue_digest(category):
    """The live control catalogue this category's adequacy is judged against.

    Empty for an unregistered category: there is no catalogue, and the review
    records that adequacy was judged against none.
    """
    if category not in known():
        return ''
    return digest(controls.catalogue(category))


def basis(plan):
    """The targets INTAKE §11 names, each as a digest a reader can compare."""
    return {'user_evidence_sha256': digest(plan['user_evidence']),
            'requirements_sha256': digest(plan['requirements']),
            'readback_response': plan['readback']['response']['status'],
            'catalogue_sha256': catalogue_digest(plan['category'])}


def review_limits(plan):
    """What the retained evidence does not let a reviewer see, from the plan.

    Recomputed, never authored: a review that omitted one of these would be
    certifying its own blind spot.
    """
    limits = []
    evidence = plan['user_evidence']
    if evidence['missing_context'].strip():
        limits.append({'kind': 'missing_context', 'message_id': '',
                       'description': evidence['missing_context']})
    for message in evidence['messages']:
        for redaction in message['redactions']:
            if redaction['limits_review']:
                limits.append({'kind': 'redaction', 'message_id': message['id'],
                               'description': redaction['description']})
    return limits


def template(plan):
    """A pending review bound to this plan revision. Pending is not approval."""
    intake.check(plan)
    return {'intake_review_version': INTAKE_REVIEW_VERSION,
            'plan': {'id': plan['id'], 'revision': plan['revision'],
                     'sha256': intake.digest(plan)},
            'basis': basis(plan),
            'review_limits': review_limits(plan),
            'reviewer': '',
            'checks': {name: {'status': PENDING, 'findings': '',
                              'requirement_ids': [], 'message_ids': []}
                       for name in CHECKS},
            'unresolved_limits': []}


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

def check_shape(review):
    """Well-formed, without a plan. Bindings need :func:`check_review`."""
    _object(review, 'intake_review_version plan basis review_limits reviewer checks '
                    'unresolved_limits', 'intake review')
    if type(review['intake_review_version']) is not int \
            or review['intake_review_version'] != INTAKE_REVIEW_VERSION:
        _fail('intake_review_version', f'unsupported version; expected {INTAKE_REVIEW_VERSION}')
    _object(review['plan'], 'id revision sha256', 'plan')
    _text(review['plan']['id'], 'plan.id')
    if type(review['plan']['revision']) is not int or review['plan']['revision'] < 1:
        _fail('plan.revision', 'expected a positive integer')
    _sha(review['plan']['sha256'], 'plan.sha256')
    _object(review['basis'], 'user_evidence_sha256 requirements_sha256 readback_response '
                             'catalogue_sha256', 'basis')
    _sha(review['basis']['user_evidence_sha256'], 'basis.user_evidence_sha256')
    _sha(review['basis']['requirements_sha256'], 'basis.requirements_sha256')
    _sha(review['basis']['catalogue_sha256'], 'basis.catalogue_sha256', empty=True)
    _text(review['basis']['readback_response'], 'basis.readback_response')
    if not isinstance(review['review_limits'], list):
        _fail('review_limits', 'expected a list')
    for limit in review['review_limits']:
        _object(limit, 'kind message_id description', 'review_limits')
        if limit['kind'] not in BLOCKED_BY:
            _fail('review_limits', 'expected one of: ' + ', '.join(BLOCKED_BY))
        _text(limit['message_id'], 'review_limits.message_id', empty=True)
        _text(limit['description'], 'review_limits.description')
    _text(review['reviewer'], 'reviewer', empty=True)
    if not isinstance(review['unresolved_limits'], list) \
            or any(not isinstance(v, str) or not v.strip() for v in review['unresolved_limits']):
        _fail('unresolved_limits', 'expected a list of nonempty text')
    checks = review['checks']
    if not isinstance(checks, dict) or set(checks) != set(CHECKS):
        _fail('checks', 'expected exactly these checks: ' + ', '.join(CHECKS))
    for name, item in checks.items():
        _object(item, 'status findings requirement_ids message_ids', 'checks.' + name)
        if item['status'] not in STATUSES:
            _fail('checks.' + name, 'expected one of: ' + ', '.join(STATUSES))
        _text(item['findings'], f'checks.{name}.findings', empty=True)
        if item['status'] != PENDING:
            if not review['reviewer'].strip() or not item['findings'].strip():
                _fail('checks.' + name, 'a completed intake review names its reviewer and '
                                        'records findings, not a bare approval')
        elif item['findings'].strip() or item['requirement_ids'] or item['message_ids']:
            _fail('checks.' + name, 'a pending check records nothing yet')
    digest(review)
    return review


def check_review(review, plan):
    """Well-formed, bound to this plan revision and the live catalogue, and honest.

    Raises :class:`IntakeReviewError` with the first reason it does not hold.
    A review that holds may still be pending, limited or failed; that is its
    :func:`status`, not a defect.
    """
    check_shape(review)
    intake.check(plan)
    expected = {'id': plan['id'], 'revision': plan['revision'], 'sha256': intake.digest(plan)}
    if review['plan'] != expected:
        _fail('plan', f'this review binds plan {review["plan"]["id"]} revision '
                      f'{review["plan"]["revision"]} ({review["plan"]["sha256"][:12]}); the '
                      f'plan at hand is {expected["id"]} revision {expected["revision"]} '
                      f'({expected["sha256"][:12]}). The binding is superseded and its '
                      f'findings are not this revision\'s: review the revision, do not '
                      f'copy a pass forward')
    live = basis(plan)
    for key in ('user_evidence_sha256', 'requirements_sha256', 'readback_response'):
        if review['basis'][key] != live[key]:
            _fail('basis.' + key, 'does not match the plan this review claims to bind')
    if review['basis']['catalogue_sha256'] != live['catalogue_sha256']:
        _fail('basis.catalogue_sha256',
              f'the {plan["category"]} control catalogue changed since this review '
              f'(recorded {review["basis"]["catalogue_sha256"][:12] or "none"}, live '
              f'{live["catalogue_sha256"][:12] or "none"}): adequacy was judged against '
              f'other controls. Reassess it against the live catalogue')
    if review['review_limits'] != review_limits(plan):
        _fail('review_limits', 'do not match the plan\'s review-limiting redactions and '
                               'missing context: what was removed is recorded as removed, '
                               'and the review says so')
    requirements = [r['id'] for r in plan['requirements']]
    messages = [m['id'] for m in plan['user_evidence']['messages']]
    blocked = {name for limit in review['review_limits'] for name in BLOCKED_BY[limit['kind']]}
    for name, item in review['checks'].items():
        _ids(item['requirement_ids'], requirements, f'checks.{name}.requirement_ids')
        _ids(item['message_ids'], messages, f'checks.{name}.message_ids')
        if item['status'] == FAIL:
            if name in REQUIREMENT_CHECKS and not item['requirement_ids']:
                _fail('checks.' + name, 'a failed check names the requirements it concerns')
            if name in EVIDENCE_CHECKS and not item['message_ids']:
                _fail('checks.' + name, 'a missing instruction is pointed at in the retained '
                                        'user messages that carry it')
        if item['status'] == PASS and name in blocked:
            _fail('checks.' + name, 'cannot be established while a redaction limits review '
                                    'or context is missing: record limited or fail, and say '
                                    'what could not be seen')
    return review


def status(review):
    """One word for the review: ``fail`` > ``pending`` > ``limited`` > ``pass``."""
    statuses = [item['status'] for item in review['checks'].values()]
    for word in (FAIL, PENDING, LIMITED):
        if word in statuses:
            return word
    return PASS


def failures(review):
    """``(check, findings)`` for every failed check, for a refusal to quote."""
    return [(name, item['findings']) for name, item in review['checks'].items()
            if item['status'] == FAIL]


def read(path):
    """Read and shape-check a review file. Binding needs the plan."""
    try:
        return check_shape(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise IntakeReviewError(f'{path}: {exc}') from exc


def load(path, plan):
    """Read a review file and check it against ``plan``."""
    review = read(path)
    try:
        return check_review(review, plan)
    except IntakeReviewError as exc:
        raise IntakeReviewError(f'{path}: {exc}') from exc
