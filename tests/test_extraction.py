"""Regression tests for the PDP extraction primitives.

These run against small HTML fixtures modelled on the structures observed on
live amazon.de PDPs, so they stay fast and offline. The shapes below (the
``parseJSON`` image blob, the malformed nutrition table, the bidi-marked
detail bullets) are copied from real pages -- they are exactly the cases a
naive parser gets wrong.
"""

import unittest

from parsel import Selector

from shopping_advisor.extraction import PdpExtractor, for_domain
from shopping_advisor.extraction import blocks
from shopping_advisor.extraction.marketplaces import UNITS
from shopping_advisor.extraction.text import (clean, decode_entities, node_text,
                                            parse_number, parse_quantity)

DE = for_domain('www.amazon.de')


class TextPrimitives(unittest.TestCase):

    def test_number_formats_seen_on_one_page(self):
        # A single German PDP mixes all of these.
        self.assertEqual(parse_number('12,9g'), 12.9)
        self.assertEqual(parse_number('3000.0 gramm'), 3000.0)
        self.assertEqual(parse_number('1.234,56 €'), 1234.56)
        self.assertEqual(parse_number('2.500 g'), 2500.0)
        self.assertEqual(parse_number('1,5 kg'), 1.5)
        self.assertIsNone(parse_number('keine Angabe'))

    def test_number_respects_locale(self):
        self.assertEqual(parse_number('1,500', decimal_sep=','), 1.5)
        self.assertEqual(parse_number('1,500', decimal_sep='.'), 1500.0)

    def test_clean_joins_split_inline_spans_without_a_gap(self):
        self.assertEqual(clean('HARTWEIZENGRIEß , Wasser.'),
                         'HARTWEIZENGRIEß, Wasser.')
        self.assertEqual(clean('Kann Spuren von Ei , Soja enthalten'),
                         'Kann Spuren von Ei, Soja enthalten')
        self.assertEqual(clean('DINKEL -VOLLKORNMEHL'), 'DINKEL-VOLLKORNMEHL')
        # but a negative number is not a split compound
        self.assertEqual(clean('haltbar bis -18 Grad'), 'haltbar bis -18 Grad')

    def test_clean_strips_bidi_marks(self):
        self.assertEqual(clean('Marke ‏ : ‎'), 'Marke:')

    def test_decode_entities_only_when_double_escaped(self):
        self.assertEqual(decode_entities('13,56&nbsp;&euro; pro kg'),
                         '13,56 € pro kg')
        self.assertEqual(decode_entities('Barilla & Co'), 'Barilla & Co')

    def test_node_text_ignores_script_and_style(self):
        html = ('<div><style>.x{color:red}</style>Echter Text'
                '<script>var a=1;</script></div>')
        self.assertEqual(node_text(Selector(html).css('div')), 'Echter Text')

    def test_parse_quantity_handles_multipacks(self):
        self.assertEqual(parse_quantity('500 Gramm', UNITS), (500.0, 'g', 500.0))
        self.assertEqual(parse_quantity('1,5 kg', UNITS), (1.5, 'kg', 1500.0))
        self.assertEqual(parse_quantity('6 x 500 g', UNITS), (3000.0, 'g', 3000.0))
        self.assertIsNone(parse_quantity('Paket', UNITS))


class Marketplaces(unittest.TestCase):

    def test_label_mapping(self):
        self.assertEqual(DE.attribute_key('Herkunftsland'), 'country_of_origin')
        self.assertEqual(DE.attribute_key('Anzahl der Artikel'), 'item_count')
        self.assertIsNone(DE.attribute_key('Völlig unbekanntes Feld'))

    def test_nutrient_mapping_prefers_longest_alias(self):
        self.assertEqual(DE.nutrient_key('davon gesättigte Fettsäuren'),
                         'saturated_fat_g')
        self.assertEqual(DE.nutrient_key('Fett'), 'fat_g')
        self.assertEqual(DE.nutrient_key('— Eiweiß'), 'protein_g')

    def test_byline_cleanup(self):
        self.assertEqual(DE.clean_byline('Besuche den Valle del Crati-Store'),
                         'Valle del Crati')
        self.assertEqual(DE.clean_byline('Marke: Naturata'), 'Naturata')

    def test_unknown_marketplace_falls_back_without_raising(self):
        self.assertEqual(for_domain('www.amazon.co.jp').language, 'en')


class ImageBlob(unittest.TestCase):
    """amazon.de wraps the gallery in A.$.parseJSON('...'), not a bare list."""

    PARSEJSON = (
        "'colorImages': { 'initial': A.$.parseJSON('"
        '[{"hiRes":"https://m.media-amazon.com/images/I/61A.jpg",'
        '"thumb":"https://m.media-amazon.com/images/I/31A.jpg",'
        '"variant":"MAIN","altText":null},'
        '{"hiRes":null,"large":"https://m.media-amazon.com/images/I/41B.jpg",'
        '"variant":"PT01","altText":"Nudeln"}]'
        "') },")

    LITERAL = ("'colorImages': { 'initial': "
               '[{"hiRes":"https://example.test/a.jpg","variant":"MAIN"}]},')

    def test_parsejson_variant(self):
        records = blocks.image_records(self.PARSEJSON)
        self.assertEqual(len(records), 2)
        self.assertEqual(blocks.best_image_url(records[0]),
                         'https://m.media-amazon.com/images/I/61A.jpg')
        # hiRes is null on the second record; large is the next best.
        self.assertEqual(blocks.best_image_url(records[1]),
                         'https://m.media-amazon.com/images/I/41B.jpg')

    def test_literal_variant(self):
        records = blocks.image_records(self.LITERAL)
        self.assertEqual(blocks.best_image_url(records[0]),
                         'https://example.test/a.jpg')

    def test_absent_blob_is_none_not_an_error(self):
        self.assertIsNone(blocks.image_records('<html>no gallery here</html>'))


NUTRITION_HTML = """
<div id="nic-eu-nutrition-facts">
  <span id="nic-nutrition-summary-serving">Pro 100g</span>
  <table id="nic-eu-nutrition-facts-table">
    <tr><td><span>Energie</span></td><td><span>1483kJ</span></td>
    <tr><td><span>— </span><span>Fett</span></td><td><span>1,2g</span></td>
    <tr><td><span>— </span><span>Kohlenhydrate</span></td><td><span>71g</span></td>
    <tr><td><span>— </span><span>Ballaststoffe</span></td><td><span>3,5g</span></td>
    <tr><td><span>— </span><span>Protein</span></td><td><span>12g</span></td>
  </table>
</div>
<div id="nic-ingredients-content">
  <span>Zutaten: </span><span>HARTWEIZENGRIEß</span><span>, Wasser.</span>
</div>
"""

TABLE_HTML = """
<div id="productOverview_feature_div"><table class="a-normal a-spacing-micro">
  <tr><td><span>Marke</span></td><td><span>Naturata</span></td></tr>
  <tr><td><span>Artikelgewicht</span></td><td><span>500 Gramm</span></td></tr>
  <tr><td><span>Anzahl der Artikel</span></td><td><span>6</span></td></tr>
  <tr><td><span>Herkunftsland</span></td><td><span>Italien</span></td></tr>
</table></div>
<div id="detailBullets_feature_div"><ul><li><span class="a-list-item">
  <span>Hersteller ‏ : ‎</span><span>Naturata AG</span>
</span></li></ul></div>
"""


class KeyValueTables(unittest.TestCase):
    """amazon.de reaches the same <table> through several of the selectors in
    ``KV_TABLE_CSS``: #prodDetails wraps the tables that the more specific ids
    also match. Each table must be read exactly once, and no table may be lost
    because another one was already read."""

    NESTED_TABLES = """
    <div id="prodDetails">
      <table id="productDetails_techSpec_section_1">
        <tr><th>Marke</th><td>Naturata</td></tr>
        <tr><th>Artikelgewicht</th><td>500 Gramm</td></tr>
      </table>
      <table id="productDetails_detailBullets_sections1">
        <tr><th>ASIN</th><td>B000000001</td></tr>
        <tr><th>Im Angebot von Amazon.de seit</th><td>18. Oktober 2023</td></tr>
      </table>
    </div>
    """

    def test_every_table_is_read_exactly_once(self):
        pairs = blocks.key_value_tables(Selector(self.NESTED_TABLES))
        self.assertEqual(pairs, [
            ('Marke', 'Naturata'),
            ('Artikelgewicht', '500 Gramm'),
            ('ASIN', 'B000000001'),
            ('Im Angebot von Amazon.de seit', '18. Oktober 2023'),
        ])

    def test_result_does_not_depend_on_object_lifetimes(self):
        # Deduplication used to key on id(element). lxml frees an element
        # proxy once nothing refers to it and CPython then reuses the address,
        # so an unrelated table could inherit a seen id and be dropped. Forcing
        # collections between selector builds reproduced that.
        import gc

        expected = blocks.key_value_tables(Selector(self.NESTED_TABLES))
        for _ in range(20):
            selector = Selector(self.NESTED_TABLES)
            gc.collect()
            self.assertEqual(blocks.key_value_tables(selector), expected)


class PdpComposition(unittest.TestCase):

    def extract(self, html):
        return PdpExtractor(DE).extract(Selector(html), html, {'asin': 'B000000001'})

    def test_nutrition_table_and_ingredients(self):
        record = self.extract('<div id="productTitle">Pasta</div>' + NUTRITION_HTML)
        nutrition = record['food']['nutrition']
        self.assertEqual(nutrition['source'], 'nutrition_card')
        self.assertNotIn('confidence', nutrition,
                         'extraction states where a value came from, never how '
                         'much to believe it (schema v4)')
        self.assertEqual(nutrition['basis_text'], 'Pro 100g')
        self.assertEqual(nutrition['per_100g']['protein_g'], 12.0)
        self.assertEqual(nutrition['per_100g']['fiber_g'], 3.5)
        self.assertEqual(nutrition['per_100g']['energy_kj'], 1483.0)
        # kcal is not published; it is derived and declared as such.
        self.assertIn('energy_kcal', nutrition['derived'])
        self.assertEqual(record['food']['ingredients'],
                         {'text': 'HARTWEIZENGRIEß, Wasser.',
                          'source': 'nutrition_card'})

    def test_raw_tables_keep_unmapped_labels(self):
        record = self.extract('<div id="productTitle">Pasta</div>' + TABLE_HTML)
        self.assertEqual(record['raw_tables']['Marke'], 'Naturata')
        self.assertEqual(record['raw_tables']['Hersteller'], 'Naturata AG')
        self.assertEqual(record['attribute_sources']['Hersteller'], 'detail_bullets')
        self.assertEqual(record['attributes']['country_of_origin'], 'Italien')
        self.assertEqual(record['brand'], 'Naturata')
        # 500 g x 6 items
        self.assertEqual(record['package']['total_quantity_base'], 3000.0)
        self.assertEqual(record['package']['total_quantity_source'],
                         'item_weight_x_count')

    def test_count_label_carrying_a_unit_is_not_a_piece_count(self):
        html = ('<div id="productTitle">Pasta</div>'
                '<table class="a-normal a-spacing-micro">'
                '<tr><td>Artikelgewicht</td><td>500 g</td></tr>'
                '<tr><td>Stückzahl</td><td>500.0 gramm</td></tr></table>')
        package = self.extract(html)['package']
        self.assertEqual(package['total_quantity_base'], 500.0)
        self.assertNotIn('item_count', package)

    def test_price_is_read_only_from_a_price_container(self):
        # A page with no buy box, but carousels full of other products'
        # prices: reporting a neighbour's price would be worse than none.
        html = ('<div id="productTitle">Pasta</div>'
                '<div id="similar"><span class="a-price">'
                '<span class="a-offscreen">EUR097</span></span></div>')
        self.assertEqual(self.extract(html)['price'], {})

    def test_price_rebuilt_when_offscreen_label_loses_the_separator(self):
        html = ('<div id="productTitle">Pasta</div>'
                '<div id="corePrice_feature_div"><span class="a-price">'
                '<span class="a-offscreen">EUR097</span>'
                '<span class="a-price-symbol">EUR</span>'
                '<span class="a-price-whole">0</span>'
                '<span class="a-price-fraction">97</span></span></div>')
        self.assertEqual(self.extract(html)['price']['amount'], 0.97)

    def test_price_uses_offscreen_label_when_it_is_usable(self):
        html = ('<div id="productTitle">Pasta</div>'
                '<div id="corePrice_feature_div"><span class="a-price">'
                '<span class="a-offscreen">3,39 €</span></span></div>')
        price = self.extract(html)['price']
        self.assertEqual(price['amount'], 3.39)
        self.assertEqual(price['currency'], 'EUR')

    def test_a_price_range_is_not_published_as_a_price(self):
        """A variation parent with nothing selected renders a range.

        The container is the page's own and entirely legitimate, so scoping
        the search to a real price container -- the fix for the *previous*
        price bug, two tests up -- does nothing here. Reading the first
        `.a-offscreen` out of it published the cheapest variant in the family
        as this listing's price: 5,63 € for a tin that cost 9,98 €.
        """
        html = ('<div id="productTitle">Montagefluid</div>'
                '<div id="corePrice_desktop"><span class="a-price-range">'
                '<span class="a-price"><span class="a-offscreen">5,63€</span>'
                '</span><span class="a-price-dash">-</span>'
                '<span class="a-price"><span class="a-offscreen">26,15€</span>'
                '</span></span></div>')
        price = self.extract(html)['price']
        self.assertNotIn('amount', price)
        self.assertEqual(price['range'], [5.63, 26.15])
        self.assertEqual(price['currency'], 'EUR')
        self.assertIn('26,15', price['text'])

    def test_a_single_price_beside_a_range_elsewhere_is_still_a_price(self):
        """The guard must not cost every ordinary listing its price."""
        html = ('<div id="productTitle">Paste</div>'
                '<div id="corePrice_feature_div"><span class="a-price">'
                '<span class="a-offscreen">10,95 €</span></span></div>'
                '<div id="similar"><span class="a-price-range">'
                '<span class="a-price"><span class="a-offscreen">1,00€</span>'
                '</span><span class="a-price"><span class="a-offscreen">'
                '2,00€</span></span></span></div>')
        price = self.extract(html)['price']
        self.assertEqual(price['amount'], 10.95)
        self.assertNotIn('range', price)

    def test_empty_page_yields_a_record_not_an_exception(self):
        record = self.extract('<html><body></body></html>')
        self.assertEqual(record['extraction']['errors'], [])
        self.assertIn('media', record['extraction']['blocks_absent'])
        self.assertEqual(record['food']['nutrition'], {})
        self.assertEqual(record['raw_tables'], {})

    def test_nutrition_from_prose_names_the_field_it_came_from(self):
        html = ('<div id="productTitle">Pasta</div><div id="productDescription">'
                'Pro 100 g: Eiweiß 13,5 g, Ballaststoffe 3,1 g.</div>')
        nutrition = self.extract(html)['food']['nutrition']
        self.assertEqual(nutrition['source'], 'text:description')
        self.assertTrue(all(row['basis_confirmed'] for row in nutrition['rows']))
        self.assertEqual(nutrition['per_100g']['protein_g'], 13.5)

    def test_a_pack_size_in_millilitres_is_not_reported_in_grams(self):
        """The unit follows the row the total came from, not a volume
        mentioned elsewhere on the page."""
        html = ('<div id="productTitle">Montagefluid 50 ml</div>'
                '<table id="productDetails_techSpec_section_1"><tr>'
                '<th>Anzahl der Einheiten</th><td>50.0 milliliter</td>'
                '</tr></table>')
        package = self.extract(html)['package']
        self.assertEqual(package['total_quantity_base'], 50.0)
        self.assertEqual(package['total_quantity_unit'], 'ml')


class PackageWeightFromDimensions(unittest.TestCase):
    """Amazon.de appends a non-food item's weight to its dimensions row.

    "Produktabmessungen: 22 x 30 x 45 cm; 1,1 Kilogramm" was the only weight
    statement on 5 of 43 school-backpack records collected on 2026-09-17,
    including the two ergonomic brands the study was about. The rule reads a
    mass after the last semicolon and nothing else.
    """

    def package(self, **attributes):
        return PdpExtractor(DE)._package(attributes, 'Satch Schulrucksack Pack')

    def test_a_weight_after_the_semicolon_becomes_the_item_weight(self):
        package = self.package(dimensions='22 x 30 x 45 cm; 1,1 Kilogramm')
        self.assertEqual(package['item_weight_base'], 1100.0)
        self.assertEqual(package['item_weight_unit'], 'kg')
        self.assertEqual(package['item_weight_text'], '1,1 Kilogramm')
        self.assertEqual(package['item_weight_origin'], 'dimensions')
        self.assertEqual(package['total_quantity_base'], 1100.0)
        self.assertEqual(package['total_quantity_source'], 'item_weight')

    def test_a_dimensions_row_without_a_weight_states_none(self):
        package = self.package(dimensions='23 x 30 x 44 cm')
        self.assertNotIn('item_weight_base', package)
        self.assertNotIn('total_quantity_base', package)

    def test_a_volume_after_the_semicolon_is_not_a_weight(self):
        package = self.package(dimensions='10 x 5 x 20 cm; 500 Milliliter')
        self.assertNotIn('item_weight_base', package)

    def test_a_dimension_that_happens_to_end_in_a_unit_is_not_read(self):
        # "30 x 44 g" never occurs, but a defensive rule costs nothing: a
        # tail that still multiplies dimensions is not a weight statement.
        package = self.package(dimensions='22 cm; 30 x 44 g')
        self.assertNotIn('item_weight_base', package)

    def test_an_explicit_artikelgewicht_row_always_wins(self):
        package = self.package(item_weight='1250 Gramm',
                               dimensions='21 x 27 x 43 cm; 1,3 Kilogramm')
        self.assertEqual(package['item_weight_base'], 1250.0)
        self.assertNotIn('item_weight_origin', package)

    def test_an_unparsed_artikelgewicht_row_is_not_overwritten(self):
        """Corpus page B0728HMWW5: "Artikelgewicht: 1,1 Pfund" beside a
        dimensions row ending in Amazon's conversion, "498,95 Gramm". The
        row's own text stays; the conversion is not read behind its back."""
        package = self.package(item_weight='1,1 Pfund',
                               dimensions='20 x 10 x 5 cm; 498,95 Gramm')
        self.assertEqual(package['item_weight_text'], '1,1 Pfund')
        self.assertNotIn('item_weight_base', package)
        self.assertNotIn('item_weight_origin', package)


class AplusComparisonTable(unittest.TestCase):
    """R15's third adaptation: a comparison table is structure, not copy.

    Modelled on the ``premium-module-5-comparison-table`` of the retained fenix
    8, fenix 9 and Instinct 3 pages: one product per ``th.aplus-data-column``,
    the page's own product sometimes the first column, sometimes the third,
    sometimes absent, and the first column carrying ``active`` whichever it is.
    """

    TABLE = (
        '<div id="aplus_feature_div"><div class="aplus-module premium-module-5-comparison-table-scroller">'
        '<p>Welche Uhr ist die Richtige?</p>'
        '<table class="a-bordered">'
        '<tr><td class="attribute empty"></td>'
        '<th class="aplus-data-column top-header active active-item"><a href="/Other-Model/dp/B0OTHER001/ref=x">Modell A</a></th>'
        '<th class="aplus-data-column top-header"><a href="/This-Model/dp/B000000001/ref=x">Modell B</a></th>'
        '<th class="aplus-data-column top-header"><a href="/Third-Model/dp/B0OTHER002/ref=x">Modell C</a></th></tr>'
        '<tr><td class="attribute">Akkulaufzeit GPS-Modus</td><td>Bis zu 42 Stunden</td><td>Bis zu 47 Stunden</td><td>Bis zu 73 Stunden</td></tr>'
        '<tr><td class="attribute">Garmin Pay</td><td>\u2714</td><td>\u2718</td><td>\u2714</td></tr>'
        '</table></div></div>'
    )

    def aplus(self, html, asin='B000000001'):
        return blocks.aplus_content(Selector(html), asin=asin)

    def test_prose_leaves_the_table_cells_out_and_text_keeps_them(self):
        aplus = self.aplus(self.TABLE)
        self.assertIn('Bis zu 42 Stunden', aplus['text'], 'text is unchanged since schema v1')
        self.assertEqual(aplus['prose'], 'Welche Uhr ist die Richtige?')

    def test_the_own_column_is_found_by_asin_not_by_position(self):
        aplus = self.aplus(self.TABLE)
        (table,) = aplus['comparison']
        self.assertEqual([c['asin'] for c in table['columns']],
                         ['B0OTHER001', 'B000000001', 'B0OTHER002'])
        self.assertEqual(table['self_column'], 1,
                         'the active first column is the scroller\'s, not the product\'s')
        self.assertEqual(table['rows'][0], ['Akkulaufzeit GPS-Modus', 'Bis zu 42 Stunden',
                                            'Bis zu 47 Stunden', 'Bis zu 73 Stunden'])

    def test_a_table_without_the_product_has_no_own_column(self):
        aplus = self.aplus(self.TABLE, asin='B0NOTHERE00')
        self.assertIsNone(aplus['comparison'][0]['self_column'])
        self.assertEqual(len(aplus['tables']), 1, 'the verbatim table is still retained')

    def test_a_spec_table_is_not_a_comparison(self):
        html = ('<div id="aplus"><table><tr><th>Kalorien</th><td>355 kcal</td></tr>'
                '<tr><th>Fett</th><td>1,5 g</td></tr></table></div>')
        aplus = self.aplus(html)
        self.assertEqual(aplus['comparison'], [])
        self.assertEqual(len(aplus['tables']), 1)
        self.assertEqual(aplus['prose'], '')

    def test_the_extractor_passes_the_page_asin_through(self):
        record = PdpExtractor(DE).extract(Selector('<div id="productTitle">Uhr</div>' + self.TABLE),
                                         self.TABLE, {'asin': 'B000000001'})
        self.assertEqual(record['content']['aplus']['comparison'][0]['self_column'], 1)


if __name__ == '__main__':
    unittest.main()
