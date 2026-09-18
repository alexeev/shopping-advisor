"""The capability index, and the lifecycle declarations it is built from.

R16. Three things are guarded here and nowhere else:

* a category cannot register without saying what it has earned, and what it
  says is complete, well-formed and points at evidence the tree holds;
* the index is read from the live registry on every call -- there is no
  second list to fall out of step -- and its applicability claims are true
  of the committed case records: every marketplace a case names is one the
  category declares, and every ASIN a ``Decline`` cites still classifies as
  ``other``;
* the ``capabilities`` command and the index's marketplace comparison do what
  the runbook says they do, and refuse what they cannot answer.

What is *not* tested here is that a state is deserved. Whether one study is
enough to call a category maintained is a decision recorded in ROADMAP and
pinned by the gate's baseline (``test_maintenance.py``); this module checks
that the declaration and the evidence agree, not that the judgement was right.
"""

import contextlib
from dataclasses import replace
import gzip
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shopping_advisor.analysis import category  # noqa: E402
from shopping_advisor.analysis.category import (  # noqa: E402
    DECISIONS, STATES, Applicability, Decline, Lifecycle, is_match)
from shopping_advisor.maintenance import load_baseline  # noqa: E402
from shopping_advisor.study import capabilities  # noqa: E402
from shopping_advisor.study.__main__ import main  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def live(key):
    return category.get(key)


def with_lifecycle(key, **changes):
    """The live category with some of its lifecycle fields replaced."""
    original = live(key)
    return replace(original, lifecycle=replace(original.lifecycle, **changes))


class Declarations(unittest.TestCase):
    """Every registered category says what it has earned, completely."""

    def test_every_registered_category_declares_a_complete_lifecycle(self):
        for key in category.known():
            with self.subTest(category=key):
                lifecycle = live(key).lifecycle
                self.assertIsInstance(lifecycle, Lifecycle)
                self.assertIn(lifecycle.state, STATES)
                self.assertIn(lifecycle.decision, DECISIONS)
                self.assertEqual(capabilities.problems(live(key), ROOT), [])

    def test_registering_without_a_lifecycle_refuses(self):
        probe = replace(live('dry_pasta'), key='probe_category', lifecycle=None)
        with patch.dict(category.REGISTRY):
            with self.assertRaises(TypeError) as caught:
                category.register(probe)
            self.assertNotIn('probe_category', category.REGISTRY)
        self.assertIn('Lifecycle', str(caught.exception))

    def test_a_defective_declaration_names_its_field(self):
        cases = {
            'state': dict(state='mature'),
            'decision': dict(decision='kept'),
            'decided': dict(decided='yesterday'),
            'reviewed': dict(reviewed='2026-13-45'),
            'maintainer': dict(maintainer='  '),
            'method_version': dict(method_version=0),
            'evidence': dict(evidence=('tests/cases/nowhere.jsonl.gz',)),
            'milestones': dict(milestones=()),
            'review': dict(review='#not-an-anchor'),
            'applicability.marketplaces': dict(applicability=Applicability(
                marketplaces=(), accepts='something')),
            'applicability.accepts': dict(applicability=Applicability(
                marketplaces=('www.amazon.de',), accepts='')),
            'applicability.declines': dict(applicability=Applicability(
                marketplaces=('www.amazon.de',), accepts='x',
                declines=(Decline('', ()),))),
        }
        for field, changes in cases.items():
            with self.subTest(field=field):
                found = capabilities.problems(
                    with_lifecycle('dry_pasta', **changes), ROOT)
                self.assertEqual([name for name, _ in found], [field], found)

    def test_an_absolute_evidence_path_is_a_defect_even_when_it_exists(self):
        absolute = str(ROOT / 'tests' / 'cases' / 'pasta_v1.jsonl.gz')
        found = capabilities.problems(
            with_lifecycle('dry_pasta', evidence=(absolute,)), ROOT)
        self.assertEqual([name for name, _ in found], ['evidence'])
        self.assertIn('absolute path', found[0][1])

    def test_a_missing_lifecycle_is_the_only_problem_reported(self):
        bare = replace(live('dry_pasta'), lifecycle=None)
        self.assertEqual(capabilities.problems(bare, ROOT),
                         [('lifecycle', 'no Lifecycle is declared')])


class ApplicabilityIsMeasured(unittest.TestCase):
    """What a category says it declines, its committed cases prove."""

    def cases(self, lifecycle):
        for path in lifecycle.evidence:
            if path.startswith('tests/cases/') and path.endswith('.jsonl.gz'):
                with gzip.open(ROOT / path, 'rt', encoding='utf-8') as handle:
                    return {record['asin']: record
                            for record in map(json.loads, handle)}
        return {}

    def test_every_case_marketplace_is_a_declared_one(self):
        for key in category.known():
            with self.subTest(category=key):
                lifecycle = live(key).lifecycle
                seen = {record.get('marketplace')
                        for record in self.cases(lifecycle).values()}
                self.assertLessEqual(
                    seen, set(lifecycle.applicability.marketplaces),
                    'a case names a marketplace the category does not declare')

    def test_every_cited_decline_still_classifies_as_other(self):
        for key in category.known():
            found = live(key)
            records = self.cases(found.lifecycle)
            for decline in found.lifecycle.applicability.declines:
                if decline.asins:
                    self.assertTrue(records, f'{key}: {decline.label} cites '
                                             f'ASINs but names no case feed')
                for asin in decline.asins:
                    with self.subTest(category=key, asin=asin):
                        self.assertIn(asin, records)
                        card = found.evaluate(records[asin])
                        self.assertFalse(is_match(card))
                        self.assertEqual(card['category'].value, 'other')

    def test_a_case_feed_backs_every_category_that_cites_one(self):
        # The one category without an acquired record set says so in its own
        # declaration rather than citing declines it cannot prove.
        for key in category.known():
            lifecycle = live(key).lifecycle
            if not self.cases(lifecycle):
                with self.subTest(category=key):
                    self.assertTrue(
                        any('no committed acquired record set' in item
                            for item in lifecycle.applicability.not_established),
                        f'{key} has no case feed and does not say so')
                    for decline in lifecycle.applicability.declines:
                        self.assertEqual(decline.asins, ())


class Index(unittest.TestCase):
    """Read from the live registry, one row per capability."""

    def setUp(self):
        self.examples = load_baseline()['examples']

    def test_one_row_per_registered_category_in_registry_order(self):
        data = capabilities.index(examples=self.examples, root=ROOT)
        self.assertEqual([row['key'] for row in data['capabilities']],
                         category.known())
        self.assertEqual(data['kinds'], ['category'])
        self.assertEqual(data['states'], list(STATES))
        for row in data['capabilities']:
            with self.subTest(category=row['key']):
                found = live(row['key'])
                self.assertEqual(row['module'], found.evaluate.__module__)
                self.assertEqual(row['axes'], list(found.axis_keys))
                self.assertEqual(row['claims'], list(found.claim_keys))
                self.assertEqual(row['state'], found.lifecycle.state)
                self.assertTrue(all(item['present'] for item in row['evidence']),
                                row['evidence'])
                self.assertNotIn('marketplace', row)

    def test_rows_track_registry_changes_without_a_parallel_list(self):
        changed = replace(
            with_lifecycle('dry_pasta', state=category.RETIRED,
                           decision='retired'),
            axes=(category.Axis('new_axis', 'New', better='higher'),),
            default_axis='new_axis')
        with patch.dict(category.REGISTRY, dry_pasta=changed):
            row = capabilities.index('dry_pasta', root=ROOT)['capabilities'][0]
        self.assertEqual(row['axes'], ['new_axis'])
        self.assertEqual((row['state'], row['decision']), ('retired', 'retired'))

    def test_the_committed_studies_are_listed_on_the_category_they_name(self):
        data = capabilities.index(examples=self.examples, root=ROOT)
        studies = {row['key']: row['studies'] for row in data['capabilities']}
        self.assertEqual(
            sorted(study['name'] for study in studies['dry_pasta']),
            ['pasta-bronze-die', 'pasta-delivered-cost',
             'pasta-low-temperature-drying', 'pasta-purchase-budget'])
        self.assertEqual(sorted(study['name'] for study in studies['basmati_rice']),
                         ['t3-insufficient', 't3-positive'])
        # Two of four categories have no committed replayable study. The index
        # says so by listing none; the architectural review records the debt.
        self.assertEqual(studies['tyre_mounting_paste'], [])
        self.assertEqual(studies['school_backpack'], [])
        bronze = next(study for study in studies['dry_pasta']
                      if study['name'] == 'pasta-bronze-die')
        self.assertEqual(bronze['study_id'], 'pasta-bronze-die-bde2b027b117')
        self.assertEqual(bronze['outcome'], 'recommendation')

    def test_an_unknown_capability_refuses(self):
        with self.assertRaises(capabilities.CapabilityError):
            capabilities.index('shopping_advisor.analysis.categories.dry_pasta',
                               root=ROOT)

    def test_the_marketplace_comparison_is_by_host_and_says_why(self):
        for host in ('www.amazon.de', 'amazon.de', 'https://www.amazon.de/'):
            with self.subTest(host=host):
                data = capabilities.index(marketplace=host, root=ROOT)
                self.assertTrue(all(row['marketplace']['applies']
                                    for row in data['capabilities']))
        data = capabilities.index(marketplace='www.amazon.com', root=ROOT)
        for row in data['capabilities']:
            with self.subTest(category=row['key']):
                self.assertFalse(row['marketplace']['applies'])
                self.assertIn('www.amazon.de', row['marketplace']['reason'])
                self.assertIn('nothing here was validated',
                              row['marketplace']['reason'])
        self.assertFalse(capabilities.applies(live('dry_pasta').lifecycle, ''))

    def test_the_index_is_json_and_carries_its_limits(self):
        data = capabilities.index(examples=self.examples, root=ROOT)
        json.dumps(data)
        self.assertTrue(any('not trust' in limit for limit in data['limits']))
        self.assertTrue(any('R15' in limit for limit in data['limits']))


class CommandLine(unittest.TestCase):

    def run_study(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(buffer):
            status = main(list(argv))
        return status, buffer.getvalue()

    def test_capabilities_prints_the_whole_index(self):
        status, output = self.run_study('capabilities')
        self.assertEqual(status, 0, output)
        data = json.loads(output)
        self.assertEqual([row['key'] for row in data['capabilities']],
                         category.known())

    def test_one_category_and_a_marketplace(self):
        status, output = self.run_study('capabilities', '--category',
                                        'school_backpack', '--marketplace',
                                        'www.amazon.com')
        self.assertEqual(status, 0, output)
        rows = json.loads(output)['capabilities']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['state'], 'experiment')
        self.assertFalse(rows[0]['marketplace']['applies'])

    def test_an_unknown_category_exits_two(self):
        status, output = self.run_study('capabilities', '--category',
                                        'no_such_category')
        self.assertEqual(status, 2)
        self.assertIn('unknown category', output)


if __name__ == '__main__':
    unittest.main()
