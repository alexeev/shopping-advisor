"""Characterisation of the three qualifications that decide nothing.

[INTAKE.md](../INTAKE.md) names three recurring failures, and one of them is a
requirement that is parsed, persisted, rendered, and then consumed by no
decision. This module pins that behaviour as it stands today, for two reasons.

The first is ordinary regression: R13 proposes to make each of these
load-bearing, and a repair that cannot be seen moving is not a repair. These
tests are expected to *change* when the stage that fixes them lands, and the
diff is the measured effect.

The second is the one that matters more. Each of these fields already looks
like it works. A brief author writes a delivered-cost basis, a budget or a
freshness policy, reads it back in the report, and has no way to discover that
eligibility, ordering and outcome were identical without it. Somebody
eventually "tidies" one of them and nothing fails. So the assertions below are
deliberately about **eligibility, ordering and outcome** and never about report
bytes or study ids, which legitimately differ and would be the wrong invariant
to freeze.

The cases these characterise are stated as expectations in
[tests/intake/README.md](intake/README.md), written before the fields they will
need exist.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from shopping_advisor.analysis.category import get  # noqa: E402
from shopping_advisor.study import brief as brief_module  # noqa: E402
from shopping_advisor.study.analysis import (  # noqa: E402
    OVER_BUDGET, RANKED, SHORTLISTED, analyse)

HERE = pathlib.Path(__file__).resolve().parent
STUDIES = HERE / 'studies'
BRONZE = STUDIES / 'pasta-bronze-die.toml'

#: Everything `analyse()` returns that a reader would call a decision. A
#: qualification that moves none of these moved nothing, whatever the report
#: says about it.
DECISIONS = ('outcome', 'shortlist', 'candidates', 'ranking', 'freshness',
             'constraints', 'classification', 'claims')


class Variant(unittest.TestCase):
    """One committed brief, and copies of it differing in one field.

    The copies are written beside the original because a brief's feeds are
    resolved against the brief's own directory: a variant somewhere else would
    be testing path resolution rather than the field that changed.
    """

    def setUp(self):
        self.addCleanup(self.sweep)
        self.written = []

    def sweep(self):
        for path in self.written:
            path.unlink(missing_ok=True)

    def variant(self, *replacements):
        text = BRONZE.read_text(encoding='utf-8')
        for old, new in replacements:
            self.assertIn(old, text, f'the brief no longer contains {old!r}')
            text = text.replace(old, new, 1)
        path = STUDIES / f'.tmp-intake-{len(self.written)}-{BRONZE.name}'
        path.write_text(text, encoding='utf-8')
        self.written.append(path)
        return path

    def analyse(self, path=BRONZE):
        result, _cards = analyse(brief_module.load(path))
        return result

    def moved(self, path):
        """Which decision keys this variant changed, as a sorted list."""
        base, other = self.analyse(), self.analyse(path)
        return sorted(key for key in DECISIONS
                      if json.dumps(base[key], sort_keys=True)
                      != json.dumps(other[key], sort_keys=True))


class NarrativeFieldsDecideNothing(Variant):
    """`cost_basis`, `unacceptable` and `limits` are prose, not predicates.

    The committed brief says in `cost_basis` that delivery is excluded because
    these records carry no shipping data. A brief that instead said *delivered
    cost* would produce a different-looking study that decided identically,
    which is the trap the delivered-cost case exists to catch.
    """

    def test_declaring_a_delivered_cost_basis_changes_no_decision(self):
        moved = self.moved(self.variant(
            ('cost_basis = "The listed price',
             'cost_basis = "Delivered cost, including shipping. The listed '
             'price')))
        # `constraints` echoes the brief's own text back, so it moves. Nothing
        # that chose a candidate or ordered one did.
        self.assertEqual(moved, ['constraints'])

    def test_an_unacceptable_entry_is_not_an_exclusion(self):
        """The natural place a buyer's budget ends up, and it is inert.

        Not even `constraints` moves here: `unacceptable` is not echoed into
        it, so there is no trace of the requirement anywhere a decision is
        recorded.
        """
        self.assertEqual(self.moved(self.variant(
            ('  "Fresh pasta',
             '  "Anything costing more than 100 EUR in total.",\n  "Fresh '
             'pasta'))), [])

    def test_a_limit_is_a_statement_about_the_study_not_an_input_to_it(self):
        self.assertEqual(self.moved(self.variant(
            ('limits = [',
             'limits = [\n  "Shipping is excluded from every figure here.",'))),
            [])


class PurchaseBudgetHasNoRepresentation(Variant):
    """"Under 100 EUR in total, then cheapest per kilogram" cannot be stated.

    It is eligibility on one dimension and ordering on another, and the brief
    has one control for each: `max_axis_value` caps the *selected* axis, and
    the selected axis is the one being ordered on. So the budget is either
    applied to the wrong quantity or not applied at all.
    """

    def ranked(self, result):
        return [(entry['asin'], entry['value']) for entry in
                result['candidates']
                if entry['decision'] in (RANKED, SHORTLISTED)]

    def over_budget(self, result):
        return [entry for entry in result['candidates']
                if entry['decision'] == OVER_BUDGET]

    def test_a_hundred_euro_budget_on_a_per_kilogram_axis_excludes_nothing(self):
        """The failure is silent, which is what makes it worth a test.

        The shelf runs from 2.96 to 8.78 EUR/kg, so a cap of 100 read as a
        purchase budget removes nobody and the study reports a clean
        recommendation over candidates whose pack prices were never compared
        with the budget at all.
        """
        capped = self.analyse(self.variant(
            ('require_claims = ["bronze_die"]',
             'require_claims = ["bronze_die"]\nmax_axis_value = 100')))
        self.assertEqual(self.over_budget(capped), [])
        self.assertEqual(capped['outcome']['code'], 'recommendation')
        self.assertEqual(self.ranked(capped), self.ranked(self.analyse()))

    def test_the_cap_that_does_fire_says_it_is_a_price_per_kilogram(self):
        """The unit in the exclusion sentence is the evidence of the mismatch.

        A reader who asked for a 5 EUR budget is told the product is "above
        the 5 EUR/kg this brief set as its limit". The control is correct and
        is answering a question nobody asked.
        """
        capped = self.analyse(self.variant(
            ('require_claims = ["bronze_die"]',
             'require_claims = ["bronze_die"]\nmax_axis_value = 5')))
        excluded = self.over_budget(capped)
        self.assertEqual([entry['asin'] for entry in excluded],
                         ['B0D4R7K82Q', 'B07NZ1K8L3'])
        for entry in excluded:
            self.assertEqual(entry['unit'], 'EUR/kg')
            self.assertIn('5 EUR/kg this brief set as its limit',
                          entry['reason'])

    def test_the_food_categories_publish_no_total_price_axis_to_move_to(self):
        """There is nowhere to express the budget, and it is not universal.

        Dry pasta and basmati publish no price axis at all, so the budget has
        no home in either. Mounting paste does publish one — which is why the
        gap must not be recorded as a fact about every category — and it still
        does not help: that category orders on pack size by default, and
        `max_axis_value` would cap pack size rather than price.
        """
        for key in ('dry_pasta', 'basmati_rice'):
            self.assertNotIn('price', get(key).axis_keys)
        paste = get('tyre_mounting_paste')
        self.assertIn('price', paste.axis_keys)
        self.assertEqual(paste.default_axis, 'quantity')


class FreshnessIsComputedAndUnconsumed(Variant):
    """The declared age policy is measured, reported, and decides nothing.

    This is the sharpest of the three, because the presentation is already
    right. The renderer puts a banner above the headline saying the comparison
    is historical and that this is not current buying advice — and the
    recommendation stands underneath it. Labelling is the whole mechanism.
    """

    def stale(self):
        return self.analyse(self.variant(
            ('as_of = "2026-09-16"', 'as_of = "2026-10-16"')))

    def test_every_ranked_candidate_breaching_the_policy_changes_nothing(self):
        base, stale = self.analyse(), self.stale()
        self.assertEqual(base['freshness']['stale_ranked'], 0)
        self.assertEqual(stale['freshness']['stale_ranked'], 5)
        self.assertEqual(stale['freshness']['oldest_ranked_days'], 32)
        self.assertGreater(stale['freshness']['oldest_ranked_days'],
                           stale['brief']['freshness']['price_max_age_days'])
        self.assertEqual(stale['shortlist'], base['shortlist'])
        self.assertEqual(stale['outcome']['code'], base['outcome']['code'])
        self.assertEqual(stale['outcome']['code'], 'recommendation')

    def test_staleness_reaches_no_candidate_decision(self):
        """Eligibility is settled before an age is known.

        The ages are attached to candidates that already have their decisions,
        so a stale observation is still a ranked one and still leads.
        """
        base, stale = self.analyse(), self.stale()
        decisions = [(entry['asin'], entry['decision'], entry['rank'])
                     for entry in stale['candidates']]
        self.assertEqual(decisions, [(entry['asin'], entry['decision'],
                                      entry['rank'])
                                     for entry in base['candidates']])
        leader = next(entry for entry in stale['candidates']
                      if entry['rank'] == 1)
        self.assertTrue(leader['stale'])
        self.assertEqual(leader['decision'], SHORTLISTED)

    def test_the_reference_date_the_policy_is_measured_against_is_authored(self):
        """A study cannot go stale unless its own brief says so.

        Every age is measured against `as_of`, which the brief's author
        supplies — the test above had to move that dial to manufacture
        staleness. That is why a delivery reference has to come from somewhere
        the author does not control.
        """
        brief = brief_module.load(BRONZE)
        self.assertEqual(brief.as_of, '2026-09-16')
        self.assertEqual(brief.price_max_age_days, 7)
        self.assertEqual(self.analyse()['freshness']['stale_ranked'], 0)


if __name__ == '__main__':
    unittest.main()
