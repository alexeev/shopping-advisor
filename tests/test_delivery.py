"""Stage 7: current advice is a structural condition checked at delivery.

INTAKE §9 and case 16 in intake/README.md state the expectations: decisive
prices that breach the declared policy block current advice; an old study
delivered again later blocks; a regression fixture stays historical however
fresh its dates look; and a disclosure never stands in for a block. The
analysis keeps measuring against the brief's ``as_of`` -- that is the
historical question -- and the delivery record measures against a reference
the brief's author does not supply.

Every reference here is declared and fixed, so nothing in this module reads
the clock, and nothing in it starts failing with the passage of time.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.study import brief as brief_module
from shopping_advisor.study import bundle, delivery, gates
from shopping_advisor.study.__main__ import main
from shopping_advisor.study.analysis import analyse

HERE = pathlib.Path(__file__).resolve().parent
STUDIES = HERE / 'studies'
INTAKE = HERE / 'intake'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
DELIVERED_PLAN, DELIVERED_BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'

#: The day the case set was built, and thirty days on: the two references
#: INTAKE §1 measured the inert freshness block with.
BUILT = '2026-09-16T12:00:00+00:00'
LATER = '2026-10-16T12:00:00+00:00'
GOVERNED = ['B0DQ2N5HRW', 'B08WJGD5Z5', 'B08BNQ2D54', 'B0D4R7K82Q', 'B07NZ1K8L3']


class DeliveryCase(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.written = []
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in self.written])

    def variant(self, *replacements, source=BRONZE):
        """A brief beside the committed one, because its feeds are relative to it."""
        text = source.read_text(encoding='utf-8')
        for old, new in replacements:
            self.assertIn(old, text, f'the brief no longer contains {old!r}')
            text = text.replace(old, new, 1)
        path = STUDIES / f'.tmp-delivery-{len(self.written)}-{source.name}'
        path.write_text(text, encoding='utf-8')
        self.written.append(path)
        return path

    def current(self, *extra):
        return self.variant(('price_max_age_days = 7',
                             'price_max_age_days = 7\nscope = "current_advice"'), *extra)

    def run_study(self, source=BRONZE, name='bundle', **kwargs):
        return bundle.run(str(source), directory=str(self.directory / name),
                          started_at='2026-09-16T00:00:00+00:00',
                          finished_at='2026-09-16T00:00:01+00:00', **kwargs)

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def deliver(self, directory, reference):
        status, text = self.cli('deliver', directory, '--reference', reference)
        self.assertEqual(status, 0, text)
        return delivery.latest(delivery.read(pathlib.Path(directory) / delivery.RECORD)), text

    def validate(self, directory, *flags):
        status, text = self.cli('validate-report', directory, *flags)
        return status, json.loads(text)

    def refresh_digests(self, directory):
        manifest = json.loads((directory / bundle.MANIFEST).read_text())
        manifest['artifacts'] = bundle.artifact_digests(directory)
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))


class ScopeIsDeclaredNotInferred(DeliveryCase):
    def test_silence_is_historical_and_moves_no_legacy_byte(self):
        brief = brief_module.load(BRONZE)
        self.assertEqual(brief.scope, '')
        self.assertNotIn('scope', brief.as_dict()['freshness'])
        directory, manifest = self.run_study()
        self.assertEqual((manifest['scope'], manifest['scope_source']), ('historical', 'undeclared'))
        self.assertEqual(manifest['study_id'], 'pasta-bronze-die-bde2b027b117')
        self.assertEqual(delivery.scope_of(json.loads((directory / bundle.BRIEF).read_text())),
                         ('historical', 'undeclared'))
        self.assertNotIn('| Scope |', (directory / bundle.REPORT).read_text())

    def test_a_declared_scope_is_persisted_and_rendered_as_a_condition(self):
        directory, manifest = self.run_study(self.current(), name='current')
        self.assertEqual((manifest['scope'], manifest['scope_source']), ('current_advice', 'brief'))
        self.assertEqual(json.loads((directory / bundle.BRIEF).read_text())['freshness']['scope'], 'current_advice')
        text = (directory / bundle.REPORT).read_text()
        self.assertIn('| Scope | current buying advice, **only with a passing delivery record**', text)
        self.assertIn('Declared scope: **current advice**. That is a structural condition, not a label', text)
        self.assertIn('this report is a historical comparison as of 2026-09-16', text)
        historical = self.variant(('price_max_age_days = 7', 'price_max_age_days = 7\nscope = "historical"'))
        directory, _ = self.run_study(historical, name='historical')
        text = (directory / bundle.REPORT).read_text()
        self.assertIn('| Scope | historical comparison as of 2026-09-16; not current buying advice |', text)
        self.assertIn('Declared scope: **historical**. However recent these observations are', text)

    def test_current_advice_needs_a_policy_and_a_rationale(self):
        with self.assertRaisesRegex(brief_module.BriefError, 'current_advice.*needs.*note'):
            brief_module.load(self.current(('note = "The records', 'note = "" # "The records')))
        with self.assertRaisesRegex(brief_module.BriefError, 'current_advice'):
            brief_module.load(self.variant(('price_max_age_days = 7', 'scope = "current_advice"')))
        with self.assertRaisesRegex(brief_module.BriefError, 'is not one of historical, current_advice'):
            brief_module.load(self.variant(('price_max_age_days = 7', 'price_max_age_days = 7\nscope = "live"')))


class TheFixturesStayHistorical(DeliveryCase):
    """Case 16, third request: fresh dates do not make a fixture buying evidence."""

    def test_a_policy_that_passes_permits_nothing_the_brief_did_not_claim(self):
        directory, _ = self.run_study()
        event, text = self.deliver(directory, BUILT)
        self.assertEqual(event['current_advice'], delivery.NOT_IN_SCOPE)
        self.assertEqual(event['counts'], {'governed': 5, 'stale': 0, 'undated': 0})
        self.assertEqual([g['asin'] for g in event['governed']], GOVERNED)
        self.assertIn('Historical comparison as of 2026-09-16; not current buying advice', event['statement'])
        self.assertIn('the brief declares no scope', event['statement'])
        self.assertIn('[not_in_scope]', text)
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['valid'], payload['delivery']['current_advice']),
                         (0, True, delivery.NOT_IN_SCOPE))

    def test_a_later_delivery_is_still_deliverable_as_history_with_its_reference(self):
        directory, _ = self.run_study()
        event, _ = self.deliver(directory, LATER)
        self.assertEqual(event['current_advice'], delivery.NOT_IN_SCOPE)
        self.assertEqual(event['counts']['stale'], 5)
        self.assertIn('Delivered at 2026-10-16T12:00:00+00:00, when 5 of 5', event['statement'])
        self.assertEqual(bundle.verify(directory)[1], [])
        self.assertEqual(self.validate(directory)[0], 0)

    def test_delivery_moves_no_decision_no_report_byte_and_no_identity(self):
        directory, manifest = self.run_study()
        before = {name: (directory / name).read_bytes() for name in bundle.ARTIFACTS}
        self.deliver(directory, BUILT)
        self.deliver(directory, LATER)
        after = {name: (directory / name).read_bytes() for name in bundle.ARTIFACTS}
        self.assertEqual(before, after)
        refreshed = bundle.load_manifest(directory)
        self.assertEqual(refreshed['study_id'], manifest['study_id'])
        self.assertIn(delivery.RECORD, refreshed['artifacts'])
        record = delivery.read(directory / delivery.RECORD)
        self.assertEqual([e['reference'] for e in record['events']], [BUILT, LATER])


class CurrentAdviceIsAStructuralCondition(DeliveryCase):
    """Case 16, first two requests: a block, not a disclosure."""

    def test_a_current_advice_study_needs_a_delivery_record_before_it_validates(self):
        directory, _ = self.run_study(self.current(), name='current')
        status, payload = self.validate(directory)
        self.assertEqual(status, 1)
        self.assertEqual([f['code'] for f in payload['findings']], ['delivery_missing'])
        self.assertEqual(payload['delivery']['current_advice'], 'no_record')

    def test_a_passing_policy_permits_and_a_stale_decisive_input_blocks(self):
        directory, _ = self.run_study(self.current(), name='current')
        event, _ = self.deliver(directory, BUILT)
        self.assertEqual(event['current_advice'], delivery.PERMITTED)
        self.assertIn('for this delivery event; a later delivery is a new assessment', event['statement'])
        self.assertEqual(self.validate(directory)[0], 0)
        event, text = self.deliver(directory, LATER)
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        self.assertEqual(len(event['blockers']), 1)
        self.assertIn('5 of 5 governed observation(s) are older than 7 day(s)', event['blockers'][0])
        for asin in GOVERNED:
            self.assertIn(asin, event['blockers'][0])
        self.assertIn('No current purchasing recommendation at 2026-10-16T12:00:00+00:00', event['statement'])
        self.assertIn('historical comparison as of 2026-09-16 may be delivered instead', event['statement'])
        self.assertIn('[blocked]', text)
        status, payload = self.validate(directory)
        self.assertEqual(status, 1)
        self.assertEqual([f['code'] for f in payload['findings']], ['current_advice_blocked'])
        self.assertEqual(len(delivery.read(directory / delivery.RECORD)['events']), 2)

    def test_the_block_is_measured_against_the_delivery_reference_not_as_of(self):
        """The stage 1 characterisation, closed from the other side.

        The analysis still measures against ``as_of`` and finds nothing stale
        -- that is the historical question, and its answer has not changed.
        The delivery reference is the one the brief's author does not supply.
        """
        directory, _ = self.run_study(self.current(), name='current')
        ranking = json.loads((directory / bundle.RANKING).read_text())
        self.assertEqual(ranking['freshness']['stale_ranked'], 0)
        self.assertEqual(ranking['outcome']['code'], 'recommendation')
        event, _ = self.deliver(directory, LATER)
        self.assertEqual(event['counts']['stale'], 5)
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        self.assertEqual(json.loads((directory / bundle.RANKING).read_text()), ranking,
                         'the analysis is not re-decided at delivery')

    def test_a_completed_semantic_review_does_not_waive_the_block(self):
        directory, _ = self.run_study(self.current(), name='current')
        self.deliver(directory, LATER)
        review = json.loads((directory / bundle.REVIEW).read_text())
        review['reviewer'] = 'test reviewer'
        for item in review['checks'].values():
            item.update(status='pass', findings='synthetic finding for a fixture')
        path = self.directory / 'review.json'
        path.write_text(json.dumps(review))
        status, text = self.cli('review', directory, path)
        self.assertEqual(status, 0, text)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(status, 1)
        self.assertEqual(payload['semantic'], 'pass')
        self.assertEqual([f['code'] for f in payload['findings']], ['current_advice_blocked'])
        # A delivery that passes lifts it without touching the review. What it
        # owes instead, when delivered as audited, is a delivery review of that
        # event (stage 10): the semantic review is not rewritten for it.
        self.deliver(directory, BUILT)
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['valid'], payload['semantic']), (0, True, 'pass'))
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual((status, payload['semantic']), (1, 'pass'))
        self.assertEqual([f['code'] for f in payload['findings']], ['delivery_review_missing'])

    def test_the_default_reference_is_the_execution_clock_and_says_so(self):
        directory, _ = self.run_study(self.current(), name='current')
        with patch('shopping_advisor.study.__main__._now', return_value=BUILT):
            status, text = self.cli('deliver', directory)
        self.assertEqual(status, 0, text)
        event = delivery.latest(delivery.read(directory / delivery.RECORD))
        self.assertEqual((event['reference'], event['reference_source']), (BUILT, delivery.EXECUTION_CLOCK))
        self.assertIn('(execution_clock)', text)
        self.assertIn('not a trusted time service', event['limits'][0])

    def test_a_reference_needs_an_offset_and_is_normalised_to_utc(self):
        self.assertEqual(delivery.parse_reference('2026-10-16T09:00:00+02:00'), '2026-10-16T07:00:00+00:00')
        for bad in ('2026-10-16T09:00:00', 'yesterday', ''):
            with self.subTest(bad=bad), self.assertRaises(delivery.DeliveryError):
                delivery.parse_reference(bad)
        directory, _ = self.run_study()
        status, text = self.cli('deliver', directory, '--reference', '2026-10-16T09:00:00')
        self.assertEqual(status, 2)
        self.assertIn('explicit time zone offset', text)
        self.assertFalse((directory / delivery.RECORD).exists())


class WhatGovernsAndWhatBlocks(unittest.TestCase):
    """The pure assessment, over minimal inputs: which observations, which blockers."""

    BRIEF = {'freshness': {'as_of': '2026-09-16', 'price_max_age_days': 7,
                           'note': 'synthetic', 'scope': 'current_advice'}}
    RANKING = {'outcome': {'code': 'recommendation'}, 'stop': ''}

    def assess(self, candidates, brief=None, ranking=None, reference=BUILT):
        return delivery.assess(brief or self.BRIEF, ranking or self.RANKING, candidates,
                               'study', 'a' * 64, reference, delivery.DECLARED)

    def candidate(self, asin, decision, fetched_at='2026-09-14T23:03:28+00:00', rank=1):
        return {'asin': asin, 'decision': decision, 'rank': rank, 'fetched_at': fetched_at}

    def test_only_decisive_comparison_inputs_are_governed(self):
        event = self.assess([self.candidate('S', 'shortlisted'), self.candidate('R', 'ranked', rank=4),
                             self.candidate('X', 'excluded', fetched_at=''),
                             self.candidate('V', 'variant', fetched_at='2020-01-01T00:00:00+00:00'),
                             self.candidate('N', 'not_category', fetched_at=''),
                             self.candidate('O', 'over_budget', fetched_at='2020-01-01T00:00:00+00:00')])
        self.assertEqual([g['asin'] for g in event['governed']], ['S', 'R'])
        self.assertEqual(event['current_advice'], delivery.PERMITTED)

    def test_an_undated_or_future_dated_governed_observation_blocks(self):
        for fetched in ('', 'not a date', '2026-09-17T00:00:00+00:00'):
            with self.subTest(fetched=fetched):
                event = self.assess([self.candidate('S', 'shortlisted', fetched_at=fetched)])
                self.assertEqual(event['current_advice'], delivery.BLOCKED)
                self.assertIn('undated or dated after the reference', event['blockers'][0])
                self.assertIsNone(event['governed'][0]['age_days'])

    def test_a_reference_before_as_of_is_inconsistent_and_blocks(self):
        event = self.assess([self.candidate('S', 'shortlisted')], reference='2026-09-10T00:00:00+00:00')
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        self.assertIn('precedes the brief\'s as_of 2026-09-16: the dates are inconsistent', event['blockers'][0])

    def test_a_withheld_recommendation_is_not_current_buying_advice(self):
        ranking = {'outcome': {'code': 'recommendation'}, 'stop': gates.REQUIREMENT_UNSUPPORTED}
        event = self.assess([self.candidate('R', 'ranked')], ranking=ranking)
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        self.assertIn('the recommendation is withheld (requirement_unsupported)', event['blockers'][0])

    def test_a_missing_policy_blocks_rather_than_defaulting_to_forever(self):
        brief = {'freshness': {'as_of': '2026-09-16', 'price_max_age_days': None,
                               'note': '', 'scope': 'current_advice'}}
        event = self.assess([self.candidate('S', 'shortlisted')], brief=brief)
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        self.assertIn('declares no age policy', event['blockers'][0])

    def test_historical_scope_records_staleness_and_blocks_nothing(self):
        brief = {'freshness': {'as_of': '2026-09-16', 'price_max_age_days': 7, 'note': 'x', 'scope': 'historical'}}
        event = self.assess([self.candidate('S', 'shortlisted')], brief=brief, reference=LATER)
        self.assertEqual((event['current_advice'], event['counts']['stale'], event['blockers']),
                         (delivery.NOT_IN_SCOPE, 1, []))

    def test_ages_are_whole_utc_days(self):
        self.assertEqual(delivery.age_days('2026-09-14T23:03:28+00:00', '2026-09-16T00:00:00+00:00'), 2)
        self.assertEqual(delivery.age_days('2026-09-15T01:00:00+02:00', '2026-09-15T00:30:00+00:00'), 1)
        self.assertEqual(delivery.age_days('2026-09-14T23:03:28', BUILT), 2, 'a naive observation is read as UTC')
        self.assertIsNone(delivery.age_days('', BUILT))


class ReplayNeverReadsTheClock(DeliveryCase):
    def test_events_re_derive_from_their_frozen_reference(self):
        directory, _ = self.run_study(self.current(), name='current')
        self.deliver(directory, BUILT)
        self.deliver(directory, LATER)
        self.assertEqual(bundle.verify(directory)[1], [])
        record = delivery.read(directory / delivery.RECORD)
        record['events'][-1]['current_advice'] = delivery.PERMITTED
        (directory / delivery.RECORD).write_text(json.dumps(record))
        codes = [f['code'] for f in bundle.verify(directory)[1]]
        self.assertEqual(codes, ['artifact_altered'])
        self.refresh_digests(directory)
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['delivery_invalid'])
        self.assertIn('delivery event 1 does not re-derive from its frozen reference: current_advice moved',
                      findings[0]['message'])

    def test_a_report_changed_after_delivery_invalidates_the_record(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        with (directory / bundle.REPORT).open('a') as handle:
            handle.write('\nApproved.\n')
        self.refresh_digests(directory)
        findings = bundle.verify(directory)[1]
        self.assertIn('delivery_invalid', [f['code'] for f in findings])
        self.assertTrue(any('different report bytes' in f['message'] for f in findings))

    def test_deliver_refuses_a_bundle_that_does_not_verify(self):
        directory, _ = self.run_study()
        (directory / bundle.CANDIDATES).write_text('')
        status, text = self.cli('deliver', directory, '--reference', BUILT)
        self.assertEqual(status, 2)
        self.assertIn('Repair the bundle before delivering it: artifact_altered', text)
        self.assertFalse((directory / delivery.RECORD).exists())

    def test_a_bounded_stage_6_study_delivers_as_history_and_carries_its_stop(self):
        directory, manifest = bundle.run(str(DELIVERED_BRIEF), directory=str(self.directory / 'bounded'),
                                         plan=str(DELIVERED_PLAN))
        event, _ = self.deliver(directory, BUILT)
        self.assertEqual((event['current_advice'], event['stop'], event['analytical_outcome']),
                         (delivery.NOT_IN_SCOPE, gates.REQUIREMENT_UNSUPPORTED, 'recommendation'))
        self.assertEqual([g['asin'] for g in event['governed']], GOVERNED, 'ranked rows govern a bounded finding')
        self.assertEqual(bundle.verify(directory)[1], [])

    def test_a_malformed_record_is_refused(self):
        for record in ({}, {'delivery_version': 2, 'events': []}, {'delivery_version': 1, 'events': []},
                       {'delivery_version': 1, 'events': [{'current_advice': 'yes'}]}):
            with self.subTest(record=record), self.assertRaises(delivery.DeliveryError):
                delivery.check_shape(record)


class Contract(unittest.TestCase):
    def test_the_delivery_contract_is_discovered_and_pinned(self):
        self.assertEqual(maintenance._contract_versions()['delivery_record'], delivery.DELIVERY_VERSION)
        with patch.object(delivery, 'DELIVERY_VERSION', 2):
            findings = maintenance.check_contracts(maintenance.load_baseline()).findings
            self.assertTrue(any(f.code == 'contract_version' and 'delivery_record' in f.message
                                for f in findings))

    def test_every_example_is_delivered_at_a_fixed_reference_as_history(self):
        import datetime
        examples = maintenance.load_baseline()['examples']
        for example in examples:
            # A fixed instant with an offset, never the wall clock: the gate
            # must fail with a change and never with the passage of time.
            reference = datetime.datetime.fromisoformat(example['deliver_at'])
            self.assertIsNotNone(reference.tzinfo, example['name'])
            self.assertEqual(example['expect']['current_advice'], delivery.NOT_IN_SCOPE, example['name'])
        bronze = next(e for e in examples if e['name'] == 'pasta-bronze-die')
        result = maintenance.check_examples({'examples': [bronze]})
        self.assertTrue(result.passed, result.findings)
        moved = dict(bronze, expect=dict(bronze['expect'], current_advice=delivery.PERMITTED))
        result = maintenance.check_examples({'examples': [moved]})
        self.assertEqual([f.code for f in result.findings], ['example_decision_changed'])
        self.assertIn('current_advice', result.findings[0].message)


if __name__ == '__main__':
    unittest.main()
