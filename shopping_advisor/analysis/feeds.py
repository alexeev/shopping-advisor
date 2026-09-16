"""Several crawls, one record per listing.

A research question outlives a single crawl. Fusilli took three: a broad one,
a brand-name one run an hour later, and an earlier pasta crawl from the night
before that already held a third of the shelf. 471 unique products came out of
582 records, which means **111 ASINs were crawled more than once** and
something has to decide which sighting the study uses.

The rule is the freshest one wins, by ``fetched_at``, and not the order the
feeds were named on the command line. Order looks like a decision and is not
one: a shell glob sorts alphabetically, so ``data/fusilli_*.jsonl`` would have
silently preferred ``fusilli_brands`` over the hour-younger ``fusilli_broad``
for every ASIN they share. Price and availability are the two fields this
project treats as a snapshot, and they are exactly the two an arbitrary
argument order would get wrong.

A record with no ``fetched_at`` loses to any record that has one: it cannot
claim to be newer than something that says when it was fetched.

Two corrections were made in T1, both of which the old rule got wrong without
reporting anything.

**A listing is a marketplace and an ASIN, not an ASIN.** ASINs are minted per
marketplace and the same ten characters name different products on different
Amazon sites -- and where they do name the same product, it is a different
offer, in another currency, with another delivery region. Keyed by ASIN alone,
a two-row probe of one ``.de`` record and one ``.com`` record kept only the
newer ``.com`` row and silently discarded the local price. The key is now the
normalised host plus the ASIN, and the merge reports which marketplaces it
saw so a caller can refuse to compare across them.

**A tie is resolved by the records, not by the argument list.** Equal
``fetched_at`` used to keep whichever feed was read first, which is the same
hidden dependency on glob order in a smaller place. Ties now fall through a
declared order: the newer *extraction* of the same observation wins, because
re-running today's extractor over retained bytes is a better reading of the
same evidence -- and it is not a new observation of the product, which is why
``extracted_at`` is a separate field from ``fetched_at``.
"""

import datetime as _dt
import hashlib
import json

from ..extraction.marketplaces import domain_key
from ..run import read_jsonl

# Older than any real crawl, so an undated record never wins a tie-break.
BEGINNING = _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)


def _stamp(value):
    """One timestamp field, or the beginning of time if it will not parse."""
    if not value:
        return BEGINNING
    try:
        parsed = _dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return BEGINNING
    # Naive and aware timestamps do not compare, and a feed that lost its
    # offset is still a feed. Read it as UTC, which is what the crawl writes.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.timezone.utc)


def fetched_at(record):
    """When this record was crawled, or the beginning of time if it won't say."""
    return _stamp(record.get('fetched_at'))


def marketplace_of(record):
    """The normalised marketplace this record was observed on, or ``''``.

    ``''`` means the record does not say, which is what a feed written before
    provenance existed looks like. It is kept as its own scope rather than
    folded into a real marketplace: an unlabelled record cannot be asserted to
    belong to one.
    """
    return domain_key(record.get('marketplace') or '')


def listing_key(record, path='', position=None):
    """``(marketplace, asin)`` -- the identity a merge may collapse on.

    A record with no ASIN cannot be merged with anything, so it keys on where
    it was read from instead of colliding with every other anonymous row.
    """
    asin = record.get('asin')
    if not asin:
        return ('', '', str(path), position)
    return (marketplace_of(record), asin)


def _digest(record):
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, ensure_ascii=False,
                   default=str).encode('utf-8')).hexdigest()


def order_key(record):
    """How two observations of one listing are ordered. Highest wins.

    Declared here in one place because every part of it is a decision:

    1. ``fetched_at`` -- when the bytes were obtained. The only term that is
       about the *product*; everything below it breaks a tie between two
       readings of equally old evidence.
    2. ``schema_version`` -- a later extractor reads more of the same page.
    3. ``extracted_at`` -- present only on a replay, so a re-extraction of
       retained bytes beats the original reading of them.
    4. ``run_id``, then a digest of the record -- arbitrary, and deliberately
       so: what matters is that two callers with the same feeds in a different
       order choose the same record, not which one they choose.
    """
    schema = record.get('schema_version')
    return (fetched_at(record),
            schema if isinstance(schema, int) else -1,
            _stamp(record.get('extracted_at')),
            str(record.get('run_id') or ''),
            _digest(record))


def _observation(record, path):
    """The audit line for one observation of a listing."""
    return {'feed': str(path), 'run_id': record.get('run_id') or '',
            'fetched_at': record.get('fetched_at') or '',
            'extracted_at': record.get('extracted_at') or '',
            'schema_version': record.get('schema_version')}


def merge(paths):
    """``(records, provenance)`` — the freshest record of each listing.

    ``provenance`` counts what the merge did: how many records survived, how
    many feeds they came from, how many listings were crawled more than once
    and resolved to their freshest copy, which marketplaces appeared, and --
    for each supersession -- which observation was selected and which were
    set aside. That last one is the audit trail: a price that changed between
    two crawls is a fact about the shelf, and the merge is where the study
    stops being able to see it unless it is written down.
    """
    chosen, order, sources = {}, [], {}
    for path in paths:
        for position, record in enumerate(read_jsonl(path)):
            key = listing_key(record, path, position)
            # Kept as (record, feed) pairs and matched by identity later, so
            # two observations that agree on every recorded field are still
            # two observations.
            sources.setdefault(key, []).append((record, path))
            if key not in chosen:
                chosen[key] = record
                order.append(key)
                continue
            if order_key(record) > order_key(chosen[key]):
                chosen[key] = record

    supersessions = []
    for key in order:
        seen = sources[key]
        if len(seen) < 2:
            continue
        supersessions.append({
            'marketplace': key[0], 'asin': key[1],
            'selected': next(_observation(record, path)
                             for record, path in seen
                             if record is chosen[key]),
            'superseded': [_observation(record, path)
                           for record, path in seen
                           if record is not chosen[key]],
        })

    records = [chosen[key] for key in order]
    return (records,
            {'records': len(order), 'feeds': len(paths),
             'superseded': len(supersessions),
             'marketplaces': marketplaces(records),
             'supersessions': supersessions})


def marketplaces(records):
    """``{normalised marketplace: records}``, in descending size."""
    counts = {}
    for record in records:
        market = marketplace_of(record)
        counts[market] = counts.get(market, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def select_marketplace(records, wanted):
    """``(kept, set_aside)`` for one stated marketplace.

    Filtering is the *explicit* answer to a mixed feed set. The implicit one
    -- rank everything and let the units sort themselves out -- produces a
    ranking across two currencies and two delivery regions that reads exactly
    like a ranking within one.
    """
    market = domain_key(wanted)
    kept = [record for record in records if marketplace_of(record) == market]
    return kept, [record for record in records if marketplace_of(record) != market]


def provenance_line(provenance):
    """The one line a report opens with, so a number can be traced to a crawl."""
    feeds, superseded = provenance['feeds'], provenance['superseded']
    seen = provenance.get('marketplaces') or {}
    line = (f'{provenance["records"]} records from {feeds} '
            f'feed{"s" if feeds != 1 else ""}, '
            f'{superseded} ASIN{"s" if superseded != 1 else ""} '
            f'superseded by a fresher crawl')
    if len(seen) > 1:
        line += (' · ' + ', '.join(f'{market or "unlabelled"} {count}'
                                   for market, count in seen.items()))
    elif seen and next(iter(seen)):
        # One marketplace is still worth naming: the report that follows is
        # about that shelf, in that currency, and nothing else says so.
        line += ' · ' + next(iter(seen))
    if provenance.get('set_aside'):
        line += (f' · {provenance["set_aside"]} record'
                 f'{"s" if provenance["set_aside"] != 1 else ""} from another '
                 f'marketplace set aside')
    return line
