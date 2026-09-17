"""R13 stage 4: catalogue resolution and meaning-sensitive execution cases."""
import contextlib
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from shopping_advisor.analysis import category, report
from shopping_advisor.study import controls
from shopping_advisor.study.__main__ import main
from shopping_advisor.study.analysis import analyse
from shopping_advisor.study.brief import load
from shopping_advisor.validation import Value


class Controls(unittest.TestCase):
    def test_catalogue_tracks_every_live_category(self):
        for key in category.known():
            with self.subTest(category=key):
                live, found = category.get(key), controls.catalogue(key)
                self.assertEqual([a['key'] for a in found['axes']], list(live.axis_keys))
                self.assertEqual([c['key'] for c in found['claims']], list(live.claim_keys))
                self.assertEqual(found['default_axis'], live.default_axis)
                self.assertEqual(set(found['controls']), {'require_claims', 'max_axis_value',
                    'classification', 'value_usability', 'offer_grouping'})
                self.assertEqual(controls.resolve(key, 'value_usability')['axis']['key'],
                                 live.default_axis)

    def test_resolver_reads_registry_changes_without_a_parallel_list(self):
        live = category.get('dry_pasta')
        changed = replace(live, axes=(category.Axis('new_axis', 'New', better='higher'),),
                          claims=(category.Claim('new_claim', 'New', 'new'),),
                          default_axis='new_axis')
        with patch.dict(category.REGISTRY, dry_pasta=changed):
            self.assertEqual(controls.resolve('dry_pasta', 'value_usability')['axis']['better'], 'higher')
            self.assertEqual(controls.resolve('dry_pasta', 'require_claims',
                                             claims=['new_claim'])['claims'][0]['key'], 'new_claim')
            with self.assertRaises(controls.ControlError):
                controls.resolve('dry_pasta', 'require_claims', claims=['bronze_die'])

    def test_unknown_category_control_and_parameters_refuse(self):
        with self.assertRaises(controls.ControlError):
            controls.catalogue('shopping_advisor.analysis.categories.dry_pasta')
        for name in ('cost_basis', 'unacceptable', 'limits', 'external_evidence'):
            with self.subTest(name=name), self.assertRaises(controls.ControlError):
                controls.resolve('dry_pasta', name)
        for name in ('classification', 'offer_grouping'):
            with self.subTest(name=name), self.assertRaises(controls.ControlError):
                controls.resolve('dry_pasta', name, max_pack_size=500)

    def test_invalid_parameters_refuse(self):
        for value in (None, True, -1, float('inf'), float('nan'), '100'):
            with self.subTest(value=value), self.assertRaises(controls.ControlError):
                controls.resolve('dry_pasta', 'max_axis_value', value=value)
        for claims in (None, 'bronze_die', [True], ['not_a_claim']):
            with self.subTest(claims=claims), self.assertRaises(controls.ControlError):
                controls.resolve('dry_pasta', 'require_claims', claims=claims)
        with self.assertRaises(controls.ControlError):
            controls.resolve('dry_pasta', 'value_usability', unit=5)
        self.assertEqual(controls.resolve('dry_pasta', 'max_axis_value', value=0)
                         ['parameters']['value'], 0)

    def test_axes_preserve_boundary_examples(self):
        for key in ('dry_pasta', 'basmati_rice'):
            with self.subTest(category=key), self.assertRaises(controls.ControlError):
                controls.resolve(key, 'max_axis_value', axis='price', value=100)
        paste = controls.catalogue('tyre_mounting_paste')
        self.assertEqual(paste['default_axis'], 'quantity')
        self.assertEqual(controls.resolve('tyre_mounting_paste', 'max_axis_value',
                                         axis='price', value=100)['axis']['better'], 'lower')
        with self.assertRaisesRegex(controls.ControlError, 'no ranking direction'):
            controls.resolve('tyre_mounting_paste', 'value_usability', axis='price_per_base')

    def test_cli_requires_category_and_outputs_json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['controls', '--category', 'basmati_rice']), 0)
        self.assertEqual(json.loads(out.getvalue()), controls.catalogue('basmati_rice'))
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                main(['controls'])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(main(['controls', '--category', 'unknown']), 2)


class ControlMeaning(unittest.TestCase):
    """Small independent counterexamples exercise the implementation, not prose."""
    def card(self, key='dry_pasta', asin='A', number=4, unit='EUR/kg', status='trusted'):
        live = category.get(key)
        card = live.evaluate({'asin': asin, 'marketplace': 'www.amazon.de',
                              'title': '', 'price': {}, 'package': {}})
        card['category'] = Value(key, status='trusted')
        card['axes'][live.default_axis] = Value(number, unit=unit, status=status)
        return card

    def test_claim_requires_trusted_presence_including_adverse_keys(self):
        for key in category.known():
            live = category.get(key)
            claim = next((c for c in live.claims if c.adverse), live.claims[0])
            mapping = controls.resolve(key, 'require_claims', claims=[claim.key])
            cards = []
            for status in ('trusted', 'unverified', 'disputed', 'unknown', 'not_claimed'):
                card = self.card(key, asin=status)
                card['claims'][claim.key] = Value(True, status=status)
                cards.append(card)
            missing = self.card(key, asin='missing')
            missing['claims'].pop(claim.key, None)
            cards.append(missing)
            ranked = report.ranking(cards, require=mapping['parameters']['claims'])
            self.assertEqual([r['asin'] for r in ranked['rows']], ['trusted'])
            self.assertEqual(len(ranked['filtered_out']), 5)
            self.assertEqual(mapping['claims'][0]['adverse'], claim.adverse)

    def test_classification_matches_value_not_confidence_or_prose(self):
        controls.resolve('dry_pasta', 'classification')
        cards = [self.card(asin='match'), self.card(asin='other'), self.card(asin='unknown')]
        cards[1]['category'] = Value('other', status='trusted')
        cards[2]['category'] = Value(None, status='unknown')
        self.assertEqual([r['asin'] for r in report.ranking(cards)['rows']], ['match'])
        # The live classifier still distinguishes dry from chilled pasta.
        live = category.get('dry_pasta')
        for breadcrumbs, expected in ((['Lebensmittel & Getränke', 'Nudeln & Pasta'], True),
                                       (['Lebensmittel & Getränke', 'Kühlprodukte', 'Gekühlte Pasta'], False)):
            self.assertEqual(category.is_match(live.evaluate({'title': 'Spaghetti',
                                                              'breadcrumbs': breadcrumbs})), expected)

    def test_value_usability_and_unit_refusals(self):
        mapping = controls.resolve('dry_pasta', 'value_usability', unit='EUR/kg')
        cards = [self.card(asin='good'), self.card(asin='disputed', status='disputed'),
                 self.card(asin='unverified', status='unverified'), self.card(asin='absent'),
                 self.card(asin='volume', unit='EUR/l')]
        del cards[3]['axes']['price_per_base']
        ranked = report.ranking(cards, axis_key=mapping['parameters']['axis'],
                                unit=mapping['parameters']['unit'])
        self.assertEqual([r['asin'] for r in ranked['rows']], ['good'])
        self.assertEqual({r['asin']: r['reason_code'] for r in ranked['excluded']},
                         {'disputed': 'not_usable', 'unverified': 'not_usable',
                          'absent': 'no_value', 'volume': 'unit_mismatch'})
        self.assertEqual(report.ranking(cards)['refusal']['code'], 'ambiguous_unit')
        self.assertEqual(report.ranking(cards, unit='EUR/100g')['refusal']['code'], 'unit_absent')
        self.assertEqual(report.ranking(cards, axis_key='quantity')['refusal']['code'], 'no_direction')

    def test_cap_is_inclusive_on_selected_axis_even_when_higher_is_better(self):
        brief = load(Path(__file__).parent / 'studies' / 'pasta-bronze-die.toml')
        for axis in ('price_per_base', 'protein_g'):
            mapping = controls.resolve('dry_pasta', 'max_axis_value', axis=axis, value=5)
            cards = [self.card(asin=str(n), number=n) for n in (4, 5, 6)]
            for card in cards:
                card['axes'][axis] = Value(int(card['asin']), unit='test-unit', status='trusted')
            capped = replace(brief, axis=axis, unit='test-unit', require_claims=(), minimum_candidates=1,
                             max_axis_value=mapping['parameters']['value'])
            with patch('shopping_advisor.study.analysis.collect', return_value=(cards, {'feeds': 1})):
                result, _ = analyse(capped)
            decisions = {c['asin']: c['decision'] for c in result['candidates']}
            self.assertEqual(decisions, {'4': 'shortlisted', '5': 'shortlisted', '6': 'over_budget'})
            self.assertEqual(result['shortlist'], ['4', '5'] if axis == 'price_per_base' else ['5', '4'])

    def test_grouping_folds_size_but_preserves_non_size_and_unknown_identity(self):
        controls.resolve('dry_pasta', 'offer_grouping')
        cards = [self.card(asin=name, number=n) for name, n in [('A', 4), ('B', 3), ('C', 2), ('D', 1)]]
        matrix = {'parent_asin': 'PARENT', 'dimensions': ['size_name', 'style_name'],
                  'values_by_asin': {'A': ['500g', 'spaghetti'], 'B': ['1kg', 'spaghetti'],
                                     'C': ['500g', 'fusilli']}}
        cards[0]['variation'] = matrix
        ranked = report.ranking(cards)
        self.assertEqual([r['asin'] for r in ranked['rows']], ['D', 'C', 'B'])
        self.assertEqual([v['asin'] for v in ranked['rows'][2]['variants']], ['A'])
        other_market = copy.deepcopy(cards[1])
        other_market['marketplace'] = 'www.amazon.com'
        from shopping_advisor.validation.variation import group_offers
        self.assertEqual(len(group_offers(cards + [other_market])), 4)


if __name__ == '__main__':
    unittest.main()
