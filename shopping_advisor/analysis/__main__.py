"""Command line for the category analysis.

    uv run python -m shopping_advisor.analysis summary data/products.jsonl
    uv run python -m shopping_advisor.analysis rank    data/products.jsonl \
        --require bronze_die --limit 15
    uv run python -m shopping_advisor.analysis card    data/products.jsonl B0CPQ5HGC8
    uv run python -m shopping_advisor.analysis compare data/products.jsonl A B
    uv run python -m shopping_advisor.analysis cards   data/products.jsonl --json

**Every command takes as many feeds as the study needed**, merged by
marketplace and ASIN with the freshest crawl winning -- see
:mod:`shopping_advisor.analysis.feeds` for why that is not the same as the order
they are named in. ``.gz`` is read directly.

    uv run python -m shopping_advisor.analysis rank \
        data/validation_v3_amazon_de.jsonl data/fusilli_broad.jsonl \
        data/fusilli_brands.jsonl --category dry_pasta

Feeds and ASINs share the positional list and are told apart by what they are:
an argument that names a readable file is a feed, and one shaped like an ASIN
is an ASIN. Anything else stops the command rather than being guessed at.

Every command takes ``--category`` (default ``dry_pasta``). The same records
can be read by any category: which one is right for a file is a question
about the crawl, not about the data.

    uv run python -m shopping_advisor.analysis rank data/paste.jsonl \
        --category tyre_mounting_paste

**One analysis covers one marketplace.** Feeds that span several stop the
command instead of being merged into a ranking across two currencies and two
delivery regions; ``--marketplace www.amazon.de`` states which one to keep and
reports how many records were set aside. Likewise ``--unit`` names the unit to
rank on when an axis is measured in more than one; nothing converts grams into
millilitres on the way.
"""

import argparse
import json
import os
import re
import sys

from . import feeds as feeds_module
from . import report
from . import categories  # noqa: F401  (registers the built-ins)
from .category import get, is_match, known

ASIN_RE = re.compile(r'[A-Z0-9]{10}')


def split_arguments(arguments):
    """``(feeds, asins)`` from one positional list.

    Two variadic positionals cannot be told apart by argparse, and naming the
    ASINs behind a flag would break every command line already written down in
    this project's reports. So they are told apart by what they are, and an
    argument that is neither a readable feed nor an ASIN is an error rather
    than a silently empty analysis.
    """
    paths, asins = [], []
    for argument in arguments:
        if os.path.isfile(argument):
            paths.append(argument)
        elif ASIN_RE.fullmatch(argument):
            asins.append(argument)
        else:
            sys.exit(f'{argument}: not a readable feed, and not an ASIN')
    if not paths:
        sys.exit('at least one feed is needed')
    return paths, asins


def one_marketplace(records, provenance, wanted):
    """``(records, provenance)`` for exactly one marketplace.

    Merging is marketplace-scoped, so a mixed feed set no longer loses
    records -- but everything downstream still compares them: one ranking,
    one currency symbol, one delivery region implied by the whole report. Two
    marketplaces in one analysis is therefore stopped here rather than
    rendered, and the caller says which one it meant.
    """
    seen = provenance.get('marketplaces') or {}
    if not wanted:
        if len(seen) > 1:
            sys.exit('these feeds hold records from more than one marketplace '
                     f'({", ".join(name or "unlabelled" for name in seen)}). '
                     'Prices, currencies and delivery regions are not '
                     'comparable across them; name one with --marketplace.')
        return records, provenance
    kept, set_aside = feeds_module.select_marketplace(records, wanted)
    if not kept:
        sys.exit(f'{wanted}: no records from that marketplace. '
                 f'These feeds hold: '
                 f'{", ".join(name or "unlabelled" for name in seen)}')
    return kept, dict(provenance, records=len(kept),
                      marketplaces=feeds_module.marketplaces(kept),
                      set_aside=len(set_aside))


def pick(cards, asin):
    for card in cards:
        if card['asin'] == asin:
            return card
    sys.exit(f'{asin}: not in any of these feeds')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='shopping_advisor.analysis',
                                     description=__doc__)
    parser.add_argument('command',
                        choices=('summary', 'rank', 'card', 'cards', 'compare',
                                 'validated'))
    parser.add_argument('feeds', nargs='+', metavar='FEED_OR_ASIN',
                        help='one or more JSONL feeds written by the '
                             'amazon_product spider, merged by marketplace '
                             'and ASIN; plus the ASIN(s) card and compare need')
    parser.add_argument('--category', default='dry_pasta',
                        help=f'one of: {", ".join(known())}')
    parser.add_argument('--require', default='',
                        help='comma-separated claims a product must make to be '
                             'ranked')
    parser.add_argument('--axis', default='',
                        help="comparison axis to rank on; defaults to the "
                             "category's own")
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--marketplace', default='',
                        help='the one marketplace to analyse, when the feeds '
                             'span several; the rest are set aside and '
                             'counted, not merged in')
    parser.add_argument('--unit', default='',
                        help='the unit to rank on, when the axis is measured '
                             'in more than one (e.g. g or ml)')
    parser.add_argument('--json', action='store_true',
                        help='emit cards, or the whole ranking with its '
                             'exclusions, as JSON instead of text')
    args = parser.parse_args(argv)

    try:
        category = get(args.category)
    except KeyError as exc:
        sys.exit(str(exc).strip("'"))

    paths, asins = split_arguments(args.feeds)
    records, provenance = feeds_module.merge(paths)
    records, provenance = one_marketplace(records, provenance, args.marketplace)
    # Where the records came from heads the report, so a number in it can be
    # traced back to a crawl. Machine-readable output gets it on stderr
    # instead, because a provenance line inside a JSONL stream is corruption.
    machine_readable = args.command == 'validated' or args.json
    print(feeds_module.provenance_line(provenance),
          file=sys.stderr if machine_readable else sys.stdout)

    if args.command == 'validated':
        # Validation with the selected category's plausibility profile, without
        # its classifier or claim evaluation. Corpus snapshots instead call
        # validate(record) without a profile to pin neutral validation.
        from ..validation import validate
        for record in records:
            print(json.dumps(validate(record, category.profile).as_dict(),
                             ensure_ascii=False))
        return

    cards = [category.evaluate(record) for record in records]
    require = tuple(key.strip() for key in args.require.split(',') if key.strip())
    for key in require:
        if key not in category.claim_keys:
            sys.exit(f'{key}: not a claim of {category.label}. '
                     f'Known: {", ".join(category.claim_keys)}')
    if args.axis and category.axis(args.axis) is None:
        sys.exit(f'{args.axis}: not an axis of {category.label}. '
                 f'Known: {", ".join(category.axis_keys)}')

    if args.command == 'summary':
        print(report.summary_text(cards))
    elif args.command == 'rank':
        if args.json:
            # The complete ranking, including every exclusion and its reason
            # code -- the text view stops at ten of those, and a consumer
            # counting them would be counting the terminal's patience.
            print(json.dumps(report.ranking(cards, args.axis or None, require,
                                            unit=args.unit or None),
                             ensure_ascii=False, indent=2))
        else:
            print(report.rank_text(cards, args.axis, require, args.limit,
                                   unit=args.unit or None))
    elif args.command == 'card':
        if not asins:
            sys.exit('card needs an ASIN')
        for asin in asins:
            card = pick(cards, asin)
            print(json.dumps(report.card_json(card), ensure_ascii=False, indent=2)
                  if args.json else report.card_text(card))
    elif args.command == 'cards':
        chosen = [card for card in cards if is_match(card)]
        for card in chosen:
            print(json.dumps(report.card_json(card), ensure_ascii=False)
                  if args.json else report.card_text(card))
    elif args.command == 'compare':
        if len(asins) != 2:
            sys.exit('compare needs exactly two ASINs')
        print(report.compare_text(pick(cards, asins[0]),
                                  pick(cards, asins[1])))


if __name__ == '__main__':
    main()
