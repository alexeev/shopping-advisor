"""Stage 6: the refusal matrix at intake, comparison support and conclusion.

The expectations are stated independently in intake/README.md, cases 6 to 9,
11, 14 and 19. These tests assert behavioural boundaries -- what is withheld,
what survives, and where it is placed -- and never grade an interpretation
against its own output. Placement and wording are asserted deliberately: INTAKE
§6 says distinct field names are not the judgement, and that a refusal with
three products under it is a recommendation wearing a disclaimer.

Everything here is inert without a plan. The legacy briefs' ids, decisions and
report bytes are pinned elsewhere; this module checks only that a plan-less
analysis carries no gates and renders no requirements section.
"""
import contextlib
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.analysis.category import get
from shopping_advisor.study import brief as brief_module
from shopping_advisor.study import bundle, controls, gates, intake, writeup
from shopping_advisor.study.__main__ import main
from shopping_advisor.study.analysis import RANKED, SHORTLISTED, analyse

HERE = Path(__file__).parent
STUDIES = HERE / 'studies'
INTAKE = HERE / 'intake'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
DRYING = STUDIES / 'pasta-low-temperature-drying.toml'
SUPPORTED = INTAKE / 'supported-plan.json'
UNSUPPORTED = INTAKE / 'unsupported-plan.json'
DELIVERED_PLAN, DELIVERED_BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'
BUDGET_PLAN, BUDGET_BRIEF = INTAKE / 'budget-plan.json', INTAKE / 'budget-brief.json'

REVIEWED = dict(evidence=[dict(id='external-observation', sha256='a' * 64)],
                reviews=[dict(id='declared-review', sha256='b' * 64)])


def ranked_order(result):
    return [(e['asin'], e['value']) for e in result['candidates']
            if e['decision'] in (RANKED, SHORTLISTED)]


class GateCase(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def refreshed(self, plan):
        plan['readback']['text'] = intake.render_readback(plan)
        intake.check(plan)
        return plan

    def bound(self, brief, plan, **changes):
        return replace(brief, intake=intake.binding(plan), **changes)

    def report(self, result):
        return writeup.render(result, 'same-id', [])

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def add_requirement(self, plan, template_index, **changes):
        """A copy of one requirement, changed, appended to the plan."""
        req = copy.deepcopy(plan['requirements'][template_index])
        for key, value in changes.items():
            if key in ('provenance', 'assessment'):
                req[key].update(value)
            else:
                req[key] = value
        plan['requirements'].append(req)
        return req

    def assert_withheld_placement(self, text, leader):
        """INTAKE §6: nobody beneath the refusal; the leader only under its own heading."""
        self.assertNotIn('**Recommendation.**', text)
        result = text.index('## Result')
        bounded = text.index('## Bounded finding')
        self.assertLess(result, bounded)
        self.assertIn('No candidate is put forward.', text[result:bounded])
        self.assertNotIn(leader, text[:bounded], 'the leader appears before its bounded heading')
        self.assertIn(leader, text[bounded:])
        self.assertNotIn('|', text[result:text.index('Analytical outcome', result)],
                         'a table directly under the refusal')
        self.assertIn('It is not a recommendation and must not be read as one.', text)


class InertWithoutAPlan(GateCase):
    def test_a_plan_less_analysis_carries_no_gates_and_renders_none(self):
        result, _ = analyse(brief_module.load(BRONZE))
        self.assertIsNone(result['gates'])
        self.assertEqual(result['stop'], '')
        text = self.report(result)
        self.assertNotIn('## Requirements and their dispositions', text)
        self.assertNotIn('Bounded finding', text)
        self.assertTrue(text.startswith(f'# {result["brief"]["question"]}\n\n**Recommendation.**'))

    def test_a_legacy_bundle_persists_no_gates_and_no_stop(self):
        directory, manifest = bundle.run(BRIEF := str(BRONZE), directory=self.directory / 'legacy')
        ranking = json.loads((directory / bundle.RANKING).read_text())
        self.assertNotIn('gates', ranking)
        self.assertNotIn('stop', ranking)
        self.assertNotIn('stop', manifest)
        self.assertEqual(manifest['study_id'], 'pasta-bronze-die-bde2b027b117')
        self.assertEqual(bundle.verify(directory)[1], [])


class DeliveredCost(GateCase):
    """Case 6. The recommendation is withheld; the item-price finding survives."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(DELIVERED_PLAN)
        self.brief = brief_module.load(DELIVERED_BRIEF)
        self.result, _ = analyse(self.brief, plan=self.plan)

    def test_the_stop_is_recorded_apart_from_the_analytical_outcome(self):
        conclusion = self.result['gates']['conclusion']
        self.assertEqual(self.result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual(self.result['outcome']['code'], 'recommendation')
        self.assertEqual(conclusion['analytical_outcome'], 'recommendation')
        self.assertEqual(conclusion['permits'], gates.PERMIT_BOUNDED_FINDING)
        self.assertEqual(conclusion['withheld'], ['delivered'])
        self.assertEqual(self.result['shortlist'], [])
        self.assertFalse(any(e['decision'] == SHORTLISTED for e in self.result['candidates']))

    def test_the_bounded_finding_is_the_legacy_ranking_unchanged(self):
        plain, _ = analyse(brief_module.load(BRONZE))
        self.assertEqual(ranked_order(self.result), ranked_order(plain))
        self.assertEqual(self.result['outcome'], plain['outcome'])
        self.assertEqual(self.result['ranking'], plain['ranking'])
        self.assertEqual(ranked_order(self.result)[0][0], 'B0DQ2N5HRW')

    def test_comparison_support_refuses_the_substitution_and_names_the_narrower_question(self):
        comparison = self.result['gates']['comparison']
        self.assertFalse(comparison['supported'])
        self.assertEqual(comparison['refused'], 'substitution')
        self.assertEqual([u['id'] for u in comparison['unanswered']], ['delivered'])
        self.assertEqual(comparison['answers'], [])   # `listed` is not decisive
        self.assertIn('lowest price per kg in EUR/kg', comparison['bounded_question'])

    def test_the_report_withholds_in_place_and_keeps_the_finding_under_its_own_heading(self):
        text = self.report(self.result)
        self.assertTrue(text.startswith(f'# {self.brief.question}\n\n**Recommendation withheld.**'))
        self.assertIn('`delivered`', text.splitlines()[2])
        self.assert_withheld_placement(text, 'B0DQ2N5HRW')
        self.assertIn('## Bounded finding: Price per kg only', text)
        self.assertIn('answers a narrower question than the one this study was asked', text)
        self.assertIn('B0DQ2N5HRW leads on price per kg, 9.1% ahead', text)
        self.assertIn('It does not answer `delivered`: the substitution is refused', text)

    def test_the_agent_axis_choice_is_legible_as_the_agents_and_not_decisive(self):
        rows = {r['id']: r for r in self.result['gates']['intake']['requirements']}
        self.assertEqual((rows['listed']['author'], rows['listed']['settlement'],
                          rows['listed']['decisive'], rows['listed']['disposition']),
                         ('agent', 'assumed', False, gates.ENFORCED))
        self.assertFalse(rows['listed']['restricts_conclusion'])
        self.assertTrue(rows['delivered']['restricts_conclusion'])
        self.assertEqual(rows['delivered']['routing'], gates.GAP_PLAN)
        text = self.report(self.result)
        self.assertIn('| `listed` — Order on listed price per kilogram as the available axis;', text)
        self.assertIn('| objective, priority 2, not decisive | assumed | agent |', text)

    def test_rewriting_the_cost_basis_prose_lifts_nothing(self):
        """§13's negative test: the gates read no narrative field."""
        relabelled = replace(self.brief, cost_basis='The listed price of the pack. Delivery excluded.',
                             limits=(), unacceptable=())
        result, _ = analyse(relabelled, plan=self.plan)
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual(result['gates'], self.result['gates'])
        # And the other way round: prose claiming delivered cost on a fully
        # supported plan creates no requirement and no stop.
        supported = intake.load(SUPPORTED)
        bronze = self.bound(brief_module.load(BRONZE), supported,
                            cost_basis='Delivered cost, including shipping.')
        result, _ = analyse(bronze, plan=supported)
        self.assertEqual(result['stop'], '')
        self.assertEqual(result['gates']['conclusion']['permits'], gates.PERMIT_RECOMMENDATION)

    def test_the_bundle_records_the_stop_and_replays_it(self):
        directory, manifest = bundle.run(str(DELIVERED_BRIEF), directory=self.directory / 'delivered',
                                         plan=str(DELIVERED_PLAN))
        self.assertEqual((manifest['outcome'], manifest['stop'], manifest['permits'],
                          manifest['counts']['shortlisted']),
                         ('recommendation', gates.REQUIREMENT_UNSUPPORTED, gates.PERMIT_BOUNDED_FINDING, 0))
        ranking = json.loads((directory / bundle.RANKING).read_text())
        self.assertEqual(ranking['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual(ranking['gates']['stage_gates_version'], gates.STAGE_GATES_VERSION)
        self.assertEqual(bundle.verify(directory)[1], [])
        text = (directory / bundle.REPORT).read_text()
        self.assert_withheld_placement(text, 'B0DQ2N5HRW')
        self.assertIn('--plan <bundle directory>/intake-plan.json', text)

    def test_a_tampered_stop_or_a_missing_gates_block_is_a_finding(self):
        directory, _ = bundle.run(str(DELIVERED_BRIEF), directory=self.directory / 'tamper',
                                  plan=str(DELIVERED_PLAN))
        path = directory / bundle.RANKING
        ranking = json.loads(path.read_text())

        def rewrite(data):
            path.write_text(json.dumps(data))
            manifest = json.loads((directory / bundle.MANIFEST).read_text())
            manifest['artifacts'] = bundle.artifact_digests(directory)
            (directory / bundle.MANIFEST).write_text(json.dumps(manifest))

        tampered = copy.deepcopy(ranking)
        tampered['stop'] = ''
        tampered['gates']['conclusion']['stop'] = ''
        rewrite(tampered)
        findings = bundle.verify(directory)[1]
        self.assertEqual(findings[0]['code'], 'decision_moved')
        self.assertIn('the stop', findings[0]['message'])
        stripped = copy.deepcopy(ranking)
        stripped.pop('gates'), stripped.pop('stop')
        rewrite(stripped)
        self.assertEqual([f['code'] for f in bundle.verify(directory)[1]], ['stage_gates_missing'])

    def test_the_cli_says_withheld_wherever_it_says_the_outcome(self):
        output = self.directory / 'cli'
        status, text = self.cli('run', DELIVERED_BRIEF, '--plan', DELIVERED_PLAN, '-o', output)
        self.assertEqual(status, 0, text)
        self.assertIn('[recommendation on the available axis; recommendation withheld: requirement_unsupported]', text)
        self.assertIn('shortlisted   0', text)
        status, text = self.cli('verify', output)
        self.assertEqual(status, 0, text)
        self.assertIn('recommendation withheld: requirement_unsupported', text)
        status, text = self.cli('plan-check', DELIVERED_PLAN, '--brief', DELIVERED_BRIEF)
        self.assertEqual(status, 0, text)
        self.assertIn('readiness     bounded', text)
        self.assertIn('delivered     unsupported', text)
        self.assertIn('restricts the conclusion', text)


class PurchaseBudget(GateCase):
    """Case 7. Eligibility on one dimension, ordering on another."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(BUDGET_PLAN)
        self.brief = brief_module.load(BUDGET_BRIEF)

    def test_the_unsupported_combination_is_detected_without_changing_units(self):
        result, _ = analyse(self.brief, plan=self.plan)
        rows = {r['id']: r for r in result['gates']['intake']['requirements']}
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual(rows['budget']['disposition'], gates.UNSUPPORTED)
        self.assertEqual(rows['price']['disposition'], gates.ENFORCED)
        self.assertEqual(result['gates']['comparison']['answers'], ['price'])
        self.assertIsNone(self.brief.max_axis_value)
        self.assertEqual([e for e in result['candidates'] if e['decision'] == 'over_budget'], [])
        self.assertEqual(ranked_order(result), ranked_order(analyse(brief_module.load(BRONZE))[0]))
        self.assertIn('would read 100 as a hundred euros per kilogram', self.report(result))

    def test_a_budget_written_into_unacceptable_satisfies_nothing(self):
        """The trap INTAKE §4 names, now a negative test for the new controls."""
        prose = self.brief.unacceptable + ('Anything costing more than 100 EUR in total.',)
        result, _ = analyse(replace(self.brief, unacceptable=prose), plan=self.plan)
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertIn('budget', result['gates']['conclusion']['withheld'])

    def test_routing_the_budget_through_the_per_kilogram_cap_is_refused(self):
        with self.assertRaisesRegex(intake.PlanError, 'max_axis_value: brief adds a cap with no active requirement'):
            analyse(replace(self.brief, max_axis_value=100), plan=self.plan)

    def test_what_the_gate_cannot_see_is_stated_not_hidden(self):
        """A plan author who maps the budget onto the cap passes as enforced.

        That is the semantic-execution limit INTAKE §12 states, and the report
        says so beside the table rather than claiming otherwise.
        """
        plan = copy.deepcopy(self.plan)
        budget = next(r for r in plan['requirements'] if r['id'] == 'budget')
        budget['assessment'].update(path='control', gap=None, controls=[
            controls.resolve('dry_pasta', 'max_axis_value', axis='price_per_base', unit='EUR/kg', value=100)])
        self.refreshed(plan)
        result, _ = analyse(self.bound(self.brief, plan, max_axis_value=100), plan=plan)
        self.assertEqual(result['stop'], '')
        self.assertIn('a control that runs correctly can answer the wrong question', self.report(result))


class IndependentConstraint(GateCase):
    """Case 7's acceptable outcome, first branch: a supported independent
    constraint. The ceiling sits on one axis and the ordering on another, and
    the harness enforces both without changing either's units or meaning.
    Added on 2026-09-18 after the second school-backpack trial met the case on
    a category that publishes the bounded axis."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(SUPPORTED)
        self.brief = brief_module.load(BRONZE)
        self.plan['user_evidence']['messages'][0]['text'] += ' Nothing above a kilogram per pack.'
        self.mapping = controls.resolve('dry_pasta', 'axis_bound', axis='quantity', unit='g', max=1000)
        self.add_requirement(
            self.plan, 0, id='pack_ceiling', statement='Exclude packs above 1000 g.',
            provenance=dict(wording='Nothing above a kilogram per pack'),
            assessment=dict(path='control', controls=[self.mapping]),
            effects=[dict(stage='candidate_assessment', consequence='Exclude packs above 1000 g.')])
        self.refreshed(self.plan)
        self.bounds = (self.mapping['parameters'],)

    def test_the_bound_is_enforced_at_candidate_assessment_and_the_ordering_stands(self):
        result, _ = analyse(self.bound(self.brief, self.plan, axis_bounds=self.bounds), plan=self.plan)
        row = next(r for r in result['gates']['intake']['requirements'] if r['id'] == 'pack_ceiling')
        self.assertEqual((row['disposition'], row['controls']), (gates.ENFORCED, ['axis_bound']))
        self.assertEqual([s['status'] for s in row['stages']], [gates.ENFORCED])
        self.assertEqual(result['stop'], '')
        self.assertEqual(result['gates']['intake']['readiness'], gates.FULL_REQUEST)
        plain = analyse(self.brief)[0]
        outside = [e for e in result['candidates'] if e['decision'] == 'out_of_bounds']
        heavy = {e['asin'] for e in outside if 'above the 1000 g' in e['reason']}
        self.assertTrue(heavy, 'the committed cases include packs above a kilogram')
        # A pack whose size the generic layer could not trust is not admitted
        # on the strength of being inside the range: it is excluded as
        # unassessable, and says so.
        self.assertTrue(all('above the 1000 g' in e['reason'] or 'no trusted pack size' in e['reason']
                            for e in outside), [e['reason'] for e in outside])
        heavy = {e['asin'] for e in outside}
        self.assertEqual(ranked_order(result),
                         [(a, v) for a, v in ranked_order(plain) if a not in heavy],
                         'the ordering axis is untouched; the bound only removes')
        self.assertEqual(result['constraints']['axis_bounds'], [self.mapping['parameters']])
        text = self.report(result)
        self.assertIn('| Bound on `quantity` in g | at most 1000 | stated in the brief |', text)
        self.assertIn('### Outside a bound this brief set', text)

    def test_a_bound_the_plan_never_recorded_is_refused(self):
        plan = intake.load(SUPPORTED)
        with self.assertRaisesRegex(intake.PlanError, 'axis_bounds: brief adds or drops a bound'):
            analyse(self.bound(self.brief, plan, axis_bounds=self.bounds), plan=plan)

    def test_a_recorded_bound_that_did_not_reach_the_brief_is_refused(self):
        with self.assertRaisesRegex(intake.PlanError, 'did not reach constraints.axis_bounds'):
            analyse(self.bound(self.brief, self.plan), plan=self.plan)
        loosened = ({**self.mapping['parameters'], 'max': 2000},)
        with self.assertRaisesRegex(intake.PlanError, 'did not reach constraints.axis_bounds'):
            analyse(self.bound(self.brief, self.plan, axis_bounds=loosened), plan=self.plan)

    def test_without_bounds_every_persisted_shape_is_unchanged(self):
        result, _ = analyse(self.brief)
        self.assertNotIn('axis_bounds', result['constraints'])
        self.assertNotIn('axis_bounds', result['brief']['constraints'])
        self.assertNotIn('bounds', result['ranking'])
        self.assertNotIn('out_of_bounds', result['ranking']['counts'])
        self.assertNotIn('Bound on', self.report(result))


class ExternalEvidenceCondition(GateCase):
    """Cases 8 and 19, and the unassessed route of INTAKE §3."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(SUPPORTED)
        self.brief = brief_module.load(BRONZE)
        self.plan['user_evidence']['messages'][0]['text'] += ' Only ones an independent test rated well.'
        self.rated = self.add_requirement(
            self.plan, 0, id='rated', statement='Only listings an independent test rated well.',
            provenance=dict(wording='Only ones an independent test rated well'),
            assessment=dict(path='evidence_review', controls=[]),
            effects=[dict(stage='candidate_assessment', consequence='Exclude listings without a good independent rating.')])

    def analysed(self, state, **assessment):
        self.rated['assessment'].update(state=state, **assessment)
        self.refreshed(self.plan)
        return analyse(self.bound(self.brief, self.plan), plan=self.plan)[0]

    def test_a_supported_finding_still_withholds_selection(self):
        result = self.analysed('supported', **REVIEWED)
        row = next(r for r in result['gates']['intake']['requirements'] if r['id'] == 'rated')
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual((row['disposition'], row['routing']), (gates.ASSESSED, gates.EXECUTE))
        self.assertIn('scoped explanation, not automated selection', row['reason'])
        self.assertEqual(ranked_order(result), ranked_order(analyse(self.brief)[0]),
                         'no candidate was removed by hand to disguise the missing control')
        self.assert_withheld_placement(self.report(result), 'B0DQ2N5HRW')

    def test_awaiting_evidence_is_a_coverage_route_not_a_capability_gap(self):
        result = self.analysed('not_assessed')
        row = next(r for r in result['gates']['intake']['requirements'] if r['id'] == 'rated')
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNASSESSED)
        self.assertEqual((row['disposition'], row['routing']), (gates.AWAITING_EVIDENCE, gates.COLLECT_OR_STOP))
        statement = result['gates']['conclusion']['statement']
        self.assertIn('not a capability gap', statement)
        text = self.report(result)
        self.assertIn('**Recommendation withheld.**', text)
        self.assert_withheld_placement(text, 'B0DQ2N5HRW')

    def test_a_failed_hard_constraint_is_a_refusal_with_bounded_observations_elsewhere(self):
        """Case 19."""
        result = self.analysed('failed', **REVIEWED)
        self.assertEqual(result['stop'], gates.REQUIREMENT_FAILED)
        self.assertEqual(result['shortlist'], [])
        text = self.report(result)
        self.assertTrue(text.startswith(f'# {self.brief.question}\n\n**Requirement cannot be met.**'))
        self.assertIn('`rated`', text.splitlines()[2])
        self.assert_withheld_placement(text, 'B0DQ2N5HRW')
        self.assertIn('the bound evidence assessment failed', text)

    def test_failure_outranks_a_gap_and_both_are_named(self):
        self.rated['assessment'].update(state='failed', **REVIEWED)
        self.plan['user_evidence']['messages'][0]['text'] += ' Cheapest once delivered.'
        self.add_requirement(self.plan, 1, id='delivered', statement='Lowest delivered cost.',
                             priority=2, provenance=dict(wording='Cheapest once delivered'),
                             assessment=dict(path='unsupported', controls=[], gap=dict(
                                 kind='evidence_and_method', reason='no shipping data', next_step='probe')))
        self.refreshed(self.plan)
        result, _ = analyse(self.bound(self.brief, self.plan), plan=self.plan)
        self.assertEqual(result['stop'], gates.REQUIREMENT_FAILED)
        self.assertEqual(result['gates']['conclusion']['withheld'], ['rated', 'delivered'])


class SupportedMethodMissingEvidence(GateCase):
    """Case 9: insufficient evidence stays a coverage finding, not a gap."""

    def test_insufficient_evidence_under_a_fully_enforced_plan_is_diagnosed_as_coverage(self):
        drying = brief_module.load(DRYING)
        plan = intake.load(SUPPORTED)
        plan.update(question=drying.question, use_case=drying.use_case)
        plan['user_evidence']['messages'][0]['text'] = (
            'Require a low-temperature drying statement. Choose the cheapest listed price per '
            'kilogram on Amazon.de with delivery in Germany. Dry pasta only. Any pack size is fine.')
        bronze = plan['requirements'][0]
        bronze.update(id='drying', statement='Require the vendor low-temperature drying claim.')
        bronze['provenance']['wording'] = 'Require a low-temperature drying statement'
        bronze['assessment']['controls'] = [controls.resolve('dry_pasta', 'require_claims', claims=['low_temperature_drying'])]
        self.refreshed(plan)
        result, _ = analyse(self.bound(drying, plan), plan=plan)
        conclusion = result['gates']['conclusion']
        self.assertEqual(result['outcome']['code'], 'insufficient_evidence')
        self.assertEqual(result['stop'], '')
        self.assertEqual(conclusion['permits'], gates.PERMIT_REFUSAL)
        self.assertTrue(conclusion['diagnosis'].startswith('coverage:'))
        self.assertIn('Not a capability gap', conclusion['diagnosis'])
        self.assertEqual(result['gates']['intake']['readiness'], gates.FULL_REQUEST)
        plain, _ = analyse(drying)
        self.assertEqual(result['candidates'], plain['candidates'], 'candidate accounting is preserved')
        text = self.report(result)
        self.assertIn('**Insufficient evidence.**', text)
        self.assertIn('No candidate is put forward.', text)
        self.assertNotIn('Bounded finding', text)


class WrongObjective(GateCase):
    """Case 11: a valid control answering the wrong question, mounting paste."""

    def test_a_structured_use_case_objective_the_axis_does_not_answer_is_caught(self):
        source = self.directory / 'paste.toml'
        source.write_text(f'''
brief_version = 1
id = "paste-one-tyre"
question = "Which tyre mounting paste for fitting one scooter tyre?"
use_case = "One scooter tyre, once."
category = "tyre_mounting_paste"
marketplace = "www.amazon.de"
inputs = ["{(STUDIES / '..' / 'cases' / 'mounting_paste_v1.jsonl.gz').resolve()}"]
[constraints]
axis = "price"
minimum_candidates = 1
''', encoding='utf-8')
        brief = brief_module.load(source)
        plan = intake.load(SUPPORTED)
        plan.update(id='paste-intake', question=brief.question, use_case=brief.use_case,
                    category='tyre_mounting_paste', delivery_region='')
        plan['user_evidence']['messages'] = [dict(id='u1', author='user', redactions=[],
            text='I am fitting one scooter tyre. Which mounting paste? Cheapest is fine.')]
        one_tyre = copy.deepcopy(plan['requirements'][1])
        one_tyre.update(id='one_tyre', statement='Enough paste for one scooter tyre and no more.', priority=1)
        one_tyre['provenance'].update(wording='fitting one scooter tyre')
        one_tyre['assessment'].update(path='unsupported', controls=[], gap=dict(
            kind='method', reason='No control judges sufficiency for a use; the pack-size axis orders quantity, not adequacy',
            next_step='Ask how much one tyre needs, or state the ordering as bounded'))
        cheapest = copy.deepcopy(plan['requirements'][1])
        cheapest.update(id='cheapest', statement='Order on listed price, lower first.', priority=2, decisive=False,
                        settlement='assumed')
        cheapest['provenance'].update(author='agent', refs=[], basis='reasonableness', wording='Cheapest is fine.')
        cheapest['assessment']['controls'] = [controls.resolve('tyre_mounting_paste', 'value_usability', axis='price')]
        plan['requirements'] = [one_tyre, cheapest]
        self.refreshed(plan)
        result, _ = analyse(self.bound(brief, plan), plan=plan)
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        self.assertEqual([u['id'] for u in result['gates']['comparison']['unanswered']], ['one_tyre'])
        self.assertIn(result['outcome']['code'], ('recommendation', 'no_decisive_winner'))
        # The category was not touched to make this pass: its smallest-pack
        # default is the original failure and stays visible as the default.
        self.assertEqual(get('tyre_mounting_paste').default_axis, 'quantity')
        text = self.report(result)
        self.assertIn('It does not answer `one_tyre`', text)
        self.assertIn('## Bounded finding: Price only', text)


class StageEffects(GateCase):
    """Case 14: one exclusion, several stages, each with its own disposition."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(SUPPORTED)
        self.brief = brief_module.load(BRONZE)

    def test_each_stage_of_a_seller_exclusion_is_accounted_for_separately(self):
        self.plan['user_evidence']['messages'][0]['text'] += ' Nothing from that seller.'
        self.add_requirement(
            self.plan, 0, id='seller', statement='Nothing from the named seller.',
            provenance=dict(wording='Nothing from that seller'),
            assessment=dict(path='unsupported', controls=[], gap=dict(
                kind='discovery_and_eligibility', reason='No seller field is extracted or filtered',
                next_step='Scoped maintenance for a seller control; meanwhile the recommendation is withheld')),
            effects=[dict(stage='discovery', consequence='Do not query the seller storefront.'),
                     dict(stage='collection', consequence='Do not fetch the seller pages.'),
                     dict(stage='candidate_assessment', consequence='Exclude offers sold by the seller.')])
        self.refreshed(self.plan)
        result, _ = analyse(self.bound(self.brief, self.plan), plan=self.plan)
        row = next(r for r in result['gates']['intake']['requirements'] if r['id'] == 'seller')
        self.assertEqual([(s['stage'], s['status']) for s in row['stages']],
                         [('discovery', 'recorded'), ('collection', 'recorded'),
                          ('candidate_assessment', gates.UNSUPPORTED)])
        self.assertIn('performs no discovery', row['stages'][0]['note'])
        self.assertEqual(result['stop'], gates.REQUIREMENT_UNSUPPORTED)
        text = self.report(result)
        self.assertIn('- `seller` at discovery: Do not query the seller storefront. — recorded; this study performs no discovery', text)
        self.assertIn('- `seller` at candidate assessment: Exclude offers sold by the seller. — unsupported.', text)

    def test_an_enforced_control_is_enforced_at_its_stage_and_recorded_at_others(self):
        bronze = self.plan['requirements'][0]
        bronze['effects'].append(dict(stage='discovery', consequence='Search for bronze-die listings first.'))
        self.refreshed(self.plan)
        result, _ = analyse(self.bound(self.brief, self.plan), plan=self.plan)
        row = result['gates']['intake']['requirements'][0]
        self.assertEqual([(s['stage'], s['status']) for s in row['stages']],
                         [('candidate_assessment', gates.ENFORCED), ('discovery', 'recorded')])
        self.assertEqual(result['stop'], '')

    def test_a_non_decisive_unsupported_preference_restricts_nothing(self):
        self.plan['user_evidence']['messages'][0]['text'] += ' Italian brands preferred.'
        self.add_requirement(
            self.plan, 1, id='italian', statement='Prefer Italian brands.', role='preference', priority=2,
            decisive=False, provenance=dict(wording='Italian brands preferred'),
            assessment=dict(path='unsupported', controls=[], gap=dict(
                kind='attribute', reason='No brand-origin attribute is extracted', next_step='None needed; not decisive')))
        self.refreshed(self.plan)
        result, _ = analyse(self.bound(self.brief, self.plan), plan=self.plan)
        row = next(r for r in result['gates']['intake']['requirements'] if r['id'] == 'italian')
        self.assertEqual(row['disposition'], gates.UNSUPPORTED)
        self.assertFalse(row['restricts_conclusion'])
        self.assertEqual(result['stop'], '')
        self.assertEqual(result['gates']['intake']['readiness'], gates.FULL_REQUEST)
        self.assertIn('| preference, priority 2, not decisive | stated | user | unsupported', self.report(result))
        self.assertTrue(self.report(result).startswith(f'# {self.brief.question}\n\n**Recommendation.**'))


class IntakeReadiness(GateCase):
    def test_readiness_is_staged_and_names_its_next_action(self):
        supported = gates.intake_gate(intake.load(SUPPORTED))
        self.assertEqual(supported['readiness'], gates.FULL_REQUEST)
        self.assertTrue(supported['category_registered'])
        unknown = gates.intake_gate(intake.load(UNSUPPORTED))
        self.assertEqual(unknown['readiness'], gates.BOUNDED)
        self.assertFalse(unknown['category_registered'])
        self.assertIn("'cordless_hedge_trimmer' is not a registered category", unknown['next_action'])
        self.assertIn('Planning authorises no engineering', unknown['next_action'])
        self.assertEqual(unknown['requirements'][0]['routing'], gates.GAP_PLAN)
        delivered = gates.intake_gate(intake.load(DELIVERED_PLAN))
        self.assertEqual(delivered['readiness'], gates.BOUNDED)
        self.assertIn('`delivered` stays unsupported', delivered['next_action'])

    def test_a_blocker_is_a_planning_outcome_not_a_path_through(self):
        plan = intake.load(SUPPORTED)
        plan['requirements'][3]['settlement'] = 'unresolved'
        self.refreshed(plan)
        gate = gates.intake_gate(plan)
        self.assertEqual(gate['readiness'], gates.BLOCKED)
        self.assertIn('packs: decisive and unresolved; ask, or stop', gate['blockers'][0])
        with self.assertRaisesRegex(intake.PlanError, 'unresolved'):
            intake.check_transition(plan, self.bound(brief_module.load(BRONZE), plan))
        status, text = self.cli('plan-check', self.write(plan))
        self.assertEqual(status, 0, text)
        self.assertIn('readiness     blocked', text)

    def write(self, plan):
        path = self.directory / 'plan.json'
        path.write_text(json.dumps(plan), encoding='utf-8')
        return path

    def test_a_correction_blocks_until_reconciled(self):
        plan = intake.load(SUPPORTED)
        plan['user_evidence']['messages'].append(dict(id='u3', author='user', text='Actually include shipping.', redactions=[]))
        plan['readback']['response'].update(status='corrected', message_ids=['u3'], scope='Cost basis')
        intake.check(plan)
        gate = gates.intake_gate(plan)
        self.assertEqual(gate['readiness'], gates.BLOCKED)
        self.assertIn('corrected the read-back', gate['blockers'][0])


class Attribution(GateCase):
    """§10: what the report may say about agreement is a function of the record."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(SUPPORTED)
        self.brief = brief_module.load(BRONZE)

    def rendered(self):
        self.refreshed(self.plan) if self.plan['readback']['response']['status'] != 'not_presented' else intake.check(self.plan)
        result, _ = analyse(self.bound(self.brief, self.plan), plan=self.plan)
        return self.report(result)

    def test_no_response_is_not_confirmation(self):
        text = self.rendered()
        self.assertIn('received no response. Silence is not confirmation', text)
        self.assertNotIn('The user confirmed', text)

    def test_not_presented_says_so(self):
        self.plan['readback'].update(text='', response=dict(status='not_presented', message_ids=[], scope=''))
        text = self.rendered()
        self.assertIn('No read-back of this plan revision was presented', text)
        self.assertNotIn('The user confirmed', text)

    def test_confirmation_is_attributed_to_the_retained_message_and_waives_nothing(self):
        self.plan['user_evidence']['messages'].append(dict(id='u3', author='user', text='Yes, that scope.', redactions=[]))
        self.plan['readback']['response'].update(status='confirmed', message_ids=['u3'],
                                                 scope='This revision of the historical comparison')
        text = self.rendered()
        self.assertIn('The user confirmed the scope of this plan revision (This revision of the historical comparison; message `u3`)', text)
        self.assertIn('does not waive a failed structural check', text)

    def test_delegation_is_not_rendered_as_confirmation(self):
        self.plan['user_evidence']['messages'].append(dict(id='u3', author='user', text='You decide on pack sizes.', redactions=[]))
        self.plan['readback']['response'].update(status='delegated', message_ids=['u3'], scope='Pack sizes')
        text = self.rendered()
        self.assertIn('The user delegated choices within this plan revision (Pack sizes; message `u3`)', text)
        self.assertIn('it is not a user-confirmed result', text)
        self.assertNotIn('The user confirmed', text)


class Contract(unittest.TestCase):
    def test_the_stage_gates_contract_is_discovered_and_pinned(self):
        self.assertEqual(maintenance._contract_versions()['stage_gates'], gates.STAGE_GATES_VERSION)
        with patch.object(gates, 'STAGE_GATES_VERSION', 2):
            findings = maintenance.check_contracts(maintenance.load_baseline()).findings
            self.assertTrue(any(f.code == 'contract_version' and 'stage_gates' in f.message for f in findings))

    def test_the_plan_backed_examples_replay_through_the_documented_commands(self):
        examples = [e for e in maintenance.load_baseline()['examples'] if e.get('plan')]
        self.assertEqual(sorted(e['name'] for e in examples), ['pasta-delivered-cost', 'pasta-purchase-budget'])
        for example in examples:
            self.assertEqual(example['expect']['stop'], gates.REQUIREMENT_UNSUPPORTED)
            self.assertEqual(example['expect']['shortlisted'], 0)
        result = maintenance.check_examples({'examples': examples})
        self.assertTrue(result.passed, result.findings)

    def test_a_moved_stop_is_an_example_finding(self):
        example = next(e for e in maintenance.load_baseline()['examples'] if e['name'] == 'pasta-delivered-cost')
        moved = dict(example, expect=dict(example['expect'], stop=''))
        result = maintenance.check_examples({'examples': [moved]})
        self.assertEqual([f.code for f in result.findings], ['example_decision_changed'])
        self.assertIn('stop', result.findings[0].message)


if __name__ == '__main__':
    unittest.main()
