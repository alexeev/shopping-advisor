"""Stage 9: the intake review, a digest-bound semantic pass over a plan revision.

INTAKE §11 and §12 state what it must do: bind the retained user evidence,
the plan revision, the resolved mappings and the control metadata; check
omissions, faithfulness, adequacy, assumptions and stage effects; never claim
faithfulness on wording a redaction removed; and be consumed by something
that fails when it is wrong. Case 7's semantic limit -- a purchase budget
mapped onto the per-kilogram cap passes the gates as enforced -- is the case
this artifact exists to record, so it is the case that closes this module.

Nothing here touches the final semantic review, its version, its checks or
its basis. The four legacy examples carry no plan and so no intake review;
their ids, decisions and report bytes are pinned elsewhere.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.provenance import sha256_file
from shopping_advisor.study import bundle, controls, gates, intake, intake_review, session
from shopping_advisor.study import brief as brief_module
from shopping_advisor.study.__main__ import main
from shopping_advisor.study.analysis import analyse

HERE = Path(__file__).resolve().parent
INTAKE = HERE / 'intake'
STUDIES = HERE / 'studies'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
PLAN, BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'
BUDGET_PLAN, BUDGET_BRIEF = INTAKE / 'budget-plan.json', INTAKE / 'budget-brief.json'
UNSUPPORTED = INTAKE / 'unsupported-plan.json'
FIXTURE = INTAKE / 'delivered-cost-intake-review.json'
AT = '2026-09-17T00:00:00+00:00'


class ReviewCase(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.plan = intake.load(PLAN)
        self.template = intake_review.template(self.plan)

    def completed(self, review=None, status=intake_review.PASS, **items):
        """Every check filled with the same status, then per-check overrides."""
        review = copy.deepcopy(review or self.template)
        review['reviewer'] = 'test reviewer, synthetic fixture'
        for name, item in review['checks'].items():
            item.update(status=status, findings=f'synthetic {name} finding for a fixture')
        for name, change in items.items():
            review['checks'][name].update(change)
        return review

    def refreshed(self, plan):
        plan['readback']['text'] = intake.render_readback(plan)
        return intake.check(plan)

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def study(self, name='bundle', plan=PLAN, brief=BRIEF, **kwargs):
        return bundle.run(str(brief), directory=str(self.directory / name),
                          plan=str(plan) if plan else None,
                          started_at='2026-09-16T00:00:00+00:00',
                          finished_at='2026-09-16T00:00:01+00:00', **kwargs)

    def validate(self, directory, *flags):
        status, text = self.cli('validate-report', directory, *flags)
        return status, json.loads(text)

    def codes(self, payload):
        return [f['code'] for f in payload['findings']]


class Contract(ReviewCase):
    def test_the_template_binds_the_plan_revision_and_the_live_catalogue(self):
        review = self.template
        self.assertEqual(review['plan'], {'id': 'pasta-delivered-intake', 'revision': 1,
                                          'sha256': intake.digest(self.plan)})
        self.assertEqual(review['basis']['user_evidence_sha256'], intake.digest(self.plan['user_evidence']))
        self.assertEqual(review['basis']['requirements_sha256'], intake.digest(self.plan['requirements']))
        self.assertEqual(review['basis']['readback_response'], 'no_response')
        self.assertEqual(review['basis']['catalogue_sha256'],
                         intake.digest(controls.catalogue('dry_pasta')))
        self.assertEqual(set(review['checks']), set(intake_review.CHECKS))
        self.assertTrue(all(item['status'] == 'pending' for item in review['checks'].values()))
        self.assertEqual((review['reviewer'], review['review_limits'], review['unresolved_limits']),
                         ('', [], []))
        self.assertEqual(intake_review.status(intake_review.check_review(review, self.plan)), 'pending')

    def test_an_unregistered_category_binds_no_catalogue(self):
        plan = intake.load(UNSUPPORTED)
        review = intake_review.template(plan)
        self.assertEqual(review['basis']['catalogue_sha256'], '')
        intake_review.check_review(review, plan)

    def test_closed_fields_versions_and_check_set(self):
        for change in (lambda r: r.update(intake_review_version=2),
                       lambda r: r.update(approved=True),
                       lambda r: r.pop('review_limits'),
                       lambda r: r['checks'].pop('adequacy'),
                       lambda r: r['checks'].update(portability={'status': 'pending', 'findings': '',
                                                                 'requirement_ids': [], 'message_ids': []}),
                       lambda r: r['checks']['adequacy'].update(status='approved'),
                       lambda r: r['checks']['adequacy'].update(note='x'),
                       lambda r: r['plan'].update(sha256='nope'),
                       lambda r: r['basis'].update(catalogue_sha256='nope'),
                       lambda r: r['review_limits'].append({'kind': 'other', 'message_id': '',
                                                            'description': 'x'}),
                       lambda r: r.update(unresolved_limits=[''])):
            review = copy.deepcopy(self.template)
            change(review)
            with self.subTest(change=change), self.assertRaises(intake_review.IntakeReviewError):
                intake_review.check_shape(review)

    def test_a_completed_check_needs_a_reviewer_and_findings_not_a_bare_approval(self):
        review = self.completed()
        intake_review.check_review(review, self.plan)
        for change in (lambda r: r.update(reviewer=''),
                       lambda r: r['checks']['adequacy'].update(findings=''),
                       lambda r: r['checks']['adequacy'].update(findings='   ')):
            broken = copy.deepcopy(review)
            change(broken)
            with self.subTest(change=change), \
                    self.assertRaisesRegex(intake_review.IntakeReviewError, 'not a bare approval'):
                intake_review.check_shape(broken)
        # And a pending check records nothing yet: no findings, no references.
        pending = copy.deepcopy(self.template)
        pending['checks']['adequacy']['findings'] = 'looks fine'
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'records nothing yet'):
            intake_review.check_shape(pending)

    def test_status_precedence_is_fail_pending_limited_pass(self):
        self.assertEqual(intake_review.status(self.completed()), 'pass')
        self.assertEqual(intake_review.status(self.completed(adequacy={'status': 'limited'})), 'limited')
        limited_and_pending = self.completed(adequacy={'status': 'limited'})
        limited_and_pending['checks']['omissions'].update(status='pending', findings='',
                                                          requirement_ids=[], message_ids=[])
        self.assertEqual(intake_review.status(limited_and_pending), 'pending')
        failed = self.completed(adequacy={'status': 'fail', 'requirement_ids': ['delivered']})
        failed['checks']['omissions'].update(status='pending', findings='')
        self.assertEqual(intake_review.status(failed), 'fail')
        self.assertEqual(intake_review.failures(failed),
                         [('adequacy', 'synthetic adequacy finding for a fixture')])

    def test_a_review_of_another_revision_is_superseded_not_carried_forward(self):
        review = self.completed()
        revised = copy.deepcopy(self.plan)
        revised['requirements'][0]['statement'] += ' (revised)'
        self.refreshed(revised)
        with self.assertRaisesRegex(intake_review.IntakeReviewError,
                                    'superseded.*do not copy a pass forward'):
            intake_review.check_review(review, revised)
        # Naming the new revision without re-reviewing is also refused: the
        # basis digests are recomputed from the plan the review claims to bind.
        relabelled = copy.deepcopy(review)
        relabelled['plan']['sha256'] = intake.digest(revised)
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'requirements_sha256'):
            intake_review.check_review(relabelled, revised)
        # A response to the read-back is part of what was reviewed.
        answered = copy.deepcopy(self.plan)
        answered['readback']['response'] = {'status': 'confirmed', 'message_ids': ['u1'],
                                            'scope': 'the whole plan'}
        intake.check(answered)
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'superseded'):
            intake_review.check_review(review, answered)

    def test_a_changed_control_catalogue_invalidates_the_adequacy_basis(self):
        review = self.completed()
        grown = copy.deepcopy(controls.catalogue('dry_pasta'))
        grown['controls']['delivered_cost'] = {'parameters': {}, 'stage': 'ranking', 'optional': True,
                                               'implementation': 'nowhere', 'effect': 'x', 'limits': 'x'}
        with patch.object(controls, 'catalogue', return_value=grown), \
                self.assertRaisesRegex(intake_review.IntakeReviewError,
                                       'dry_pasta control catalogue changed.*adequacy'):
            intake_review.check_review(review, self.plan)

    def test_a_failure_points_at_what_it_concerns(self):
        for name in intake_review.REQUIREMENT_CHECKS:
            with self.subTest(check=name):
                with self.assertRaisesRegex(intake_review.IntakeReviewError, 'names the requirements'):
                    intake_review.check_review(self.completed(**{name: {'status': 'fail'}}), self.plan)
                with self.assertRaisesRegex(intake_review.IntakeReviewError, 'unresolved references'):
                    intake_review.check_review(
                        self.completed(**{name: {'status': 'fail', 'requirement_ids': ['budget']}}), self.plan)
                intake_review.check_review(
                    self.completed(**{name: {'status': 'fail', 'requirement_ids': ['delivered']}}), self.plan)
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'retained user messages'):
            intake_review.check_review(self.completed(omissions={'status': 'fail'}), self.plan)
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'unresolved references'):
            intake_review.check_review(self.completed(omissions={'status': 'fail', 'message_ids': ['u9']}),
                                       self.plan)
        intake_review.check_review(self.completed(omissions={'status': 'fail', 'message_ids': ['u1']}),
                                   self.plan)

    def test_review_limits_are_recomputed_and_forbid_a_pass_on_what_was_not_seen(self):
        plan = copy.deepcopy(self.plan)
        plan['user_evidence']['messages'][0]['redactions'].append(
            {'description': 'a street address', 'reason': 'personal data', 'limits_review': False})
        self.refreshed(plan)
        self.assertEqual(intake_review.template(plan)['review_limits'], [],
                         'a redaction that does not limit review limits nothing')
        plan['user_evidence']['messages'][0]['redactions'].append(
            {'description': 'a sentence naming the acceptable shipping cost', 'reason': 'personal data',
             'limits_review': True})
        self.refreshed(plan)
        template = intake_review.template(plan)
        self.assertEqual(template['review_limits'], [{
            'kind': 'redaction', 'message_id': 'u1',
            'description': 'a sentence naming the acceptable shipping cost'}])
        dropped = self.completed(template)
        dropped['review_limits'] = []
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'recorded as removed'):
            intake_review.check_review(dropped, plan)
        for name in ('omissions', 'faithfulness'):
            with self.subTest(check=name), \
                    self.assertRaisesRegex(intake_review.IntakeReviewError,
                                           f'{name}: cannot be established while a redaction'):
                intake_review.check_review(self.completed(template, **{
                    other: {'status': 'limited'} for other in ('omissions', 'faithfulness') if other != name}),
                    plan)
        honest = self.completed(template, omissions={'status': 'limited'}, faithfulness={'status': 'limited'})
        self.assertEqual(intake_review.status(intake_review.check_review(honest, plan)), 'limited')
        failed = self.completed(template, omissions={'status': 'fail', 'message_ids': ['u1']},
                                faithfulness={'status': 'limited'})
        self.assertEqual(intake_review.status(intake_review.check_review(failed, plan)), 'fail')

    def test_missing_context_forbids_a_pass_on_omissions_alone(self):
        plan = copy.deepcopy(self.plan)
        plan['user_evidence']['missing_context'] = 'Earlier messages in this thread were not retained.'
        self.refreshed(plan)
        template = intake_review.template(plan)
        self.assertEqual([l['kind'] for l in template['review_limits']], ['missing_context'])
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'omissions: cannot be established'):
            intake_review.check_review(self.completed(template), plan)
        review = self.completed(template, omissions={'status': 'limited'})
        self.assertEqual(intake_review.status(intake_review.check_review(review, plan)), 'limited')
        self.assertEqual(review['checks']['faithfulness']['status'], 'pass',
                         'retained wording can still be read faithfully')


class BundleIntegration(ReviewCase):
    def test_run_snapshots_the_review_and_it_enters_neither_id_nor_report(self):
        without, _ = self.study('plain')
        pending = self.write('pending.json', self.template)
        directory, manifest = self.study('reviewed', plan_review=pending)
        self.assertEqual(manifest['study_id'], 'pasta-delivered-cost-43425b41286a')
        self.assertEqual(manifest['intake_review'],
                         {'status': 'pending', 'sha256': intake_review.digest(self.template)})
        self.assertIn(intake_review.SNAPSHOT, manifest['artifacts'])
        self.assertEqual(json.loads((directory / intake_review.SNAPSHOT).read_text()), self.template)
        self.assertEqual(sha256_file(directory / bundle.REPORT), sha256_file(without / bundle.REPORT),
                         'approval is never rendered into the report it approves')
        self.assertEqual(bundle.verify(directory)[1], [])
        status, text = self.cli('verify', directory)
        self.assertEqual(status, 0, text)

    def test_run_refuses_a_failed_review_and_writes_nothing(self):
        failed = self.write('failed.json', self.completed(
            adequacy={'status': 'fail', 'requirement_ids': ['listed'],
                      'findings': 'the listed-price axis is presented as the answer'}))
        with self.assertRaisesRegex(bundle.BundleError,
                                    'fails review — adequacy: the listed-price axis.*Nothing was written'):
            self.study('refused', plan_review=failed)
        self.assertFalse((self.directory / 'refused').exists())
        status, text = self.cli('run', BRIEF, '--plan', PLAN, '--intake-review', failed,
                                '-o', self.directory / 'refused-cli')
        self.assertEqual(status, 2)
        self.assertIn('fails review', text)

    def test_run_refuses_a_review_without_its_plan_or_of_another_revision(self):
        pending = self.write('pending.json', self.template)
        with self.assertRaisesRegex(bundle.BundleError, 'run this study with --plan'):
            bundle.run(str(BRONZE), directory=str(self.directory / 'planless'), plan_review=str(pending))
        other = self.write('other.json', intake_review.template(intake.load(BUDGET_PLAN)))
        with self.assertRaisesRegex(intake_review.IntakeReviewError, 'superseded'):
            self.study('mismatched', plan_review=other)
        self.assertFalse((self.directory / 'mismatched').exists())

    def test_verify_flags_a_snapshot_that_reviewed_another_plan_or_lies_about_its_status(self):
        directory, manifest = self.study('reviewed', plan_review=self.write('p.json', self.template))
        foreign = intake_review.template(intake.load(BUDGET_PLAN))
        (directory / intake_review.SNAPSHOT).write_text(json.dumps(foreign))
        manifest['artifacts'] = bundle.artifact_digests(directory)
        manifest['intake_review'] = {'status': 'pending', 'sha256': intake_review.digest(foreign)}
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        _, findings = bundle.verify(directory)
        self.assertEqual([f['code'] for f in findings], ['intake_review_invalid'])
        self.assertIn('superseded', findings[0]['message'])
        # The right bytes with a manifest that overstates them.
        (directory / intake_review.SNAPSHOT).write_text(json.dumps(self.template))
        manifest['artifacts'] = bundle.artifact_digests(directory)
        manifest['intake_review'] = {'status': 'pass', 'sha256': intake_review.digest(self.template)}
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        _, findings = bundle.verify(directory)
        self.assertEqual([f['code'] for f in findings], ['intake_review_invalid'])
        self.assertIn('another intake review digest or status', findings[0]['message'])
        # Tampered bytes are caught before anything is said about the binding.
        manifest['intake_review'] = {'status': 'pending', 'sha256': intake_review.digest(self.template)}
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        self.assertEqual(bundle.verify(directory)[1], [])
        (directory / intake_review.SNAPSHOT).write_text(json.dumps(self.completed()))
        self.assertEqual([f['code'] for f in bundle.verify(directory)[1]], ['artifact_altered'])

    def test_review_intake_attaches_and_a_recorded_failure_fails_validation(self):
        directory, _ = self.study('unreviewed')
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['intake_review'], self.codes(payload)), (0, 'absent', []),
                         'without --require-review a pending review is not a finding')
        status, text = self.cli('review-intake', directory, self.write('pending.json', self.template))
        self.assertEqual(status, 0, text)
        self.assertIn('[intake review pending]', text)
        self.assertEqual(bundle.load_manifest(directory)['intake_review']['status'], 'pending')
        self.assertEqual(bundle.verify(directory)[1], [])
        failed = self.completed(adequacy={'status': 'fail', 'requirement_ids': ['listed'],
                                          'findings': 'the listed axis is offered as the answer'})
        status, text = self.cli('review-intake', directory, self.write('failed.json', failed))
        self.assertEqual(status, 0, text)
        self.assertIn('misreads the request', text)
        for flags in ((), ('--require-review',)):
            status, payload = self.validate(directory, *flags)
            with self.subTest(flags=flags):
                self.assertEqual((status, payload['intake_review']), (1, 'fail'))
                self.assertIn('intake_review_failed', self.codes(payload))
                self.assertIn('the listed axis is offered as the answer',
                              next(f['message'] for f in payload['findings']
                                   if f['code'] == 'intake_review_failed'))
        status, text = self.cli('review-intake', directory, self.write('passed.json', self.completed()))
        self.assertEqual(status, 0, text)
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['intake_review'], self.codes(payload)), (0, 'pass', []))
        # A bundle that does not verify says nothing about its review either way.
        (directory / intake_review.SNAPSHOT).write_text('{}')
        status, payload = self.validate(directory)
        self.assertEqual((status, payload['intake_review']), (1, 'not_checked'))
        self.assertEqual(self.codes(payload), ['artifact_altered'])
        # Not a plan-backed study: nothing for a review to bind.
        legacy, _ = bundle.run(str(BRONZE), directory=str(self.directory / 'legacy'))
        status, text = self.cli('review-intake', legacy, self.write('again.json', self.template))
        self.assertEqual(status, 2)
        self.assertIn('not a plan-backed study', text)

    def test_an_audited_plan_backed_report_needs_a_passing_intake_review(self):
        directory, _ = self.study('unreviewed')
        status, payload = self.validate(directory, '--require-review')
        self.assertIn('intake_review_missing', self.codes(payload))
        self.assertIn('plan-review-template', next(f['message'] for f in payload['findings']
                                                    if f['code'] == 'intake_review_missing'))
        self.cli('review-intake', directory, self.write('pending.json', self.template))
        status, payload = self.validate(directory, '--require-review')
        self.assertIn('intake_review_incomplete', self.codes(payload))
        self.cli('review-intake', directory,
                 self.write('limited.json', self.completed(adequacy={'status': 'limited'})))
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(payload['intake_review'], 'limited')
        self.assertIn('intake_review_incomplete', self.codes(payload))
        self.cli('review-intake', directory, self.write('passed.json', self.completed()))
        status, payload = self.validate(directory, '--require-review')
        self.assertEqual(payload['intake_review'], 'pass')
        self.assertEqual(self.codes(payload), ['semantic_review'], 'only the final review is still owed')
        # A legacy study has no plan and is asked for no intake review.
        legacy, _ = bundle.run(str(BRONZE), directory=str(self.directory / 'legacy'))
        status, payload = self.validate(legacy, '--require-review')
        self.assertEqual((payload['intake_review'], self.codes(payload)), ('absent', ['semantic_review']))

    def test_resume_reports_the_intake_review_state_beside_the_final_review(self):
        directory, _ = self.study('reviewed', plan_review=self.write('p.json', self.template),
                                  session_ledger=str(INTAKE / 'session-ledger.json'))
        report = session.resume(directory, reference=AT)
        self.assertEqual((report['review'], report['intake_review']), ('pending', 'pending'))
        status, text = self.cli('resume', directory, '--reference', AT)
        self.assertEqual(status, 0, text)
        self.assertIn('intake review pending', text)
        plain, _ = self.study('plain')
        self.assertIsNone(session.resume(plain, reference=AT)['intake_review'])


class TheBudgetOnTheCap(ReviewCase):
    """Case 7's semantic limit. The gates pass it as enforced; the review can say no."""

    def setUp(self):
        super().setUp()
        self.plan = intake.load(BUDGET_PLAN)
        budget = next(r for r in self.plan['requirements'] if r['id'] == 'budget')
        budget['assessment'].update(path='control', gap=None, controls=[
            controls.resolve('dry_pasta', 'max_axis_value', axis='price_per_base', unit='EUR/kg', value=100)])
        self.refreshed(self.plan)
        brief = brief_module.load(BUDGET_BRIEF)
        from dataclasses import replace
        self.brief = replace(brief, max_axis_value=100, intake=intake.binding(self.plan))
        data = self.brief.as_dict()
        data.pop('source')
        data['inputs'] = list(self.brief.resolved_inputs)
        self.brief_path = self.write('budget-on-cap.json', data)
        self.plan_path = self.write('budget-on-cap-plan.json', self.plan)

    def test_the_gates_cannot_see_it_and_the_review_records_it(self):
        result, _ = analyse(self.brief, plan=self.plan)
        rows = {r['id']: r for r in result['gates']['intake']['requirements']}
        self.assertEqual((result['stop'], rows['budget']['disposition']), ('', gates.ENFORCED))
        review = self.completed(intake_review.template(self.plan), adequacy={
            'status': 'fail', 'requirement_ids': ['budget'],
            'findings': 'max_axis_value caps euros per kilogram, not the purchase total: 100 on '
                        'that axis excludes nothing from a shelf running 2.96 to 8.78 EUR/kg and '
                        'answers a question the buyer did not ask'})
        intake_review.check_review(review, self.plan)
        path = self.write('review.json', review)
        with self.assertRaisesRegex(bundle.BundleError, 'caps euros per kilogram'):
            bundle.run(str(self.brief_path), directory=str(self.directory / 'refused'),
                       plan=str(self.plan_path), plan_review=str(path))
        self.assertFalse((self.directory / 'refused').exists())
        status, text = self.cli('plan-review', self.plan_path, path)
        self.assertEqual(status, 1, text)
        self.assertIn('status fail', text)
        self.assertIn('[budget]', text)
        # Without the review the same study runs, enforced and wrong, as stage 6 documented.
        directory, manifest = bundle.run(str(self.brief_path), directory=str(self.directory / 'unreviewed'),
                                         plan=str(self.plan_path))
        self.assertEqual(manifest.get('stop'), '')
        self.assertNotIn('intake_review', manifest)


class CommandLine(ReviewCase):
    def test_template_writes_a_new_file_and_prints_the_questions(self):
        output = self.directory / 'review.json'
        status, text = self.cli('plan-review-template', PLAN, '-o', output)
        self.assertEqual(status, 0, text)
        self.assertEqual(json.loads(output.read_text()), self.template)
        for name in intake_review.CHECKS:
            self.assertIn(intake_review.QUESTIONS[name], text)
        self.assertIn('Pending is not approval', text)
        status, text = self.cli('plan-review-template', PLAN, '-o', output)
        self.assertEqual(status, 2, 'an existing file is not overwritten')
        status, text = self.cli('plan-review-template', PLAN, '-o', self.directory / 'review.txt')
        self.assertEqual(status, 2)

    def test_template_names_the_limits_a_redaction_imposes(self):
        plan = copy.deepcopy(self.plan)
        plan['user_evidence']['messages'][0]['redactions'].append(
            {'description': 'the acceptable shipping cost', 'reason': 'personal data', 'limits_review': True})
        self.refreshed(plan)
        status, text = self.cli('plan-review-template', self.write('plan.json', plan),
                                '-o', self.directory / 'review.json')
        self.assertEqual(status, 0, text)
        self.assertIn('limit         redaction in u1: the acceptable shipping cost — omissions and '
                      'faithfulness cannot pass', text)

    def test_plan_review_exit_codes_say_bound_failed_or_unusable(self):
        pending = self.write('pending.json', self.template)
        status, text = self.cli('plan-review', PLAN, pending)
        self.assertEqual(status, 0, text)
        self.assertIn('status pending', text)
        self.assertIn('(none yet)', text)
        passed = self.write('passed.json', self.completed())
        status, text = self.cli('plan-review', PLAN, passed)
        self.assertEqual(status, 0, text)
        self.assertIn('status pass', text)
        self.assertIn('not that the buyer confirmed it', text)
        failed = self.write('failed.json', self.completed(omissions={'status': 'fail', 'message_ids': ['u1']}))
        status, text = self.cli('plan-review', PLAN, failed)
        self.assertEqual(status, 1, text)
        status, text = self.cli('plan-review', BUDGET_PLAN, passed)
        self.assertEqual(status, 2)
        self.assertIn('superseded', text)


class Fixture(ReviewCase):
    def test_the_committed_review_binds_the_committed_plan_and_passes(self):
        review = intake_review.load(FIXTURE, self.plan)
        self.assertEqual(intake_review.status(review), 'pass')
        self.assertTrue(review['reviewer'])
        self.assertEqual(review['checks']['omissions']['message_ids'], ['u1'])
        self.assertEqual(set(review['checks']['adequacy']['requirement_ids']),
                         {r['id'] for r in self.plan['requirements']})
        self.assertIn('no_response', review['basis']['readback_response'])
        self.assertTrue(any('nothing is user-confirmed' in text for text in review['unresolved_limits']))

    def test_the_gate_replays_the_reviewed_example_and_pins_its_status(self):
        example = next(e for e in maintenance.load_baseline()['examples']
                       if e['name'] == 'pasta-delivered-cost')
        self.assertEqual(example['intake_review'], 'tests/intake/delivered-cost-intake-review.json')
        self.assertEqual(example['expect']['intake_review'], 'pass')
        result = maintenance.check_examples({'examples': [example]})
        self.assertTrue(result.passed, result.findings)
        moved = dict(example, expect=dict(example['expect'], intake_review='pending'))
        result = maintenance.check_examples({'examples': [moved]})
        self.assertEqual([f.code for f in result.findings], ['example_decision_changed'])
        self.assertIn('intake_review', result.findings[0].message)
        for other in maintenance.load_baseline()['examples']:
            if other['name'] != 'pasta-delivered-cost':
                self.assertEqual(other['expect']['intake_review'], '', other['name'])

    def test_the_contract_is_discovered_and_pinned(self):
        self.assertEqual(maintenance._contract_versions()['intake_review'],
                         intake_review.INTAKE_REVIEW_VERSION)
        self.assertEqual(maintenance.load_baseline()['contracts']['intake_review'],
                         intake_review.INTAKE_REVIEW_VERSION)
        with patch.object(intake_review, 'INTAKE_REVIEW_VERSION', 2):
            findings = maintenance.check_contracts(maintenance.load_baseline()).findings
            self.assertTrue(any(f.code == 'contract_version' and 'intake_review' in f.message
                                for f in findings))
        from shopping_advisor.study import audit
        self.assertEqual((audit.REVIEW_VERSION, audit.REVIEW_CHECKS),
                         (2, ('citation_support', 'variant_applicability', 'user_priorities',
                              'coverage_and_limits', 'conclusion_presentation')),
                         'stage 10 moved the final review once, and the two committed '
                         'reviews were reissued with it; the intake review did not move')


if __name__ == '__main__':
    unittest.main()
