"""The maintenance gate, and the part of it that resists being weakened.

These tests never invoke the ``tests`` check against this repository's own
suite: the gate runs that suite, and this module is in it. They use small
synthetic trees instead, which is also the only way to assert what the gate
does when a test module disappears.
"""

import json
import sys
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shopping_advisor import maintenance                       # noqa: E402
from shopping_advisor.maintenance import __main__ as gate_cli  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def codes(findings):
    return sorted(finding.code for finding in findings)


class TrackedBaseline(unittest.TestCase):
    """The committed baseline is the gate's authority; it has to be honest."""

    def setUp(self):
        self.baseline = maintenance.load_baseline()

    def test_every_implemented_check_is_required(self):
        # The quiet failure mode: the code still checks something, and the
        # baseline stopped asking for it.
        self.assertEqual(sorted(self.baseline['checks']),
                         sorted(maintenance.CHECKS))

    def test_the_committed_baseline_passes_its_own_guard(self):
        self.assertEqual(maintenance._guard(self.baseline,
                                            maintenance.CHECKS), [])

    def test_declared_examples_and_documents_exist(self):
        for example in self.baseline['examples']:
            for key in ('brief', 'evidence', 'review'):
                if example.get(key):
                    self.assertTrue((ROOT / example[key]).is_file(),
                                    f'{example["name"]}: missing {key}')
        for name in self.baseline['documentation']:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_recorded_contracts_are_the_published_ones(self):
        self.assertEqual(self.baseline['contracts'],
                         maintenance._contract_versions())


class Guard(unittest.TestCase):
    """What the gate says when the baseline itself is the thing that moved."""

    def test_a_required_check_nobody_implements_is_a_finding(self):
        findings = maintenance._guard({'checks': ['docs', 'invented']},
                                      {'docs': None})
        self.assertEqual(codes(findings), ['unknown_check'])

    def test_dropping_a_check_from_the_baseline_is_a_finding(self):
        findings = maintenance._guard({'checks': ['docs']},
                                      {'docs': None, 'tests': None})
        self.assertEqual(codes(findings), ['check_not_required'])
        self.assertIn('tests', findings[0].message)

    def test_an_empty_check_list_establishes_nothing(self):
        findings = maintenance._guard({'checks': []}, {'docs': None})
        self.assertEqual(codes(findings), ['no_required_checks'])


class BaselineFile(unittest.TestCase):

    def write(self, payload):
        path = Path(self.enterContext(
            __import__('tempfile').TemporaryDirectory())) / 'baseline.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    def test_a_missing_baseline_is_not_a_failed_check(self):
        with self.assertRaises(maintenance.GateError) as caught:
            maintenance.load_baseline(ROOT / 'no-such-baseline.json')
        self.assertIn('restore it from Git', str(caught.exception))

    def test_an_unsupported_baseline_version_refuses_to_be_reinterpreted(self):
        path = self.write({'baseline_version': 99})
        with self.assertRaises(maintenance.GateError) as caught:
            maintenance.load_baseline(path)
        self.assertIn('baseline_version', str(caught.exception))

    def test_a_removed_section_is_a_removed_check(self):
        payload = dict(maintenance.load_baseline())
        del payload['tests']
        with self.assertRaises(maintenance.GateError) as caught:
            maintenance.load_baseline(self.write(payload))
        self.assertIn("no 'tests' section", str(caught.exception))


class Contracts(unittest.TestCase):

    def test_a_silent_version_bump_fails(self):
        declared = dict(maintenance._contract_versions())
        declared['extraction_schema'] -= 1
        result = maintenance.check_contracts({'contracts': declared})
        self.assertEqual(codes(result.findings), ['contract_version'])
        self.assertIn('CONTRACT.md', result.findings[0].message)

    def test_an_untracked_published_version_fails(self):
        declared = dict(maintenance._contract_versions())
        del declared['evidence_ledger']
        result = maintenance.check_contracts({'contracts': declared})
        self.assertEqual(codes(result.findings), ['contract_untracked'])

    def test_the_published_versions_pass(self):
        result = maintenance.check_contracts(
            {'contracts': maintenance._contract_versions()})
        self.assertTrue(result.passed, result.findings)


class Categories(unittest.TestCase):

    def test_a_lost_category_fails_and_a_new_one_does_not(self):
        lost = maintenance.check_categories({'categories': ['no_such_thing']})
        self.assertEqual(codes(lost.findings), ['category_missing'])
        kept = maintenance.check_categories({'categories': ['dry_pasta']})
        self.assertTrue(kept.passed, kept.findings)
        self.assertIn('new:', kept.summary)


class Tests(unittest.TestCase):
    """The suite check, exercised against a synthetic suite, never our own."""

    def setUp(self):
        import tempfile
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / 'tests').mkdir()
        # Discovery puts its start directory on the path and leaves the
        # probe modules imported; neither belongs to the rest of the suite.
        self.addCleanup(sys.path.__setitem__, slice(None), list(sys.path))
        for name in ('test_gate_probe_one', 'test_gate_probe_two'):
            self.addCleanup(sys.modules.pop, name, None)

    def write(self, name, body):
        (self.root / 'tests' / f'{name}.py').write_text(
            textwrap.dedent(body), encoding='utf-8')

    def baseline(self, **tests):
        return {'tests': {'minimum': 0, 'modules': [], **tests}}

    def test_a_deleted_test_module_fails_even_when_the_rest_is_green(self):
        self.write('test_gate_probe_one', '''
            import unittest

            class Kept(unittest.TestCase):
                def test_one(self): pass
                def test_two(self): pass
        ''')
        result = maintenance.check_tests(
            self.baseline(minimum=2,
                          modules=['test_gate_probe_one',
                                   'test_gate_probe_two']),
            root=self.root)
        self.assertEqual(codes(result.findings), ['test_module_missing'])
        self.assertIn('test_gate_probe_two', result.findings[0].message)

    def test_a_lowered_test_count_fails_against_the_recorded_floor(self):
        self.write('test_gate_probe_one', '''
            import unittest

            class Kept(unittest.TestCase):
                def test_one(self): pass
        ''')
        result = maintenance.check_tests(self.baseline(minimum=5),
                                         root=self.root)
        self.assertEqual(codes(result.findings), ['test_count'])
        self.assertIn('4 test(s) disappeared', result.findings[0].message)

    def test_a_failing_test_is_reported_with_its_traceback(self):
        self.write('test_gate_probe_one', '''
            import unittest

            class Broken(unittest.TestCase):
                def test_one(self):
                    self.assertEqual(1, 2)
        ''')
        result = maintenance.check_tests(self.baseline(), root=self.root)
        self.assertEqual(codes(result.findings), ['test_failed'])
        self.assertIn('AssertionError', result.findings[0].message)

    def test_a_green_suite_at_its_floor_passes_and_reports_its_measure(self):
        self.write('test_gate_probe_one', '''
            import unittest

            class Kept(unittest.TestCase):
                def test_one(self): pass
                def test_two(self): pass
        ''')
        result = maintenance.check_tests(self.baseline(minimum=2),
                                         root=self.root)
        self.assertTrue(result.passed, result.findings)
        self.assertEqual(result.observed['minimum'], 2)


class Docs(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body).lstrip(), encoding='utf-8')

    def check(self, *names):
        return maintenance.check_docs({'documentation': list(names)},
                                      root=self.root)

    def test_live_links_and_anchors_pass(self):
        self.write('A.md', '''
            # Title
            See [B](B.md#a-second-heading--with-punctuation) and
            [back](#title).
            An [external](https://example.org/nowhere) link is not ours.
        ''')
        self.write('B.md', '''
            # B
            ## A second heading — with punctuation
        ''')
        result = self.check('A.md', 'B.md')
        self.assertTrue(result.passed, result.findings)
        self.assertIn('2 local links', result.summary)

    def test_a_dead_file_and_a_dead_anchor_are_separate_findings(self):
        self.write('A.md', '''
            # Title
            [gone](missing.md) and [wrong](B.md#no-such-heading)
        ''')
        self.write('B.md', '# B\n')
        self.assertEqual(codes(self.check('A.md', 'B.md').findings),
                         ['dead_anchor', 'dead_link'])

    def test_commands_inside_a_fence_are_not_links(self):
        self.write('A.md', '''
            # Title

            ```text
            run --input [notalink](nowhere.md)
            ```
            ''')
        result = self.check('A.md')
        self.assertTrue(result.passed, result.findings)
        self.assertIn('0 local links', result.summary)

    def test_a_document_removed_from_the_tree_is_a_finding(self):
        self.assertEqual(codes(self.check('Absent.md').findings),
                         ['document_missing'])

    def test_the_anchor_slug_matches_the_repositorys_own_headings(self):
        self.assertEqual(
            maintenance.slug('Product vision — the shopping conversation'),
            'product-vision--the-shopping-conversation')
        self.assertEqual(maintenance.slug('8. Study audit contracts (T3)'),
                         '8-study-audit-contracts-t3')
        self.assertEqual(maintenance.slug('A `code` **span**'),
                         'a-code-span')


class Examples(unittest.TestCase):
    """One committed example, replayed through the documented commands."""

    BRONZE = {'name': 'pasta-bronze-die',
              'brief': 'tests/studies/pasta-bronze-die.toml'}

    def recorded(self):
        for example in maintenance.load_baseline()['examples']:
            if example['name'] == self.BRONZE['name']:
                return example
        raise AssertionError('the bronze-die example left the baseline')

    def test_the_recorded_decisions_still_reproduce(self):
        result = maintenance.check_examples({'examples': [self.recorded()]})
        self.assertTrue(result.passed, result.findings)

    def test_a_moved_decision_is_a_finding_naming_the_field(self):
        moved = dict(self.recorded(),
                     expect={'shortlisted': 99, 'outcome': 'recommendation'})
        result = maintenance.check_examples({'examples': [moved]})
        self.assertEqual(codes(result.findings), ['example_decision_changed'])
        self.assertIn('shortlisted', result.findings[0].message)

    def test_an_unusable_brief_fails_the_command_rather_than_the_gate(self):
        result = maintenance.check_examples(
            {'examples': [{'name': 'absent', 'brief': 'tests/studies/no.toml',
                           'expect': {}}]})
        self.assertEqual(codes(result.findings), ['example_command_failed'])


class CommandLine(unittest.TestCase):

    def run_gate(self, *argv):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(buffer):
            status = gate_cli.main(list(argv))
        return status, buffer.getvalue()

    def test_a_partial_run_says_it_is_not_the_gate(self):
        status, output = self.run_gate('check', '--only', 'contracts')
        self.assertEqual(status, 0)
        self.assertIn('partial run: not the gate', output)

    def test_an_unknown_check_cannot_be_asked_for(self):
        status, output = self.run_gate('check', '--only', 'invented')
        self.assertEqual(status, 2)
        self.assertIn('unknown check', output)

    def test_json_output_carries_the_findings_agents_act_on(self):
        status, output = self.run_gate('check', '--only', 'contracts',
                                       '--json')
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(payload['gate'], 'partial')
        self.assertTrue(payload['passed'])
        self.assertEqual([check['name'] for check in payload['checks']],
                         ['contracts'])

    def test_baseline_prints_the_tracked_floors(self):
        status, output = self.run_gate('baseline')
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)['baseline_version'],
                         maintenance.BASELINE_VERSION)

    def test_update_refuses_to_record_a_tree_that_does_not_pass(self):
        import tempfile
        payload = dict(maintenance.load_baseline())
        payload['checks'] = ['contracts']
        payload['contracts'] = dict(payload['contracts'])
        payload['contracts']['extraction_schema'] += 1
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        path = directory / 'baseline.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        before = path.read_bytes()
        status, output = self.run_gate('--baseline', str(path), 'baseline',
                                       '--update')
        self.assertEqual(status, 1)
        self.assertIn('The baseline is unchanged', output)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
