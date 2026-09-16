"""Brief plus feeds to decisions, deterministically and with every candidate.

This module decides nothing the layers beneath it already decide. It merges
feeds with :mod:`shopping_advisor.analysis.feeds`, classifies and evaluates with
the category, and ranks with :func:`shopping_advisor.analysis.report.ranking`.
What it adds is the three things a study has and a command line does not:

**Every considered candidate, with the reason for its fate.** A ranking prints
its first twenty rows and ten of its exclusions. A study that cannot say why
the product a reader asks about is absent has not recorded its own work, so
``candidates`` holds one entry per record considered -- ranked, folded into
another pack size, excluded for an unusable value, filtered out by a stated
requirement, or not of this category at all.

**The study's own constraints, kept apart from the category's defaults.** The
category says price per kilogram is what dry pasta is compared on; the brief
says this buyer will not pay more than five euros for one. Both end in the
same ordering and they are not the same kind of statement, so the budget is
applied here, after the ranking, and every constraint records whether the
brief stated it or the category supplied it.

**A stated stopping criterion.** ``minimum_candidates`` and
``decisive_margin`` are declared in the brief, before the data is seen, so
"there is not enough here to choose" is a criterion the study met rather than
a judgement it improvised at the end. Refusing to pick a winner is a result.

Determinism is a property this module owes its callers: the same brief over
the same inputs must produce the same decisions and the same numbers on any
machine. Nothing here reads the clock, the filesystem's timestamps or the
environment; freshness is measured against the brief's own ``as_of``.
"""

import datetime as _dt

from ..analysis import feeds as feeds_module
from ..analysis import report
from ..analysis.category import get, is_match

#: A winner the evidence supports.
RECOMMENDATION = 'recommendation'
#: Enough candidates to compare, too close together to separate on the axis
#: the brief declared decisive. A shortlist, and no winner.
NO_DECISIVE_WINNER = 'no_decisive_winner'
#: Fewer usable candidates than the brief said it needed, or no ranking at
#: all. The honest answer, and the one a study is most tempted to dress up.
INSUFFICIENT_EVIDENCE = 'insufficient_evidence'

#: What happened to a candidate. ``variant`` is not an exclusion: it is the
#: other pack size of an offer that is in the ranking.
SHORTLISTED = 'shortlisted'
RANKED = 'ranked'
VARIANT = 'variant'
OVER_BUDGET = 'over_budget'
EXCLUDED = 'excluded'
FILTERED_OUT = 'filtered_out'
NOT_CATEGORY = 'not_category'


class StudyError(ValueError):
    """The study cannot be produced from what the brief names."""


def _fetched_at(card):
    validated = card.get('validated')
    return (validated.record or {}).get('fetched_at') or '' if validated else ''


def _age_days(fetched_at, as_of):
    """Whole days between an observation and the date the study is about."""
    if not fetched_at or not as_of:
        return None
    try:
        observed = _dt.datetime.fromisoformat(fetched_at).date()
        reference = _dt.date.fromisoformat(as_of)
    except ValueError:
        return None
    return (reference - observed).days


def _candidate(card, decision, **extra):
    entry = {'asin': card['asin'],
             'marketplace': card.get('marketplace') or '',
             'brand': card['brand'] or '', 'title': card['title'] or '',
             'decision': decision, 'rank': None, 'value': None, 'unit': '',
             'reason_code': '', 'reason': '', 'fetched_at': _fetched_at(card),
             'age_days': None, 'stale': False}
    entry.update(extra)
    return entry


def collect(brief):
    """``(cards, merge provenance)`` for the feeds the brief names."""
    records, provenance = feeds_module.merge(list(brief.resolved_inputs))
    kept, set_aside = feeds_module.select_marketplace(records,
                                                      brief.marketplace)
    if not kept:
        seen = ', '.join(name or 'unlabelled'
                         for name in provenance.get('marketplaces') or {})
        raise StudyError(
            f'{brief.marketplace}: none of the {provenance["records"]} '
            f'records in this brief\'s inputs come from that marketplace. '
            f'They hold: {seen or "nothing"}')
    provenance = dict(provenance, records=len(kept),
                      marketplaces=feeds_module.marketplaces(kept),
                      set_aside=len(set_aside))
    category = get(brief.category)
    return [category.evaluate(record) for record in kept], provenance


def analyse(brief):
    """Every decision this brief's inputs support, as data.

    The return value is what the bundle persists and what ``verify`` recomputes
    and compares, so every number a report states has to be in here.
    """
    category = get(brief.category)
    cards, provenance = collect(brief)
    ranked = report.ranking(cards, axis_key=brief.axis or None,
                            require=brief.require_claims,
                            unit=brief.unit or None)

    # A queue per listing rather than one card, because a record whose ASIN
    # never extracted is not identified by its ASIN: the merge keeps every
    # such record, and keyed on `(marketplace, None)` they would all collapse
    # onto whichever one was read last. Each ranking entry consumes one card,
    # in the order both were produced.
    pool = {}
    for card in cards:
        pool.setdefault((card.get('marketplace') or '', card['asin']),
                        []).append(card)

    def card_of(entry):
        queue = pool.get((entry.get('marketplace') or '', entry['asin']))
        # The entry itself carries the identity; falling back to it costs the
        # observation time and never an invented one.
        return queue.pop(0) if queue else entry

    matched = [card for card in cards if is_match(card)]
    classification = {
        'records': len(cards), 'matched': len(matched),
        'other': sum(1 for card in cards if card['category'].value == 'other'),
        'undecided': sum(1 for card in cards if not card['category'].known),
    }

    axis_key = brief.axis or category.default_axis
    axis = category.axis(axis_key)
    constraints = {
        'axis': {'key': axis_key, 'label': axis.label if axis else '',
                 'better': axis.better if axis else '',
                 'source': 'brief' if brief.axis else 'category_default'},
        'unit': {'value': (ranked['axis'] or {}).get('unit') or brief.unit,
                 'source': 'brief' if brief.unit else 'measured'},
        'require_claims': list(brief.require_claims),
        'max_axis_value': brief.max_axis_value,
        'cost_basis': brief.cost_basis,
        'shortlist': brief.shortlist,
        'minimum_candidates': brief.minimum_candidates,
        'decisive_margin': brief.decisive_margin,
    }

    candidates, eligible, accounted = [], [], set()

    def add(card, decision, **extra):
        entry = _candidate(card, decision, **extra)
        candidates.append(entry)
        accounted.add(id(card))
        return entry

    for row in ranked['rows']:
        over = (brief.max_axis_value is not None
                and row['value'] > brief.max_axis_value)
        entry = add(card_of(row), OVER_BUDGET if over else RANKED,
                    rank=row['rank'], value=row['value'], unit=row['unit'],
                    reason_code='over_budget' if over else '',
                    reason=(f'{row["shown"]} is above the '
                            f'{brief.max_axis_value:g} '
                            f'{row["unit"]} this brief set as its limit'
                            if over else ''))
        if not over:
            eligible.append(entry)
        for other in row['variants']:
            add(card_of(other), VARIANT, value=other['value'],
                unit=row['unit'], rank=row['rank'], reason_code='variant',
                reason=f'the same offer as {row["asin"]} in another pack '
                       f'size, which the ranking folds into one row')
    for group, decision in ((ranked['excluded'], EXCLUDED),
                            (ranked['filtered_out'], FILTERED_OUT)):
        for item in group:
            add(card_of(item), decision, reason_code=item['reason_code'],
                reason=item['reason'])
    for card in cards:
        if id(card) in accounted:
            continue
        if not is_match(card):
            notes = card['category'].notes
            add(card, NOT_CATEGORY, reason_code='not_category',
                reason=notes[0] if notes else
                f'not classified as {category.label}')
        else:
            # A refusal that fired before the ranking got as far as this
            # record -- an axis with no direction, two units in one column.
            # It is still a candidate somebody will ask about, and the
            # refusal is the reason it has no place.
            add(card, EXCLUDED,
                reason_code=(ranked['refusal'] or {}).get('code') or 'no_value',
                reason=(ranked['refusal'] or {}).get('message')
                or 'no value for this axis')

    stale = 0
    for entry in candidates:
        entry['age_days'] = _age_days(entry['fetched_at'], brief.as_of)
        if brief.price_max_age_days is not None and \
                entry['age_days'] is not None:
            entry['stale'] = entry['age_days'] > brief.price_max_age_days
        if entry['stale'] and entry['decision'] in (RANKED, OVER_BUDGET):
            stale += 1

    outcome = _decide(brief, ranked, eligible)
    # A study that refuses puts nobody forward. `no_decisive_winner` still
    # names its shortlist -- the point of that outcome is that both are
    # defensible -- but `insufficient_evidence` with three products under it
    # is a recommendation wearing a disclaimer, and it will be read as one.
    shortlist = ([] if outcome['code'] == INSUFFICIENT_EVIDENCE
                 else eligible[:brief.shortlist])
    for entry in shortlist:
        entry['decision'] = SHORTLISTED
    freshness = {
        'as_of': brief.as_of,
        'price_max_age_days': brief.price_max_age_days,
        'note': brief.freshness_note,
        'assessed': bool(brief.as_of),
        'stale_ranked': stale,
        'oldest_ranked_days': max(
            (entry['age_days'] for entry in eligible
             if entry['age_days'] is not None), default=None),
        'undated': sum(1 for entry in candidates if not entry['fetched_at']),
    }

    return {
        'brief': brief.as_dict(),
        'category': category.key, 'category_label': category.label,
        'marketplace': brief.marketplace,
        'merge': provenance,
        'classification': classification,
        'constraints': constraints,
        'ranking': ranked,
        'candidates': candidates,
        'shortlist': [entry['asin'] for entry in shortlist],
        'freshness': freshness,
        'outcome': outcome,
        'claims': _claims(brief, ranked, eligible, classification, provenance),
    }, cards


def brief_fault(result):
    """Why this brief, rather than this evidence, is why there is no ranking.

    The two look identical from inside the analysis and are opposite findings
    for a reader. "No pasta states low-temperature drying *and* has a price
    per kilogram that survived validation" is a result, and a study records
    it. "The brief asks for EUR/100g and every value is in EUR/kg" is a typo,
    and persisting a bundle that says *insufficient evidence* would file an
    operator's slip as a fact about the shelf.

    Returns the sentence to stop on, or ``None`` when the refusal -- or the
    absence of one -- is about the evidence.
    """
    refusal = result['ranking']['refusal']
    if refusal is None:
        return None
    units = result['ranking']['units']
    if refusal['code'] == 'unit_absent' and units:
        return (f'{refusal["message"]} Nothing converts between them, so fix '
                f'constraints.unit in the brief rather than reading this as a '
                f'gap in the evidence.')
    if refusal['code'] == 'ambiguous_unit':
        return (f'{refusal["message"]} The brief has to name it: a study '
                f'cannot leave that to whichever unit happened to be '
                f'commonest.')
    if refusal['code'] == 'no_direction':
        return (f'{refusal["message"]} A study ranks on an axis the category '
                f'says has a better side, or it states no ranking axis and '
                f'takes the default.')
    return None


def _margin(eligible):
    """How far the leader is ahead of the runner-up, as a share of the leader.

    ``None`` when there is nobody to be ahead of. A zero-valued leader has no
    relative margin either, and saying so beats dividing by it.
    """
    if len(eligible) < 2:
        return None
    best, second = eligible[0]['value'], eligible[1]['value']
    if not isinstance(best, (int, float)) or not isinstance(second, (int, float)):
        return None
    if best == 0:
        return None
    return abs(second - best) / abs(best)


def _decide(brief, ranked, eligible):
    """The outcome, and the sentence that says why it is that one."""
    if ranked['refusal'] is not None:
        return {'code': INSUFFICIENT_EVIDENCE,
                'reason_code': ranked['refusal']['code'],
                'statement': f'No ranking was produced. '
                             f'{ranked["refusal"]["message"]}',
                'margin': None}
    if len(eligible) < brief.minimum_candidates:
        return {'code': INSUFFICIENT_EVIDENCE,
                'reason_code': 'too_few_candidates',
                'statement': (
                    f'{len(eligible)} candidate'
                    f'{"" if len(eligible) == 1 else "s"} survived the brief\'s '
                    f'requirements with a usable '
                    f'{(ranked["axis"] or {}).get("label", "value").lower()}, '
                    f'and the brief asked for at least '
                    f'{brief.minimum_candidates} before choosing. Nothing is '
                    f'recommended.'),
                'margin': None}
    margin = _margin(eligible)
    if brief.decisive_margin is not None and margin is not None and \
            margin < brief.decisive_margin:
        return {'code': NO_DECISIVE_WINNER, 'reason_code': 'within_margin',
                'statement': (
                    f'{eligible[0]["asin"]} and {eligible[1]["asin"]} are '
                    f'{margin:.1%} apart, inside the {brief.decisive_margin:.1%} '
                    f'the brief declared decisive. Both are named; neither is '
                    f'picked.'),
                'margin': margin}
    return {'code': RECOMMENDATION, 'reason_code': 'clear_leader',
            'statement': (
                f'{eligible[0]["asin"]} leads on '
                f'{(ranked["axis"] or {}).get("label", "the axis").lower()}'
                + (f', {margin:.1%} ahead of the next candidate'
                   if margin is not None else '') + '.'),
            'margin': margin}


def _claims(brief, ranked, eligible, classification, provenance):
    """Every number the report is allowed to state, as checkable data.

    A report is prose and prose cannot be compared between two runs. These
    can, which is what makes "the same inputs produce the same numeric
    claims" a check rather than an assertion.
    """
    claims = [
        {'id': 'records_considered', 'value': classification['records'],
         'unit': 'records',
         'statement': f'{classification["records"]} records were considered'},
        {'id': 'classified', 'value': classification['matched'],
         'unit': 'records',
         'statement': f'{classification["matched"]} were classified as the '
                      f'briefed category'},
        {'id': 'feeds', 'value': provenance['feeds'], 'unit': 'feeds',
         'statement': f'from {provenance["feeds"]} feed(s)'},
        {'id': 'eligible', 'value': len(eligible), 'unit': 'candidates',
         'statement': f'{len(eligible)} candidates were eligible to be ranked'},
    ]
    if ranked['refusal'] is None:
        claims.append({'id': 'excluded', 'value': ranked['counts']['excluded'],
                       'unit': 'records',
                       'statement': f'{ranked["counts"]["excluded"]} were '
                                    f'excluded from the ranking'})
        claims.append({'id': 'filtered_out',
                       'value': ranked['counts']['filtered_out'],
                       'unit': 'records',
                       'statement': f'{ranked["counts"]["filtered_out"]} did '
                                    f'not state a required claim'})
    for index, name in ((0, 'best'), (1, 'runner_up')):
        if len(eligible) > index:
            entry = eligible[index]
            claims.append({'id': f'{name}_value', 'value': entry['value'],
                           'unit': entry['unit'], 'asin': entry['asin'],
                           'statement': f'{entry["asin"]} at {entry["value"]} '
                                        f'{entry["unit"]}'})
    margin = _margin(eligible)
    if margin is not None:
        claims.append({'id': 'margin', 'value': round(margin, 6), 'unit': '',
                       'statement': f'the leader is {margin:.1%} ahead'})
    return claims
