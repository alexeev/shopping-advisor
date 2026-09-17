"""Stage 10: the delivery review, a scoped re-check bound to one delivery event.

INTAKE §8 sets the expectation: a previously issued report does not stay
current, so a later purchase is a new delivery event, and if the policy passes
the new delivery binding is reviewed as a scoped re-check of freshness,
applicability and conclusion presentation -- without rewriting the semantic
findings for an analysis whose inputs, decisions and report bytes have not
moved. INTAKE §9 adds what no check can establish: that the reference was the
clock honestly read and the declared scope true, which a deliverer attests by
name and which stays a statement, not a proof.

Every reference here is declared and fixed. Nothing reads the clock.
"""
import contextlib
import copy
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.provenance import sha256_file
from shopping_advisor.study import audit, bundle, delivery, delivery_review, session
from shopping_advisor.study.__main__ import main

HERE = pathlib.Path(__file__).resolve().parent
STUDIES = HERE / 'studies'
INTAKE = HERE / 'intake'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
PLAN, BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'
BUILT = '2026-09-16T12:00:00+00:00'
LATER = '2026-10-16T12:00:00+00:00'


class DeliveryReviewCase(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.written = []
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in self.written])

    def current(self, source=BRONZE):
        """The committed brief declared current advice, beside its feeds."""
        text = source.read_text(encoding='utf-8')
        old = 'price_max_age_days = 7'
        self.assertIn(old, text)
        path = STUDIES / f'.tmp-delivery-review-{len(self.written)}-{source.name}'
        path.write_text(text.replace(old, old + '\nscope = "current_advice"', 1), encoding='utf-8')
        self.written.append(path)
        return path

    def run_study(self, source=None, name='bundle', **kwargs):
        return bundle.run(str(source or self.current()), directory=str(self.directory / name),
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

    def codes(self, payload):
        return [f['code'] for f in payload['findings']]

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def completed(self, review, status=delivery_review.PASS, attest=True, **items):
        """Every check filled with one status and an attestation, then overrides."""
        review = copy.deepcopy(review)
        review['reviewer'] = 'test deliverer, synthetic fixture'
        for name, item in review['checks'].items():
            item.update(status=status, findings=f'synthetic {name} finding for a fixture')
        for name, change in items.items():
            review['checks'][name].update(change)
        review['attestation'].update(by='test deliverer', reference_read_honestly=attest,
                                     declaration_true=attest,
                                     statement='fixture attestation, not a real delivery')
        return review

    def approve_final(self, directory):
        """A completed passing semantic review attached through the CLI."""
        review = json.loads((directory / bundle.REVIEW).read_text())
        review['reviewer'] = 'test reviewer'
        for item in review['checks'].values():
            item.update(status='pass', findings='synthetic finding for a fixture')
        status, text = self.cli('review', directory, self.write('final.json', review))
        self.assertEqual(status, 0, text)


class TheTemplate(DeliveryReviewCase):
    def test_it_binds_the_latest_event_the_report_and_the_semantic_review(self):
        directory, manifest = self.run_study()
        event, _ = self.deliver(directory, BUILT)
        review = delivery_review.template(directory)
        self.assertEqual((review['event'], review['reference'], review['current_advice']),
                         (0, BUILT, delivery.PERMITTED))
        self.assertEqual(review['event_sha256'], delivery_review.digest(event))
        self.assertEqual(review['report_sha256'], sha256_file(directory / bundle.REPORT))
        self.assertEqual(review['semantic_review'],
                         {'status': 'pending', 'sha256': sha256_file(directory / bundle.REVIEW)})
        self.assertEqual((review['session_sha256'], review['intake_review_sha256']), ('', ''))
        self.assertEqual(delivery_review.status(review), 'pending')
        self.assertEqual(list(review['checks']), list(delivery_review.CHECKS))
        self.assertEqual(review['attestation'],
                         {'by': '', 'reference_read_honestly': None, 'declaration_true': None,
                          'statement': ''})
        self.assertIn('not a proof', review['limits'][0])
        delivery_review.check_shape(review)
        delivery_review.check_binding(review, directory)

    def test_a_plan_backed_study_binds_its_session_and_intake_review_snapshots(self):
        directory, _ = bundle.run(str(BRIEF), directory=str(self.directory / 'plan'), plan=str(PLAN),
                                  session_ledger=str(INTAKE / 'session-ledger.json'),
                                  plan_review=str(INTAKE / 'delivered-cost-intake-review.json'))
        self.deliver(directory, BUILT)
        review = delivery_review.template(directory)
        self.assertEqual(review['session_sha256'], sha256_file(directory / session.SNAPSHOT))
        self.assertEqual(review['intake_review_sha256'], sha256_file(directory / 'intake-review.json'))
        self.assertEqual(review['current_advice'], delivery.NOT_IN_SCOPE)

    def test_a_bundle_nobody_delivered_has_nothing_to_review(self):
        directory, _ = self.run_study()
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'deliver the study before'):
            delivery_review.template(directory)
        self.deliver(directory, BUILT)
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'no delivery event 3'):
            delivery_review.template(directory, 3)

    def test_the_cli_writes_a_new_file_and_prints_the_questions(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        output = self.directory / 'review.json'
        status, text = self.cli('delivery-review-template', directory, '-o', output)
        self.assertEqual(status, 0, text)
        self.assertIn('pending delivery review of event 0 (permitted at', text)
        for name in delivery_review.CHECKS:
            self.assertIn(delivery_review.QUESTIONS[name], text)
        self.assertIn('not a proof', text)
        self.assertEqual(json.loads(output.read_text()), delivery_review.template(directory))
        status, text = self.cli('delivery-review-template', directory, '-o', output)
        self.assertEqual(status, 2)
        self.assertIn('new .json output', text)


class TheContract(DeliveryReviewCase):
    def setUp(self):
        super().setUp()
        self.bundle, _ = self.run_study()
        self.deliver(self.bundle, BUILT)
        self.template = delivery_review.template(self.bundle)

    def test_a_completed_check_needs_a_reviewer_findings_and_an_attestation(self):
        review = copy.deepcopy(self.template)
        review['checks']['freshness']['status'] = 'pass'
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'reviewer and findings'):
            delivery_review.check_shape(review)
        review['reviewer'] = 'someone'
        review['checks']['freshness']['findings'] = 'looked'
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'null is not an answer'):
            delivery_review.check_shape(review)
        review['attestation'].update(by='someone', reference_read_honestly=True, declaration_true=True)
        delivery_review.check_shape(review)
        pending = copy.deepcopy(self.template)
        pending['checks']['freshness']['findings'] = 'a pending check records nothing'
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'records nothing'):
            delivery_review.check_shape(pending)

    def test_approval_needs_both_attestations_true(self):
        for name in delivery_review.ATTESTED:
            review = self.completed(self.template)
            review['attestation'][name] = False
            with self.subTest(attested=name), \
                    self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'both attestations true'):
                delivery_review.check_shape(review)
        failed = self.completed(self.template, attest=False, freshness={'status': 'fail'})
        self.assertEqual(delivery_review.status(delivery_review.check_shape(failed)), 'fail',
                         'a failure may be recorded by someone who will not vouch for the delivery')

    def test_closed_fields_version_and_limits(self):
        for change, message in ((lambda r: r.update(delivery_review_version=2), 'unsupported version'),
                                (lambda r: r.update(extra=1), 'exactly these fields'),
                                (lambda r: r.pop('limits'), 'exactly these fields'),
                                (lambda r: r['limits'].append('mine'), 'this contract'),
                                (lambda r: r['checks'].pop('freshness'), 'expected exactly'),
                                (lambda r: r['semantic_review'].update(status='limited'), 'expected one of'),
                                (lambda r: r.update(event=-1), 'non-negative')):
            review = copy.deepcopy(self.template)
            change(review)
            with self.subTest(message=message), \
                    self.assertRaisesRegex(delivery_review.DeliveryReviewError, message):
                delivery_review.check_shape(review)

    def test_a_review_of_other_bytes_is_superseded_and_names_what_moved(self):
        review = self.completed(self.template)
        delivery_review.check_binding(review, self.bundle)
        stale = copy.deepcopy(review)
        stale['event'] = 1
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'no delivery event 1'):
            delivery_review.check_binding(stale, self.bundle)
        self.deliver(self.bundle, LATER)
        delivery_review.check_binding(review, self.bundle)
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'event_sha256'):
            delivery_review.check_binding(stale, self.bundle)
        # The semantic review is completed after the delivery review bound it.
        self.approve_final(self.bundle)
        with self.assertRaisesRegex(delivery_review.DeliveryReviewError, 'semantic_review'):
            delivery_review.check_binding(review, self.bundle)


class WhatConsumesIt(DeliveryReviewCase):
    def test_a_permitted_current_advice_event_owes_a_passing_review_when_audited(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        self.approve_final(directory)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual((status, payload['delivery']['review']), (1, 'absent'))
        self.assertEqual(self.codes(payload), ['delivery_review_missing'])
        self.assertIn('delivery-review-template', payload['findings'][0]['message'])
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['valid']), (0, True), 'owed only when delivered as audited')

        template = delivery_review.template(directory)
        status, text = self.cli('review-delivery', directory, self.write('pending.json', template))
        self.assertEqual(status, 0, text)
        self.assertIn('[delivery review pending: event 0, permitted at', text)
        self.assertIn('Pending is not approval', text)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(self.codes(payload), ['delivery_review_incomplete'])
        self.assertEqual(payload['delivery']['review'], 'pending')
        self.assertEqual(bundle.verify(directory)[1], [])
        self.assertIn(delivery_review.RECORD, bundle.load_manifest(directory)['artifacts'])

        status, text = self.cli('review-delivery', directory,
                                self.write('passed.json', self.completed(template)))
        self.assertEqual(status, 0, text)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual((status, payload['valid'], payload['semantic'], payload['delivery']['review']),
                         (0, True, 'pass', 'pass'))
        record = delivery_review.read_record(directory / delivery_review.RECORD)
        self.assertEqual([r['event'] for r in record['reviews']], [0], 'replaced, not duplicated')

    def test_a_later_delivery_is_a_new_event_and_the_semantic_review_stands(self):
        """INTAKE §8's affordability claim, as a test."""
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        self.approve_final(directory)
        self.cli('review-delivery', directory,
                 self.write('passed.json', self.completed(delivery_review.template(directory))))
        self.assertEqual(self.validate(directory, '--require-review')[0], 0)
        final = json.loads((directory / bundle.REVIEW).read_text())

        event, _ = self.deliver(directory, LATER)
        self.assertEqual(event['current_advice'], delivery.BLOCKED)
        audit.check_review(final, directory, required=True)
        self.assertEqual(json.loads((directory / bundle.REVIEW).read_text()), final,
                         'a new delivery event does not touch the semantic review')
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(payload['semantic'], 'pass')
        self.assertEqual(self.codes(payload), ['current_advice_blocked'])
        self.assertEqual(payload['delivery']['review'], 'absent', 'the earlier review binds event 0')
        self.assertEqual(bundle.verify(directory)[1], [], 'the earlier review still binds its event')

        # A third event that passes again is delivered as audited only with its own review.
        self.deliver(directory, BUILT)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(self.codes(payload), ['delivery_review_missing'])
        review = delivery_review.template(directory)
        self.assertEqual(review['event'], 2)
        self.assertEqual(review['semantic_review']['status'], 'pass')
        self.cli('review-delivery', directory, self.write('third.json', self.completed(review)))
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual((status, payload['valid']), (0, True))
        record = delivery_review.read_record(directory / delivery_review.RECORD)
        self.assertEqual([r['event'] for r in record['reviews']], [0, 2])

    def test_a_recorded_failure_fails_validation_whatever_the_flags(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        failed = self.completed(delivery_review.template(directory), attest=False,
                                applicability={'status': 'fail',
                                               'findings': 'the governed pack is not the buyer\'s variant'})
        status, text = self.cli('review-delivery', directory, self.write('failed.json', failed))
        self.assertEqual(status, 0, text)
        self.assertIn('does not hold', text)
        for flags in ((), ('--require-review',)):
            status, payload = self.validate(directory, *flags)
            with self.subTest(flags=flags):
                self.assertEqual((status, payload['delivery']['review']), (1, 'fail'))
                self.assertIn('delivery_review_failed', self.codes(payload))
                self.assertIn('not the buyer\'s variant',
                              next(f['message'] for f in payload['findings']
                                   if f['code'] == 'delivery_review_failed'))

    def test_a_historical_study_is_asked_for_nothing(self):
        directory, _ = bundle.run(str(BRONZE), directory=str(self.directory / 'legacy'))
        self.deliver(directory, BUILT)
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(self.codes(payload), ['semantic_review'], 'only the final review is owed')
        self.assertEqual(payload['delivery']['review'], 'absent')
        # It may still carry one, and a failure still counts.
        self.cli('review-delivery', directory,
                 self.write('r.json', self.completed(delivery_review.template(directory))))
        self.assertEqual(self.validate(directory)[1]['delivery']['review'], 'pass')

    def test_verify_reports_a_review_whose_bindings_no_longer_hold(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        self.cli('review-delivery', directory,
                 self.write('r.json', self.completed(delivery_review.template(directory))))
        self.assertEqual(bundle.verify(directory)[1], [])
        path = directory / delivery_review.RECORD
        record = json.loads(path.read_text())
        record['reviews'][0]['event_sha256'] = 'f' * 64
        path.write_text(json.dumps(record))
        manifest = bundle.load_manifest(directory)
        manifest['artifacts'] = bundle.artifact_digests(directory)
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['delivery_review_invalid'])
        self.assertIn('event_sha256', findings[0]['message'])
        # Two reviews of one event are a duplicate, not a history.
        record['reviews'][0]['event_sha256'] = delivery_review.template(directory)['event_sha256']
        record['reviews'].append(copy.deepcopy(record['reviews'][0]))
        path.write_text(json.dumps(record))
        manifest['artifacts'] = bundle.artifact_digests(directory)
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['delivery_review_invalid'])
        self.assertIn('two reviews', findings[0]['message'])

    def test_a_superseded_review_of_the_same_event_can_be_replaced(self):
        """The semantic review is reissued after the delivery review bound it.

        Found in use on 2026-09-17: two counts in a completed semantic review
        were corrected and `review` replaced it, so the delivery review of
        event 0 no longer bound -- and both the template and the attach
        refused because the bundle did not verify, on account of the very
        review they were about to replace. A stale review of the event being
        reviewed is not a reason to refuse its replacement; a stale review of
        another event still is, and so is any other finding.
        """
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        status, text = self.cli('review-delivery', directory, self.write(
            'r0.json', self.completed(delivery_review.template(directory))))
        self.assertEqual(status, 0, text)
        self.deliver(directory, LATER)            # event 1, never reviewed
        self.approve_final(directory)             # supersedes event 0's review
        self.assertEqual([f['code'] for f in bundle.verify(directory)[1]],
                         ['delivery_review_invalid'])
        status, text = self.cli('delivery-review-template', directory,
                                '-o', self.directory / 't1.json', '--event', '1')
        self.assertEqual(status, 2, text)
        self.assertIn('Repair the bundle', text)
        status, text = self.cli('delivery-review-template', directory,
                                '-o', self.directory / 't0.json', '--event', '0')
        self.assertEqual(status, 0, text)
        template = json.loads((self.directory / 't0.json').read_text())
        self.assertEqual(template['semantic_review']['status'], 'pass')
        status, text = self.cli('review-delivery', directory,
                                self.write('r0b.json', self.completed(template)))
        self.assertEqual(status, 0, text)
        self.assertEqual(bundle.verify(directory)[1], [])
        record = delivery_review.read_record(directory / delivery_review.RECORD)
        self.assertEqual([r['event'] for r in record['reviews']], [0])

    def test_the_bundle_must_verify_before_a_review_is_attached(self):
        directory, _ = self.run_study()
        self.deliver(directory, BUILT)
        review = self.write('r.json', self.completed(delivery_review.template(directory)))
        (directory / bundle.REPORT).write_text('changed')
        status, text = self.cli('review-delivery', directory, review)
        self.assertEqual(status, 2)
        self.assertIn('Repair the bundle', text)

    def test_resume_reports_the_state_of_the_latest_events_review(self):
        directory, _ = self.run_study()
        self.assertIsNone(session.resume(directory, reference=BUILT)['delivery_review'],
                          'nothing delivered, nothing to review')
        self.deliver(directory, BUILT)
        self.assertEqual(session.resume(directory, reference=BUILT)['delivery_review'], 'absent')
        self.cli('review-delivery', directory,
                 self.write('r.json', self.completed(delivery_review.template(directory))))
        report = session.resume(directory, reference=BUILT)
        self.assertEqual(report['delivery_review'], 'pass')
        status, text = self.cli('resume', directory, '--reference', BUILT)
        self.assertIn('delivery rev. pass (latest event)', text)
        self.deliver(directory, LATER)
        self.assertEqual(session.resume(directory, reference=LATER)['delivery_review'], 'absent')


class Contract(unittest.TestCase):
    def test_the_contract_is_discovered_and_pinned(self):
        self.assertEqual(maintenance._contract_versions()['delivery_review'],
                         delivery_review.DELIVERY_REVIEW_VERSION)
        self.assertEqual(maintenance.load_baseline()['contracts']['delivery_review'],
                         delivery_review.DELIVERY_REVIEW_VERSION)
        with patch.object(delivery_review, 'DELIVERY_REVIEW_VERSION', 2):
            findings = maintenance.check_contracts(maintenance.load_baseline()).findings
            self.assertTrue(any(f.code == 'contract_version' and 'delivery_review' in f.message
                                for f in findings))

    def test_the_delivery_record_names_where_the_attestation_lives(self):
        self.assertIn('delivery review', delivery.LIMITS[2])
        self.assertIn('proves the clock', delivery.LIMITS[2])


if __name__ == '__main__':
    unittest.main()
