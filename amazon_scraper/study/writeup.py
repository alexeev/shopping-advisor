"""The study's report, generated from its decisions and nothing else.

Every number here comes out of :mod:`amazon_scraper.study.analysis`, which is
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
"""

from ..analysis.category import get
from .analysis import (EXCLUDED, FILTERED_OUT, INSUFFICIENT_EVIDENCE,
                       NOT_CATEGORY, NO_DECISIVE_WINNER, OVER_BUDGET,
                       RANKED, RECOMMENDATION, SHORTLISTED, VARIANT)

HEADLINE = {
    RECOMMENDATION: 'Recommendation',
    NO_DECISIVE_WINNER: 'No decisive winner',
    INSUFFICIENT_EVIDENCE: 'Insufficient evidence',
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


def render(result, study_id, inputs):
    """The study report as Markdown."""
    brief = result['brief']
    outcome, constraints = result['outcome'], result['constraints']
    ranked = result['ranking']
    category = get(result['category'])
    lines = [f'# {brief["question"]}', '',
             f'**{HEADLINE[outcome["code"]]}.** {outcome["statement"]}', '',
             '| | |', '|---|---|',
             f'| Study | `{study_id}` |',
             f'| Brief | `{brief["id"]}` · v{brief["brief_version"]} · '
             f'`{brief["source"]["sha256"][:12]}` |',
             f'| Category | {category.label} (`{category.key}`) |',
             f'| Marketplace | {result["marketplace"]}'
             + (f' · delivery {brief["delivery_region"]}'
                if brief['delivery_region'] else '') + ' |',
             f'| As of | {brief["freshness"]["as_of"] or "not stated"} |',
             f'| Inputs | '
             + '<br>'.join(f'`{item["declared"]}` · `{item["sha256"][:12]}` · '
                           f'{item["records"]} records' for item in inputs)
             + ' |', '']

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

    lines += ['## Result', '']
    shortlisted = [entry for entry in result['candidates']
                   if entry['decision'] == SHORTLISTED]
    if shortlisted:
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
            lines.append(f'- {freshness["undated"]} record(s) carry no fetch '
                         f'time at all; their freshness is unknown, which is '
                         f'not the same as current.')
        if freshness['note']:
            lines.append(f'- {freshness["note"]}')
        lines.append('')

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
                  'that a source is about the product, the variant or the '
                  'batch in front of you; that is the next stage. Read each '
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
              f'uv run --offline --locked python -m amazon_scraper.study run '
              f'<path to {brief["source"]["path"] or "the brief"}>',
              f'uv run --offline --locked python -m amazon_scraper.study '
              f'verify <bundle directory>', '```', '',
              'The study id is derived from the brief, the input digests and '
              'the published contract versions, so the same inputs produce '
              'the same id on any machine. It does not cover the analysis '
              'code: `verify` is what catches a decision that moved because '
              'a rule changed.', '']
    return '\n'.join(lines) + '\n'
