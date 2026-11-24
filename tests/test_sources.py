"""Bucket F: a declared source mapping is checked against the record, never inferred."""
import contextlib
import io
import json
from pathlib import Path
import unittest

from shopping_advisor.jsonl import read_jsonl
from shopping_advisor.provenance import sha256_text
from shopping_advisor.study import sources
from shopping_advisor.study.__main__ import main

FIXTURE = Path(__file__).parent / 'sources'
LEDGER = FIXTURE / 'ledger.json'
FEED = FIXTURE / 'records.jsonl'


def ledger():
    return json.loads(LEDGER.read_text(encoding='utf-8'))


def records():
    return {f'www.amazon.de:{r["asin"]}': r for r in read_jsonl(FEED)}


def row(result, asin, kind):
    return [r for r in result['rows'] if r['listing'].endswith(asin) and r['kind'] == kind]


class Assessment(unittest.TestCase):
    def setUp(self):
        self.result = sources.assess(ledger(), records())

    def test_every_listing_and_kind_in_scope_is_reported(self):
        self.assertEqual(len(self.result['rows']), 4 * 3)
        self.assertEqual(self.result['counts'], {'checked': 2, 'declared': 1,
                                                 'nothing_found': 1, 'not_looked_up': 8})
        self.assertEqual(self.result['findings'], [])

    def test_a_quote_found_in_the_named_field_is_checked(self):
        (found,) = row(self.result, 'B0SRC00001', 'manufacturer_datasheet')
        self.assertEqual((found['status'], found['same_string']), ('checked', True))
        self.assertEqual(found['statement_label'], 'vendor declaration')
        self.assertEqual([s['subject'] for s in found['statements']],
                         ['input-voltage', 'temperature-range'])

    def test_a_revision_in_the_source_is_reported_and_not_decided(self):
        """PB763 is in the record and the certificate names PB763 v2: the
        counterexample automatic matching was rejected on. The quote is where
        the operator said, and the strings are shown as different."""
        (found,) = row(self.result, 'B0SRC00002', 'certificate')
        self.assertEqual(found['status'], 'checked')
        self.assertFalse(found['same_string'])
        self.assertEqual((found['record_quote'], found['source_model']), ('PB763', 'PB763 v2'))
        self.assertIn('NOT the same string', sources.render(self.result))

    def test_a_mapping_with_no_record_field_stays_declared(self):
        (found,) = row(self.result, 'B0SRC00003', 'manufacturer_datasheet')
        self.assertEqual(found['status'], 'declared')
        self.assertTrue(found['basis'])

    def test_a_recorded_empty_lookup_differs_from_none(self):
        self.assertEqual(row(self.result, 'B0SRC00001', 'safety_notice')[0]['status'], 'nothing_found')
        self.assertEqual(row(self.result, 'B0SRC00001', 'certificate')[0]['status'], 'not_looked_up')

    def test_an_unmapped_listing_is_never_matched_by_resemblance(self):
        """FX-200 has no mapping; FX-100's datasheet is one character away."""
        self.assertEqual({r['status'] for r in self.result['rows'] if r['listing'].endswith('B0SRC00004')},
                         {'not_looked_up'})

    def test_no_row_renders_a_verdict(self):
        text = sources.render(self.result).lower()
        body = text.replace(sources.NOTE.lower(), '')
        for word in ('safe', 'compliant', 'suitable', 'applies', 'certified'):
            self.assertNotRegex(body, rf'\b{word}\b')


class Contradictions(unittest.TestCase):
    def test_a_quote_absent_from_the_field_is_a_finding_and_stays_declared(self):
        data = ledger()
        data['mappings'][0]['quote'] = 'FX-101'
        result = sources.assess(data, records())
        self.assertEqual([f['code'] for f in result['findings']], ['quote_absent'])
        self.assertEqual(row(result, 'B0SRC00001', 'manufacturer_datasheet')[0]['status'], 'declared')

    def test_an_unresolved_field_is_a_finding(self):
        data = ledger()
        data['mappings'][0]['field'] = '/raw_tables/Nope'
        self.assertEqual([f['code'] for f in sources.assess(data, records())['findings']],
                         ['field_unresolved'])

    def test_a_listing_in_no_feed_is_a_finding(self):
        some = records()
        del some['www.amazon.de:B0SRC00004']
        self.assertEqual([f['code'] for f in sources.assess(ledger(), some)['findings']],
                         ['listing_absent'])


class Structure(unittest.TestCase):
    def refuse(self, change, fragment):
        data = ledger()
        change(data)
        with self.assertRaises(sources.SourceError) as caught:
            sources.check(data)
        self.assertIn(fragment, str(caught.exception))

    def test_a_statement_absent_from_the_retained_text_is_refused(self):
        self.refuse(lambda d: d['sources'][0]['statements'][1].update(quote='-40 bis +85 °C'),
                    'absent from the retained text')

    def test_an_altered_retained_text_is_refused(self):
        self.refuse(lambda d: d['sources'][0]['snapshot'].update(text='x'), 'digest mismatch')

    def test_the_model_string_must_be_in_the_retained_text(self):
        def change(d):
            d['sources'][0]['model'] = 'FX-100 rev B'
        self.refuse(change, 'model string is absent')

    def test_a_lookup_that_found_nothing_cannot_stand_beside_a_mapping(self):
        self.refuse(lambda d: d['lookups'][0].update(kind='manufacturer_datasheet'), 'contradicts a mapping')

    def test_a_mapping_without_field_needs_a_basis(self):
        self.refuse(lambda d: d['mappings'][2].update(basis=''), 'states its basis')

    def test_unknown_kinds_fields_and_versions_are_refused(self):
        self.refuse(lambda d: d['kinds'].append('press_article'), 'distinct kinds')
        self.refuse(lambda d: d.update(verdict='safe'), 'exactly the fields')
        self.refuse(lambda d: d.update(source_ledger_version=2), 'unsupported source_ledger_version')

    def test_an_unretained_source_keeps_its_statements_unchecked(self):
        data = ledger()
        data['sources'][0]['snapshot'] = {'status': 'unavailable', 'reason': 'read once, text not kept'}
        result = sources.assess(data, records())
        self.assertEqual(row(result, 'B0SRC00001', 'manufacturer_datasheet')[0]['snapshot'], 'unavailable')
        self.assertIn('text unavailable', sources.render(result))

    def test_the_fixture_digests_are_what_the_text_hashes_to(self):
        for source in ledger()['sources']:
            self.assertEqual(sha256_text(source['snapshot']['text']), source['snapshot']['sha256'])


class CommandLine(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def test_the_committed_example_passes_and_normalises_the_host(self):
        code, out = self.run_cli('sources-check', str(LEDGER), str(FEED))
        self.assertEqual(code, 0)
        self.assertIn('2 checked, 1 declared, 1 nothing_found, 8 not_looked_up', out)

    def test_json_carries_the_same_rows(self):
        code, out = self.run_cli('sources-check', str(LEDGER), str(FEED), '--json')
        self.assertEqual((code, json.loads(out)['counts']['checked']), (0, 2))

    def test_the_gate_pins_the_version(self):
        from shopping_advisor.maintenance import _contract_versions
        self.assertEqual(_contract_versions()['source_ledger'], sources.SOURCE_LEDGER_VERSION)


if __name__ == '__main__':
    unittest.main()
