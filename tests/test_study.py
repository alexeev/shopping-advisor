"""Tests for the saved study: the brief, the decisions, and the replay.

What these guard is not the analysis -- ``test_analysis.py`` and
``test_validation.py`` already own that -- but the three properties a study
bundle claims and a command line cannot:

* the same brief over the same bytes decides the same way, anywhere;
* every candidate considered is recorded with the reason for its fate, and
  a refusal is one of the recorded outcomes rather than an empty result;
* a brief, a bundle, an input or a version that is wrong is *reported* as
  wrong, in a sentence that says what to change.

The committed briefs under ``studies/`` are the worked examples the runbook
points at, so they are asserted here down to the ASINs: a study whose numbers
drift silently is exactly the thing the bundle exists to prevent.
"""

import gzip
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from shopping_advisor.analysis import report  # noqa: E402
from shopping_advisor.study import bundle, brief as brief_module  # noqa: E402
from shopping_advisor.study.analysis import (  # noqa: E402
    EXCLUDED, FILTERED_OUT, INSUFFICIENT_EVIDENCE, NOT_CATEGORY,
    RECOMMENDATION, SHORTLISTED, StudyError, analyse)

HERE = pathlib.Path(__file__).resolve().parent
STUDIES = HERE / 'studies'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
DRYING = STUDIES / 'pasta-low-temperature-drying.toml'


def rewrite(source, replacements, directory):
    """A copy of a committed brief with lines replaced, beside the cases.

    The feeds a brief names are relative to the brief, so a variant has to
    live where the original does -- which is also the property being relied
    on when a bundle is replayed somewhere else.
    """
    text = source.read_text(encoding='utf-8')
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new, 1)
    path = STUDIES / f'.tmp-{directory}-{source.name}'
    path.write_text(text, encoding='utf-8')
    return path


class Temporary(unittest.TestCase):
    """A scratch directory, and briefs written beside the real case feeds."""

    def setUp(self):
        self.temporary = tempfile.mkdtemp(prefix='study-test-')
        self.addCleanup(shutil.rmtree, self.temporary, ignore_errors=True)
        # A brief's feeds are relative to the brief, so a variant of a
        # committed one has to sit beside it -- which is the same property a
        # bundle relies on when it is replayed somewhere else.
        self.scratch = pathlib.Path(self.temporary).name
        self.addCleanup(self.sweep)

    def sweep(self):
        for path in STUDIES.glob(f'.tmp-{self.scratch}-*'):
            path.unlink()

    def out(self, name='bundle'):
        return pathlib.Path(self.temporary) / name


class BriefValidation(Temporary):
    """A brief that is wrong has to say which line to change."""

    def refuses(self, replacements, expected):
        path = rewrite(BRONZE, replacements, self.scratch)
        with self.assertRaises(brief_module.BriefError) as caught:
            brief_module.load(path)
        self.assertIn(expected, str(caught.exception))

    def test_the_committed_briefs_are_valid(self):
        for path in (BRONZE, DRYING):
            loaded = brief_module.load(path)
            self.assertEqual(loaded.category, 'dry_pasta')
            self.assertEqual(loaded.marketplace, 'www.amazon.de')

    def test_an_unsupported_version_is_refused_rather_than_read_partly(self):
        self.refuses([('brief_version = 1', 'brief_version = 2')],
                     'is not supported; this build reads version 1')

    def test_an_unknown_category_lists_the_ones_that_exist(self):
        self.refuses([('category = "dry_pasta"', 'category = "vacuum_cleaner"')],
                     'unknown category. Known: basmati_rice, dry_pasta')

    def test_a_category_named_by_import_path_is_refused(self):
        """A brief selects among things this repository already reviewed. It
        is data, and the only power it has is to name a registry key."""
        self.refuses([('category = "dry_pasta"',
                       'category = "shopping_advisor.analysis'
                       '.categories.dry_pasta"')],
                     'A category is named by its key, never by an import path')

    def test_an_axis_the_category_does_not_have_names_the_ones_it_does(self):
        self.refuses([('axis = "price_per_base"', 'axis = "flavour"')],
                     'Known: price_per_base, quantity, raw_materials')

    def test_a_required_claim_the_category_cannot_find_is_refused(self):
        self.refuses([('require_claims = ["bronze_die"]',
                       'require_claims = ["organic"]')],
                     'not a claim of dry pasta')

    def test_an_id_that_is_not_a_slug_is_refused(self):
        """It becomes a directory name, so it is checked as one."""
        self.refuses([('id = "pasta-bronze-die"', 'id = "../escape"')],
                     'must be a slug')

    def test_a_missing_input_says_where_it_looked(self):
        self.refuses([('inputs = ["../cases/pasta_v1.jsonl.gz"]',
                       'inputs = ["nope.jsonl.gz"]')],
                     'Feed paths are relative to the brief')

    def test_a_typo_in_a_constraint_is_not_silently_ignored(self):
        """The failure this rejects is the quiet one: a misspelt constraint
        that does nothing produces a study with no sign anything was asked."""
        self.refuses([('shortlist = 3', 'shortlst = 3')],
                     'has no key shortlst')

    def test_a_freshness_policy_without_a_reference_date_is_refused(self):
        self.refuses([('as_of = "2026-09-16"\n', '')],
                     'would make the same study decide differently tomorrow')

    def test_defaults_are_recorded_not_left_implied(self):
        """What the brief did not say is part of what the study decided."""
        path = rewrite(BRONZE, [('axis = "price_per_base"\n', ''),
                                ('unit = "EUR/kg"\n', '')], self.scratch)
        result, _cards = analyse(brief_module.load(path))
        self.assertEqual(result['constraints']['axis']['source'],
                         'category_default')
        self.assertEqual(result['constraints']['axis']['key'],
                         'price_per_base')
        self.assertEqual(result['constraints']['unit']['source'], 'measured')


class TheWorkedExample(Temporary):
    """The bronze-die study, asserted to its numbers."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.cards = analyse(brief_module.load(BRONZE))

    def decisions(self, decision):
        return [entry['asin'] for entry in self.result['candidates']
                if entry['decision'] == decision]

    def test_it_recommends_the_cheapest_bronze_die_kilogram(self):
        self.assertEqual(self.result['outcome']['code'], RECOMMENDATION)
        self.assertEqual(self.result['shortlist'],
                         ['B0DQ2N5HRW', 'B08WJGD5Z5', 'B08BNQ2D54'])
        best = next(claim for claim in self.result['claims']
                    if claim['id'] == 'best_value')
        self.assertEqual(best['asin'], 'B0DQ2N5HRW')
        self.assertAlmostEqual(best['value'], 2.96, places=2)
        self.assertEqual(best['unit'], 'EUR/kg')

    def test_every_record_considered_has_a_recorded_fate(self):
        """Not the first twenty rows and ten exclusions a terminal shows."""
        self.assertEqual(len(self.result['candidates']), 25)
        self.assertEqual(len(self.decisions(SHORTLISTED)), 3)
        self.assertEqual(len(self.decisions(FILTERED_OUT)), 14)
        self.assertEqual(len(self.decisions(EXCLUDED)), 3)
        self.assertEqual(len(self.decisions(NOT_CATEGORY)), 3)

    def test_a_disputed_pack_size_is_excluded_with_its_reason(self):
        excluded = {entry['asin']: entry for entry in self.result['candidates']
                    if entry['decision'] == EXCLUDED}
        self.assertIn('B0173KFFIG', excluded)
        self.assertEqual(excluded['B0173KFFIG']['reason_code'], 'not_usable')
        self.assertIn('counts pieces rather than content',
                      excluded['B0173KFFIG']['reason'])

    def test_a_requirement_removes_a_record_visibly_not_silently(self):
        """`rank --require` drops these without a word; a study may not."""
        filtered = {entry['asin']: entry for entry in self.result['candidates']
                    if entry['decision'] == FILTERED_OUT}
        self.assertIn('B0CT3Q17FP', filtered,
                      'the cheapest pasta overall does not state bronze-die '
                      'and its absence has to be visible')
        self.assertIn('bronze_die', filtered['B0CT3Q17FP']['reason'])

    def test_the_brief_stated_the_axis_and_the_report_says_so(self):
        constraints = self.result['constraints']
        self.assertEqual(constraints['axis']['source'], 'brief')
        self.assertEqual(constraints['unit']['source'], 'brief')

    def test_freshness_is_measured_against_the_brief_not_against_today(self):
        freshness = self.result['freshness']
        self.assertTrue(freshness['assessed'])
        self.assertEqual(freshness['as_of'], '2026-09-16')
        self.assertEqual(freshness['oldest_ranked_days'], 2)
        self.assertEqual(freshness['stale_ranked'], 0)


class TheRefusal(Temporary):
    """The same evidence, a requirement two listings meet, and no answer."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.cards = analyse(brief_module.load(DRYING))

    def test_it_refuses_rather_than_ranking_a_disputed_value(self):
        self.assertEqual(self.result['outcome']['code'], INSUFFICIENT_EVIDENCE)
        self.assertEqual(self.result['shortlist'], [])
        self.assertEqual(self.result['outcome']['reason_code'], 'unit_absent')

    def test_the_two_listings_that_do_state_it_are_named_with_their_reason(self):
        """The refusal is specific: the requirement is met and the *axis* is
        not. An empty result would have said neither."""
        excluded = {entry['asin']: entry['reason']
                    for entry in self.result['candidates']
                    if entry['decision'] == EXCLUDED}
        self.assertEqual(sorted(excluded), ['B0173KFFIG', 'B0C5XK2QFR'])
        for reason in excluded.values():
            self.assertIn('counts pieces rather than content', reason)

    def test_the_refusal_still_accounts_for_every_record(self):
        self.assertEqual(len(self.result['candidates']), 25)

    def test_a_shortfall_of_candidates_is_a_stated_criterion(self):
        """`minimum_candidates` is declared in the brief before the data is
        seen, so "not enough to choose" is met rather than improvised."""
        path = rewrite(BRONZE, [('minimum_candidates = 3',
                                 'minimum_candidates = 9')], self.scratch)
        result, _cards = analyse(brief_module.load(path))
        self.assertEqual(result['outcome']['code'], INSUFFICIENT_EVIDENCE)
        self.assertEqual(result['outcome']['reason_code'],
                         'too_few_candidates')
        self.assertEqual(result['shortlist'], [])

    def test_two_candidates_too_close_together_produce_no_winner(self):
        path = rewrite(BRONZE, [('decisive_margin = 0.05',
                                 'decisive_margin = 0.2')], self.scratch)
        result, _cards = analyse(brief_module.load(path))
        self.assertEqual(result['outcome']['code'], 'no_decisive_winner')
        self.assertIn('9.1%', result['outcome']['statement'])
        self.assertEqual(len(result['shortlist']), 3,
                         'a shortlist is still offered; only the winner is not')

    def test_a_brief_that_asks_for_an_absent_unit_is_an_error_not_a_finding(self):
        """"Every value is in EUR/kg and the brief says EUR/100g" is a typo.
        Filing it as insufficient evidence would record an operator's slip as
        a fact about the shelf."""
        path = rewrite(BRONZE, [('unit = "EUR/kg"', 'unit = "EUR/100g"')],
                       self.scratch)
        with self.assertRaises(StudyError) as caught:
            bundle.run(str(path), directory=str(self.out()))
        self.assertIn('fix constraints.unit', str(caught.exception))
        self.assertFalse(self.out().exists(), 'nothing may be written')


class Bundles(Temporary):
    """Writing one, and reading it back without collecting again."""

    def run_study(self, source=BRONZE, name='bundle'):
        return bundle.run(str(source), directory=str(self.out(name)),
                          started_at='2026-09-16T00:00:00+00:00',
                          finished_at='2026-09-16T00:00:01+00:00')

    def test_a_bundle_holds_every_artifact_with_its_digest(self):
        directory, manifest = self.run_study()
        for name in bundle.ARTIFACTS:
            self.assertTrue((directory / name).is_file(), name)
            self.assertIn(name, manifest['artifacts'])
        self.assertEqual(manifest['outcome'], RECOMMENDATION)
        self.assertEqual(manifest['brief_id'], 'pasta-bronze-die')

    def test_the_study_id_is_derived_from_what_the_answer_rests_on(self):
        """Not random, unlike a crawl id: a study is a pure function of a
        brief and some pinned bytes, so the same study lands in the same
        directory name wherever it is computed."""
        _first, one = self.run_study(name='one')
        _second, two = self.run_study(name='two')
        self.assertEqual(one['study_id'], two['study_id'])
        self.assertTrue(one['study_id'].startswith('pasta-bronze-die-'))

    def test_a_changed_brief_produces_a_different_study(self):
        path = rewrite(BRONZE, [('shortlist = 3', 'shortlist = 2')],
                       self.scratch)
        _a, one = self.run_study(name='one')
        _b, two = self.run_study(source=path, name='two')
        self.assertNotEqual(one['study_id'], two['study_id'])

    def test_two_runs_differ_only_where_the_manifest_says_they_may(self):
        """The acceptance property: identical decisions and numeric claims,
        and only declared metadata variation."""
        first, one = self.run_study(name='one')
        second, two = self.run_study(name='two')
        for name in bundle.ARTIFACTS:
            self.assertEqual((first / name).read_bytes(),
                             (second / name).read_bytes(), name)
        moved = {key for key in set(one) | set(two)
                 if one.get(key) != two.get(key)}
        self.assertLessEqual(moved, set(one['volatile']),
                             'a manifest field moved without being declared '
                             'volatile')

    def test_the_bundle_does_not_carry_the_path_it_was_invoked_by(self):
        """An absolute path is a fact about one machine. It belongs in the
        manifest, which is local, and not in the study, which is portable."""
        directory, manifest = self.run_study()
        persisted = json.loads((directory / bundle.BRIEF)
                               .read_text(encoding='utf-8'))
        self.assertEqual(persisted['source']['path'],
                         'pasta-bronze-die.toml')
        self.assertEqual(manifest['brief_source']['path'], str(BRONZE))
        self.assertNotIn(str(HERE), (directory / bundle.REPORT)
                         .read_text(encoding='utf-8'))

    def test_a_second_run_of_the_same_study_refuses_to_overwrite(self):
        self.run_study()
        with self.assertRaises(bundle.BundleError) as caught:
            self.run_study()
        self.assertIn('--force', str(caught.exception))

    def test_the_cards_are_the_complete_evidence_of_every_candidate(self):
        directory, _manifest = self.run_study()
        with (directory / bundle.CARDS).open(encoding='utf-8') as handle:
            cards = [json.loads(line) for line in handle]
        self.assertEqual(len(cards), 22)
        self.assertEqual([card['asin'] for card in cards],
                         sorted(card['asin'] for card in cards))
        self.assertIn('validated', cards[0])
        self.assertIn('drying', cards[0], 'a category extra must be published')

    def test_the_report_states_the_refusal_as_plainly_as_the_answer(self):
        directory, manifest = self.run_study(source=DRYING)
        text = (directory / bundle.REPORT).read_text(encoding='utf-8')
        self.assertEqual(manifest['outcome'], INSUFFICIENT_EVIDENCE)
        self.assertIn('**Insufficient evidence.**', text)
        self.assertIn('No candidate is put forward.', text)
        self.assertIn('B0173KFFIG', text,
                      'the listings that met the requirement are still named')


class Verification(Temporary):
    """What ``verify`` has to catch, and what it must not mistake for a fault."""

    def setUp(self):
        super().setUp()
        self.directory, self.manifest = bundle.run(
            str(BRONZE), directory=str(self.out()))

    def codes(self, **kwargs):
        _manifest, findings = bundle.verify(str(self.directory), **kwargs)
        return [finding['code'] for finding in findings], findings

    def test_an_untouched_bundle_verifies(self):
        codes, _findings = self.codes()
        self.assertEqual(codes, [])

    def test_a_missing_artifact_is_reported_with_what_is_missing(self):
        (self.directory / bundle.RANKING).unlink()
        codes, findings = self.codes()
        self.assertEqual(codes, ['artifact_missing'])
        self.assertIn('ranking.json', findings[0]['message'])

    def test_an_altered_artifact_is_reported_before_anything_is_recomputed(self):
        path = self.directory / bundle.REPORT
        path.write_text(path.read_text(encoding='utf-8')
                        .replace('2.96', '0.96'), encoding='utf-8')
        codes, findings = self.codes()
        self.assertEqual(codes, ['artifact_altered'])
        self.assertIn('not the study\'s own record', findings[0]['message'])

    def test_a_tampered_input_stops_the_recomputation(self):
        """Every number rests on those bytes, so a diff of the decisions
        would describe the tampering rather than report it."""
        feed = pathlib.Path(self.temporary) / 'pasta_v1.jsonl.gz'
        records = [json.loads(line) for line in
                   gzip.open(HERE / 'cases' / 'pasta_v1.jsonl.gz', 'rt',
                             encoding='utf-8')]
        records[0]['price'] = {'amount': 0.01, 'currency': 'EUR'}
        with gzip.open(feed, 'wt', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + '\n')
        root = pathlib.Path(self.temporary) / 'root'
        (root / 'cases').mkdir(parents=True)
        (root / 'studies').mkdir()
        shutil.copy(feed, root / 'cases' / 'pasta_v1.jsonl.gz')
        codes, findings = self.codes(input_root=str(root / 'studies'))
        self.assertEqual(codes, ['input_altered'])
        self.assertIn('is not the file this study read', findings[0]['message'])

    def test_a_missing_input_says_where_it_looked(self):
        codes, findings = self.codes(input_root=str(self.out('nowhere')))
        self.assertEqual(codes, ['input_missing'])
        self.assertIn('Looked in:', findings[0]['message'])
        self.assertIn('--input-root', findings[0]['message'])

    def test_an_unsupported_manifest_version_checks_nothing_below_it(self):
        path = self.directory / bundle.MANIFEST
        data = json.loads(path.read_text(encoding='utf-8'))
        data['manifest_version'] = 99
        path.write_text(json.dumps(data), encoding='utf-8')
        codes, findings = self.codes()
        self.assertEqual(codes, ['unsupported_manifest_version'])
        self.assertIn('Nothing below was checked', findings[0]['message'])

    def test_a_decision_that_moved_is_named_not_counted(self):
        """The finding a changed analysis rule produces."""
        path = self.directory / bundle.RANKING
        data = json.loads(path.read_text(encoding='utf-8'))
        data['shortlist'] = ['B08WJGD5Z5', 'B0DQ2N5HRW', 'B08BNQ2D54']
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        path.write_text(text + '\n', encoding='utf-8')
        manifest_path = self.directory / bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['artifacts'][bundle.RANKING] = bundle.artifact_entry(
            self.directory, bundle.RANKING)
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        codes, findings = self.codes()
        self.assertEqual(codes, ['decision_moved'])
        self.assertIn('the shortlist', findings[0]['message'])

    def test_a_bundle_replays_from_somewhere_else_entirely(self):
        """The portability property: a copy of the bundle and a copy of the
        feeds, in another tree, with no other file from this checkout."""
        elsewhere = pathlib.Path(self.temporary) / 'elsewhere'
        (elsewhere / 'studies').mkdir(parents=True)
        (elsewhere / 'cases').mkdir()
        shutil.copy(HERE / 'cases' / 'pasta_v1.jsonl.gz', elsewhere / 'cases')
        shutil.copytree(self.directory, elsewhere / 'bundle')
        _manifest, findings = bundle.verify(str(elsewhere / 'bundle'),
                                            str(elsewhere / 'studies'))
        self.assertEqual([finding['code'] for finding in findings], [])


class StructuredRanking(unittest.TestCase):
    """The ranking as data, which the study and the text view share."""

    @classmethod
    def setUpClass(cls):
        from shopping_advisor.analysis import feeds as feeds_module
        from shopping_advisor.analysis.category import get
        records, _provenance = feeds_module.merge(
            [str(HERE / 'cases' / 'pasta_v1.jsonl.gz')])
        category = get('dry_pasta')
        cls.cards = [category.evaluate(record) for record in records]

    def test_the_text_view_renders_the_structure_and_adds_nothing(self):
        structured = report.ranking(self.cards)
        text = report.rank_text(self.cards)
        self.assertEqual(len(structured['rows']), 14)
        self.assertIn(structured['rows'][0]['asin'], text)
        self.assertIn(f'{structured["counts"]["offers"]} offers', text)

    def test_exclusions_are_complete_in_the_data_and_truncated_in_the_text(self):
        """Ten is a terminal's patience, not a finding."""
        cards = self.cards * 2
        structured = report.ranking(cards)
        text = report.rank_text(cards)
        self.assertGreater(len(structured['excluded']), 10)
        self.assertIn('and', text)
        self.assertIn('more', text)

    def test_a_requirement_filter_is_reported_rather_than_silent(self):
        structured = report.ranking(self.cards, require=('bronze_die',))
        self.assertEqual(len(structured['filtered_out']), 14)
        self.assertEqual(structured['filtered_out'][0]['reason_code'],
                         'requirement_not_met')
        self.assertEqual(structured['filtered_out'][0]['missing'],
                         ['bronze_die'])

    def test_it_says_whether_the_axis_was_chosen_or_defaulted(self):
        self.assertFalse(report.ranking(self.cards)['axis']['stated'])
        self.assertTrue(report.ranking(self.cards, 'price_per_base')
                        ['axis']['stated'])

    def test_a_refusal_carries_a_code_a_consumer_can_act_on(self):
        structured = report.ranking(self.cards, 'raw_materials')
        self.assertEqual(structured['refusal']['code'], 'no_direction')
        self.assertEqual(structured['rows'], [])


class CompleteCategoryJson(unittest.TestCase):
    """Every card section a category renders has to survive serialisation."""

    def card(self, key, record):
        from shopping_advisor.analysis.category import get
        return report.card_json(get(key).evaluate(record))

    def test_basmati_publishes_everything_its_text_card_shows(self):
        """Its grain, cultivar, external test, review signals and score are
        the whole of what that category knows, and the JSON card omitted all
        five until T2."""
        from test_basmati import record
        card = self.card('basmati_rice', record())
        for key in ('grain_type', 'cultivar', 'declaration_conflict',
                    'review_signals', 'external_test', 'score'):
            self.assertIn(key, card, key)
        self.assertEqual(json.loads(json.dumps(card)), card)
        self.assertIn('parts', card['score'])
        self.assertIn('status', card['grain_type'])

    def test_a_declared_extra_is_published_even_when_it_is_absent(self):
        """"no contradiction on this page" and "this category does not look
        for one" are different statements."""
        from test_basmati import record
        card = self.card('basmati_rice', record())
        self.assertIsNone(card['declaration_conflict'])

    def test_every_category_declares_the_keys_it_adds(self):
        from shopping_advisor.analysis.category import REGISTRY
        self.assertEqual(REGISTRY['dry_pasta'].extras, ('drying',))
        self.assertEqual(REGISTRY['tyre_mounting_paste'].extras,
                         ('suitability',))
        self.assertIn('score', REGISTRY['basmati_rice'].extras)


if __name__ == '__main__':
    unittest.main()
