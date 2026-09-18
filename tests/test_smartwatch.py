"""Tests for the smartwatch category -- the fifth, and the first written through R15.

Two jobs, as for the categories before it. The category's own rules: a
positional title classifier that tells a smartwatch from a strap, a fitness
band, a GPS tracker and a dive computer; six vendor statements named as the
trial's engineering proposal named them; price as the one ranked axis with
the stated depth rating, ATM rating, runtimes and display technology shown
and never ranked. And the contract: the price on a card is the very object
:func:`validate` produced, the module names no status for a measured value it
did not read from prose, and it imports no rule.

The cases are the 55 unique records of the three committed probe feeds of the
third R13 conversational trial (2026-09-18), merged on ASIN. Everything a
smartwatch buyer with a scuba trip asked about is decided here by the vendor's
own words and by nothing else, which is the honest limit the trial's hand
reading had too; the tests hold the code to the same limit.
"""

import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shopping_advisor.analysis import report  # noqa: E402
from shopping_advisor.analysis.categories.smartwatch import (  # noqa: E402
    CATEGORY, KEY, classify, evaluate)
from shopping_advisor.validation import (  # noqa: E402
    NOT_CLAIMED, TEXT, TRUSTED, UNKNOWN, UNVERIFIED, validate)

HERE = pathlib.Path(__file__).resolve().parent
CASES = HERE / 'cases' / 'smartwatch_v1.jsonl.gz'
MODULE = (HERE.parent / 'shopping_advisor' / 'analysis' / 'categories' / 'smartwatch.py')


def load_cases():
    with gzip.open(CASES, 'rt', encoding='utf-8') as handle:
        return {record['asin']: record for record in map(json.loads, handle)}


def record(**overrides):
    base = {
        'asin': 'B000000000', 'title': 'Garmin Testwatch GPS-Multisport-Smartwatch',
        'brand': 'Test', 'product_url': 'https://www.amazon.de/dp/B000000000',
        'search_query': 'smartwatch', 'breadcrumbs': [],
        'price': {'amount': 299.0, 'currency': 'EUR'}, 'unit_price': {},
        'package': {}, 'raw_tables': {},
        'content': {'feature_bullets': [], 'description': '',
                    'important_information': [], 'aplus': {}},
        'food': {'ingredients': {}, 'allergens': [], 'nutrition': {}},
    }
    base.update(overrides)
    return base


class Classification(unittest.TestCase):
    def assertOther(self, title, phrase, **kw):
        value = classify(record(title=title, **kw))
        self.assertEqual((value.value, value.status), ('other', TRUSTED), title)
        self.assertIn(phrase, value.notes[0])

    def test_a_smartwatch_and_a_gps_sports_watch_are_smartwatches(self):
        for title in ('HUAWEI Watch Ultimate 2 Smartwatch, Sportuhr mit GPS, 20 ATM',
                      'Polar Grit X2 Pro Outdoor GPS-Sportuhr mit Saphirglas',
                      'Garmin Instinct 3 45mm SOLAR – GPS-Multisport-Smartwatch',
                      'Apple Watch Ultra 3 GPS + Cellular 49 mm Premium Smartwatch'):
            with self.subTest(title=title):
                value = classify(record(title=title))
                self.assertEqual((value.value, value.status), (KEY, TRUSTED))

    def test_a_dive_computer_that_names_no_smartwatch_function_is_a_dive_computer(self):
        self.assertOther('Cressi GOA Tauchcomputer und Uhr', 'dive computer')
        self.assertOther('SUUNTO D5 Tauchcomputer mit Farbdisplay, wasserdicht bis 100 m',
                         'dive computer')
        value = classify(record(title='Garmin Descent G2, 46 mm, GPS-Tauchcomputer/Smartwatch'))
        self.assertEqual(value.value, KEY, 'a smartwatch that dives is a smartwatch')

    def test_a_band_or_tracker_heading_the_title_names_the_listing(self):
        self.assertOther('Xiaomi Smart Band 10, Smart Watch, Fitness-Tracker', 'band or tracker')
        self.assertOther('SOLAR Finder 4G GPS-Tracker mit 3 Monate Premium ABO', 'band or tracker')
        value = classify(record(title='Poounur Smartwatch Herren, 2.01" AMOLED, Fitness Tracker'))
        self.assertEqual(value.value, KEY, 'a tracker word after the watch word is a feature')

    def test_an_accessory_noun_heading_the_title_or_naming_the_watch_it_fits_is_an_accessory(self):
        self.assertOther('22mm Nylon Armband Kompatibel mit Garmin Fenix 8', 'accessory')
        self.assertOther('Hülle Kompatibel mit Garmin Tactix 8 51mm', 'accessory')
        self.assertOther('USB-C zu Garmin Watch Ladeadapter 4-Pack', 'accessory')
        self.assertOther('Smartwatch Armband kompatibel mit Garmin Venu', 'accessory')
        value = classify(record(title='Apple Watch Ultra 3 Premium Smartwatch mit Ozean Armband'))
        self.assertEqual(value.value, KEY, "a watch's own strap after the watch word is the watch's")
        value = classify(record(title='Garmin Descent MK3 – 43 mm Edelstahl mit nebelgrauem Silikonband',
                                content={'feature_bullets': [], 'description': 'Edelstahl-Smartwatch',
                                         'important_information': [], 'aplus': {}}))
        self.assertEqual(value.value, KEY, '"Silikonband" is not an accessory noun')

    def test_a_title_naming_no_class_is_accepted_only_from_the_node_or_the_body_as_unverified(self):
        bare = 'Garmin Descent Mk3i 43mm Carbon Grey DLC Titanium Black with Silicone Strap'
        value = classify(record(title=bare, breadcrumbs=['Elektronik & Foto', 'Tragbare Technologie',
                                                          'Smartwatches']))
        self.assertEqual((value.value, value.status), (KEY, UNVERIFIED))
        self.assertTrue(any(e.field == 'breadcrumbs' for e in value.evidence))
        value = classify(record(title=bare, content={
            'feature_bullets': ['Ein helles AMOLED-Display'], 'description': 'Edelstahl-Smartwatch mit Band',
            'important_information': [], 'aplus': {}}))
        self.assertEqual((value.value, value.status), (KEY, UNVERIFIED))
        self.assertTrue(any(e.field.startswith('content.') for e in value.evidence))
        self.assertOther(bare, 'names neither')

    def test_a_listing_with_no_title_is_unclassified_not_excluded(self):
        self.assertEqual(classify(record(title='')).status, UNKNOWN)


class Claims(unittest.TestCase):
    def claims(self, *bullets, description=''):
        card = evaluate(record(content={'feature_bullets': list(bullets), 'description': description,
                                        'important_information': [], 'aplus': {}}))
        return card['claims']

    def test_a_dive_function_is_a_stated_mode_not_the_word_diving(self):
        found = self.claims('Mehrere Tauchmodi und DiveView-Karten')['scuba_dive_mode']
        self.assertEqual((found.value, found.status, found.source), (True, TRUSTED, TEXT))
        found = self.claims('Der bewährte Bühlmann ZHL-16C Dekompressionsalgorithmus')['scuba_dive_mode']
        self.assertEqual((found.value, found.status), (True, TRUSTED))
        for text in ('Ob Laufen, Radfahren, Surfen oder Tauchen: über 80 Sport-Apps',
                     'Erkennung von Schlafapnoe über Nacht',
                     'wassergeschützt bis 100 m – perfekt zum Schwimmen, Tauchen und Wassersport'):
            with self.subTest(text=text):
                self.assertEqual(self.claims(text)['scuba_dive_mode'].status, NOT_CLAIMED)
        self.assertEqual(self.claims('Nicht zum Tauchen geeignet')['scuba_dive_mode'].status,
                         NOT_CLAIMED)

    def test_dive_capable_and_freediving_are_not_a_scuba_function(self):
        # Method version 2 (R15, the second adaptation). Version 1 read all
        # three of these as a stated dive function; the study revision over
        # the trial's plan found a 178 EUR watch credited with one on the
        # third, and the plan's dive_computer condition says a water-resistance
        # sentence never satisfies it.
        for text in ('Wasserdichte Tasten machen sie tauchfähig bis 40m Tiefe.',
                     'für anspruchsvolle Unterwasseraktivitäten konzipiert – inklusive '
                     'Freitauchen bis zu 45 Metern.',
                     '40 Meter Tauchleistung, mit Unterstützung für Apnoe-Tauchaktivitäten',
                     'Die weltweit erste Smartwatch für Tauchgänge in bis zu 150 Metern'):
            with self.subTest(text=text):
                self.assertEqual(self.claims(text)['scuba_dive_mode'].status, NOT_CLAIMED)
        found = self.claims('Tauchtechnologie für bis zu 150 m Tiefe: Die weltweit erste Smartwatch '
                            'für Tauchgänge in bis zu 150 Metern')['scuba_dive_mode']
        self.assertEqual((found.value, found.status), (True, TRUSTED))

    def test_nfc_and_a_payment_service_are_one_claim_and_payment_in_germany_is_none(self):
        found = self.claims('bezahlen Sie kontaktlos mit Garmin Pay')['nfc_payment']
        self.assertEqual((found.value, found.status), (True, TRUSTED))
        self.assertNotIn('payment_usable_in_germany', CATEGORY.claim_keys)

    def test_a_bare_nfc_is_connectivity_and_not_a_payment_statement(self):
        # Method version 3 (R15's fourth adaptation): version 2 credited the
        # connectivity row "Bluetooth, GPS, NFC" as a payment statement on six
        # committed cards. A chip is not a payment function.
        for text in ('Konnektivitätstechnologie: Bluetooth, GPS, NFC',
                     'NFC, Bluetooth 5.2, WLAN', 'Wallet für Bordkarten'):
            with self.subTest(text=text):
                self.assertEqual(self.claims(text)['nfc_payment'].status, NOT_CLAIMED)
        for text in ('Kontaktlos bezahlen mit Huawei Wallet', 'NFC-Zahlungen mit Garmin Pay',
                     'Google Wallet und kontaktloses Zahlen', 'Bezahlen mit Samsung Pay'):
            with self.subTest(text=text):
                self.assertEqual(self.claims(text)['nfc_payment'].value, True)

    def test_android_named_is_a_statement_and_iphone_only_is_not_claimed(self):
        self.assertEqual(self.claims('Kompatibel mit iOS- und Android-Geräten')['android_compatible'].value, True)
        for text in ('Erfordert ein iPhone mit iOS 26', 'Nur mit iPhone kompatibel'):
            with self.subTest(text=text):
                self.assertEqual(self.claims(text)['android_compatible'].status, NOT_CLAIMED)

    def test_a_sensor_present_is_the_claim_and_nothing_about_its_quality(self):
        found = self.claims('Herzfrequenzmessung am Handgelenk, barometrischer Höhenmesser, Multiband-GPS')
        for key in ('heart_rate_sensor', 'barometric_altimeter', 'gps'):
            with self.subTest(key=key):
                self.assertEqual(found[key].value, True)
        self.assertNotIn('quality', CATEGORY.claim('heart_rate_sensor').label.lower())

    def test_an_unstated_criterion_is_not_claimed_rather_than_false(self):
        card = evaluate(record(title='Testwatch Smartwatch Herren', content={
            'feature_bullets': ['Ein helles Display'], 'description': '',
            'important_information': [], 'aplus': {}}))
        for key, value in card['claims'].items():
            with self.subTest(key=key):
                self.assertEqual((value.value, value.status), (False, NOT_CLAIMED))
                self.assertIn('not the same as it being untrue', value.notes[0])


class Axes(unittest.TestCase):
    def axes(self, *bullets, title='Garmin Testwatch GPS-Multisport-Smartwatch'):
        return evaluate(record(title=title, content={
            'feature_bullets': list(bullets), 'description': '', 'important_information': [],
            'aplus': {}}))['axes']

    def test_a_depth_in_metres_is_read_and_an_atm_rating_is_never_converted(self):
        axes = self.axes('wasserdicht bis 100 m', '10 ATM Wasserdichtigkeit')
        self.assertEqual((axes['depth_rating_m'].value, axes['depth_rating_m'].unit,
                          axes['depth_rating_m'].status), (100.0, 'm', UNVERIFIED))
        self.assertEqual((axes['water_resistance_atm'].value, axes['water_resistance_atm'].unit),
                         (10.0, 'atm'))
        atm_only = self.axes('5ATM Wasserdichtigkeit')
        self.assertEqual(atm_only['depth_rating_m'].status, UNKNOWN)
        self.assertEqual(atm_only['water_resistance_atm'].value, 5.0)

    def test_runtimes_keep_their_mode_and_standby_is_not_one(self):
        axes = self.axes('Akkulaufzeit: bis zu 10 Tage im Smartwatch-Modus und bis zu 30 Stunden im Tauchmodus',
                         'bis zu 40 Stunden GPS-Tracking mit optimaler Genauigkeit')
        self.assertEqual((axes['smartwatch_runtime_days'].value, axes['smartwatch_runtime_days'].unit),
                         (10.0, 'days'))
        self.assertEqual((axes['gps_runtime_hours'].value, axes['gps_runtime_hours'].unit), (40.0, 'h'))
        standby = self.axes('eine Standby-Zeit von bis zu 25 Tagen')
        self.assertEqual(standby['smartwatch_runtime_days'].status, UNKNOWN)

    def test_no_runtime_axis_has_a_ranking_direction(self):
        for key in ('depth_rating_m', 'water_resistance_atm', 'gps_runtime_hours',
                    'smartwatch_runtime_days', 'display_type'):
            with self.subTest(axis=key):
                self.assertEqual(CATEGORY.axis(key).better, '')
                self.assertTrue(CATEGORY.axis(key).caveat)
        self.assertEqual(CATEGORY.default_axis, 'price')
        self.assertEqual(CATEGORY.axis('price').better, 'lower')

    def test_the_display_technology_is_a_name_and_transflective_reads_as_mip(self):
        self.assertEqual(self.axes('brillantes AMOLED Display')['display_type'].value, 'AMOLED')
        self.assertEqual(self.axes('transflektives MIP-Display')['display_type'].value, 'MIP')
        self.assertEqual(self.axes('ein helles Display')['display_type'].status, UNKNOWN)


class ContractUse(unittest.TestCase):
    """The criterion R2 finished against, asserted on the fifth category."""

    def setUp(self):
        self.cases = load_cases()
        self.card = evaluate(self.cases['B0CZ6S2SX7'])   # Suunto Ocean

    def test_the_price_is_the_validation_layers_value(self):
        self.assertIs(self.card['axes']['price'], self.card['validated'].price)

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
                names.update(alias.name for alias in node.names if 'validation' in alias.name)
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

    def test_the_lifecycle_is_an_experiment_that_says_what_it_does_not_establish(self):
        lifecycle = CATEGORY.lifecycle
        self.assertEqual((lifecycle.state, lifecycle.decision), ('experiment', 'retained'))
        self.assertTrue(any('ordering of battery life' in item
                            for item in lifecycle.applicability.not_established))
        self.assertIn('r15--controlled-task-driven-capability-adaptation', lifecycle.milestones)


class RealCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = load_cases()
        cls.cards = {asin: evaluate(rec) for asin, rec in cls.records.items()}

    # Written from the titles before the module ran over them. The first two
    # feeds (48 unique) were the development set; the seven ASIN-fetched
    # records (CHECK) were run once when the rules were fixed.
    SMARTWATCHES = ('B0CZ6S2SX7', 'B0CZ6G2XC1', 'B0CZ6KJVZZ', 'B0DX21FHWP', 'B0DX1T7JQ3',
                    'B0CNSG78ZQ', 'B0CNSF5DK2', 'B0FL1YW13Z', 'B0DBV9ZV69', 'B0FL2JXW3B',
                    'B0FQFJQK5K', 'B0FQFBW86Q', 'B0DSG9VCRH', 'B0DSC8GLRX', 'B0BXM1RQR5',
                    'B0DC6ZD321', 'B0DC71V3ZD', 'B0DC6ZD31R', 'B0DFLTQTDB', 'B0H7HZNYRC',
                    'B0H7J5FZ99', 'B0HFSHKPJL', 'B0G1ZGK7MV', 'B0FR8LXTWP', 'B0CXHJRWN9',
                    'B0HCN4V5KD', 'B0HG9QLSLY', 'B0GT96NZX8', 'B0H98JPZRT', 'B0GVMTW5CD',
                    'B0H6F8LPVX')
    UNVERIFIED_SMARTWATCHES = ('B0CP819M6S',)
    DIVE_COMPUTERS = ('B0CRDZ35S8', 'B082B8WMBD', 'B0DQ2MHKHW', 'B0719H6GGH', 'B07P1WV8VP',
                      'B0G1S9FV62')
    ACCESSORIES = ('B0F9WXLL2X', 'B0H8P8FT5Q', 'B0D4F71WQC', 'B07D6HM812', 'B09V7CJZWQ',
                   'B07DJ92CFR', 'B09TRS84XP')
    BANDS_AND_TRACKERS = ('B0DYF82545', 'B0GNNFBJ3H')
    NAMES_NO_CLASS = ('B0DFLYZ28M',)
    CHECK = {'B0CPF5C7XH': (KEY, UNVERIFIED), 'B0CPF2Q5PB': (KEY, TRUSTED),
             'B0CNSCY41D': (KEY, TRUSTED), 'B0B45XTKRN': (KEY, TRUSTED),
             'B0HFP18YKP': (KEY, TRUSTED), 'B0FPMK7KYX': (KEY, TRUSTED),
             'B0GKPJLHNH': (KEY, TRUSTED)}

    def test_the_case_set_is_complete(self):
        listed = (set(self.SMARTWATCHES) | set(self.UNVERIFIED_SMARTWATCHES)
                  | set(self.DIVE_COMPUTERS) | set(self.ACCESSORIES)
                  | set(self.BANDS_AND_TRACKERS) | set(self.NAMES_NO_CLASS) | set(self.CHECK))
        self.assertEqual(listed, set(self.records))
        self.assertEqual(len(self.records), 55)
        self.assertEqual(len(self.records) - len(self.CHECK), 48)

    def test_classification_holds_on_the_real_titles(self):
        for asin in self.SMARTWATCHES:
            with self.subTest(asin=asin, expect='smartwatch'):
                self.assertEqual((self.cards[asin]['category'].value, self.cards[asin]['category'].status),
                                 (KEY, TRUSTED))
        for asin in self.UNVERIFIED_SMARTWATCHES:
            with self.subTest(asin=asin, expect='smartwatch, from the node'):
                self.assertEqual((self.cards[asin]['category'].value, self.cards[asin]['category'].status),
                                 (KEY, UNVERIFIED))
        for group in (self.DIVE_COMPUTERS, self.ACCESSORIES, self.BANDS_AND_TRACKERS, self.NAMES_NO_CLASS):
            for asin in group:
                with self.subTest(asin=asin, expect='other'):
                    self.assertEqual(self.cards[asin]['category'].value, 'other')

    def test_the_check_set_classifies_as_expected_once_the_rules_were_fixed(self):
        for asin, expected in self.CHECK.items():
            with self.subTest(asin=asin):
                value = self.cards[asin]['category']
                self.assertEqual((value.value, value.status), expected)

    def test_every_declared_decline_is_proven_by_a_case(self):
        cited = {asin for decline in CATEGORY.lifecycle.applicability.declines for asin in decline.asins}
        self.assertEqual(cited, set(self.DIVE_COMPUTERS) | set(self.ACCESSORIES) | set(self.BANDS_AND_TRACKERS))

    # The vendor states a scuba function: a dive mode, a dive computer or a
    # decompression model, in the fields the search reads.
    STATE_A_DIVE_FUNCTION = ('B0CZ6S2SX7', 'B0CZ6G2XC1', 'B0CZ6KJVZZ', 'B0DX21FHWP', 'B0DX1T7JQ3',
                             'B0CNSG78ZQ', 'B0CNSF5DK2', 'B0CNSCY41D', 'B0CPF5C7XH', 'B0CPF2Q5PB',
                             'B0B45XTKRN', 'B0FL1YW13Z', 'B0FL2JXW3B', 'B0GKPJLHNH', 'B0DBV9ZV69')
    # Method version 1 credited these five on "tauchfähig bis 40m" (fenix 8,
    # three sizes), "Apnoe-Tauchaktivitäten" and "Tauchleistung" (fenix 8 Pro)
    # and "Freitauchen bis zu 45 Metern" (KOSPET Tank T4). The fenix 8's A+
    # image alt text says "Tauchfunktion", which the search does not read;
    # Garmin's manual documents the dive apps, and a manual is not the page.
    DIVE_CAPABLE_OR_FREEDIVING_ONLY = ('B0DC6ZD321', 'B0DC71V3ZD', 'B0DC6ZD31R', 'B0FPMK7KYX',
                                       'B0FR8LXTWP')

    def test_the_dive_function_is_stated_where_the_page_states_a_scuba_function(self):
        for asin in self.STATE_A_DIVE_FUNCTION:
            with self.subTest(asin=asin):
                self.assertEqual(self.cards[asin]['claims']['scuba_dive_mode'].value, True)
        for asin in self.DIVE_CAPABLE_OR_FREEDIVING_ONLY + ('B0DSG9VCRH', 'B0FQFJQK5K',
                                                            'B0HFP18YKP', 'B0HCN4V5KD'):
            with self.subTest(asin=asin):
                self.assertEqual(self.cards[asin]['claims']['scuba_dive_mode'].status, NOT_CLAIMED)
        stated = [asin for asin, card in self.cards.items()
                  if card['category'].value == KEY and card['claims']['scuba_dive_mode'].value]
        self.assertEqual(sorted(stated), sorted(self.STATE_A_DIVE_FUNCTION))

    # Method version 2 also credited these five Huawei listings on a
    # connectivity row's "NFC" (both Watch Ultimate 2, two GT 7 Pro, the Watch
    # D3); version 3 reads a payment service or a contactless-payment phrase,
    # and fifteen keep the claim on one -- the Amazfit Active Max among them,
    # on "Mit Zepp Pay und NFC bezahlst du", which the operating agent's
    # first-quote reading of the revision-8 study's cards had filed under the
    # bare word; the review itself named the Huawei listings only.
    STATE_A_PAYMENT_SERVICE = ('B0BXM1RQR5', 'B0CNSF5DK2', 'B0CNSG78ZQ', 'B0CP819M6S', 'B0CPF2Q5PB',
                               'B0CPF5C7XH', 'B0DC6ZD31R', 'B0DC6ZD321', 'B0DC71V3ZD', 'B0DSC8GLRX',
                               'B0DSG9VCRH', 'B0DX1T7JQ3', 'B0DX21FHWP', 'B0G1ZGK7MV', 'B0HFP18YKP')
    NFC_ONLY = ('B0FL1YW13Z', 'B0FL2JXW3B', 'B0H7HZNYRC', 'B0H7J5FZ99', 'B0HFSHKPJL')

    def test_the_payment_claim_needs_a_payment_service_not_a_chip(self):
        for asin in self.STATE_A_PAYMENT_SERVICE:
            with self.subTest(asin=asin):
                self.assertEqual(self.cards[asin]['claims']['nfc_payment'].value, True)
        for asin in self.NFC_ONLY:
            with self.subTest(asin=asin):
                self.assertEqual(self.cards[asin]['claims']['nfc_payment'].status, NOT_CLAIMED)
        stated = [asin for asin, card in self.cards.items()
                  if card['category'].value == KEY and card['claims']['nfc_payment'].value]
        self.assertEqual(sorted(stated), sorted(self.STATE_A_PAYMENT_SERVICE))

    def test_the_three_unpriced_listings_have_no_price_value(self):
        for asin in ('B0DC6ZD321', 'B0CPF5C7XH', 'B0B45XTKRN'):
            with self.subTest(asin=asin):
                self.assertIsNone(self.cards[asin]['axes']['price'].value)

    def test_runtimes_are_read_with_their_mode_on_the_real_pages(self):
        ocean = self.cards['B0CZ6S2SX7']['axes']
        self.assertEqual(ocean['gps_runtime_hours'].value, 40.0)
        mk3 = self.cards['B0CPF5C7XH']['axes']
        self.assertEqual(mk3['smartwatch_runtime_days'].value, 10.0)
        self.assertEqual(mk3['depth_rating_m'].value, 200.0)
        cheap = self.cards['B0HCN4V5KD']['axes']
        self.assertEqual(cheap['water_resistance_atm'].value, 5.0)
        instinct = self.cards['B0DSG9VCRH']['axes']
        self.assertEqual(instinct['display_type'].value, 'MIP')

    def test_the_price_ranking_refuses_nothing_and_ranks_only_watches(self):
        ranked = report.ranking(list(self.cards.values()), axis_key='price')
        self.assertIsNone(ranked['refusal'])
        offers = {row['asin'] for row in ranked['rows']}
        self.assertFalse(offers & (set(self.DIVE_COMPUTERS) | set(self.ACCESSORIES)))
        self.assertNotIn('B0DC6ZD321', offers)


class ProvisionalMethod(unittest.TestCase):
    """R16 review 1's debt, assigned to R15: a report resting on an experiment says so."""

    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.brief = HERE / 'studies' / f'.tmp-smartwatch-{self.directory.name}.toml'
        self.brief.write_text(
            'brief_version = 1\n'
            'id = "smartwatch-price-test"\n'
            'question = "Cheapest smartwatch that states a dive function, among the committed cases?"\n'
            'category = "smartwatch"\n'
            'marketplace = "www.amazon.de"\n'
            'inputs = ["../cases/smartwatch_v1.jsonl.gz"]\n'
            '[constraints]\naxis = "price"\nunit = "EUR"\nrequire_claims = ["scuba_dive_mode"]\n'
            'shortlist = 3\nminimum_candidates = 2\n'
            '[freshness]\nas_of = "2026-09-18"\n',
            encoding='utf-8')
        self.addCleanup(lambda: self.brief.unlink(missing_ok=True))

    def test_the_report_and_the_ranking_artifact_say_the_method_is_provisional(self):
        from shopping_advisor.study import bundle
        directory, manifest = bundle.run(str(self.brief), directory=str(self.directory / 'study'))
        text = (directory / 'report.md').read_text(encoding='utf-8')
        self.assertIn('**Provisional method.**', text)
        self.assertIn('`smartwatch`', text.split('**Provisional method.**')[1][:80])
        self.assertIn('ordering of battery life', text)
        ranking = json.loads((directory / 'ranking.json').read_text(encoding='utf-8'))
        self.assertEqual(ranking['method']['state'], 'experiment')
        self.assertEqual(ranking['method']['category'], 'smartwatch')
        self.assertEqual(bundle.verify(directory)[1], [])

    def test_a_maintained_category_writes_no_such_line(self):
        from shopping_advisor.study import bundle
        directory, _ = bundle.run(str(HERE / 'studies' / 'pasta-bronze-die.toml'),
                                  directory=str(self.directory / 'pasta'))
        self.assertNotIn('Provisional method', (directory / 'report.md').read_text(encoding='utf-8'))
        self.assertNotIn('method', json.loads((directory / 'ranking.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
