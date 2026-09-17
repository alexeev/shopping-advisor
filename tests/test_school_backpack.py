"""Tests for the school-backpack category -- the fourth, and the first non-consumable.

Two jobs, as for tyre mounting paste. The category's own rules: a
positional title classifier that tells a secondary-school backpack from a
primary-school satchel, a laptop pack and an adult's daypack; four vendor
statements; a weight axis that is the validation layer's value and nothing
more. And the contract: the axes on a card are the very objects
:func:`validate` produced, the module names no status for a measured value it
did not read from prose, and it imports no rule.

The cases are the 43 unique records two bounded Amazon.de probes returned on
2026-09-17 for "Schulrucksack Mädchen", "Schulrucksack Jugendliche" and eight
brand queries, re-extracted from their retained pages after the extractor
learned to read the weight Amazon.de appends to the dimensions row. The same
searches return trekking packs, hiking packs, men's laptop bags, first-graders'
satchel sets and a leisure daypack, and vendors stuff "Schulranzen" and
"Schulrucksack" into one title for the traffic -- so classification carries the
weight here that it does for pasta, and it cannot use the breadcrumbs, which
file Satch and a first-grader's set under the same node.
"""

import gzip
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shopping_advisor.analysis import report  # noqa: E402
from shopping_advisor.analysis.categories.school_backpack import (  # noqa: E402
    CATEGORY, KEY, classify, evaluate)
from shopping_advisor.validation import (  # noqa: E402
    NOT_CLAIMED, TEXT, TRUSTED, UNKNOWN, UNVERIFIED, validate)

CASES = pathlib.Path(__file__).resolve().parent / 'cases' / 'school_backpack_v1.jsonl.gz'
MODULE = (pathlib.Path(__file__).resolve().parent.parent / 'shopping_advisor' /
          'analysis' / 'categories' / 'school_backpack.py')


def load_cases():
    with gzip.open(CASES, 'rt', encoding='utf-8') as handle:
        return {record['asin']: record for record in map(json.loads, handle)}


def record(**overrides):
    base = {
        'asin': 'B000000000', 'title': 'Schulrucksack', 'brand': 'Test',
        'product_url': 'https://www.amazon.de/dp/B000000000',
        'search_query': 'schulrucksack', 'breadcrumbs': [],
        'price': {'amount': 99.0, 'currency': 'EUR'}, 'unit_price': {},
        'package': {}, 'raw_tables': {},
        'content': {'feature_bullets': [], 'description': '',
                    'important_information': [], 'aplus': {}},
        'food': {'ingredients': {}, 'allergens': [], 'nutrition': {}},
    }
    base.update(overrides)
    return base


class Classification(unittest.TestCase):
    """Decided on the title, read positionally; one Amazon node may speak."""

    def name(self, title, breadcrumbs=()):
        return classify({'title': title, 'breadcrumbs': list(breadcrumbs)}).value

    def test_a_plain_school_backpack_is_one(self):
        self.assertEqual(self.name('Satch Schulrucksack Pack'), KEY)
        self.assertEqual(self.name('deuter Cotogy (26 L) Schulrucksack ab der '
                                   '5.Klasse'), KEY)

    def test_schulranzen_for_teenagers_is_a_school_backpack(self):
        """On Amazon.de the word names the node that holds Satch as well as
        the first-graders' satchels; only the grade markers separate them."""
        self.assertEqual(self.name('Amythe Schulranzen Teenager Mädchen mit '
                                   'Abnehmbarem Hüftgurt'), KEY)

    def test_a_first_graders_set_is_a_different_product(self):
        self.assertEqual(self.name('Undercover Schulranzen Set 5-TLG. Mädchen '
                                   '1. Klasse, Mit personalisiertem Zubehör'),
                         'other')
        self.assertEqual(self.name('Scout Schulranzen Alpha Einschulung'), 'other')
        self.assertEqual(self.name('Ergobag Cubo Schulranzen Grundschule'), 'other')

    def test_grades_one_to_five_is_not_a_first_grade_marker(self):
        """"1. - 5. Klasse" spans the move to secondary school; it is not the
        first-day-of-school satchel the marker exists to exclude."""
        self.assertEqual(self.name('Amythe Schultasche Mädchen Rucksack Schule '
                                   'Mädchen 1. - 5. Klasse'), KEY)

    def test_an_adults_pack_with_a_stuffed_school_word_is_an_adults_pack(self):
        for title in ('Rucksack Herren, Schulrucksack Jungen Teenager, Laptop '
                      'Rucksack 15,6 Zoll',
                      'YAMTION Rucksack für Herren, Schultaschen für Jungen '
                      'und Teenager, Laptop-Rucksack',
                      'Rucksack Herren Groß, Laptop Rucksack Wasserdicht 17,3 '
                      'Zoll Schulrucksack Laptoptasche'):
            with self.subTest(title=title):
                self.assertEqual(self.name(title), 'other')

    def test_a_feature_after_the_school_word_is_a_feature(self):
        self.assertEqual(self.name('EASTPAK Tutor 39L Schulrucksack Groß '
                                   'Mehrfächer Laptop 16"'), KEY)
        self.assertEqual(self.name('Chase Chic Schulrucksack Mädchen, Cord '
                                   'Rucksack Teenageralter Leichter Schulranzen '
                                   'Daypack'), KEY)

    def test_a_compound_school_word_counts(self):
        self.assertEqual(self.name('EASTPAK Out of Office Rucksack 27L, '
                                   'Laptopfach 13–15 Zoll, wasserabweisender '
                                   'Schul- & Arbeitsrucksack'), KEY)
        self.assertEqual(self.name('Beckmann, Rucksack Urban, für Schule Uni '
                                   'Arbeit Freizeit, mit extra Laptopraum'), KEY)

    def test_trekking_hiking_and_leisure_packs_are_not_school_backpacks(self):
        for title in ('deuter Aircontact Pro 75+10 Trekkingrucksack',
                      'deuter Futura 23 Wanderrucksack mit Netzrücken',
                      'Jack Wolfskin Unisex Kinder Rebel Pack 25 Daypack',
                      'Eastpak Wyoming Rucksack, 24 L',
                      'PUMA Buzz Backpack, Unisex-Erwachsene Rucksack'):
            with self.subTest(title=title):
                self.assertEqual(self.name(title), 'other')

    def test_the_satchel_set_node_speaks_when_the_title_is_silent(self):
        crumbs = ['Fashion', 'Gepäck & Reiseausrüstung',
                  'Schultaschen, Federmäppchen & Sets', 'Schultaschen-Sets']
        self.assertEqual(self.name('GMT for Kids Schulranzen 32L Ergonomische '
                                   'Schultasche Mädchen Groß Schulrucksack',
                                   crumbs), 'other')

    def test_the_school_node_is_weaker_than_the_vendor_saying_so(self):
        crumbs = ['Fashion', 'Gepäck & Reiseausrüstung',
                  'Schultaschen, Federmäppchen & Sets', 'Schulranzen']
        value = classify({'title': 'Beckmann Sport Junior Rucksack 30L',
                          'breadcrumbs': crumbs})
        self.assertEqual(value.value, KEY)
        self.assertEqual(value.status, UNVERIFIED)
        crumbs[-1] = 'Kinderrucksäcke'
        self.assertEqual(classify({'title': 'EASTPAK Provider Rucksack - 33 L',
                                   'breadcrumbs': crumbs}).value, 'other')

    def test_a_listing_with_no_title_is_unclassified_not_excluded(self):
        self.assertEqual(classify({'title': ''}).status, UNKNOWN)


class Claims(unittest.TestCase):

    def card(self, bullets=(), tables=None):
        return evaluate(record(
            content={'feature_bullets': list(bullets), 'description': '',
                     'important_information': [], 'aplus': {}},
            raw_tables=tables or {}))

    def test_a_reflector_sentence_is_quoted(self):
        card = self.card(['Reflektierende Elemente sorgen für Sichtbarkeit im '
                          'Straßenverkehr.'])
        claim = card['claims']['reflective_elements']
        self.assertEqual(claim.status, TRUSTED)
        self.assertIn('Reflektierende', claim.evidence[0].quote)

    def test_a_negated_reflector_sentence_is_not_a_claim(self):
        card = self.card(['Ohne Reflektoren geliefert.'])
        self.assertEqual(card['claims']['reflective_elements'].status, NOT_CLAIMED)

    def test_the_warranty_row_is_a_claim_and_the_statutory_row_is_not(self):
        stated = self.card(tables={'Garantie für das Produkt': '4 Jahre'})
        self.assertEqual(stated['claims']['manufacturer_warranty'].status, TRUSTED)
        self.assertEqual(stated['axes']['warranty_years'].value, 4.0)
        self.assertEqual(stated['axes']['warranty_years'].status, UNVERIFIED)
        statutory = self.card(tables={'Garantie für das Produkt': 'Gesetzlich'})
        self.assertEqual(statutory['claims']['manufacturer_warranty'].status,
                         NOT_CLAIMED)
        self.assertEqual(statutory['axes']['warranty_years'].status, UNKNOWN)

    def test_amazons_return_policy_and_marketing_verbs_are_not_warranties(self):
        card = self.card(
            ['Mehrfach verstärkte Nähte garantieren maximale Reißfestigkeit.'],
            tables={'Unsere freiwillige Amazon.de Rückgabegarantie':
                    'Unabhängig von deinem gesetzlichen Widerrufsrecht genießt '
                    'du ein 30-tägiges Rückgaberecht.'})
        self.assertEqual(card['claims']['manufacturer_warranty'].status, NOT_CLAIMED)

    def test_a_written_out_year_and_a_month_count_are_warranties(self):
        """"ein Jahr Garantie" and "innerhalb von 12 Monaten nach dem Kauf ...
        deckt die Garantie": two of 192 collected listings, both missed by
        the first pattern, which wanted a digit next to the noun."""
        card = self.card(['Qualitätssicherung: Auf jeden Kinderrucksack gibt es '
                          'ein Jahr Garantie.'])
        self.assertEqual(card['claims']['manufacturer_warranty'].status, TRUSTED)
        self.assertEqual(card['axes']['warranty_years'].value, 1.0)
        card = self.card(['Innerhalb von 12 Monaten nach dem Kauf des Produkts '
                          'deckt die Garantie die kostenlose Reparatur ab.'])
        self.assertEqual(card['claims']['manufacturer_warranty'].status, TRUSTED)
        self.assertEqual(card['axes']['warranty_years'].value, 1.0)

    def test_an_adjustable_back_in_the_title_counts(self):
        card = evaluate(record(title='coocazoo Schulrucksack Mate, ergonomischer '
                                     '& anpassbarer Tornister, höhen- & '
                                     'größenverstellbar, mit Brustgurt'))
        self.assertEqual(card['claims']['adjustable_back'].status, TRUSTED)
        self.assertEqual(card['claims']['hip_or_chest_strap'].status, TRUSTED)

    def test_an_unstated_criterion_is_not_claimed_rather_than_false(self):
        card = self.card()
        for key in ('reflective_elements', 'manufacturer_warranty',
                    'adjustable_back', 'hip_or_chest_strap'):
            self.assertEqual(card['claims'][key].status, NOT_CLAIMED)
            self.assertIn('not the same as it being untrue',
                          card['claims'][key].notes[0])


class Axes(unittest.TestCase):

    def test_a_body_height_range_is_read_in_centimetres_and_metres(self):
        card = evaluate(record(content={
            'feature_bullets': ['Passt bei einer Körpergröße von 135 cm bis '
                                '180 cm.'],
            'description': '', 'important_information': [], 'aplus': {}}))
        self.assertEqual(card['axes']['body_height'].value, '135–180 cm')
        card = evaluate(record(raw_tables={
            'geeignet für': 'Der satch pack kann auf Körpergrößen von 1,40 - '
                            '1,80 m eingestellt werden.'}))
        self.assertEqual(card['axes']['body_height'].value, '140–180 cm')
        self.assertEqual(card['axes']['body_height'].status, UNVERIFIED)

    def test_a_weight_stated_only_in_prose_is_unverified(self):
        card = evaluate(record(content={
            'feature_bullets': [], 'description': '',
            'important_information': [],
            'aplus': {'text': 'Mit einem Gewicht von 1.250 Gramm und 30 Litern '
                              'Volumen ist der MATE ein Allrounder.'}}))
        weight = card['axes']['weight']
        self.assertEqual(weight.value, 1250.0)
        self.assertEqual(weight.status, UNVERIFIED)
        self.assertEqual(weight.source, TEXT)
        self.assertEqual(card['axes']['volume'].value, 30.0)

    def test_a_multipack_weight_row_is_not_the_weight_of_one_bag(self):
        card = evaluate(record(package={
            'item_count': 2, 'item_weight_base': 500.0,
            'total_quantity_base': 1000.0, 'total_quantity_unit': 'g',
            'total_quantity_source': 'item_weight_x_count'}))
        self.assertEqual(card['axes']['weight'].status, UNKNOWN)

    def test_no_weight_anywhere_is_unknown(self):
        self.assertEqual(evaluate(record())['axes']['weight'].status, UNKNOWN)


class ContractUse(unittest.TestCase):
    """The criterion R2 finished against, asserted on the fourth category."""

    def setUp(self):
        self.cases = load_cases()
        self.card = evaluate(self.cases['B0GM19PXKV'])   # Satch Pack

    def test_the_weight_is_the_validation_layers_value(self):
        validated = self.card['validated']
        self.assertIs(self.card['axes']['weight'], validated.quantity)
        self.assertIs(self.card['axes']['price'], validated.price)

    def test_a_dimensions_row_weight_reaches_the_card_trusted(self):
        """"Produktabmessungen: 22 x 30 x 45 cm; 1,1 Kilogramm", confirmed by
        the A+ copy's "Gewicht 1200 g": the two generic changes this category
        needed, measured on the record that needed them."""
        weight = self.card['axes']['weight']
        self.assertEqual(weight.value, 1100.0)
        self.assertEqual(weight.status, TRUSTED)
        self.assertEqual(self.cases['B0GM19PXKV']['package']['item_weight_origin'],
                         'dimensions')
        self.assertTrue(any(e.field == 'content.aplus' for e in weight.evidence))

    ALLOWED = {'CategoryProfile', 'Validated', 'Value', 'Evidence', 'validate',
               'search', 'TRUSTED', 'DISPUTED', 'UNVERIFIED', 'UNKNOWN',
               'NOT_CLAIMED', 'STRUCTURED', 'ATTRIBUTES', 'TEXT', 'PUBLISHED',
               'DERIVED', 'CONTRACT_VERSION'}

    def imported_from_validation(self):
        import ast
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and 'validation' in (node.module or ''):
                names.update(alias.name for alias in node.names)
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names
                             if 'validation' in alias.name)
        return names

    def test_the_category_imports_the_contract_and_no_rule(self):
        self.assertTrue(self.imported_from_validation() <= self.ALLOWED,
                        self.imported_from_validation() - self.ALLOWED)

    def test_the_category_never_disputes_or_promotes_a_measured_value(self):
        source = MODULE.read_text(encoding='utf-8')
        self.assertNotIn('.dispute(', source)
        self.assertNotIn('status = TRUSTED', source)

    def test_its_profile_carries_no_bands(self):
        self.assertEqual(CATEGORY.profile.nutrition_bands, {})
        self.assertIsNone(CATEGORY.profile.price_band)


class RealCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = load_cases()
        cls.cards = {asin: evaluate(rec) for asin, rec in cls.records.items()}

    # Written from the titles before the module ran over them.
    BACKPACKS = ('B003OSUDOS', 'B099PLV2F4', 'B09MCSCQGD', 'B0C1BVTCR1',
                 'B0DNZBZSR6', 'B0DTD4KXGD', 'B0G6KJYRSB', 'B0GCHZ4RYR',
                 'B00JPZ0B2S', 'B07V3FR8V3', 'B08Y5WHP98', 'B09MCRN848',
                 'B09MCT66NR', 'B0DVTDG2G2', 'B0DWXLM44P', 'B0DXJDZDB9',
                 'B0DXJJ861V', 'B0DXJLY2L2', 'B0DY8BN2BJ', 'B0F8NJ5TGL',
                 'B0GGJHD7M6', 'B0GGV5ZNFC', 'B0GM19PXKV')
    NOT_BACKPACKS = ('B07RW36W3K', 'B0B1VXPQF9', 'B0BRKHTWB1', 'B0CYBW4V5H',
                     'B000RE5A4U', 'B07DNZCRVX', 'B07P6M89HV', 'B0B2RC7F6M',
                     'B0B6H24C3H', 'B0CKTHQVXF', 'B0CYZKT2V5', 'B0D5R73HZ2',
                     'B0DCH9D4H9', 'B0DSPQ96PH', 'B0F8W25VDC', 'B0FHKWFVDR',
                     'B0FHL3BH68', 'B0GPNQ54YZ', 'B0GYS582DH', 'B0HCPS1THW')

    def test_the_case_set_is_complete(self):
        self.assertEqual(set(self.BACKPACKS) | set(self.NOT_BACKPACKS),
                         set(self.records))
        self.assertEqual(len(self.records), 43)

    def test_classification_holds_on_the_real_titles(self):
        for asin in self.BACKPACKS:
            with self.subTest(asin=asin, expect='school backpack'):
                self.assertEqual(self.cards[asin]['category'].value, KEY)
        for asin in self.NOT_BACKPACKS:
            with self.subTest(asin=asin, expect='other'):
                self.assertEqual(self.cards[asin]['category'].value, 'other')

    def test_the_first_graders_set_and_the_satchel_node_are_excluded(self):
        self.assertIn('Schulranzen Set',
                      self.cards['B0GYS582DH']['category'].notes[0])
        self.assertIn('primary-school satchel sets',
                      self.cards['B0CYZKT2V5']['category'].notes[0])

    def test_trusted_weights_after_the_generic_changes(self):
        """3 of the 43 records before the dimensions row and the A+ copy were
        read, 10 after -- nine of them school backpacks, among them all five
        Satch Pack variants and the Coocazoo Porter, whose weight is on the
        page exactly twice."""
        trusted = sorted(asin for asin, card in self.cards.items()
                         if card['category'].value == KEY
                         and card['axes']['weight'].status == TRUSTED)
        self.assertEqual(trusted, sorted((
            'B09MCSCQGD', 'B0DNZBZSR6', 'B0DWXLM44P', 'B0DXJDZDB9',
            'B0DXJJ861V', 'B0DXJLY2L2', 'B0GGJHD7M6', 'B0GGV5ZNFC',
            'B0GM19PXKV')))

    def test_a_prose_only_weight_stays_unverified(self):
        weight = self.cards['B09MCRN848']['axes']['weight']   # Coocazoo Mate
        self.assertEqual(weight.value, 1250.0)
        self.assertEqual(weight.status, UNVERIFIED)

    def test_the_two_ergonomic_brands_state_their_height_ranges(self):
        self.assertEqual(self.cards['B0GM19PXKV']['axes']['body_height'].value,
                         '140–180 cm')
        self.assertEqual(self.cards['B09MCRN848']['axes']['body_height'].value,
                         '135–180 cm')

    def test_the_warranty_row_is_read_where_it_exists(self):
        for asin, years in (('B0GGV5ZNFC', 4.0), ('B0GGJHD7M6', 4.0),
                            ('B00JPZ0B2S', 20.0), ('B003OSUDOS', 20.0)):
            with self.subTest(asin=asin):
                self.assertEqual(self.cards[asin]['claims']['manufacturer_warranty'].status,
                                 TRUSTED)
                self.assertEqual(self.cards[asin]['axes']['warranty_years'].value, years)
        for asin in ('B0GM19PXKV', 'B0F8NJ5TGL', 'B0DVTDG2G2'):
            with self.subTest(asin=asin, expect='no warranty stated'):
                self.assertEqual(self.cards[asin]['claims']['manufacturer_warranty'].status,
                                 NOT_CLAIMED)

    def test_the_satch_pack_states_reflectors_and_an_adjustable_back(self):
        claims = self.cards['B0GM19PXKV']['claims']
        self.assertEqual(claims['reflective_elements'].status, TRUSTED)
        self.assertEqual(claims['adjustable_back'].status, TRUSTED)

    def test_ranking_prefers_the_lightest_bag_that_states_both_claims(self):
        cards = list(self.cards.values())
        text = report.rank_text(cards, require=('reflective_elements',
                                                'manufacturer_warranty'), unit='g')
        self.assertIn('ranked by weight of the bag (lower first)', text)
        first = [line for line in text.splitlines()
                 if line.strip().startswith('1.')][0]
        self.assertIn('B0GGV5ZNFC', first)
        self.assertIn('1000 g', first)

    def test_a_directionless_axis_is_shown_and_refused_as_a_ranking(self):
        text = report.rank_text(list(self.cards.values()), 'volume')
        self.assertIn('declares no better direction', text)

    def test_every_card_renders(self):
        for asin, card in self.cards.items():
            with self.subTest(asin=asin):
                self.assertTrue(report.card_text(card))
                json.dumps(report.card_json(card))

    def test_the_summary_renders(self):
        self.assertIn('school backpack',
                      report.summary_text(list(self.cards.values())))

    def test_two_bags_compare_on_weight(self):
        text = ' '.join(report.compare_text(self.cards['B0GGV5ZNFC'],
                                            self.cards['B0GGJHD7M6']).split())
        self.assertIn('lighter', text)


if __name__ == '__main__':
    unittest.main()
