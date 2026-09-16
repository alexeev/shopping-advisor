"""Tests for reading Amazon's variation matrix.

The two failure modes this layer has are opposite, and both are tested:
collapsing too little leaves sixteen listings of one pasta crowding a ranking,
and collapsing too much merges spaghetti with fusilli because Amazon files
them under one parent. The corpus page `B088419TTP` is the real example of the
second -- one family, three shapes, five pack sizes -- and it is why grouping
is done along the size dimension rather than by family.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from shopping_advisor.analysis import report  # noqa: E402
from shopping_advisor.analysis.categories.dry_pasta import evaluate  # noqa: E402
from shopping_advisor.validation import quantity as checks, variation  # noqa: E402
from test_corpus import extract_dir  # noqa: E402


def matrix(dimensions, values_by_asin, parent='B0PARENT01'):
    return {'dimensions': list(dimensions),
            'values_by_asin': dict(values_by_asin),
            'parent_asin': parent}


def record(asin='B000000000', **overrides):
    base = {
        'asin': asin,
        'title': 'Spaghetti',
        'brand': 'Test',
        'breadcrumbs': ['Lebensmittel & Getränke', 'Nudeln & Pasta'],
        'price': {'amount': 2.0, 'currency': 'EUR'},
        'unit_price': {},
        'package': {},
        'raw_tables': {},
        'content': {'feature_bullets': [], 'description': '',
                    'important_information': [], 'aplus': {}},
        'food': {'ingredients': {}, 'allergens': [], 'nutrition': {}},
    }
    base.update(overrides)
    return base


class SizeDimension(unittest.TestCase):

    def test_the_size_dimension_is_looked_up_not_guessed(self):
        data = matrix(['flavor_name', 'size_name'],
                      {'B1': ['Weiß', '5 kg (1er Pack)']})
        self.assertEqual(variation.dimension_value(data, 'B1'), '5 kg (1er Pack)')

    def test_a_product_that_varies_only_by_colour_has_no_size(self):
        """"Roségold" must never become a quantity."""
        data = matrix(['color_name'], {'B1': ['Roségold']})
        self.assertEqual(variation.dimension_value(data, 'B1'), '')
        self.assertIsNone(checks.size_label_quantity('Roségold'))

    def test_misaligned_dimensions_yield_nothing_rather_than_a_guess(self):
        data = matrix(['size_name', 'style_name'], {'B1': ['500 g']})
        self.assertEqual(variation.dimension_value(data, 'B1'), '')

    def test_a_bare_weight_size_label_states_the_pack_content(self):
        # Only true of a size label: "5 L" in a title could be anything.
        self.assertEqual(checks.size_label_quantity('5 L'), 5000.0)
        self.assertEqual(checks.size_label_quantity('Uzair Reis 5kg'), 5000.0)

    def test_a_counted_label_is_left_to_the_general_parser(self):
        self.assertIsNone(checks.size_label_quantity('500 g (5er Pack)'))
        hints = checks.pack_hints(record(
            variation=matrix(['size_name'], {'B000000000': ['500 g (5er Pack)']})))
        self.assertIn(2500.0, [grams for grams, _ in hints])

    def test_english_pack_phrasing_on_a_german_marketplace(self):
        hints = checks.pack_hints(record(
            variation=matrix(['size_name'],
                             {'B000000000': ['1000 g (Pack of 1)']})))
        self.assertIn(1000.0, [grams for grams, _ in hints])


class Quantity(unittest.TestCase):

    def test_the_twister_states_a_pack_size_the_attribute_table_omits(self):
        """Four corpus pages have an empty `Paketgröße - Name` and a twister
        label; this is the case the new source exists for."""
        data = record(package={'size_name': '', 'total_quantity_base': 500.0,
                               'total_quantity_unit': 'g',
                               'total_quantity_source': 'unit_count'},
                      variation=matrix(['size_name'],
                                       {'B000000000': ['500 g (1er Pack)']}))
        value = checks.reconcile(data)
        self.assertEqual(value.status, 'trusted')
        self.assertTrue(any('variation' in e.field for e in value.evidence))

    def test_the_twister_can_contradict_the_attribute_table(self):
        data = record(title='Garofalo Fusilli',
                      package={'total_quantity_base': 500.0,
                               'total_quantity_unit': 'g',
                               'total_quantity_source': 'unit_count'},
                      variation=matrix(['size_name'],
                                       {'B000000000': ['500 g (16er Pack)']}))
        self.assertEqual(checks.reconcile(data).status, 'disputed')

    def test_records_crawled_before_schema_v3_still_work(self):
        """The committed evidence set has no `variation` key at all."""
        data = record(package={'total_quantity_base': 500.0,
                               'total_quantity_unit': 'g',
                               'total_quantity_source': 'unit_count'})
        self.assertIsNone(variation.offer_key(data))
        self.assertEqual(variation.size_label(data), '')
        self.assertEqual(checks.reconcile(data).status, 'unverified')


class Offers(unittest.TestCase):

    # One family, three shapes, several pack sizes -- modelled on the real
    # B088419TTP matrix.
    MEMBERS = {
        'B_SPAG_1': ['500 g (1er Pack)', 'Spaghetti n. 5 Integrale'],
        'B_SPAG_10': ['500 g (10er Pack)', 'Spaghetti n. 5 Integrale, 10x500g'],
        'B_PENNE_1': ['500 g (1er Pack)', 'Penne Rigate Integrale'],
        'B_PENNE_5': ['500 g (5er Pack)', 'Penne Rigate Integrale'],
        'B_FUSIL_1': ['500 g (1er Pack)', 'Fusilli Integrale'],
    }
    SHAPES = matrix(['size_name', 'style_name'], MEMBERS)

    def keys(self):
        return {asin: variation.offer_key(record(asin, variation=self.SHAPES))
                for asin in self.MEMBERS}

    def test_pack_sizes_of_one_product_share_an_offer(self):
        keys = self.keys()
        self.assertEqual(keys['B_PENNE_1'], keys['B_PENNE_5'])

    def test_different_shapes_stay_different_products(self):
        keys = self.keys()
        self.assertNotEqual(keys['B_PENNE_1'], keys['B_FUSIL_1'])
        self.assertNotEqual(keys['B_SPAG_1'], keys['B_PENNE_1'])

    def test_a_pack_size_baked_into_a_style_label_is_not_a_new_product(self):
        """"Spaghetti n. 5 Integrale, 10x500g" is the size dimension leaking
        into the style label, not a different pasta."""
        self.assertEqual(self.keys()['B_SPAG_1'], self.keys()['B_SPAG_10'])

    def test_grouping_puts_the_shapes_in_separate_groups(self):
        records = [record(asin, variation=self.SHAPES) for asin in self.MEMBERS]
        groups = variation.group_offers(records)
        sizes = sorted(len(members) for _, members in groups)
        self.assertEqual(sizes, [1, 2, 2])

    def test_a_sibling_without_its_own_matrix_is_still_placed(self):
        """Amazon does not render the twister on every member of a family, so
        one record's matrix is used to place the others. The claim is already
        in hand; asking each record only about itself throws it away."""
        records = [record('B_PENNE_1', variation=self.SHAPES),
                   record('B_PENNE_5')]          # no matrix of its own
        groups = variation.group_offers(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0][1]), 2)

    def test_an_unrelated_record_is_not_swept_into_a_pooled_family(self):
        records = [record('B_PENNE_1', variation=self.SHAPES),
                   record('B_STRANGER')]
        groups = variation.group_offers(records)
        self.assertEqual(sorted(len(members) for _, members in groups), [1, 1])

    def test_an_ungroupable_record_is_its_own_offer(self):
        groups = variation.group_offers([record('B1'), record('B2')])
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(key is None for key, _ in groups))


class AcrossMarketplaces(unittest.TestCase):
    """An ASIN is minted per marketplace, and so is a parent ASIN.

    Without a marketplace in the key, one family key covers two shelves: two
    listings in two currencies collapse into a single ranked row, and a
    ``.de`` matrix places a ``.com`` record it has never seen.
    """

    FAMILY = matrix(['size_name'], {'B_ONE': ['500 g (1er Pack)'],
                                    'B_FIVE': ['500 g (5er Pack)']})

    def on(self, marketplace, asin='B_ONE', **overrides):
        return record(asin, marketplace=marketplace, variation=self.FAMILY,
                      **overrides)

    def test_the_same_parent_on_two_marketplaces_is_two_families(self):
        self.assertNotEqual(variation.family_key(self.on('www.amazon.de')),
                            variation.family_key(self.on('www.amazon.com')))

    def test_the_marketplace_is_normalised_before_it_is_used(self):
        self.assertEqual(variation.family_key(self.on('www.amazon.de')),
                         variation.family_key(self.on('amazon.de')))

    def test_two_marketplaces_are_never_folded_into_one_offer_row(self):
        groups = variation.group_offers([self.on('www.amazon.de'),
                                         self.on('www.amazon.com')])
        self.assertEqual(sorted(len(members) for _, members in groups), [1, 1])

    def test_a_matrix_only_places_siblings_on_its_own_marketplace(self):
        """The pooled index is the path that crosses marketplaces silently:
        the ``.de`` record's matrix names B_FIVE, and a ``.com`` B_FIVE is a
        different listing."""
        groups = variation.group_offers([
            self.on('www.amazon.de'),
            record('B_FIVE', marketplace='www.amazon.com')])
        self.assertEqual(sorted(len(members) for _, members in groups), [1, 1])

    def test_a_record_that_names_no_marketplace_keeps_its_own_scope(self):
        self.assertNotEqual(variation.family_key(self.on('www.amazon.de')),
                            variation.family_key(record('B_ONE',
                                                        variation=self.FAMILY)))


class AgainstTheCorpus(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = extract_dir('amazon_de')

    def test_every_size_label_on_the_corpus_parses(self):
        # 22 of the 38 amazon.de pages carry a size label: 20 groceries, and
        # the two non-food pages added in R2, labelled "50 ml" and "100g" --
        # the first size dimension in the corpus that is a volume.
        labelled = {asin: rec for asin, rec in self.records.items()
                    if variation.size_label(rec)}
        self.assertEqual(len(labelled), 22)
        for asin, rec in labelled.items():
            with self.subTest(asin=asin):
                hints = checks.pack_hints(rec)
                self.assertTrue(
                    [g for g, e in hints if e.field == 'variation.size_name'],
                    f'{asin}: {variation.size_label(rec)!r} produced no quantity')

    def test_no_size_label_contradicts_a_quantity_that_was_already_right(self):
        for asin, rec in self.records.items():
            total = rec['package'].get('total_quantity_base')
            hints = [g for g, e in checks.pack_hints(rec)
                     if e.field == 'variation.size_name']
            if not (total and hints):
                continue
            with self.subTest(asin=asin):
                self.assertLessEqual(
                    min(abs(g - total) / max(g, total) for g in hints), 0.15)

    def test_a_real_family_holds_more_than_one_product(self):
        data = self.records['B088419TTP']['variation']
        shapes = {variation.variant_signature(data, asin)
                  for asin in data['values_by_asin']}
        self.assertEqual(len(shapes), 3, 'spaghetti, penne and fusilli')


class Reporting(unittest.TestCase):

    def pasta(self, asin, price, quantity, variation_data=None,
              currency='EUR', marketplace='www.amazon.de'):
        return evaluate(record(
            asin, title='Penne Rigate', brand='Garofalo',
            marketplace=marketplace,
            price={'amount': price, 'currency': currency},
            unit_price={'amount': round(price / (quantity / 1000), 2),
                        'unit': 'kg'},
            package={'total_quantity_base': quantity, 'total_quantity_unit': 'g',
                     'total_quantity_source': 'unit_count'},
            food={'ingredients': {'text': 'HARTWEIZENGRIESS'}, 'allergens': [],
                  'nutrition': {}},
            variation=variation_data or {}))

    def test_two_currencies_are_not_ranked_as_one_price_list(self):
        """Currency is the unit of the price axis, so the same rule that
        refuses grams against millilitres refuses euros against dollars. It
        should not be reachable through the CLI -- that stops earlier, on the
        marketplace -- but a ranking that quietly sorted 7.99 USD below
        8.49 EUR would read exactly like an answer."""
        cards = [self.pasta('B_EUR', 2.5, 500.0),
                 self.pasta('B_USD', 2.0, 500.0, currency='USD',
                            marketplace='www.amazon.com')]
        text = report.rank_text(cards, 'price_per_base')
        self.assertIn('measured in more than one unit', text)
        self.assertIn('--unit EUR/kg', text)
        self.assertIn('1. ', report.rank_text(cards, 'price_per_base',
                                              unit='EUR/kg'))

    def test_an_axis_with_no_better_direction_is_not_ranked(self):
        """Sorting it ascending produced an ordering that reads exactly like
        a recommendation for a value the category says has no better side."""
        cards = [self.pasta('B_ONE', 2.5, 500.0)]
        text = report.rank_text(cards, 'raw_materials')
        self.assertIn('declares no better direction', text)
        self.assertIn('Rankable axes:', text)

    def test_pack_sizes_collapse_into_one_ranked_row(self):
        family = matrix(['size_name'], {
            'B_ONE': ['500 g (1er Pack)'], 'B_FIVE': ['500 g (5er Pack)']})
        cards = [self.pasta('B_ONE', 2.5, 500.0, family),
                 self.pasta('B_FIVE', 10.0, 2500.0, family)]
        text = report.rank_text(cards)
        self.assertIn('1 offers with a trusted price_per_base', text)
        self.assertIn('1 pack-size variants folded in', text)
        self.assertIn('same product, other pack', text)

    def test_comparing_two_pack_sizes_says_so_instead_of_comparing_quality(self):
        family = matrix(['size_name'], {
            'B_ONE': ['500 g (1er Pack)'], 'B_FIVE': ['500 g (5er Pack)']})
        text = report.compare_text(self.pasta('B_ONE', 2.5, 500.0, family),
                                   self.pasta('B_FIVE', 9.0, 2500.0, family))
        flat = ' '.join(text.split())
        self.assertIn('same product in different pack sizes', flat)
        self.assertIn('not which product is better', flat)
        self.assertIn('B wins on price per kg', flat)

    def test_two_real_products_are_still_compared_normally(self):
        text = report.compare_text(self.pasta('B_A', 2.5, 500.0),
                                   self.pasta('B_B', 4.0, 500.0))
        self.assertIn('Differences', text)
        self.assertNotIn('same product in different pack sizes', text)


if __name__ == '__main__':
    unittest.main()
