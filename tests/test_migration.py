"""Stage 10: the one migration, argued as one claim.

INTAKE §16 stage 10 lands together what a bump of either version moves at
once -- every committed study id and both committed final reviews: manifest
v3 with a declared artifact inventory, the review basis as a contract, the
phase-aware final review at v2 resting on valid intake findings, the identity
decision, the delivery review and the dirty-tree caveat. What this module
holds the migration to is the sentence that ends the stage: **ids move;
decisions must not.**

The decisions below are the pre-migration record, written down here rather
than read from the baseline, so that the gate's own re-recording cannot
certify a moved decision.
"""
import contextlib
from dataclasses import replace
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.study import (adaptation, audit, brief as brief_module, bundle, delivery,
                                    delivery_review, intake, intake_review, inventory, session)
from shopping_advisor.study.__main__ import main

HERE = pathlib.Path(__file__).resolve().parent
STUDIES, INTAKE, T3 = HERE / 'studies', HERE / 'intake', HERE / 'studies' / 't3'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
PLAN, BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'
PASSING_INTAKE_REVIEW = INTAKE / 'delivered-cost-intake-review.json'
AT = '2026-09-17T00:00:00+00:00'

#: What the six examples decided before the migration (baseline recorded at
#: 2026-09-17T15:35:43+00:00, manifest v2), with their ids left out on purpose.
DECISIONS_BEFORE = {
    'pasta-bronze-die': {'outcome': 'recommendation', 'stop': '', 'offers': 5, 'excluded': 3,
                         'shortlisted': 3, 'current_advice': 'not_in_scope'},
    'pasta-low-temperature-drying': {'outcome': 'insufficient_evidence', 'stop': '', 'offers': 0,
                                     'excluded': 2, 'shortlisted': 0, 'current_advice': 'not_in_scope'},
    't3-positive': {'outcome': 'recommendation', 'stop': '', 'offers': 3, 'excluded': 0,
                    'shortlisted': 3, 'current_advice': 'not_in_scope'},
    't3-insufficient': {'outcome': 'insufficient_evidence', 'stop': '', 'offers': 3, 'excluded': 0,
                        'shortlisted': 0, 'current_advice': 'not_in_scope'},
    'pasta-delivered-cost': {'outcome': 'recommendation', 'stop': 'requirement_unsupported', 'offers': 5,
                             'excluded': 3, 'shortlisted': 0, 'current_advice': 'not_in_scope',
                             'intake_review': 'pass', 'resumable': 'yes'},
    'pasta-purchase-budget': {'outcome': 'recommendation', 'stop': 'requirement_unsupported', 'offers': 5,
                              'excluded': 3, 'shortlisted': 0, 'current_advice': 'not_in_scope'},
}
IDS_BEFORE = {'pasta-bronze-die': 'pasta-bronze-die-46127870314d',
              'pasta-low-temperature-drying': 'pasta-low-temperature-drying-d309972b3bd0',
              't3-positive': 'basmati-audit-positive-571cca1a2d4b',
              't3-insufficient': 'basmati-audit-insufficient-18b88dc2bd3c',
              'pasta-delivered-cost': 'pasta-delivered-cost-608160f72d15',
              'pasta-purchase-budget': 'pasta-purchase-budget-85064fcacd0e'}


class MigrationCase(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def legacy(self, name='legacy'):
        return bundle.run(str(BRONZE), directory=str(self.directory / name))

    def plan_backed(self, name='plan', review=None, **kwargs):
        return bundle.run(str(BRIEF), directory=str(self.directory / name), plan=str(PLAN),
                          plan_review=review, **kwargs)

    def approved(self, directory):
        review = json.loads((directory / bundle.REVIEW).read_text())
        review['reviewer'] = 'test reviewer'
        for item in review['checks'].values():
            item.update(status='pass', findings='synthetic finding for a fixture')
        return review


class TheInventory(MigrationCase):
    """INTAKE §6: a new artifact cannot enter the bundle without a binding decision."""

    def test_every_binding_is_a_known_kind_and_the_table_is_the_manifests_order(self):
        for name, row in inventory.BINDINGS.items():
            self.assertEqual(set(row), {'required', 'binding'}, name)
            self.assertIn(row['binding'], inventory.KINDS, name)
        self.assertEqual(inventory.ARTIFACTS, bundle.ARTIFACTS)
        self.assertEqual(len(inventory.ARTIFACTS), 9)
        self.assertEqual(set(inventory.OPTIONAL),
                         {intake.SNAPSHOT, intake_review.SNAPSHOT, delivery.RECORD,
                          session.SNAPSHOT, delivery_review.RECORD, adaptation.RECORD})

    def test_a_full_bundle_writes_nothing_the_inventory_does_not_name(self):
        # R15: the adaptation record is the one optional artifact a v1 ledger
        # cannot fund, so the committed record is re-pointed at this ledger's
        # retained engineering proposal; the method digest does not move.
        record = adaptation.load(INTAKE / 'adaptation-record.json')
        record['origin'].update(session_id='pasta-delivered-session', action_id='engineer-1')
        adaptation.seal(record)
        directory, manifest = self.plan_backed(
            review=str(PASSING_INTAKE_REVIEW), session_ledger=str(INTAKE / 'session-ledger.json'),
            adaptation_record=record)
        self.cli('deliver', directory, '--reference', AT)
        template = delivery_review.template(directory)
        template['reviewer'] = 'r'
        for item in template['checks'].values():
            item.update(status='pass', findings='f')
        template['attestation'].update(by='r', reference_read_honestly=True, declaration_true=True)
        status, text = self.cli('review-delivery', directory, self.write('dr.json', template))
        self.assertEqual(status, 0, text)
        files = {p.name for p in directory.iterdir() if p.is_file()} - {bundle.MANIFEST}
        self.assertEqual(files, set(inventory.BINDINGS), 'every optional artifact appears once here, '
                                                        'so the table is neither short nor padded')
        recorded = bundle.load_manifest(directory)['artifacts']
        self.assertEqual(set(recorded), files)
        for name, entry in recorded.items():
            self.assertEqual(entry['binding'], inventory.BINDINGS[name]['binding'], name)
        self.assertEqual(bundle.verify(directory)[1], [])

    def test_an_undeclared_file_is_refused_by_the_writer_and_reported_by_verify(self):
        directory, _ = self.legacy()
        (directory / 'notes.json').write_text('{}')
        with self.assertRaisesRegex(bundle.BundleError, 'notes.json is not in the bundle inventory'):
            bundle.artifact_digests(directory)
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['artifact_undeclared'])
        self.assertIn('study/inventory.py', findings[0]['message'])
        status, text = self.cli('deliver', directory, '--reference', AT)
        self.assertEqual(status, 2)
        self.assertIn('artifact_undeclared', text)

    def test_the_manifest_records_each_binding_and_a_changed_one_is_a_finding(self):
        directory, manifest = self.legacy()
        self.assertEqual(manifest['manifest_version'], 3)
        for name in bundle.ARTIFACTS:
            self.assertEqual(manifest['artifacts'][name]['binding'], inventory.BINDINGS[name]['binding'])
        path = directory / bundle.MANIFEST
        data = json.loads(path.read_text())
        data['artifacts'][bundle.CARDS]['binding'] = inventory.DELIVERY
        path.write_text(json.dumps(data))
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['artifact_binding_changed'])
        self.assertIn("'delivery'", findings[0]['message'])
        del data['artifacts'][bundle.CARDS]['binding']
        path.write_text(json.dumps(data))
        self.assertEqual([f['code'] for f in bundle.verify(directory)[1]], ['artifact_binding_changed'])

    def test_a_v2_bundle_is_refused_not_reinterpreted(self):
        directory, _ = self.legacy()
        path = directory / bundle.MANIFEST
        data = json.loads(path.read_text())
        data['manifest_version'] = 2
        path.write_text(json.dumps(data))
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['unsupported_manifest_version'])
        self.assertIn('Nothing below was checked', findings[0]['message'])


class TheReviewBasisIsAContract(MigrationCase):
    def test_the_basis_is_exactly_the_semantic_rows_that_are_present(self):
        legacy, _ = self.legacy()
        self.assertEqual(list(audit.review_basis(legacy)),
                         ['brief.json', 'candidates.jsonl', 'cards.jsonl', 'ranking.json',
                          'ledger.json', 'claim-index.json'])
        plain, _ = self.plan_backed('plain')
        self.assertEqual(list(audit.review_basis(plain))[6:], [intake.SNAPSHOT])
        reviewed, _ = self.plan_backed('reviewed', review=str(PASSING_INTAKE_REVIEW),
                                       session_ledger=str(INTAKE / 'session-ledger.json'))
        self.cli('deliver', reviewed, '--reference', AT)
        basis = audit.review_basis(reviewed)
        self.assertEqual(list(basis)[6:], [intake.SNAPSHOT, intake_review.SNAPSHOT])
        for name in (delivery.RECORD, session.SNAPSHOT, bundle.REPORT, bundle.REVIEW, bundle.VALIDATION):
            self.assertNotIn(name, basis, f'{name} is bound elsewhere, or binds others')
        self.assertEqual(set(basis), set(inventory.present(reviewed, inventory.SEMANTIC)))

    def test_the_semantic_rows_are_the_basis_and_the_delivery_rows_are_not(self):
        self.assertEqual(set(inventory.bound(inventory.SEMANTIC)),
                         {'brief.json', 'candidates.jsonl', 'cards.jsonl', 'ranking.json', 'ledger.json',
                          'claim-index.json', intake.SNAPSHOT, intake_review.SNAPSHOT, adaptation.RECORD})
        self.assertEqual(set(inventory.bound(inventory.DELIVERY)), {delivery.RECORD, session.SNAPSHOT})
        self.assertEqual(inventory.bound(inventory.REPORT_TARGET), (bundle.REPORT,))
        self.assertEqual(set(inventory.bound(inventory.REVIEW_RECORD)),
                         {bundle.REVIEW, bundle.VALIDATION, delivery_review.RECORD})


class ReviewV2(MigrationCase):
    def test_a_v1_review_is_refused_outright(self):
        directory, _ = self.legacy()
        review = audit.review_template(directory)
        review['review_version'] = 1
        del review['phase']
        del review['intake_review']
        del review['checks']['conclusion_presentation']
        with self.assertRaisesRegex(audit.AuditError, 'unsupported semantic review version'):
            audit.check_review(review, directory)
        review = audit.review_template(directory)
        review['phase'] = 'intake'
        with self.assertRaisesRegex(audit.AuditError, 'phase must be'):
            audit.check_review(review, directory)

    def test_the_template_names_its_phase_five_checks_and_the_intake_findings(self):
        legacy, _ = self.legacy()
        template = json.loads((legacy / bundle.REVIEW).read_text())
        self.assertEqual((template['review_version'], template['phase']), (2, 'final'))
        self.assertEqual(set(template['checks']), set(audit.REVIEW_CHECKS))
        self.assertIn('conclusion_presentation', template['checks'])
        self.assertIsNone(template['intake_review'])
        plain, _ = self.plan_backed('plain')
        self.assertEqual(json.loads((plain / bundle.REVIEW).read_text())['intake_review'],
                         {'status': 'absent', 'sha256': ''})
        pending = intake_review.template(intake.load(PLAN))
        reviewed, _ = self.plan_backed('reviewed', review=self.write('pending.json', pending))
        self.assertEqual(json.loads((reviewed / bundle.REVIEW).read_text())['intake_review'],
                         {'status': 'pending', 'sha256': intake_review.digest(pending)})
        for name in audit.REVIEW_CHECKS:
            self.assertTrue(audit.REVIEW_QUESTIONS[name].endswith('?'), name)

    def test_final_approval_requires_valid_intake_findings(self):
        pending = intake_review.template(intake.load(PLAN))
        directory, _ = self.plan_backed(review=self.write('pending.json', pending))
        approval = self.approved(directory)
        with self.assertRaisesRegex(audit.AuditError, 'final approval requires valid intake findings.*pending'):
            audit.check_review(approval, directory)
        recorded_failure = json.loads(json.dumps(approval))
        recorded_failure['checks']['user_priorities']['status'] = 'fail'
        audit.check_review(recorded_failure, directory)
        unreviewed, _ = self.plan_backed('unreviewed')
        with self.assertRaisesRegex(audit.AuditError, 'intake review is absent'):
            audit.check_review(self.approved(unreviewed), unreviewed)
        reviewed, _ = self.plan_backed('reviewed', review=str(PASSING_INTAKE_REVIEW))
        audit.check_review(self.approved(reviewed), reviewed, required=True)
        legacy, _ = self.legacy()
        audit.check_review(self.approved(legacy), legacy, required=True)

    def test_a_changed_intake_review_supersedes_a_completed_final_review(self):
        directory, _ = self.plan_backed(review=str(PASSING_INTAKE_REVIEW))
        status, text = self.cli('review', directory, self.write('final.json', self.approved(directory)))
        self.assertEqual(status, 0, text)
        self.assertEqual(self.cli('validate-report', directory, '--require-review')[0], 0)
        # Through the CLI: the order is intake review, then final review.
        another = intake_review.load(PASSING_INTAKE_REVIEW, intake.load(PLAN))
        another['unresolved_limits'].append('a later reading')
        status, text = self.cli('review-intake', directory, self.write('another.json', another))
        self.assertEqual(status, 2)
        self.assertIn('the intake review comes first', text)
        self.assertEqual(bundle.verify(directory)[1], [], 'nothing was written')
        # Behind the CLI's back: the final review no longer binds.
        (directory / intake_review.SNAPSHOT).write_text(json.dumps(another))
        manifest = bundle.load_manifest(directory)
        manifest['intake_review'] = {'status': 'pass', 'sha256': intake_review.digest(another)}
        manifest['artifacts'] = bundle.artifact_digests(directory)
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        final = json.loads((directory / bundle.REVIEW).read_text())
        with self.assertRaisesRegex(audit.AuditError, 'different evidence/decision bytes'):
            audit.check_review(final, directory)
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['report_invalid'])

    def test_review_intake_refreshes_the_pending_template_it_will_rest_on(self):
        directory, _ = self.plan_backed()
        before = json.loads((directory / bundle.REVIEW).read_text())
        self.assertEqual(before['intake_review'], {'status': 'absent', 'sha256': ''})
        status, text = self.cli('review-intake', directory, PASSING_INTAKE_REVIEW)
        self.assertEqual(status, 0, text)
        after = json.loads((directory / bundle.REVIEW).read_text())
        self.assertEqual(after['intake_review']['status'], 'pass')
        self.assertEqual(after['intake_review']['sha256'],
                         bundle.load_manifest(directory)['intake_review']['sha256'])
        self.assertIn(intake_review.SNAPSHOT, after['basis'])
        self.assertEqual(bundle.verify(directory)[1], [])
        self.assertEqual(json.loads((directory / bundle.VALIDATION).read_text()),
                         audit.validation_result(after))

    def test_the_reissued_fixture_reviews_are_v2_and_bind_the_migrated_bundles(self):
        for name, brief in (('positive', 'positive.toml'), ('insufficient', 'insufficient.toml')):
            with self.subTest(name=name):
                directory, manifest = bundle.run(T3 / brief, directory=self.directory / name,
                                                 evidence=T3 / 'evidence.json')
                review = json.loads((T3 / f'{name}-review.json').read_text())
                self.assertEqual((review['review_version'], review['phase']), (2, 'final'))
                self.assertIsNone(review['intake_review'])
                self.assertIn('conclusion_presentation', review['checks'])
                self.assertTrue(any('re-read against the new report' in t for t in review['unresolved_limits']))
                audit.check_review(review, directory, required=True)


class Identity(MigrationCase):
    """§8 resolved: the plan binding in the brief bytes is the identity projection."""

    def test_the_manifest_version_is_identity_material_and_moved_every_id(self):
        brief = brief_module.load(BRONZE)
        inputs = bundle.input_digests(brief)
        now = bundle.study_id(brief, inputs)
        self.assertEqual(now, 'pasta-bronze-die-bde2b027b117')
        with patch.object(bundle, 'STUDY_MANIFEST_VERSION', 2):
            self.assertEqual(bundle.study_id(brief, inputs), IDS_BEFORE['pasta-bronze-die'])

    def test_a_plan_change_moves_the_id_through_the_brief_binding_and_nothing_else_does(self):
        plan = intake.load(PLAN)
        self.assertEqual(plan['readback']['response']['status'], 'no_response')
        plan['readback']['response']['status'] = 'not_presented'
        plan['readback']['text'] = ''
        intake.check(plan)
        brief = replace(brief_module.load(BRIEF), intake=intake.binding(plan))
        data = brief.as_dict()
        data.pop('source')
        data['inputs'] = list(brief.resolved_inputs)
        rebound = self.write('rebound.json', data)
        moved, moved_manifest = bundle.run(str(rebound), directory=str(self.directory / 'moved'),
                                           plan=self.write('plan.json', plan))
        original, original_manifest = self.plan_backed('original')
        self.assertNotEqual(moved_manifest['study_id'], original_manifest['study_id'])
        self.assertIn('No read-back of this plan revision was presented',
                      (moved / bundle.REPORT).read_text())
        self.assertIn('was presented and', (original / bundle.REPORT).read_text())
        for name in (bundle.CANDIDATES, bundle.CARDS):
            self.assertEqual((moved / name).read_bytes(), (original / name).read_bytes(),
                             'the response status moves the id and the attribution, not a decision')
        # What does not move it: the intake review, the session snapshot, a delivery.
        reviewed, manifest = self.plan_backed('reviewed', review=str(PASSING_INTAKE_REVIEW),
                                              session_ledger=str(INTAKE / 'session-ledger.json'))
        self.cli('deliver', reviewed, '--reference', AT)
        self.assertEqual(manifest['study_id'], original_manifest['study_id'])
        self.assertEqual(bundle.load_manifest(reviewed)['study_id'], original_manifest['study_id'])
        self.assertNotEqual(original_manifest['study_id'], bundle.run(
            str(BRONZE), directory=str(self.directory / 'plain'))[1]['study_id'])


class CodeCaveat(MigrationCase):
    def test_a_dirty_tree_is_a_caveat_not_a_finding(self):
        directory, manifest = self.legacy()
        path = directory / bundle.MANIFEST
        data = json.loads(path.read_text())
        data['code']['git_dirty'] = True
        path.write_text(json.dumps(data))
        self.assertEqual(bundle.verify(directory)[1], [])
        caveats = bundle.code_caveats(data)
        self.assertEqual(len(caveats), 1)
        self.assertIn('does not identify the code that ran', caveats[0])
        status, text = self.cli('verify', directory)
        self.assertEqual(status, 0, text)
        self.assertIn('uncommitted changes', text)
        self.assertIn('verified', text)
        status, text = self.cli('validate-report', directory)
        payload = json.loads(text)
        self.assertEqual((status, payload['valid']), (0, True))
        self.assertEqual(payload['code'], caveats)
        data['code']['git_dirty'] = None
        self.assertIn('unknown is not clean', bundle.code_caveats(data)[0])
        data['code']['git_dirty'] = False
        self.assertEqual(bundle.code_caveats(data), [])


class IdsMoveDecisionsDoNot(MigrationCase):
    def test_the_contracts_that_moved_are_pinned_and_the_ones_that_did_not_are_still_one(self):
        versions = maintenance._contract_versions()
        self.assertEqual((versions['study_manifest'], versions['semantic_review'], versions['delivery_review']),
                         (3, 2, 1))
        for name in ('brief', 'intake_plan', 'intake_review', 'stage_gates', 'delivery_record',
                     'evidence_ledger', 'study_audit'):
            self.assertEqual(versions[name], 1, name)
        # R15 phase 0 (2026-09-18): the ledger moved to let engineering run, and
        # the adaptation record arrived; the manifest stayed at v3 on purpose.
        self.assertEqual((versions['session_ledger'], versions['adaptation_record']), (2, 2))
        self.assertEqual(maintenance.load_baseline()['contracts'], versions)

    def test_every_example_decides_as_it_did_before_the_migration_under_a_new_id(self):
        examples = {e['name']: e for e in maintenance.load_baseline()['examples']}
        # Examples added after the migration have no pre-migration decision to
        # hold to; the adaptation example's claim is in test_adaptation, and
        # the two smartwatch studies' (R15 phases 2 and 4) in test_smartwatch
        # and the gate.
        self.assertEqual(set(examples) - {'pasta-adaptation', 'smartwatch-dive-nfc',
                                          'smartwatch-dive-nfc-reextracted'},
                         set(DECISIONS_BEFORE))
        for name, before in DECISIONS_BEFORE.items():
            with self.subTest(example=name):
                expect = examples[name]['expect']
                for field, value in before.items():
                    self.assertEqual(expect[field], value, field)
                self.assertNotEqual(expect['study_id'], IDS_BEFORE[name])
                self.assertEqual(expect['study_id'].rsplit('-', 1)[0], IDS_BEFORE[name].rsplit('-', 1)[0])
        result = maintenance.check_examples({'examples': list(examples.values())})
        self.assertTrue(result.passed, result.findings)

    def test_the_intake_review_fixture_and_the_session_ledger_did_not_move(self):
        """Neither binds a study id or report bytes, so the migration owes them nothing."""
        plan = intake.load(PLAN)
        review = intake_review.load(PASSING_INTAKE_REVIEW, plan)
        self.assertEqual((review['intake_review_version'], intake_review.status(review)), (1, 'pass'))
        ledger = session.load(INTAKE / 'session-ledger.json')
        self.assertEqual(ledger['plan']['sha256'], intake.digest(plan))


if __name__ == '__main__':
    unittest.main()
