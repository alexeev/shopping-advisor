"""R15: the adaptation record, the controlled trial and the study binding.

What these guard is the loop ROADMAP R15 asks for -- gap → patch → checks
inside a boundary → review → adoption → study revision -- and the ways it
must refuse: a patch edited after review, a check that timed out, an
evaluator the patch rewrote, a budget spent, a record the manifest does not
name, a reader that has never heard of the record. The kernel boundary is
demonstrated where ``sandbox-exec`` runs and skipped, saying so, where it does
not: a skipped boundary test is not a demonstrated boundary.
"""

import contextlib
import copy
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.provenance import write_json_atomically
from shopping_advisor.study import adaptation, bundle, inventory, session, trial
from shopping_advisor.study.__main__ import main

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
STUDIES = HERE / 'studies'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
LEDGER_V2 = HERE / 'intake' / 'adaptation-session.json'
LEDGER_V1 = HERE / 'intake' / 'session-ledger.json'
AT = '2026-09-18T12:00:00+00:00'
VENV = ROOT / '.venv'
INTERPRETER = str(VENV / 'bin' / 'python')
SANDBOXED = trial.available() and pathlib.Path(INTERPRETER).is_file()


def passing_check(seconds=1.5):
    return {'command': ['python', '-m', 'unittest'], 'started_at': AT, 'finished_at': AT,
            'seconds': seconds, 'exit': 0, 'timed_out': False, 'output_sha256': '',
            'output_path': '', 'summary': 'exit 0', 'boundary': 'kernel'}


def accepted_record(identifier='fixture-1', session_id='pasta-adaptation-session',
                    action_id='engineer-1', content=b'# a patched file\n'):
    """A valid record that has been through the whole loop, without a sandbox."""
    record = adaptation.template(identifier, 'method', 'A synthetic patch for the tests.',
                                 session_id, action_id, 1800, 2)
    record['patch']['files'] = [adaptation.file_entry('tests/test_fixture_smoke.py', 'added', content)]
    record['base'] = {'git_revision': '1626b49', 'tree_sha256': 'a' * 64}
    record['result_tree_sha256'] = 'b' * 64
    record['evaluator'] = {'files': ['pyproject.toml'], 'base_sha256': 'c' * 64, 'frozen': True}
    record['inspection'] = trial.inspect(record['patch']['files'])
    record['checks'] = [passing_check()]
    record['attempts'] = 1
    record['consumption'] = {'seconds': 1.5, 'attempts': 1}
    record['runner'].update(boundary='kernel', profile_sha256='d' * 64, timeout_seconds=300)
    adaptation.seal(record)
    record['review'] = {'reviewer': 'reviewer', 'verdict': 'pass', 'findings': ['nothing moves'],
                        'patch_sha256': record['patch']['sha256'],
                        'checks_sha256': adaptation.checks_digest(record)}
    record['adoption'] = {'decision': 'accepted', 'decided': AT, 'by': 'repository maintainer',
                          'reason': 'fixture'}
    return adaptation.seal(record)


def harness_only_record(exception='maintainer message 2026-09-18: sandbox-exec exits 71 in this '
                                  'container; run the checks bare and label them'):
    """The same loop under the exception the maintainer recorded: no profile, a label."""
    record = accepted_record()
    record['checks'][0]['boundary'] = 'harness-only'
    record['runner'].update(boundary='harness-only', profile_sha256='', exception=exception)
    record['review']['checks_sha256'] = adaptation.checks_digest(record)
    return adaptation.seal(record)


class Contract(unittest.TestCase):
    def test_a_template_is_valid_and_names_the_gap_without_capturing_or_running(self):
        record = adaptation.template('smoke', 'category', 'hypothesis', 'session', 'engineer-1', 100, 2)
        self.assertEqual(record['patch'], {'sha256': '', 'files': []})
        self.assertEqual(record['adoption']['decision'], 'pending')
        self.assertEqual(record['review']['verdict'], 'pending')
        self.assertEqual(record['descriptor_sha256'], adaptation.descriptor(record))

    def test_closed_fields_and_vocabularies(self):
        base = accepted_record()
        for change, message in (
                (lambda r: r.update(adaptation_version=adaptation.ADAPTATION_VERSION + 1), 'unsupported version'),
                (lambda r: r.update(scheduler='cron'), 'exactly these fields'),
                (lambda r: r.update(layer='frontend'), 'expected one of'),
                (lambda r: r['adoption'].update(decision='shipped'), 'expected one of'),
                (lambda r: r['runner'].update(boundary='container'), 'expected one of'),
                (lambda r: r['budget'].update(seconds=0), 'at least 1'),
                (lambda r: r['patch']['files'][0].update(path='../outside.py'), 'never climb out')):
            record = copy.deepcopy(base)
            change(record)
            with self.subTest(message=message), self.assertRaisesRegex(adaptation.AdaptationError, message):
                adaptation.check(record)

    def test_the_patch_carries_its_content_and_the_content_its_digest(self):
        record = accepted_record()
        tampered = copy.deepcopy(record)
        tampered['patch']['files'][0]['content'] = '# something else\n'
        with self.assertRaisesRegex(adaptation.AdaptationError, 'does not match its recorded digest'):
            adaptation.check(tampered)
        binary = adaptation.file_entry('cases.gz', 'added', b'\x1f\x8b\xff\x00binary')
        self.assertIsNone(binary['content'])
        self.assertEqual(adaptation.file_content(binary), b'\x1f\x8b\xff\x00binary')
        deleted = adaptation.file_entry('old.py', 'deleted')
        self.assertEqual((deleted['sha256'], deleted['content'], deleted['content_base64']), ('', None, ''))

    def test_the_descriptor_moves_with_the_method_and_not_with_the_review(self):
        record = accepted_record()
        reviewed = copy.deepcopy(record)
        reviewed['review']['findings'] = ['a different finding']
        self.assertEqual(adaptation.descriptor(reviewed), record['descriptor_sha256'])
        other = accepted_record(content=b'# another patch\n')
        self.assertNotEqual(other['descriptor_sha256'], record['descriptor_sha256'])
        other_base = copy.deepcopy(record)
        other_base['base']['git_revision'] = 'deadbeef'
        self.assertNotEqual(adaptation.descriptor(other_base), record['descriptor_sha256'])

    def test_a_patch_or_a_check_after_the_review_supersedes_it(self):
        record = accepted_record()
        edited = copy.deepcopy(record)
        edited['patch']['files'][0] = adaptation.file_entry('tests/test_fixture_smoke.py', 'added', b'# edited\n')
        edited['patch']['sha256'] = adaptation.patch_digest(edited['patch']['files'])
        edited['descriptor_sha256'] = adaptation.descriptor(edited)
        with self.assertRaisesRegex(adaptation.AdaptationError, 'patch edited after review'):
            adaptation.check(edited)
        rerun = copy.deepcopy(record)
        rerun['checks'].append(passing_check())
        rerun['attempts'] = rerun['consumption']['attempts'] = 2
        with self.assertRaisesRegex(adaptation.AdaptationError, 'checks run after review'):
            adaptation.check(rerun)

    def test_acceptance_needs_a_passing_review_a_frozen_evaluator_and_a_finished_passing_check(self):
        for change, message in (
                (lambda r: r['review'].update(verdict='limited'), 'passing review'),
                (lambda r: r['evaluator'].update(frozen=False), 'proven frozen'),
                (lambda r: r['checks'][-1].update(exit=1, summary='exit 1'), 'declares none'),
                (lambda r: r['checks'][-1].update(exit=None, timed_out=True), 'timed-out check')):
            record = accepted_record()
            change(record)
            record['review']['checks_sha256'] = adaptation.checks_digest(record)
            with self.subTest(message=message), self.assertRaisesRegex(adaptation.AdaptationError, message):
                adaptation.check(record)

    def test_a_failing_last_check_is_accepted_only_with_declared_baseline_moves_and_a_passing_review(self):
        record = accepted_record()
        record['checks'][-1].update(exit=1, summary='exit 1: capability_untracked, 3 baseline tests')
        record['baseline_moves'] = ['capabilities: smartwatch is a new experiment the baseline must record',
                                    'tests: test_smartwatch.py is a new module; the floor moves']
        record['review']['checks_sha256'] = adaptation.checks_digest(record)
        adaptation.check(record)
        record['review']['verdict'] = 'limited'
        with self.assertRaisesRegex(adaptation.AdaptationError, 'passing review'):
            adaptation.check(record)
        record['review']['verdict'] = 'pass'
        record['checks'][-1].update(exit=None, timed_out=True)
        record['review']['checks_sha256'] = adaptation.checks_digest(record)
        with self.assertRaisesRegex(adaptation.AdaptationError, 'timed-out check'):
            adaptation.check(record)

    def test_a_timed_out_check_has_no_exit_status_and_no_pass(self):
        record = accepted_record()
        record['adoption'] = {'decision': 'pending', 'decided': '', 'by': '', 'reason': ''}
        record['checks'][-1].update(exit=0, timed_out=True)
        record['review']['checks_sha256'] = adaptation.checks_digest(record)
        with self.assertRaisesRegex(adaptation.AdaptationError, 'killed, and it has no pass'):
            adaptation.check(record)

    def test_attempts_beyond_the_budget_and_an_unexplained_harness_only_boundary_are_refused(self):
        record = accepted_record()
        record['attempts'] = record['consumption']['attempts'] = 3
        with self.assertRaisesRegex(adaptation.AdaptationError, 'exceed the budget'):
            adaptation.check(record)
        record = accepted_record()
        record['runner'].update(boundary='harness-only', exception='')
        with self.assertRaisesRegex(adaptation.AdaptationError, 'exception the maintainer recorded'):
            adaptation.check(record)

    def test_a_harness_only_boundary_with_its_exception_passes_and_the_binding_carries_the_label(self):
        record = harness_only_record()
        adaptation.check(record)
        self.assertEqual(adaptation.binding(record)['boundary'], 'harness-only')
        # The label is not part of the method identity: the same patch run bare
        # and run inside the profile is the same code, and a study bound to
        # either derives the same id. What differs is the caveat, not the method.
        self.assertEqual(record['descriptor_sha256'], accepted_record()['descriptor_sha256'])

    def test_the_binding_names_the_record_exactly(self):
        record = accepted_record()
        bound = adaptation.binding(record)
        adaptation.check_binding(record, bound)
        with self.assertRaisesRegex(adaptation.AdaptationError, 'adoption moved'):
            adaptation.check_binding(record, dict(bound, adoption='pending'))


class Trees(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.base = self.directory / 'base'
        self.worktree = self.directory / 'trial'
        for root in (self.base, self.worktree):
            (root / 'pkg').mkdir(parents=True)
            (root / 'pkg' / 'mod.py').write_text('VALUE = 1\n', encoding='utf-8')
            (root / 'pkg' / 'gone.py').write_text('OLD = True\n', encoding='utf-8')
            (root / 'pyproject.toml').write_text('[project]\nname = "x"\n', encoding='utf-8')
            (root / 'data').mkdir()
            (root / 'data' / 'output.jsonl').write_text('ignored\n', encoding='utf-8')
            (root / '__pycache__').mkdir()
            (root / '__pycache__' / 'x.pyc').write_bytes(b'\x00')

    def test_a_tree_identity_ignores_outputs_and_caches(self):
        files = trial.tree_files(self.base)
        self.assertEqual(files, ['pkg/gone.py', 'pkg/mod.py', 'pyproject.toml'])
        digest = trial.tree_digest(self.base)
        (self.base / 'data' / 'output.jsonl').write_text('changed\n', encoding='utf-8')
        self.assertEqual(trial.tree_digest(self.base), digest)
        (self.base / 'pkg' / 'mod.py').write_text('VALUE = 2\n', encoding='utf-8')
        self.assertNotEqual(trial.tree_digest(self.base), digest)

    def test_capture_records_added_modified_and_deleted_files_with_content(self):
        (self.worktree / 'pkg' / 'mod.py').write_text('VALUE = 2\n', encoding='utf-8')
        (self.worktree / 'pkg' / 'new.py').write_text('NEW = True\n', encoding='utf-8')
        (self.worktree / 'pkg' / 'gone.py').unlink()
        captured = trial.capture(self.base, self.worktree)
        by_path = {f['path']: f for f in captured['files']}
        self.assertEqual({p: f['status'] for p, f in by_path.items()},
                         {'pkg/mod.py': 'modified', 'pkg/new.py': 'added', 'pkg/gone.py': 'deleted'})
        self.assertEqual(by_path['pkg/mod.py']['content'], 'VALUE = 2\n')
        self.assertEqual(captured['base']['tree_sha256'], trial.tree_digest(self.base))
        self.assertEqual(captured['result_tree_sha256'], trial.tree_digest(self.worktree))
        self.assertTrue(captured['evaluator']['frozen'])
        self.assertEqual(captured['evaluator']['files'], ['pyproject.toml'])
        restored = self.directory / 'restored'
        shutil.copytree(self.base, restored)
        trial.apply_patch(captured['files'], restored)
        self.assertEqual(trial.tree_digest(restored), captured['result_tree_sha256'])

    def test_a_patch_that_touches_the_evaluator_set_is_flagged_and_not_frozen(self):
        (self.worktree / 'pyproject.toml').write_text('[project]\nname = "y"\n', encoding='utf-8')
        captured = trial.capture(self.base, self.worktree)
        self.assertFalse(captured['evaluator']['frozen'])
        inspection = trial.inspect(captured['files'], self.base)
        self.assertEqual(inspection['flags']['evaluator'], ['pyproject.toml'])
        self.assertEqual(inspection['flags']['dependencies'], ['pyproject.toml'])
        self.assertTrue(any('ordinary maintenance' in f for f in inspection['findings']))
        self.assertTrue(trial.in_evaluator_set('shopping_advisor/maintenance/baseline.json'))
        self.assertFalse(trial.in_evaluator_set('shopping_advisor/maintenance_notes.md'))


class StaticInspection(unittest.TestCase):
    def inspect(self, source, path='shopping_advisor/analysis/categories/new.py', base=None):
        files = [adaptation.file_entry(path, 'modified' if base else 'added', source.encode('utf-8'))]
        return trial.inspect(files, base)

    def test_a_quiet_module_is_not_flagged(self):
        source = ('"""Doc."""\nimport re\nfrom dataclasses import dataclass\n\nPATTERN = re.compile("x")\n'
                  'CLAIMS = ("a", "b")\n\n\ndef classify(record):\n    return PATTERN.search(record)\n')
        inspection = self.inspect(source)
        self.assertEqual({k: v for k, v in inspection['flags'].items() if v}, {})
        self.assertEqual(inspection['findings'], [])

    def test_network_process_and_write_reaching_code_is_named_by_line(self):
        source = ('import socket\nimport subprocess\nfrom pathlib import Path\n'
                  'from urllib import request\n\n\ndef go():\n    subprocess.run(["ls"])\n'
                  '    Path("x").write_text("y")\n    open("z", "w")\n    os.system("rm")\n')
        flags = self.inspect(source)['flags']
        self.assertEqual(len(flags['network']), 2)
        self.assertEqual(len(flags['subprocess']), 3)
        self.assertEqual(len(flags['file_writes']), 2)
        self.assertTrue(all(':' in item for item in flags['network'] + flags['subprocess']))

    def test_work_at_import_time_and_a_moved_version_constant_are_flagged(self):
        source = 'import os\nSETTINGS = os.environ.copy()\nprint("hello")\nSCHEMA_VERSION = 7\n'
        flags = self.inspect(source)['flags']
        self.assertEqual(len(flags['import_side_effects']), 2)
        with tempfile.TemporaryDirectory() as base:
            path = 'shopping_advisor/extraction/pdp.py'
            (pathlib.Path(base) / path).parent.mkdir(parents=True)
            (pathlib.Path(base) / path).write_text('SCHEMA_VERSION = 6\n', encoding='utf-8')
            flags = self.inspect('SCHEMA_VERSION = 7\n', path, base)['flags']
        self.assertEqual(flags['contracts'], [f'{path}: SCHEMA_VERSION = 7'])

    def test_a_file_that_does_not_parse_is_reported_not_imported(self):
        flags = self.inspect('def broken(:\n    pass\n')['flags']
        self.assertTrue(flags['import_side_effects'] and 'does not parse' in flags['import_side_effects'][0])


class Boundary(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.worktree = self.directory / 'tree'
        self.scratch = self.worktree / 'data' / 'scratch'
        self.outside = self.directory / 'outside'
        self.worktree.mkdir()

    def test_the_profile_denies_by_default_and_allows_exactly_the_declared_paths(self):
        text = trial.profile(self.worktree, self.scratch, INTERPRETER, VENV)
        self.assertIn('(deny default)', text)
        self.assertIn('(deny network*)', text)
        self.assertIn(f'(subpath "{self.scratch.resolve()}")', text)
        self.assertIn(str(VENV.resolve()), text)
        self.assertIn('tests/studies/', text)
        self.assertNotIn(str(pathlib.Path.home()) + '"', text.replace(str(VENV.resolve()), ''))

    def test_a_kernel_label_without_a_profile_is_refused(self):
        with self.assertRaisesRegex(trial.TrialError, 'label is a lie'):
            trial.execute(['true'], self.worktree, self.scratch, 5, None, boundary='kernel')

    @unittest.skipUnless(SANDBOXED, 'sandbox-exec is not available here: the kernel boundary is not '
                                    'demonstrated on this machine, and this says so rather than passing')
    def test_the_boundary_is_demonstrated_with_failure_cases(self):
        result = trial.probe(self.worktree, self.scratch, INTERPRETER, VENV, self.outside,
                             home=pathlib.Path.home())
        self.assertEqual(result['results'], trial.EXPECTED_PROBE)
        self.assertTrue(result['demonstrated'])
        self.assertFalse(result['leaked'])
        self.assertEqual(result['check']['boundary'], 'kernel')

    @unittest.skipUnless(SANDBOXED, 'sandbox-exec is not available here')
    def test_a_timeout_kills_the_whole_process_group_and_records_no_pass(self):
        self.scratch.mkdir(parents=True)
        profile_path = self.scratch / 'profile.sb'
        profile_path.write_text(trial.profile(self.worktree, self.scratch, INTERPRETER, VENV))
        script = self.scratch / 'hang.py'
        script.write_text('import subprocess, sys, time\n'
                          'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
                          'print("child", child.pid, flush=True)\ntime.sleep(60)\n', encoding='utf-8')
        started = time.monotonic()
        check = trial.execute([INTERPRETER, str(script)], self.worktree, self.scratch, 2,
                              profile_path, INTERPRETER)
        self.assertLess(time.monotonic() - started, 30)
        self.assertTrue(check['timed_out'])
        self.assertIsNone(check['exit'])
        self.assertIn('no pass', check['summary'])
        output = pathlib.Path(check['output_path']).read_text()
        child_pid = int(output.split()[1])
        deadline = time.monotonic() + 5
        while deadline > time.monotonic():
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.kill(child_pid, 9)
            self.fail('the child outlived the timeout: the process group was not killed')

    @unittest.skipUnless(SANDBOXED, 'sandbox-exec is not available here')
    def test_a_check_inside_the_boundary_records_exit_time_and_output(self):
        self.scratch.mkdir(parents=True)
        profile_path = self.scratch / 'profile.sb'
        profile_path.write_text(trial.profile(self.worktree, self.scratch, INTERPRETER, VENV))
        check = trial.execute([INTERPRETER, '-c', 'import tempfile; print(tempfile.gettempdir())'],
                              self.worktree, self.scratch, 30, profile_path, INTERPRETER)
        self.assertEqual(check['exit'], 0)
        self.assertEqual(check['boundary'], 'kernel')
        self.assertIn(str(self.scratch / 'tmp'), pathlib.Path(check['output_path']).read_text())


class LedgerV2(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.ledger = session.load(LEDGER_V2)

    def action(self, name, ledger=None):
        return next(a for a in (ledger or self.ledger)['actions'] if a['id'] == name)

    def test_the_fixture_is_a_v2_ledger_whose_engineering_is_authorisable(self):
        self.assertEqual(self.ledger['session_version'], 2)
        decision = session.authorise(self.ledger, 'engineer-1', AT)
        self.assertTrue(decision['authorised'], decision['reasons'])
        self.assertEqual(session.reconcile(self.ledger, AT)['proposals'], [])
        self.assertEqual([d['action'] for d in session.reconcile(self.ledger, AT)['permitted']], ['engineer-1'])

    def test_a_v1_ledger_keeps_refusing_to_execute_engineering(self):
        ledger = session.load(LEDGER_V1)
        self.assertFalse(session.executes(ledger))
        self.assertFalse(session.authorise(ledger, 'engineer-1', AT)['authorised'])
        ledger['session_version'] = 2
        ledger['limits'][2]['amount'] = 7200
        self.assertTrue(session.authorise(ledger, 'engineer-1', AT)['authorised'])

    def test_research_still_does_not_fund_engineering_under_v2(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('engineer-1', ledger)['limit_ids'] = ['research-seconds']
        with self.assertRaisesRegex(session.SessionError, 'does not fund engineering'):
            session.check(ledger)

    def test_engineering_is_recorded_from_its_adaptation_record(self):
        record = accepted_record()
        path = self.directory / 'record.json'
        path.write_text(json.dumps(record), encoding='utf-8')
        ledger = copy.deepcopy(self.ledger)
        self.action('engineer-1', ledger).update(state='authorised', authorisation='checked')
        session.record(ledger, 'engineer-1', adaptation_record=path)
        action = self.action('engineer-1', ledger)
        self.assertEqual((action['state'], action['consumption_source'], action['consumption']),
                         ('completed', 'adaptation_record', {'seconds': 1.5}))
        self.assertEqual(action['run_id'], 'fixture-1')
        self.assertEqual(action['run_manifest']['path'], str(path))
        row = next(r for r in session.reconcile(ledger, AT)['limits'] if r['id'] == 'engineering-seconds')
        self.assertEqual(row['consumed'], 1.5)

    def test_a_record_for_another_action_or_session_is_refused(self):
        other = accepted_record(action_id='engineer-9')
        path = self.directory / 'other.json'
        path.write_text(json.dumps(other), encoding='utf-8')
        with self.assertRaisesRegex(session.SessionError, 'not this action'):
            session.record(copy.deepcopy(self.ledger), 'engineer-1', adaptation_record=path)
        ledger = copy.deepcopy(self.ledger)
        self.action('analyse-1', ledger).update(state='planned', consumption={}, consumption_source='unknown',
                                                started_at='', finished_at='', authorisation='')
        with self.assertRaisesRegex(session.SessionError, 'engineering, nothing else'):
            session.record(ledger, 'analyse-1', adaptation_record=path)

    def test_a_record_links_only_a_finished_attempt_and_never_a_crawl_manifest(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('engineer-1', ledger)['run_manifest'] = {'path': 'x', 'sha256': 'e' * 64}
        with self.assertRaisesRegex(session.SessionError, 'when the attempt finished'):
            session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        self.action('engineer-1', ledger).update(state='completed', authorisation='checked', started_at=AT,
                                                 consumption={'seconds': 3}, consumption_source='run_manifest')
        with self.assertRaisesRegex(session.SessionError, 'not a crawl manifest'):
            session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        self.action('analyse-1', ledger)['consumption_source'] = 'adaptation_record'
        with self.assertRaisesRegex(session.SessionError, 'engineering, nothing else'):
            session.check(ledger)

    def test_the_version_is_discovered_and_pinned(self):
        from shopping_advisor import maintenance
        versions = maintenance._contract_versions()
        # v3 since 2026-09-19 (CONTRACT §16); the v2 fixtures here keep v2's rules.
        self.assertEqual(versions['session_ledger'], 3)
        self.assertEqual(versions['adaptation_record'], adaptation.ADAPTATION_VERSION)
        self.assertEqual(adaptation.ADAPTATION_VERSION, 2)


class StudyBinding(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.record = accepted_record()
        self.record_path = self.directory / 'record.json'
        self.record_path.write_text(json.dumps(self.record), encoding='utf-8')
        self.ledger = session.load(LEDGER_V2)
        self.ledger['actions'][1].update(state='authorised', authorisation='checked')
        session.record(self.ledger, 'engineer-1', adaptation_record=self.record_path)

    def run_study(self, name, **kwargs):
        return bundle.run(BRONZE, directory=self.directory / name, started_at=AT, finished_at=AT, **kwargs)

    def test_a_bound_study_carries_the_record_and_a_different_id_than_the_same_brief_unbound(self):
        plain, plain_manifest = self.run_study('plain')
        bound, manifest = self.run_study('bound', adaptation_record=self.record_path, session_ledger=self.ledger)
        self.assertEqual(plain_manifest['study_id'], 'pasta-bronze-die-bde2b027b117')
        self.assertNotEqual(manifest['study_id'], plain_manifest['study_id'])
        self.assertTrue((bound / adaptation.RECORD).is_file())
        self.assertEqual(manifest['adaptation'], adaptation.binding(self.record))
        self.assertEqual(manifest['artifacts'][adaptation.RECORD]['binding'], inventory.SEMANTIC)
        self.assertEqual(manifest['outcome'], plain_manifest['outcome'])
        _, findings = bundle.verify(bound)
        self.assertEqual(findings, [])
        self.assertTrue(any('adaptation fixture-1' in c for c in bundle.code_caveats(manifest)))

    def test_a_study_on_a_harness_only_record_says_so_wherever_the_bundle_is_read(self):
        path = self.directory / 'harness-only.json'
        path.write_text(json.dumps(harness_only_record()), encoding='utf-8')
        bound, manifest = self.run_study('harness', adaptation_record=path)
        self.assertEqual(manifest['adaptation']['boundary'], 'harness-only')
        caveats = bundle.code_caveats(manifest)
        self.assertTrue(any('harness-only boundary' in c and 'none of R15' in c for c in caveats), caveats)
        self.assertEqual(bundle.verify(bound)[1], [])
        # And a kernel-bound study of the same patch says nothing of the kind.
        _, kernel = self.run_study('kernel', adaptation_record=self.record_path)
        self.assertFalse(any('harness-only' in c for c in bundle.code_caveats(kernel)))
        # The label travels in the binding: upgrading it afterwards is a finding.
        manifest_path = bound / 'manifest.json'
        data = json.loads(manifest_path.read_text())
        data['adaptation']['boundary'] = 'kernel'
        manifest_path.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual([f['code'] for f in bundle.verify(bound)[1]], ['adaptation_invalid'])

    def test_the_same_inputs_under_another_method_are_another_study(self):
        other = accepted_record(content=b'# another method\n')
        path = self.directory / 'other.json'
        path.write_text(json.dumps(other), encoding='utf-8')
        _, first = self.run_study('first', adaptation_record=self.record_path)
        _, second = self.run_study('second', adaptation_record=path)
        self.assertNotEqual(first['study_id'], second['study_id'])

    def test_an_unadopted_record_runs_only_as_a_trial_and_says_so(self):
        pending = accepted_record()
        pending['adoption'] = {'decision': 'pending', 'decided': '', 'by': '', 'reason': ''}
        adaptation.seal(pending)
        path = self.directory / 'pending.json'
        path.write_text(json.dumps(pending), encoding='utf-8')
        with self.assertRaisesRegex(bundle.BundleError, 'not accepted'):
            self.run_study('refused', adaptation_record=path)
        _, manifest = self.run_study('trial', adaptation_record=path, trial=True)
        self.assertEqual(manifest['adaptation']['adoption'], 'pending')

    def test_a_record_that_accounts_against_an_absent_action_is_refused(self):
        ledger = session.load(LEDGER_V2)
        ledger['actions'] = [ledger['actions'][0]]
        with self.assertRaisesRegex(bundle.BundleError, 'does not hold'):
            self.run_study('orphan', adaptation_record=self.record_path, session_ledger=ledger)

    def test_a_tampered_or_renamed_record_fails_verify(self):
        bound, manifest = self.run_study('bound', adaptation_record=self.record_path)
        stored = json.loads((bound / adaptation.RECORD).read_text())
        stored['adoption']['reason'] = 'edited afterwards'
        (bound / adaptation.RECORD).write_text(json.dumps(stored), encoding='utf-8')
        _, findings = bundle.verify(bound)
        self.assertIn('artifact_altered', [f['code'] for f in findings])
        write_json_atomically(bound / adaptation.RECORD, self.record)
        manifest_path = bound / 'manifest.json'
        data = json.loads(manifest_path.read_text())
        data['adaptation']['adoption'] = 'pending'
        manifest_path.write_text(json.dumps(data), encoding='utf-8')
        _, findings = bundle.verify(bound)
        self.assertEqual([f['code'] for f in findings], ['adaptation_invalid'])
        self.assertIn('adoption moved', findings[0]['message'])

    def test_an_id_that_does_not_carry_the_method_is_a_finding(self):
        bound, manifest = self.run_study('bound', adaptation_record=self.record_path)
        manifest_path = bound / 'manifest.json'
        data = json.loads(manifest_path.read_text())
        data['study_id'] = 'pasta-bronze-die-bde2b027b117'
        manifest_path.write_text(json.dumps(data), encoding='utf-8')
        _, findings = bundle.verify(bound)
        self.assertIn('adaptation_invalid', [f['code'] for f in findings])
        self.assertTrue(any('does not re-derive' in f['message'] for f in findings))

    def test_a_reader_without_the_inventory_row_refuses_the_bundle_loudly(self):
        bound, _ = self.run_study('bound', adaptation_record=self.record_path)
        legacy = {k: v for k, v in inventory.BINDINGS.items() if k != adaptation.RECORD}
        optional = tuple(n for n in inventory.OPTIONAL if n != adaptation.RECORD)
        with mock.patch.dict(inventory.BINDINGS, legacy, clear=True), \
                mock.patch.object(inventory, 'OPTIONAL', optional):
            _, findings = bundle.verify(bound)
        codes = [f['code'] for f in findings]
        self.assertIn('artifact_undeclared', codes)
        self.assertTrue(any(adaptation.RECORD in f['message'] for f in findings))

    def test_a_record_made_for_another_plan_revision_is_not_bound_to_this_one(self):
        from shopping_advisor.study import intake
        plan = intake.load(HERE / 'intake' / 'supported-plan.json')
        record = adaptation.template('planned', 'category', 'h', 'pasta-adaptation-session', 'engineer-1',
                                     100, 1, plan=plan)
        record['origin']['plan_revision'] = plan['revision'] + 1
        adaptation.seal(record)
        path = self.directory / 'planned.json'
        path.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaisesRegex(bundle.BundleError, 'run this study with --plan'):
            self.run_study('noplan', adaptation_record=path, trial=True)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.base = self.directory / 'base'
        self.worktree = self.directory / 'trial'
        for root in (self.base, self.worktree):
            (root / 'pkg').mkdir(parents=True)
            (root / 'pkg' / 'mod.py').write_text('VALUE = 1\n', encoding='utf-8')
        (self.worktree / 'pkg' / 'new.py').write_text('NEW = 2\n', encoding='utf-8')
        self.ledger = self.directory / 'ledger.json'
        shutil.copy(LEDGER_V2, self.ledger)
        self.record = self.directory / 'record.json'

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def test_template_capture_review_adopt_and_check_through_the_commands(self):
        status, out = self.cli('session-authorise', self.ledger, 'engineer-1', '--record', '--reference', AT)
        self.assertEqual(status, 0, out)
        status, out = self.cli('adaptation-template', 'cli-1', '--session', self.ledger, '--action', 'engineer-1',
                               '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '1',
                               '-o', self.record)
        self.assertEqual(status, 0, out)
        status, out = self.cli('adaptation-capture', self.record, '--base', self.base, '--worktree', self.worktree)
        self.assertEqual(status, 0, out)
        self.assertIn('1 file(s)', out)
        record = adaptation.load(self.record)
        self.assertEqual(record['patch']['files'][0]['path'], 'pkg/new.py')
        record['checks'] = [passing_check()]
        record['attempts'] = 1
        record['consumption'] = {'seconds': 1.5, 'attempts': 1}
        record['runner'].update(boundary='kernel', profile_sha256='d' * 64, timeout_seconds=60)
        self.record.write_text(json.dumps(adaptation.seal(record)), encoding='utf-8')
        status, out = self.cli('adaptation-review', self.record, '--reviewer', 'r', '--verdict', 'pass',
                               '--finding', 'fine')
        self.assertEqual(status, 0, out)
        status, out = self.cli('adaptation-adopt', self.record, '--decision', 'accepted', '--by', 'maintainer',
                               '--reason', 'fixture')
        self.assertEqual(status, 0, out)
        status, out = self.cli('adaptation-adopt', self.record, '--decision', 'rejected', '--by', 'maintainer',
                               '--reason', 'again')
        self.assertEqual(status, 2)
        self.assertIn('recorded once', out)
        status, out = self.cli('session-record', self.ledger, 'engineer-1', '--adaptation', self.record)
        self.assertEqual(status, 0, out)
        self.assertIn('adaptation_record', out)
        status, out = self.cli('adaptation-check', self.record)
        self.assertEqual(status, 0)
        self.assertIn('adoption accepted', out)

    def test_a_patch_touching_the_evaluator_set_is_captured_and_refused(self):
        (self.worktree / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
        self.cli('adaptation-template', 'cli-2', '--session', self.ledger, '--action', 'engineer-1',
                 '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '1', '-o', self.record)
        status, out = self.cli('adaptation-capture', self.record, '--base', self.base, '--worktree', self.worktree)
        self.assertEqual(status, 1)
        self.assertIn('ordinary maintenance', out)
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch',
                               self.worktree / 'data' / 'scratch', '--', 'true')
        self.assertEqual(status, 2)
        self.assertIn('evaluator set', out)

    def test_a_template_needs_a_v2_ledger_and_an_engineering_action(self):
        status, out = self.cli('adaptation-template', 'cli-3', '--session', LEDGER_V1, '--action', 'engineer-1',
                               '--layer', 'method', '--hypothesis', 'h', '--seconds', '1', '--attempts', '1',
                               '-o', self.record)
        self.assertEqual(status, 2)
        self.assertIn('v1 ledger', out)
        status, out = self.cli('adaptation-template', 'cli-3', '--session', self.ledger, '--action', 'analyse-1',
                               '--layer', 'method', '--hypothesis', 'h', '--seconds', '1', '--attempts', '1',
                               '-o', self.record)
        self.assertEqual(status, 2)
        self.assertIn('not an engineering action', out)

    def test_run_needs_the_command_after_the_separator(self):
        self.cli('adaptation-template', 'cli-4', '--session', self.ledger, '--action', 'engineer-1',
                 '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '1', '-o', self.record)
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch',
                               self.worktree / 'data' / 'scratch')
        self.assertEqual(status, 2)
        self.assertIn('after `--`', out)

    def test_a_recorded_exception_runs_the_check_bare_and_labels_it_harness_only(self):
        """The path a container without sandbox-exec takes, and the only one it may take.

        No skip: this is the case the kernel tests above skip on. The check runs
        under the harness's isolation alone, the record says so in the check and
        in the runner, no profile digest is recorded, and the label follows the
        exception -- even on a machine where the profile is available.
        """
        self.cli('adaptation-template', 'cli-7', '--session', self.ledger, '--action', 'engineer-1',
                 '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '2', '-o', self.record)
        self.cli('adaptation-capture', self.record, '--base', self.base, '--worktree', self.worktree)
        scratch = self.worktree / 'data' / 'scratch'
        exception = 'maintainer message 2026-09-18: sandbox-exec exits 71 in this container'
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch', scratch,
                               '--venv', VENV, '--timeout', '60', '--exception', exception, '--',
                               sys.executable, '-c', 'import pkg.new; print(pkg.new.NEW)')
        self.assertEqual(status, 0, out)
        self.assertIn('harness-only', out)
        record = adaptation.load(self.record)
        check = record['checks'][0]
        self.assertEqual((record['attempts'], check['exit'], check['boundary']), (1, 0, 'harness-only'))
        self.assertEqual((record['runner']['boundary'], record['runner']['profile_sha256'],
                          record['runner']['exception']), ('harness-only', '', exception))
        self.assertFalse((scratch / 'profile.sb').exists())
        self.assertIn('2', pathlib.Path(check['output_path']).read_text())
        # Review, adopt, check: the exception is what lets the record stand.
        self.cli('adaptation-review', self.record, '--reviewer', 'r', '--verdict', 'pass', '--finding', 'ran bare')
        self.cli('adaptation-adopt', self.record, '--decision', 'accepted', '--by', 'repository maintainer',
                 '--reason', 'fixture')
        status, out = self.cli('adaptation-check', self.record)
        self.assertEqual(status, 0, out)
        self.assertIn('harness-only', out)

    @unittest.skipUnless(SANDBOXED, 'sandbox-exec is not available here')
    def test_a_check_runs_inside_the_boundary_counts_an_attempt_and_exhaustion_refuses_the_next(self):
        self.cli('adaptation-template', 'cli-5', '--session', self.ledger, '--action', 'engineer-1',
                 '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '1', '-o', self.record)
        self.cli('adaptation-capture', self.record, '--base', self.base, '--worktree', self.worktree)
        scratch = self.worktree / 'data' / 'scratch'
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch', scratch,
                               '--venv', VENV, '--timeout', '60', '--', INTERPRETER, '-c',
                               'import pkg.new; print(pkg.new.NEW)')
        self.assertEqual(status, 0, out)
        record = adaptation.load(self.record)
        self.assertEqual((record['attempts'], record['checks'][0]['exit'], record['runner']['boundary']),
                         (1, 0, 'kernel'))
        self.assertIn('2', pathlib.Path(record['checks'][0]['output_path']).read_text())
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch', scratch,
                               '--venv', VENV, '--', INTERPRETER, '-c', 'pass')
        self.assertEqual(status, 2)
        self.assertIn('exhaustion stops new work', out)

    @unittest.skipUnless(SANDBOXED, 'sandbox-exec is not available here')
    def test_a_rewritten_evaluator_in_the_worktree_is_refused_before_anything_runs(self):
        self.cli('adaptation-template', 'cli-6', '--session', self.ledger, '--action', 'engineer-1',
                 '--layer', 'method', '--hypothesis', 'h', '--seconds', '600', '--attempts', '2', '-o', self.record)
        self.cli('adaptation-capture', self.record, '--base', self.base, '--worktree', self.worktree)
        (self.worktree / 'pyproject.toml').write_text('# an always-passing gate would live here\n')
        status, out = self.cli('adaptation-run', self.record, '--worktree', self.worktree, '--scratch',
                               self.worktree / 'data' / 'scratch', '--venv', VENV, '--', INTERPRETER, '-c', 'pass')
        self.assertEqual(status, 2)
        self.assertIn('judges nothing', out)
        self.assertFalse(adaptation.load(self.record)['evaluator']['frozen'])

    def test_the_probe_command_reports_each_case(self):
        if not SANDBOXED:
            self.skipTest('sandbox-exec is not available here')
        status, out = self.cli('adaptation-probe', '--worktree', self.worktree, '--scratch',
                               self.worktree / 'data' / 'scratch', '--venv', VENV, '--outside',
                               self.directory / 'outside')
        self.assertEqual(status, 0, out)
        self.assertIn('[demonstrated]', out)
        self.assertIn('read_home', out)


class RunnerPaths(unittest.TestCase):
    """The second adaptation's first attempt exec'd a relative `.venv/bin/python`
    from the worktree, where none exists, and sandbox-exec exited 71 before any
    import. The CLI resolves both paths where the command was typed."""

    def test_a_relative_venv_is_resolved_before_the_working_directory_changes(self):
        from shopping_advisor.study.__main__ import _runner_paths
        with tempfile.TemporaryDirectory() as here:
            venv, interpreter = _runner_paths(os.path.join(here, '.venv'), '')
            self.assertTrue(os.path.isabs(venv) and os.path.isabs(interpreter))
            self.assertEqual(interpreter, os.path.join(venv, 'bin', 'python'))
            venv, interpreter = _runner_paths('.venv', 'python3')
            self.assertTrue(os.path.isabs(venv) and os.path.isabs(interpreter))
            self.assertTrue(interpreter.endswith('python3'))


if __name__ == '__main__':
    unittest.main()
