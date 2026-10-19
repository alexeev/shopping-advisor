"""Regression test over saved real Amazon pages: extraction, then validation.

`tests/corpus/` holds the pages the extraction layer was built against, one
gzipped HTML file per ASIN, grouped by marketplace, next to two snapshots:

`expected.jsonl.gz`
    the record each page should extract to -- what the page says.
`validated.jsonl.gz`
    the contract record each of those should validate to, with **no category
    profile** -- how much of what the page says holds up on its own.

Both are compared field by field. The second exists because the published
contract is now something downstream code depends on, and a change in a
status, a source or a note is exactly as much of a breaking change as a
change in an extracted value -- and far easier to make by accident, because
the validation rules interact. It is deliberately run without a category:
what is pinned is the layer that belongs to nobody.

This is the test the unit tests cannot be: the fixtures in
`test_extraction.py` are hand-written and pin down structures we already
understand, while these are 2 MB pages full of structures nobody enumerated.
A runtime upgrade once silently dropped an attribute table from two of them
and no unit test noticed.

When a change is *meant* to alter either output, regenerate the snapshots and
review the diff as part of the change:

    uv run python tests/test_corpus.py --update
"""

import contextlib
import gzip
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

from parsel import Selector

# This module doubles as the snapshot updater, so it has to import the project
# when run as a script from anywhere, not only under `unittest discover`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shopping_advisor.extraction import PdpExtractor, for_domain  # noqa: E402
from shopping_advisor.redaction import SESSION_ID  # noqa: E402
from shopping_advisor.run import read_page  # noqa: E402
from shopping_advisor.validation import validate  # noqa: E402

CORPUS = pathlib.Path(__file__).resolve().parent / 'corpus'

# Directory name -> the marketplace host its pages were fetched from, which
# selects the locale profile the extractor runs with.
MARKETPLACES = {
    'amazon_de': 'www.amazon.de',
    'amazon_com': 'www.amazon.com',
}

SNAPSHOT = 'expected.jsonl.gz'
VALIDATED = 'validated.jsonl.gz'

# Set by the crawl, not by the page: it would differ on every run.
VOLATILE = 'fetched_at'
PLACEHOLDER = '<runtime>'


def extract_dir(name):
    """Every page in one marketplace directory, as {asin: record}."""
    extractor = PdpExtractor(for_domain(MARKETPLACES[name]))
    records = {}
    for path in sorted((CORPUS / name).glob('*.html.gz')):
        asin = path.name[:-len('.html.gz')]
        # The replay's reader, so a page reads here as `reextract` reads it:
        # text mode would turn a CRLF on the page into LF.
        html = read_page(path)
        record = extractor.extract(Selector(html), html, {'asin': asin})
        record[VOLATILE] = PLACEHOLDER
        records[asin] = record
    return records


def validate_all(records):
    """Every extracted record put through the contract, category-free."""
    return {asin: validate(record).as_dict()
            for asin, record in records.items()}


def load_snapshot(name, filename=SNAPSHOT):
    with gzip.open(CORPUS / name / filename, 'rt', encoding='utf-8') as fh:
        return {r['asin']: r for r in map(json.loads, fh)}


def write_snapshot(name, records, filename=SNAPSHOT, root=CORPUS):
    (root / name).mkdir(parents=True, exist_ok=True)
    with gzip.open(root / name / filename, 'wt', encoding='utf-8',
                   compresslevel=9) as fh:
        for asin in sorted(records):
            fh.write(json.dumps(records[asin], ensure_ascii=False,
                                sort_keys=True) + '\n')


def flatten(value, prefix=''):
    """A record as {dotted.path: scalar}, so a diff can name what moved."""
    flat = {}
    if isinstance(value, dict):
        for key, child in value.items():
            flat.update(flatten(child, f'{prefix}.{key}' if prefix else key))
    elif isinstance(value, list):
        flat[f'{prefix}[]'] = len(value)
        for index, child in enumerate(value):
            flat.update(flatten(child, f'{prefix}[{index}]'))
    else:
        flat[prefix] = value
    return flat


def differences(expected, actual):
    """Human-readable field-level differences between two records."""
    want, got = flatten(expected), flatten(actual)
    lines = []
    for path in sorted(set(want) | set(got)):
        a, b = want.get(path, '<absent>'), got.get(path, '<absent>')
        if a != b:
            lines.append(f'    {path}\n'
                         f'      expected: {str(a)[:160]}\n'
                         f'      actual:   {str(b)[:160]}')
    return lines


class Corpus(unittest.TestCase):

    def check(self, name, what, expected, actual):
        self.assertEqual(sorted(expected), sorted(actual),
                         f'{name}: corpus and snapshot cover different ASINs; '
                         f'run `python tests/test_corpus.py --update`')

        report = []
        for asin in sorted(expected):
            diff = differences(expected[asin], actual[asin])
            if diff:
                report.append(f'  {asin}:\n' + '\n'.join(diff))
        if report:
            self.fail(
                f'{name}: {what} changed for {len(report)} of '
                f'{len(expected)} saved pages.\n' + '\n'.join(report[:5]) +
                ('\n  ...' if len(report) > 5 else '') +
                '\nIf this is intended, regenerate with '
                '`python tests/test_corpus.py --update` and review the diff.')

    def check_extraction(self, name):
        self.check(name, 'extraction', load_snapshot(name), extract_dir(name))

    def check_validation(self, name):
        self.check(name, 'validation output',
                   load_snapshot(name, VALIDATED),
                   validate_all(extract_dir(name)))

    def test_amazon_de(self):
        self.check_extraction('amazon_de')

    def test_amazon_com(self):
        # One page only. amazon.com is probed, not supported: it is here to
        # keep the marketplace-generic paths honest, not to claim coverage.
        self.check_extraction('amazon_com')

    def test_amazon_de_validation(self):
        self.check_validation('amazon_de')

    def test_amazon_com_validation(self):
        self.check_validation('amazon_com')


class DeliveryOnSavedPages(unittest.TestCase):
    """The delivery promise on pages whose buy box shows more than one.

    The snapshot pins every page's `delivery`; these say why the values are
    the right ones, on the pages where reading the wrong block was possible.
    """

    def page(self, asin):
        html = read_page(CORPUS / 'amazon_de' / f'{asin}.html.gz')
        selector = Selector(html)
        record = PdpExtractor(for_domain('www.amazon.de')).extract(
            selector, html, {'asin': asin})
        on_page = [node.attrib['data-csa-c-delivery-time']
                   for node in selector.css('[data-csa-c-delivery-time]')]
        return record, on_page

    def times(self, record):
        return [option['time_text'] for option in record['delivery']['options']]

    def test_a_faster_offer_and_a_used_offer_lend_no_promise(self):
        # B082B8WMBD opens on "Neu kaufen" at 168,00 €; a "Schnellere
        # Lieferung" row is another offer at 170,99 € arriving "Morgen", and a
        # used one arrives on the 23rd. The record's price is the first row's,
        # and so is its promise.
        record, on_page = self.page('B082B8WMBD')
        self.assertEqual(record['price']['amount'], 168.0)
        self.assertEqual(self.times(record), ['22. - 23. September'])
        self.assertIn('Morgen, 19. September', on_page)
        self.assertIn('Mittwoch, 23. September', on_page)

    def test_accordion_head_and_subscription_copies_are_not_extra_options(self):
        record, on_page = self.page('B0728HMWW5')
        self.assertEqual(len(on_page), 7)
        self.assertEqual(self.times(record),
                         ['Donnerstag, 17. September', 'Mittwoch, 16. September'])
        self.assertEqual([o['price_text'] for o in record['delivery']['options']],
                         ['GRATIS', 'schnellste'])

    def test_the_promise_names_the_location_it_was_made_for(self):
        # Fetched by an anonymous session Amazon placed in Austria: the
        # promise is for there, and a relative day stays relative.
        record, _ = self.page('B07J2W1S6Q')
        self.assertEqual(record['delivery']['location_text'],
                         'Liefern nach Österreich')
        self.assertEqual(self.times(record),
                         ['Freitag, 18. September', 'Morgen, 16. September'])

    def test_a_page_without_a_selected_offer_states_no_promise(self):
        # A variation parent with no size chosen, and a listing with no
        # featured offer: neither makes a promise, and neither is an empty one.
        for asin in ('B000RW5FVA', 'B01M25SBQ5'):
            record, on_page = self.page(asin)
            self.assertEqual(on_page, [], asin)
            self.assertEqual(record['delivery'], {}, asin)
            self.assertIn('delivery', record['extraction']['blocks_absent'], asin)


class LengthOnSavedPages(unittest.TestCase):
    """What is sold by the metre, on five floss pages of 2026-10-18.

    The snapshot pins every value; these say why they are the right ones. The
    floss is the only product class here that Amazon files and prices by
    length, and every floss page also states its box in centimetres.
    """

    SOLD_BY_LENGTH = {'B0H71G6PJ6': 50.0, 'B0C2DG1GMN': 40.0,
                      'B0FQV77NR5': 200.0, 'B0FS5TTWYM': 60.0}

    @classmethod
    def setUpClass(cls):
        cls.records = extract_dir('amazon_de')
        cls.validated = {asin: validate(record)
                         for asin, record in cls.records.items()}

    def test_only_what_is_sold_by_length_has_a_length(self):
        # Thirty of the 49 pages carry a dimensions row in centimetres, the
        # stick pack among them; none of those rows is a length sold.
        with_length = {asin: record['package']['total_length_base']
                       for asin, record in self.records.items()
                       if 'total_length_base' in record['package']}
        self.assertEqual(with_length, self.SOLD_BY_LENGTH)

    def test_a_spool_is_priced_per_metre_and_agrees_with_amazon(self):
        for asin, euros in (('B0H71G6PJ6', 0.05), ('B0C2DG1GMN', 0.10),
                            ('B0FQV77NR5', 0.05), ('B0FS5TTWYM', 0.15)):
            per_metre = self.validated[asin].price_per_length
            self.assertEqual((per_metre.value, per_metre.unit, per_metre.status),
                             (euros, 'EUR/m', 'trusted'), asin)
            self.assertEqual(self.records[asin]['unit_price']['unit'], 'meter')
            self.assertEqual(self.validated[asin].length.status, 'trusted', asin)

    def test_a_four_pack_is_confirmed_by_its_counted_title(self):
        length = self.validated['B0FQV77NR5'].length
        self.assertEqual(length.value, 200.0)
        self.assertEqual(length.evidence[-1].quote, '4 x 50m')

    def test_a_length_under_a_count_label_is_not_sixty_pieces(self):
        # "Stückzahl: 60.0 meter" was read as sixty pieces and multiplied by
        # the 40 g spool into a 2,4 kg pack.
        package = self.records['B0FS5TTWYM']['package']
        self.assertNotIn('item_count', package)
        self.assertEqual(package['total_length_source'], 'item_count')
        self.assertEqual((package['total_quantity_base'],
                          package['total_quantity_source']), (40.0, 'item_weight'))

    def test_a_stick_pack_is_not_read_as_metres(self):
        validated = self.validated['B0H62SDCK2']
        self.assertEqual(self.records['B0H62SDCK2']['unit_price']['unit'], 'stück')
        self.assertFalse(validated.length.known)
        self.assertFalse(validated.price_per_length.known)
        self.assertNotIn('length', validated.as_dict())

    def test_the_weight_total_keeps_its_meaning(self):
        # Beside the length, the pack's content total is still grams, and
        # Amazon's per-metre figure is no check on a price per kilogram.
        for asin in self.SOLD_BY_LENGTH:
            validated = self.validated[asin]
            self.assertEqual(validated.quantity.unit, 'g', asin)
            self.assertEqual(validated.price_per_base.unit, 'EUR/kg', asin)
            self.assertNotEqual(validated.price_per_base.status, 'trusted', asin)


class Promotion(unittest.TestCase):
    """`corpus/redact.py` is how a retained page enters the corpus."""

    def test_a_promoted_page_keeps_its_line_endings(self):
        """It read and wrote in text mode, so a retained page's CRLF arrived
        in the corpus as LF: redaction is meant to be the only change, and
        the committed page was not the page its run recorded a digest for."""
        spec = importlib.util.spec_from_file_location(
            'corpus_redact', CORPUS / 'redact.py')
        redact_cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(redact_cli)
        page = ("<html><title>t</title>\r\n<script>var ue_sid="
                "'123-4567890-1234567';</script>\r</html>")
        with tempfile.TemporaryDirectory() as tmp:
            retained = pathlib.Path(tmp) / 'B000000000.html.gz'
            promoted = pathlib.Path(tmp) / 'promoted.html.gz'
            with gzip.open(retained, 'wb') as fh:
                fh.write(page.encode('utf-8'))
            with contextlib.redirect_stdout(io.StringIO()):
                redact_cli.main(str(retained), str(promoted))
            self.assertEqual(read_page(promoted),
                             page.replace('123-4567890-1234567', SESSION_ID))


if __name__ == '__main__':
    if '--update' in sys.argv:
        # ``--output DIR`` writes the snapshots under DIR instead of in place,
        # so that they can be regenerated inside an R15 execution boundary,
        # whose one writable directory is never the tree, and copied in after
        # the diff has been read.
        root = CORPUS
        if '--output' in sys.argv:
            root = pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).resolve()
        for marketplace in MARKETPLACES:
            records = extract_dir(marketplace)
            write_snapshot(marketplace, records, root=root)
            write_snapshot(marketplace, validate_all(records), VALIDATED, root=root)
            print(f'{marketplace}: wrote {len(records)} records to '
                  f'{root / marketplace / SNAPSHOT} and '
                  f'{root / marketplace / VALIDATED}')
    else:
        unittest.main()
