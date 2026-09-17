"""Stage gates: intake readiness, comparison support and the conclusion.

R13 stage 6. The refusal matrix of INTAKE §3 applied at the stages of §5, for
a plan-backed study only. Without a plan nothing here runs, and a study decides
and renders exactly as it did before: the plan is an optional input to
``analyse()``, as the evidence ledger is.

What the gates consume is the plan's recorded semantics -- role, settlement,
decisiveness and assessment path -- and what they refuse on is narrow:

* A **decisive requirement with no executable control** withholds the
  full-request purchasing recommendation. It does not stop the analysis: the
  ranking on the available axis survives as a *bounded finding* that names
  the narrower question it answers, under its own heading and never in the
  place a recommendation occupies.
* A **decisive preference or objective the declared axis does not answer**
  refuses the substitution at comparison support. "Cheapest once delivered"
  over records with no shipping data is the case this exists for: item price
  per kilogram is reported as what it is, not as the answer.
* A **decisive hard constraint whose bound assessment failed** cannot be met,
  and the refusal is presented without a shortlist beneath it.
* A **decisive requirement awaiting its evidence assessment** withholds the
  recommendation for a different reason -- the method exists and the evidence
  has not been assessed -- and is routed to collection or a coverage stop,
  never to a capability gap.

Stop reasons are recorded separately from the analytical outcome: a study can
compute a clear leader on price per kilogram *and* withhold the recommendation,
and both facts are kept. The gates read no narrative field. ``cost_basis``,
``unacceptable`` and ``limits`` remain prose, and a requirement that is only
written there is a requirement the plan never recorded, which software cannot
detect. Nor can the gates tell that a control answers the wrong question: a
budget mapped onto a per-kilogram cap passes here as enforced. That is
semantic review, and the report says so.
"""

from ..analysis.category import known
from . import intake

#: The persisted shape of the ``gates`` block. Tracked by the maintenance gate.
STAGE_GATES_VERSION = 1

# --- dispositions of one requirement -------------------------------------
ENFORCED = 'enforced'
ASSESSED = 'assessed'
AWAITING_EVIDENCE = 'awaiting_evidence'
UNSUPPORTED = 'unsupported'
NON_OPERATIVE = 'non_operative'
INACTIVE = 'inactive'

# --- routing, INTAKE §3's three outcomes that look alike -------------------
EXECUTE = 'execute'
COLLECT_OR_STOP = 'collect_or_stop'
GAP_PLAN = 'gap_plan'
NO_ROUTE = 'none'

# --- stops, kept apart from the three analytical outcomes -------------------
REQUIREMENT_FAILED = 'requirement_failed'
REQUIREMENT_UNSUPPORTED = 'requirement_unsupported'
REQUIREMENT_UNASSESSED = 'requirement_unassessed'
STOPS = (REQUIREMENT_FAILED, REQUIREMENT_UNSUPPORTED, REQUIREMENT_UNASSESSED)

# --- intake readiness, staged and naming its next action -------------------
BLOCKED = 'blocked'
BOUNDED = 'bounded'
FULL_REQUEST = 'full_request'

# --- what the conclusion may present -----------------------------------------
PERMIT_RECOMMENDATION = 'recommendation'
PERMIT_SHORTLIST = 'shortlist'
PERMIT_REFUSAL = 'refusal'
PERMIT_BOUNDED_FINDING = 'bounded_finding'

#: Where each executable control takes effect, in the plan's stage vocabulary.
CONTROL_STAGE = {'candidate_filter': 'candidate_assessment',
                 'ranked_row_filter': 'candidate_assessment',
                 'ranking': 'comparison'}

#: The stages an offline ``study run`` performs. An effect recorded at any
#: other stage is retained for the action that performs it; it is not executed
#: here and is not claimed to be.
PERFORMED = ('candidate_assessment', 'comparison', 'conclusion')

AXIS_CONTROLS = ('value_usability', 'max_axis_value')


def disposition(requirement):
    """One word for what happens to this requirement, from its assessment."""
    assessment = requirement['assessment']
    path, state = assessment['path'], assessment['state']
    if path in ('withdrawn', 'revised'):
        return INACTIVE
    if path == 'not_applicable':
        return NON_OPERATIVE
    if path == 'control':
        return ENFORCED
    if path == 'evidence_review':
        return AWAITING_EVIDENCE if state == 'not_assessed' else ASSESSED
    return UNSUPPORTED


def routing(word):
    """INTAKE §3: execute, collect or stop on coverage, or plan the gap."""
    return {ENFORCED: EXECUTE, ASSESSED: EXECUTE,
            AWAITING_EVIDENCE: COLLECT_OR_STOP,
            UNSUPPORTED: GAP_PLAN}.get(word, NO_ROUTE)


def _failed(requirement, word):
    return (requirement['decisive'] and requirement['role'] == 'hard_constraint'
            and word in (ENFORCED, ASSESSED)
            and requirement['assessment']['state'] == 'failed')


def _reason(requirement, word):
    """Why this requirement restricts the conclusion, in one sentence."""
    assessment = requirement['assessment']
    if word == UNSUPPORTED:
        return assessment['gap']['reason']
    if word == AWAITING_EVIDENCE:
        return ('an evidence-and-review method exists and the evidence has not '
                'been assessed; collect, probe or stop on coverage')
    if word == ASSESSED:
        if assessment['state'] == 'failed':
            return 'the bound evidence assessment failed: the requirement is not met'
        if assessment['state'] == 'unknown':
            return 'the bound evidence assessment could not decide'
        return ('a reviewed finding supports a scoped explanation, not automated '
                'selection: no path carries it into eligibility or ordering')
    if word == ENFORCED and assessment['state'] == 'failed':
        return 'the bound evidence assessment failed: the requirement is not met'
    return ''


def _stages(requirement, word):
    executed = set()
    if word == ENFORCED:
        executed = {CONTROL_STAGE[m['metadata']['stage']]
                    for m in requirement['assessment']['controls']}
    rows = []
    for effect in requirement['effects']:
        stage = effect['stage']
        if word == ENFORCED and stage in executed:
            status, note = ENFORCED, ''
        elif stage not in PERFORMED:
            status = 'recorded'
            note = (f'this study performs no {stage}; the consequence is '
                    f'retained for the action that does')
        elif word == ENFORCED:
            status = 'recorded'
            note = ('the control takes effect at '
                    + ', '.join(sorted(executed)) + ', not at this stage')
        else:
            status, note = word, ''
        rows.append({'stage': stage, 'consequence': effect['consequence'],
                     'status': status, 'note': note})
    return rows


def requirement_row(requirement):
    word = disposition(requirement)
    active = word not in (INACTIVE, NON_OPERATIVE)
    failed = _failed(requirement, word)
    restricts = bool(requirement['decisive'] and active
                     and (word != ENFORCED or failed))
    return {
        'id': requirement['id'], 'statement': requirement['statement'],
        'role': requirement['role'], 'priority': requirement['priority'],
        'decisive': requirement['decisive'],
        'settlement': requirement['settlement'],
        'author': requirement['provenance']['author'],
        'basis': requirement['provenance']['basis'],
        'disposition': word, 'routing': routing(word),
        'state': requirement['assessment']['state'],
        'failed': failed,
        'controls': [m['control'] for m in requirement['assessment']['controls']],
        'gap': requirement['assessment']['gap'],
        'reason': _reason(requirement, word) if restricts else '',
        'restricts_conclusion': restricts,
        'stages': _stages(requirement, word),
    }


def intake_gate(plan):
    """Whether dependent work may proceed, and which next action is justified.

    Readiness is staged: ready for a bounded study is not ready for a
    recommendation, and a recorded blocker is a planning outcome rather than
    authorisation to proceed through it. This reads the plan alone, so it
    runs before a category module or a feed exists.
    """
    rows = [requirement_row(r) for r in plan['requirements']]
    blockers = []
    for row in rows:
        if row['decisive'] and row['settlement'] == 'unresolved' \
                and row['disposition'] not in (INACTIVE, NON_OPERATIVE):
            blockers.append(f'{row["id"]}: decisive and unresolved; ask, or '
                            f'stop with the choice recorded')
    if plan['readback']['response']['status'] == 'corrected':
        blockers.append('the user corrected the read-back and the plan has not '
                        'been revised to reconcile it')
    restricting = [row['id'] for row in rows if row['restricts_conclusion']]
    registered = plan['category'] in known()
    if blockers:
        readiness = BLOCKED
        next_action = ('No dependent work. ' + ' '.join(blockers) + '.')
    elif restricting:
        readiness = BOUNDED
        if registered:
            next_action = (
                'A bounded study on the resolved controls, labelled as such: '
                'the full-request recommendation is withheld while '
                + ', '.join(f'`{name}`' for name in restricting)
                + (' stays' if len(restricting) == 1 else ' stay')
                + ' unsupported, and the gap plan stands.')
        else:
            next_action = (
                f'A bounded probe or the gap plan. No executable brief exists: '
                f'{plan["category"]!r} is not a registered category, and '
                + ', '.join(f'`{name}`' for name in restricting)
                + (' has' if len(restricting) == 1 else ' have')
                + ' no executable control. Planning authorises no engineering.')
    else:
        readiness = FULL_REQUEST
        next_action = ('Collection and comparison under the declared controls; a '
                       'recommendation is permitted if the evidence supports one.')
    return {'readiness': readiness, 'next_action': next_action,
            'blockers': blockers, 'restricting': restricting,
            'category_registered': registered, 'requirements': rows}


def comparison_gate(plan, rows, axis_key, axis, unit, axis_source):
    """Does the declared axis answer every decisive preference and objective?

    "Choose the cheapest delivered option" is an optimisation objective, not
    an eligibility condition. A gate naming only hard constraints would let
    it through, so this one looks at the ordering the brief actually
    declares and asks which decisive preferences it answers.
    """
    answered, unanswered = [], []
    for row in rows:
        if row['role'] not in ('preference', 'objective') or not row['decisive']:
            continue
        if row['disposition'] in (INACTIVE, NON_OPERATIVE):
            continue
        if row['disposition'] == ENFORCED and set(row['controls']) & set(AXIS_CONTROLS):
            answered.append(row['id'])
        elif row['disposition'] == ENFORCED:
            answered.append(row['id'])   # enforced by a filter, not by ordering
        else:
            unanswered.append({'id': row['id'], 'statement': row['statement'],
                               'reason': row['reason']})
    label = axis.label if axis else axis_key
    better = axis.better if axis else ''
    return {
        'axis': {'key': axis_key, 'label': label, 'better': better,
                 'unit': unit, 'source': axis_source},
        'answers': answered, 'unanswered': unanswered,
        'supported': not unanswered,
        'refused': 'substitution' if unanswered else '',
        'bounded_question': (
            f'Among the candidates the enforced controls admit, which has the '
            f'{"lowest" if better == "lower" else "highest" if better == "higher" else "best"} '
            f'{label.lower()}' + (f' in {unit}' if unit else '') + '?'),
    }


def conclusion_gate(rows, comparison, outcome):
    """Recommendation, tie, bounded finding or refusal -- and which stop, if any.

    The stop is a fact about the request; the analytical outcome is a fact
    about the evidence. Both are kept, because "the cheapest listed kilogram
    is B0DQ2N5HRW" and "delivered cost is unknown" are both true and a report
    that drops either one misleads.
    """
    failed = [r for r in rows if r['failed']]
    unsupported = [r for r in rows if r['restricts_conclusion'] and not r['failed']
                   and r['disposition'] in (UNSUPPORTED, ASSESSED)]
    unassessed = [r for r in rows if r['restricts_conclusion']
                  and r['disposition'] == AWAITING_EVIDENCE]
    withheld = [r['id'] for r in failed + unsupported + unassessed]

    def names(group):
        return '; '.join(f'`{r["id"]}` ({r["statement"]}) — {r["reason"]}'
                         for r in group)

    if failed:
        stop = REQUIREMENT_FAILED
        statement = (f'A decisive requirement cannot be met: {names(failed)}. '
                     f'No purchasing recommendation is made.')
    elif unsupported:
        stop = REQUIREMENT_UNSUPPORTED
        statement = (f'The purchasing recommendation is withheld. '
                     f'{len(unsupported)} decisive requirement'
                     f'{"" if len(unsupported) == 1 else "s"} '
                     f'{"has" if len(unsupported) == 1 else "have"} no executable '
                     f'control: {names(unsupported)}. This is a gap plan, not an '
                     f'evidence finding.')
    elif unassessed:
        stop = REQUIREMENT_UNASSESSED
        statement = (f'The purchasing recommendation is withheld until '
                     f'{names(unassessed)}. The assessment method exists; this is '
                     f'not a capability gap.')
    else:
        stop, statement = '', ''

    if stop:
        permits = PERMIT_BOUNDED_FINDING
    else:
        permits = {'recommendation': PERMIT_RECOMMENDATION,
                   'no_decisive_winner': PERMIT_SHORTLIST,
                   'insufficient_evidence': PERMIT_REFUSAL}[outcome['code']]
    diagnosis = ''
    if not stop and outcome['code'] == 'insufficient_evidence':
        diagnosis = ('coverage: every decisive requirement has an executable '
                     'control and the evidence within the inspected scope did not '
                     'support a choice. Not a capability gap; not a fact about the market.')
    return {'stop': stop, 'statement': statement, 'permits': permits,
            'withheld': withheld, 'analytical_outcome': outcome['code'],
            'diagnosis': diagnosis,
            'bounded_question': comparison['bounded_question'] if stop else ''}


def evaluate(plan, brief, category, outcome):
    """All three gates for one plan-backed analysis, as persistable data."""
    intake.check(plan)
    gate = intake_gate(plan)
    axis_key = brief.axis or category.default_axis
    comparison = comparison_gate(plan, gate['requirements'], axis_key,
                                 category.axis(axis_key), brief.unit,
                                 'brief' if brief.axis else 'category_default')
    conclusion = conclusion_gate(gate['requirements'], comparison, outcome)
    return {'stage_gates_version': STAGE_GATES_VERSION,
            'plan': {'id': plan['id'], 'revision': plan['revision'],
                     'sha256': intake.digest(plan),
                     'response': plan['readback']['response']['status'],
                     'response_scope': plan['readback']['response']['scope'],
                     'response_message_ids': list(plan['readback']['response']['message_ids'])},
            'intake': gate, 'comparison': comparison, 'conclusion': conclusion}
