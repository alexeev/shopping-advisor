"""The study's report, generated from its decisions and nothing else.

Every number here comes out of :mod:`shopping_advisor.study.analysis`, which is
the point of generating it rather than writing it: a hand-written report can
state a figure the analysis never produced, and this repository's own history
records two occasions where one did -- "no listing says this", twice, where
"no listing I saw says this" was what the evidence supported.

The report is **deterministic**. It carries no generation timestamp and no
hostname, so two runs of the same brief over the same feeds produce the same
bytes, and a diff between two studies is a diff of what changed about the
shelf. When the bundle was produced is in the manifest, where a reader who
needs it will look and a byte comparison will not.

It is a report and not a recommendation engine: the refusal outcomes get the
same structure, the same shortlist section and the same evidence as the
positive one. An insufficient-evidence answer that looks like a failure will
be rewritten by somebody into an answer that is not one.

A plan-backed study adds two things and moves nothing else. A **stop** from
the stage gates replaces the headline and empties the result: the ranking on
the available axis survives, but under its own heading that names the narrower
question it answers, because an analytical leader placed where a
recommendation goes is read as one. And a **requirements** section renders the
plan's roles, settlements, authors and dispositions, with what the report may
say about user agreement taken from the retained response status and nothing
else.
"""

from ..analysis.category import get
from . import gates as gates_module
from .analysis import (EXCLUDED, FILTERED_OUT, INSUFFICIENT_EVIDENCE,
                       NOT_CATEGORY, NO_DECISIVE_WINNER, OVER_BUDGET,
                       RANKED, RECOMMENDATION, SHORTLISTED, VARIANT)

HEADLINE = {
    RECOMMENDATION: 'Recommendation',
    NO_DECISIVE_WINNER: 'No decisive winner',
    INSUFFICIENT_EVIDENCE: 'Insufficient evidence',
}

#: A stop is not one of the three outcomes and is not headlined as one.
STOP_HEADLINE = {
    gates_module.REQUIREMENT_UNSUPPORTED: 'Recommendation withheld',
    gates_module.REQUIREMENT_UNASSESSED: 'Recommendation withheld',
    gates_module.REQUIREMENT_FAILED: 'Requirement cannot be met',
}

#: What the report may say about user agreement, keyed by the retained
#: response status. No response is not agreement, and a report claiming a
#: confirmation the record does not hold is a structural failure.
ATTRIBUTION = {
    'not_presented': 'No read-back of this plan revision was presented to the '
                     'user. Nothing in this report is described as user-confirmed.',
    'no_response': 'The read-back of this plan revision was presented and '
                   'received no response. Silence is not confirmation: nothing '
                   'in this report is described as user-confirmed.',
    'confirmed': 'The user confirmed the scope of this plan revision',
    'delegated': 'The user delegated choices within this plan revision',
}

#: The order exclusion groups are explained in, and what to call each.
GROUPS = (
    (OVER_BUDGET, 'Above the limit this brief set'),
    (FILTERED_OUT, 'Did not state a claim the brief required'),
    (EXCLUDED, 'No value that may be ranked on'),
    (VARIANT, 'Another pack size of an offer already listed'),
    (NOT_CATEGORY, 'Not this category'),
)


def _row(entry):
    title = entry['title'][:60]
    return (f'| {entry["rank"] or ""} | `{entry["asin"]}` | '
            f'{entry["brand"] or "?"} | {title} | '
            f'{entry["value"]:g} {entry["unit"]} |'.replace('\n', ' '))


def _source(constraint):
    return {'brief': 'stated in the brief',
            'category_default': 'the category default — the brief stated none',
            'measured': 'the only unit the evidence is measured in'}.get(
        constraint, constraint)


def _scope_row(brief):
    """A header row only when the brief declares a scope: legacy bytes stay."""
    scope = brief['freshness'].get('scope')
    if not scope:
        return []
    if scope == 'current_advice':
        return ['| Scope | current buying advice, **only with a passing delivery '
                'record** (`delivery.json`); this report alone is a historical '
                f'comparison as of {brief["freshness"]["as_of"]} |']
    return [f'| Scope | historical comparison as of {brief["freshness"]["as_of"] or "an unstated date"}; '
            f'not current buying advice |']


def _scope_lines(brief):
    scope = brief['freshness'].get('scope')
    if not scope:
        return []
    if scope == 'current_advice':
        return ['Declared scope: **current advice**. That is a structural condition, '
                'not a label: it is checked at each delivery event against a '
                'reference the execution environment supplies, never against the '
                'date above, and the result is frozen in `delivery.json`. Without a '
                'delivery record whose latest event permits current advice, this '
                f'report is a historical comparison as of '
                f'{brief["freshness"]["as_of"]}.', '']
    return ['Declared scope: **historical**. However recent these observations are, '
            'they are not offered as current buying advice; a delivery record '
            'states the reference date at which they were delivered as history.', '']


def _attribution(plan):
    status = plan['response']
    sentence = ATTRIBUTION[status]
    if status in ('confirmed', 'delegated'):
        ids = ', '.join(f'`{item}`' for item in plan['response_message_ids'])
        sentence += (f' ({plan["response_scope"]}; message {ids}). '
                     + ('Confirmation does not waive a failed structural check '
                        'and authorises no unrelated engineering.'
                        if status == 'confirmed' else
                        'A delegated choice is recorded with its rationale and '
                        'what changes if it is wrong; it is not a user-confirmed '
                        'result.'))
    return sentence


def _requirements(gates):
    """The plan's requirements: who said each, in what role, and its fate."""
    plan, intake, comparison = gates['plan'], gates['intake'], gates['comparison']
    lines = ['## Requirements and their dispositions', '',
             f'Plan `{plan["id"]}`, revision {plan["revision"]}, digest '
             f'`{plan["sha256"][:12]}`; the full snapshot is `intake-plan.json` '
             f'in this bundle. {_attribution(plan)}', '',
             f'Readiness at intake: **{intake["readiness"].replace("_", " ")}**. '
             f'{intake["next_action"]}', '',
             'Provenance says who introduced a requirement; role says what it '
             'does to the decision; disposition says what this study did with '
             'it. Enforced means an executable control ran at its stage. It does '
             'not mean the control answers the requirement — that is semantic '
             'review, and a control that runs correctly can answer the wrong '
             'question.', '',
             '| Requirement | Role | Settlement | Introduced by | Disposition | '
             'Restricts the conclusion |', '|---|---|---|---|---|---|']
    for row in intake['requirements']:
        role = row['role'].replace('_', ' ')
        if row['priority'] is not None:
            role += f', priority {row["priority"]}'
        if not row['decisive']:
            role += ', not decisive'
        word = row['disposition'].replace('_', ' ')
        if row['controls']:
            word += ' (' + ', '.join(f'`{c}`' for c in row['controls']) + ')'
        if row['reason']:
            word += f': {row["reason"]}'
        lines.append(f'| `{row["id"]}` — {row["statement"]} | {role} | '
                     f'{row["settlement"]} | {row["author"].replace("_", " ")} | '
                     f'{word} | {"**yes**" if row["restricts_conclusion"] else "no"} |'
                     .replace('\n', ' '))
    lines.append('')
    effects = [(row, stage) for row in intake['requirements'] for stage in row['stages']]
    if effects:
        lines += ['Stage effects, one line per stage a requirement names. A '
                  'consequence at a stage this offline study does not perform is '
                  'retained, not executed, and not claimed.', '']
        for row, stage in effects:
            lines.append(f'- `{row["id"]}` at {stage["stage"].replace("_", " ")}: '
                         f'{stage["consequence"]} — {stage["status"].replace("_", " ")}'
                         + (f'; {stage["note"]}' if stage['note'] else '') + '.')
        lines.append('')
    axis = comparison['axis']
    sentence = (f'Comparison support: the declared axis is {axis["label"]} '
                f'(`{axis["key"]}`, {axis["better"] or "no direction"} first'
                + (f', {axis["unit"]}' if axis['unit'] else '') + '), '
                + _source(axis['source']) + '.')
    if comparison['answers']:
        sentence += ' It answers ' + ', '.join(f'`{i}`' for i in comparison['answers']) + '.'
    if comparison['unanswered']:
        sentence += (' It does not answer '
                     + ', '.join(f'`{u["id"]}`' for u in comparison['unanswered'])
                     + ': the substitution is refused, and ordering on this axis '
                       'is reported below as a bounded finding, not as the answer.')
    lines += [sentence, '']
    return lines


def _withheld(gates):
    """Under a stop: what was withheld and why, in the place the answer goes."""
    conclusion = gates['conclusion']
    rows = {row['id']: row for row in gates['intake']['requirements']}
    lines = ['No candidate is put forward.', '',
             f'Analytical outcome on the available axis: '
             f'`{conclusion["analytical_outcome"]}`. It is not presented as the '
             f'answer to the question above, because:', '']
    for name in conclusion['withheld']:
        row = rows[name]
        line = (f'- `{name}` ({row["role"].replace("_", " ")}, {row["settlement"]}, '
                f'introduced by {row["author"].replace("_", " ")}): '
                f'{row["statement"]} — {row["disposition"].replace("_", " ")}'
                + (f'; {row["reason"]}' if row['reason'] else '') + '.')
        if row['gap']:
            line += f' Next step: {row["gap"]["next_step"]}'
        lines.append(line)
    return lines + ['']


def _bounded(result, gates):
    """The finding that survives a stop, under a heading that says what it is."""
    outcome, constraints = result['outcome'], result['constraints']
    conclusion = gates['conclusion']
    label = constraints['axis']['label']
    lines = [f'## Bounded finding: {label} only', '',
             f'This section answers a narrower question than the one this study '
             f'was asked: *{conclusion["bounded_question"]}* It leaves '
             + ', '.join(f'`{i}`' for i in conclusion['withheld'])
             + ' unenforced and unanswered. It is not a recommendation and must '
               'not be read as one.', '']
    ranked = sorted((e for e in result['candidates'] if e['decision'] == RANKED),
                    key=lambda e: e['rank'])
    if outcome['code'] == INSUFFICIENT_EVIDENCE or not ranked:
        lines += [f'On the narrower question too, the evidence is insufficient: '
                  f'{outcome["statement"]}', '']
        return lines
    lines += [outcome['statement'], '',
              f'| # | ASIN | Brand | Title | {label} |', '|---|---|---|---|---|']
    lines += [_row(entry) for entry in ranked[:constraints['shortlist']]]
    lines.append('')
    if len(ranked) > constraints['shortlist']:
        lines += [f'{len(ranked) - constraints["shortlist"]} further candidate(s) '
                  f'were ranked on this axis and are in `candidates.jsonl`.', '']
    return lines


def render(result, study_id, inputs):
    """The study report as Markdown."""
    brief = result['brief']
    outcome, constraints = result['outcome'], result['constraints']
    ranked = result['ranking']
    category = get(result['category'])
    gates = result.get('gates')
    stop = result.get('stop') or ''
    if stop:
        headline = f'**{STOP_HEADLINE[stop]}.** {gates["conclusion"]["statement"]}'
    else:
        headline = f'**{HEADLINE[outcome["code"]]}.** {outcome["statement"]}'
    lines = [f'# {brief["question"]}', '', headline, '',
             '| | |', '|---|---|',
             f'| Study | `{study_id}` |',
             f'| Brief | `{brief["id"]}` · v{brief["brief_version"]} · '
             f'`{brief["source"]["sha256"][:12]}` |',
             f'| Category | {category.label} (`{category.key}`) |',
             f'| Marketplace | {result["marketplace"]}'
             + (f' · delivery {brief["delivery_region"]}'
                if brief['delivery_region'] else '') + ' |',
             f'| As of | {brief["freshness"]["as_of"] or "not stated"} |',
             *_scope_row(brief),
             f'| Inputs | '
             + '<br>'.join(f'`{item["declared"]}` · `{item["sha256"][:12]}` · '
                           f'{item["records"]} records' for item in inputs)
             + ' |', '']

    if result['freshness']['stale_ranked'] or not result['freshness']['assessed'] or result['freshness']['undated']:
        lines.insert(2, '**Historical / incomplete comparison. Prices are stale or freshness '
                     'is not fully established; this is not current buying advice.**\n')
    if brief['use_case']:
        lines += ['## What was asked', '', brief['use_case'], '']
    if brief['unacceptable']:
        lines += ['Ruled out from the start:', '']
        lines += [f'- {item}' for item in brief['unacceptable']] + ['']

    stated, unstated = 'stated in the brief', 'the brief stated none'
    before = 'stated in the brief, before the data was seen'
    required = ', '.join(f'`{key}`' for key in constraints['require_claims'])
    cap, margin = constraints['max_axis_value'], constraints['decisive_margin']
    lines += ['## What decided it', '',
              'Each line says whether this study chose it or the category did. '
              'A category default is a property of the product class; a stated '
              'constraint belongs to this question and to no other.', '',
              '| Decision | Value | Where it came from |', '|---|---|---|',
              f'| Ranking axis | {constraints["axis"]["label"]} '
              f'(`{constraints["axis"]["key"]}`, '
              f'{constraints["axis"]["better"] or "no direction"} first) | '
              f'{_source(constraints["axis"]["source"])} |',
              f'| Unit | {constraints["unit"]["value"] or "—"} | '
              f'{_source(constraints["unit"]["source"])} |',
              f'| Required claims | {required or "none"} | '
              f'{stated if required else "the brief required none"} |',
              f'| Limit on the axis | '
              + (f'{cap:g} {constraints["unit"]["value"]}' if cap is not None
                 else 'none')
              + f' | {stated if cap is not None else unstated} |',
              f'| Enough to choose from | at least '
              f'{constraints["minimum_candidates"]} candidate(s) | {before} |',
              '| Decisive margin | '
              + (f'{margin:.1%}' if margin is not None else 'not required')
              + f' | {before if margin is not None else "not required"} |',
              '']
    if constraints['cost_basis']:
        lines += [f'Cost basis: {constraints["cost_basis"]}', '']
    if gates is not None:
        lines += _requirements(gates)

    lines += ['## Result', '']
    shortlisted = [entry for entry in result['candidates']
                   if entry['decision'] == SHORTLISTED]
    if stop:
        lines += _withheld(gates)
    elif shortlisted:
        lines += ['| # | ASIN | Brand | Title | '
                  f'{constraints["axis"]["label"]} |',
                  '|---|---|---|---|---|']
        lines += [_row(entry) for entry in shortlisted]
        lines += ['']
        remaining = sum(1 for entry in result['candidates']
                        if entry['decision'] == RANKED)
        if remaining:
            lines += [f'{remaining} further candidate(s) were ranked and are '
                      f'in `candidates.jsonl`; the brief asked for a '
                      f'shortlist of {constraints["shortlist"]}.', '']
    else:
        lines += ['No candidate is put forward.', '']
    if ranked['refusal']:
        lines += [f'> {ranked["refusal"]["message"]}', '']
    if stop:
        lines += _bounded(result, gates)

    lines += ['## Why every other candidate is not here', '',
              'Complete, not truncated: a study that cannot say why the '
              'product a reader asks about is absent has not recorded its own '
              'work.', '']
    for decision, heading in GROUPS:
        group = [entry for entry in result['candidates']
                 if entry['decision'] == decision]
        if not group:
            continue
        lines += [f'### {heading} ({len(group)})', '']
        for entry in sorted(group, key=lambda item: item['asin']):
            lines.append(f'- `{entry["asin"]}` {entry["brand"] or "?"} · '
                         f'{entry["title"][:60]} — '
                         f'{entry["reason"] or entry["reason_code"]}')
        lines.append('')

    lines += ['## Freshness', '']
    freshness = result['freshness']
    if not freshness['assessed']:
        lines += ['The brief stated no `as_of` date, so the age of these '
                  'observations was not assessed. Treat every price in this '
                  'report as of unknown age.', '']
    else:
        policy = freshness['price_max_age_days']
        lines += [f'Measured against the brief\'s own `as_of` '
                  f'({freshness["as_of"]}), not against the day this bundle '
                  f'was produced — otherwise the same study would decide '
                  f'differently tomorrow.', '']
        if freshness['oldest_ranked_days'] is not None:
            lines.append(f'- Oldest ranked observation: '
                         f'{freshness["oldest_ranked_days"]} day(s) old.')
        elif not result['shortlist']:
            lines.append('- Nothing was ranked, so no observation age was '
                         'assessed.')
        else:
            lines.append('- No ranked observation carries a fetch time, so '
                         'its age is unknown rather than current.')
        if policy is not None:
            lines.append(f'- Policy: prices older than {policy} day(s) are '
                         f'stale. {freshness["stale_ranked"]} ranked '
                         f'candidate(s) exceed it.')
        if freshness['undated']:
            lines.append(f'- {freshness["undated"]} record(s) lack a usable observation '
                         f'date at or before the reference; freshness is unknown, which is '
                         f'not the same as current.')
        if freshness['note']:
            lines.append(f'- {freshness["note"]}')
        lines.append('')
    lines += _scope_lines(brief)

    if brief['assumptions']:
        lines += ['## Assumptions', '',
                  'Each of these was chosen, not established. A wrong one '
                  'changes the line beside it.', '',
                  '| Assumption | Default taken | If it is wrong |',
                  '|---|---|---|']
        for item in brief['assumptions']:
            lines.append(f'| {item["statement"]} | {item.get("default", "—")} '
                         f'| {item.get("if_wrong", "—")} |')
        lines.append('')

    if brief['questions']:
        lines += ['## Questions', '', '| Question | Answer |', '|---|---|']
        for item in brief['questions']:
            answer = item.get('answer') or (
                f'unanswered — assumed {item["default_used"]}'
                if item.get('default_used') else 'unanswered')
            lines.append(f'| {item["question"]} | {answer} |')
        lines.append('')

    if brief['sources']:
        lines += ['## External sources named by the brief', '',
                  '**Declared, not verified.** Nothing in this build checks '
                  'that these declarations apply to the product, variant or '
                  'batch. Use the external ledger to index checked support. Read each '
                  'one before letting it decide anything.', '']
        for item in brief['sources']:
            lines.append(f'- {item.get("title") or item["url"]} — '
                         f'{item["why"]} ({item["url"]})')
        lines.append('')

    lines += ['## Coverage and limits', '',
              f'- Among the {result["classification"]["records"]} records in '
              f'the declared inputs, and nothing else. This is not a survey '
              f'of the marketplace: search does not enumerate a shelf, and a '
              f'product nobody named and no query returned is simply absent.',
              f'- {result["classification"]["matched"]} were classified as '
              f'{category.label}, {result["classification"]["other"]} as '
              f'other products, {result["classification"]["undecided"]} '
              f'undecided. These are classifier decisions; their accuracy is '
              f'not measured.',
              '- A `trusted` value is one that survived the applicable '
              'checks. A vendor claim that is trusted is a claim the page '
              'demonstrably makes, not an independently verified property.']
    if result['merge']['set_aside']:
        lines.append(f'- {result["merge"]["set_aside"]} record(s) from another '
                     f'marketplace were set aside, not merged in.')
    if result['merge']['superseded']:
        lines.append(f'- {result["merge"]["superseded"]} listing(s) were seen '
                     f'more than once and resolved to the freshest '
                     f'observation; `manifest.json` records which.')
    lines += [f'- {item}' for item in brief['limits']]
    lines += ['']

    lines += ['## Reproducing this study', '',
              'From the repository root, with no network:', '', '```text',
              f'uv run --offline --locked python -m shopping_advisor.study run '
              f'<path to {brief["source"]["path"] or "the brief"}>'
              + (' --plan <bundle directory>/intake-plan.json' if gates is not None else ''),
              f'uv run --offline --locked python -m shopping_advisor.study '
              f'verify <bundle directory>', '```', '',
              'The study id is derived from the brief, the input digests and '
              'the published contract versions, so the same inputs produce '
              'the same id on any machine. It does not cover the analysis '
              'code: `verify` is what catches a decision that moved because '
              'a rule changed.', '']
    return '\n'.join(lines) + '\n'
