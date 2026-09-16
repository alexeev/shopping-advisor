"""Tests for reading a study's feeds as one corpus.

A research question outlives a single crawl, and the moment two feeds are read
together something has to decide which sighting of an ASIN the study uses. The
rule is ``fetched_at``, and these tests exist because the obvious alternative
-- whichever feed was named last -- is wrong in a way nothing would report: a
shell glob sorts alphabetically, and the alphabetically later feed is not the
younger one.

The CLI tests are here too, because telling a feed path from an ASIN is the
one piece of argument handling this command line does by hand.
"""

import gzip
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from amazon_scraper.analysis import feeds  # noqa: E402
from amazon_scraper.analysis.__main__ import (one_marketplace,  # noqa: E402
                                              split_arguments)


def record(asin, fetched_at, **extra):
    row = {'asin': asin, 'title': f'{asin} pasta'}
    if fetched_at is not None:
        row['fetched_at'] = fetched_at
    row.update(extra)
    return row


class Feeds(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def write(self, name, records):
        path = pathlib.Path(self.directory.name) / name
        opener = gzip.open if name.endswith('.gz') else open
        with opener(path, 'wt', encoding='utf-8') as handle:
            for row in records:
                handle.write(json.dumps(row) + '\n')
        return str(path)


class Merge(Feeds):

    def test_one_feed_is_read_unchanged(self):
        path = self.write('a.jsonl', [record('B000000001', '2026-09-15T10:00:00+00:00'),
                                      record('B000000002', '2026-09-15T10:01:00+00:00')])
        records, provenance = feeds.merge([path])
        self.assertEqual([r['asin'] for r in records],
                         ['B000000001', 'B000000002'])
        self.assertEqual(provenance['records'], 2)
        self.assertEqual(provenance['feeds'], 1)
        self.assertEqual(provenance['superseded'], 0)
        self.assertEqual(provenance['supersessions'], [])

    def test_the_freshest_crawl_wins_not_the_last_argument(self):
        """The bug this rule exists for. ``data/study_*.jsonl`` expands
        alphabetically, which has nothing to do with when each crawl ran, and
        price and availability are exactly the fields that would go stale."""
        older = self.write('z_older.jsonl',
                           [record('B000000001', '2026-09-15T08:00:00+00:00',
                                   price={'amount': 9.99})])
        newer = self.write('a_newer.jsonl',
                           [record('B000000001', '2026-09-15T14:00:00+00:00',
                                   price={'amount': 7.49})])
        for order in ([newer, older], [older, newer]):
            records, provenance = feeds.merge(order)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['price']['amount'], 7.49,
                             f'argument order {order} decided the winner')
            self.assertEqual(provenance['superseded'], 1)

    def test_an_asin_crawled_three_times_is_one_record_and_one_supersession(self):
        stamps = ['2026-09-15T08:00:00+00:00', '2026-09-15T09:00:00+00:00',
                  '2026-09-15T10:00:00+00:00']
        paths = [self.write(f'{index}.jsonl', [record('B000000001', stamp)])
                 for index, stamp in enumerate(reversed(stamps))]
        records, provenance = feeds.merge(paths)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['fetched_at'], stamps[-1])
        self.assertEqual(provenance['records'], 1)
        self.assertEqual(provenance['feeds'], 3)
        self.assertEqual(provenance['superseded'], 1)
        # One supersession, but two observations were set aside, and a price
        # that moved between them is a fact about the shelf.
        self.assertEqual(len(provenance['supersessions'][0]['superseded']), 2)
        self.assertEqual(provenance['supersessions'][0]['selected']['fetched_at'],
                         stamps[-1])

    def test_a_record_that_will_not_say_when_it_was_fetched_loses(self):
        undated = self.write('undated.jsonl', [record('B000000001', None,
                                                      price={'amount': 1.0})])
        dated = self.write('dated.jsonl',
                           [record('B000000001', '2026-01-01T00:00:00+00:00',
                                   price={'amount': 2.0})])
        for order in ([undated, dated], [dated, undated]):
            records, _ = feeds.merge(order)
            self.assertEqual(records[0]['price']['amount'], 2.0)

    def test_a_timestamp_without_an_offset_is_read_as_utc_not_dropped(self):
        """Naive and aware timestamps raise when compared. A feed that lost
        its offset is still a feed, and must not take the whole merge down."""
        naive = self.write('naive.jsonl', [record('B000000001',
                                                  '2026-09-15T14:00:00')])
        aware = self.write('aware.jsonl', [record('B000000001',
                                                  '2026-09-15T08:00:00+00:00')])
        records, _ = feeds.merge([aware, naive])
        self.assertEqual(records[0]['fetched_at'], '2026-09-15T14:00:00')

    def test_an_unparseable_timestamp_does_not_end_the_merge(self):
        broken = self.write('broken.jsonl', [record('B000000001', 'yesterday')])
        good = self.write('good.jsonl', [record('B000000001',
                                                '2026-09-15T08:00:00+00:00')])
        records, _ = feeds.merge([broken, good])
        self.assertEqual(records[0]['fetched_at'], '2026-09-15T08:00:00+00:00')

    def test_records_keep_the_order_they_were_first_seen_in(self):
        first = self.write('first.jsonl',
                           [record('B000000001', '2026-09-15T08:00:00+00:00'),
                            record('B000000002', '2026-09-15T08:00:00+00:00')])
        second = self.write('second.jsonl',
                            [record('B000000003', '2026-09-15T09:00:00+00:00'),
                             record('B000000001', '2026-09-15T09:00:00+00:00')])
        records, _ = feeds.merge([first, second])
        self.assertEqual([r['asin'] for r in records],
                         ['B000000001', 'B000000002', 'B000000003'],
                         'a fresher copy replaces a record, it does not move it')

    def test_a_record_with_no_asin_is_kept_rather_than_collided(self):
        path = self.write('odd.jsonl', [{'title': 'no asin'},
                                        {'title': 'also no asin'}])
        records, provenance = feeds.merge([path])
        self.assertEqual(len(records), 2)
        self.assertEqual(provenance['superseded'], 0)

    def test_gzipped_feeds_are_read_directly(self):
        plain = self.write('plain.jsonl',
                           [record('B000000001', '2026-09-15T08:00:00+00:00')])
        packed = self.write('packed.jsonl.gz',
                            [record('B000000002', '2026-09-15T08:00:00+00:00')])
        records, provenance = feeds.merge([plain, packed])
        self.assertEqual(provenance['records'], 2)
        self.assertEqual({r['asin'] for r in records},
                         {'B000000001', 'B000000002'})


class Marketplace(Feeds):
    """An ASIN is only unique within one Amazon site."""

    def de_and_com(self):
        return self.write('mixed.jsonl', [
            record('B000000001', '2026-09-15T08:00:00+00:00',
                   marketplace='www.amazon.de',
                   price={'amount': 2.49, 'currency': 'EUR'}),
            record('B000000001', '2026-09-15T14:00:00+00:00',
                   marketplace='www.amazon.com',
                   price={'amount': 7.99, 'currency': 'USD'})])

    def test_one_asin_on_two_marketplaces_is_two_listings(self):
        """Keyed by ASIN alone, the newer ``.com`` row replaced the ``.de``
        one and the local price was gone -- with the merge reporting a
        supersession that had not happened."""
        records, provenance = feeds.merge([self.de_and_com()])
        self.assertEqual(len(records), 2)
        self.assertEqual(provenance['superseded'], 0)
        self.assertEqual(provenance['marketplaces'],
                         {'amazon.com': 1, 'amazon.de': 1})

    def test_the_same_marketplace_written_two_ways_is_one_marketplace(self):
        path = self.write('hosts.jsonl', [
            record('B000000001', '2026-09-15T08:00:00+00:00',
                   marketplace='www.amazon.de', price={'amount': 2.49}),
            record('B000000001', '2026-09-15T14:00:00+00:00',
                   marketplace='amazon.de', price={'amount': 1.99})])
        records, provenance = feeds.merge([path])
        self.assertEqual(len(records), 1, 'www. is not a second marketplace')
        self.assertEqual(records[0]['price']['amount'], 1.99)
        # The census counts the records that survived the merge, which is the
        # set everything downstream reads.
        self.assertEqual(provenance['marketplaces'], {'amazon.de': 1})

    def test_an_unlabelled_record_is_its_own_scope(self):
        """A feed written before provenance existed cannot be asserted to
        belong to any marketplace, so it is not folded into one."""
        path = self.write('legacy.jsonl', [
            record('B000000001', '2026-09-15T08:00:00+00:00'),
            record('B000000001', '2026-09-15T09:00:00+00:00',
                   marketplace='www.amazon.de')])
        records, provenance = feeds.merge([path])
        self.assertEqual(len(records), 2)
        self.assertEqual(provenance['marketplaces'], {'': 1, 'amazon.de': 1})

    def test_selecting_a_marketplace_sets_the_rest_aside(self):
        records, _ = feeds.merge([self.de_and_com()])
        kept, aside = feeds.select_marketplace(records, 'www.amazon.de')
        self.assertEqual([r['price']['currency'] for r in kept], ['EUR'])
        self.assertEqual(len(aside), 1)

    def test_an_analysis_of_two_marketplaces_is_refused(self):
        """Merging keeps both rows; everything downstream still renders one
        ranking, in one currency, for one delivery region."""
        records, provenance = feeds.merge([self.de_and_com()])
        with self.assertRaises(SystemExit) as raised:
            one_marketplace(records, provenance, '')
        self.assertIn('more than one marketplace', str(raised.exception))

        kept, narrowed = one_marketplace(records, provenance, 'www.amazon.de')
        self.assertEqual(len(kept), 1)
        self.assertEqual(narrowed['set_aside'], 1)
        self.assertIn('1 record from another marketplace set aside',
                      feeds.provenance_line(narrowed))

    def test_a_marketplace_with_no_records_stops_the_command(self):
        records, provenance = feeds.merge([self.de_and_com()])
        with self.assertRaises(SystemExit) as raised:
            one_marketplace(records, provenance, 'www.amazon.co.uk')
        self.assertIn('no records from that marketplace', str(raised.exception))


class Ties(Feeds):
    """Equal ``fetched_at`` used to keep whichever feed was read first."""

    SAME = '2026-09-15T08:00:00+00:00'

    def test_a_tie_is_decided_by_the_records_not_the_argument_order(self):
        first = self.write('a.jsonl', [record('B000000001', self.SAME,
                                              run_id='run-a', price={'amount': 1.0})])
        second = self.write('b.jsonl', [record('B000000001', self.SAME,
                                               run_id='run-b', price={'amount': 2.0})])
        winners = {feeds.merge(order)[0][0]['price']['amount']
                   for order in ([first, second], [second, first])}
        self.assertEqual(len(winners), 1, 'argument order decided the winner')

    def test_a_newer_reading_of_the_same_bytes_wins_the_tie(self):
        """A re-extraction is a better reading of the same observation, not a
        newer observation: ``fetched_at`` is unchanged and ``extracted_at``
        says when the record was produced."""
        crawled = self.write('crawl.jsonl', [
            record('B000000001', self.SAME, run_id='run-a', schema_version=5,
                   price={'amount': 1.0})])
        replayed = self.write('replay.jsonl', [
            record('B000000001', self.SAME, run_id='run-a', schema_version=6,
                   extracted_at='2026-09-16T09:00:00+00:00',
                   price={'amount': 1.0, 'currency': 'EUR'})])
        for order in ([crawled, replayed], [replayed, crawled]):
            records, _ = feeds.merge(order)
            self.assertEqual(records[0]['schema_version'], 6)
            self.assertEqual(records[0]['fetched_at'], self.SAME,
                             'a replay must not look like a fresh fetch')

    def test_an_anonymous_row_in_each_feed_is_kept_separately(self):
        first = self.write('one.jsonl', [{'title': 'no asin'}])
        second = self.write('two.jsonl', [{'title': 'no asin'}])
        records, provenance = feeds.merge([first, second])
        self.assertEqual(len(records), 2)
        self.assertEqual(provenance['superseded'], 0)


class ProvenanceLine(Feeds):

    def test_it_states_records_feeds_and_supersessions(self):
        line = feeds.provenance_line({'records': 471, 'feeds': 3,
                                      'superseded': 95})
        self.assertEqual(line, '471 records from 3 feeds, 95 ASINs superseded '
                               'by a fresher crawl')

    def test_it_counts_in_the_singular_too(self):
        line = feeds.provenance_line({'records': 1, 'feeds': 1,
                                      'superseded': 1})
        self.assertIn('1 feed,', line)
        self.assertIn('1 ASIN superseded', line)


class Arguments(Feeds):
    """Feeds and ASINs share one positional list, so it has to be split."""

    def test_a_readable_file_is_a_feed_and_the_rest_are_asins(self):
        path = self.write('a.jsonl', [])
        paths, asins = split_arguments([path, 'B0CPQ5HGC8', 'B003CJ707C'])
        self.assertEqual(paths, [path])
        self.assertEqual(asins, ['B0CPQ5HGC8', 'B003CJ707C'])

    def test_several_feeds_and_no_asins(self):
        first, second = self.write('a.jsonl', []), self.write('b.jsonl', [])
        paths, asins = split_arguments([first, second])
        self.assertEqual(paths, [first, second])
        self.assertEqual(asins, [])

    def test_a_mistyped_path_stops_the_command(self):
        """The failure this guards against is an analysis of nothing that
        still prints a well-formed report."""
        with self.assertRaises(SystemExit) as raised:
            split_arguments([self.write('a.jsonl', []), 'data/typo.jsonl'])
        self.assertIn('data/typo.jsonl', str(raised.exception))

    def test_asins_alone_are_not_an_analysis(self):
        with self.assertRaises(SystemExit) as raised:
            split_arguments(['B0CPQ5HGC8'])
        self.assertIn('feed', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
