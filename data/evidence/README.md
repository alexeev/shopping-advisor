# Evidence

Crawl output that a roadmap decision rests on, committed so the numbers in
[`../../ROADMAP.md`](../../ROADMAP.md) can be re-derived rather than taken on
trust. Everything else under `data/` is working output and stays out of git —
a run retains roughly 390 KB gzipped per product page, which does not belong
in a history. The same rule kept the third R13 trial's plan revisions,
intake reviews and buyer report out: their digest is the R13 entries in the
roadmap, and the six `probe-amazon-de-smartwatch-*` files below are the only
part of that trial whose value outlives the roadmap text.

| File | What it is |
|---|---|
| `validation-amazon-de-2026-09-14.jsonl.gz` | 195 product records, three queries, Amazon.de, no proxy, no browser. Schema v2 — the set every coverage and data-quality figure in EXTRACTION.md and R0 was measured on. |
| `validation-amazon-de-2026-09-15-v3.jsonl.gz` | The same three queries re-crawled under schema v3, so the records carry `run_id`, `locale` and the variation matrix. The basis for every R3 figure. |
| `validation-amazon-de-2026-09-15-v3.manifest.json` | That crawl's manifest. |
| `discovery-amazon-de-2026-09-14.jsonl.gz` | 213 discovery occurrences from the R1 verification crawl: every sighting, before de-duplication. The evidence for the sponsored share and the repeat-sighting rate. |
| `discovery-amazon-de-2026-09-14.manifest.json` | That crawl's manifest — arguments, locale, counts, stats, finish reason. |
| `validation-amazon-de-mounting-paste-2026-09-15-v4.jsonl.gz` | 90 product records, three Amazon.de queries for tyre mounting paste. The second category, and the basis for every R2 figure. |
| `validation-amazon-de-mounting-paste-2026-09-15-v4.manifest.json` | That crawl's manifest. |
| `validation-amazon-de-mounting-paste-2026-09-15-v5.jsonl.gz` | 48 product records, three narrower Amazon.de queries (`montagefluid fahrrad reifen`, `reifenmontagepaste wasserlöslich`, `montagepaste e-scooter reifen`). Crawled to look for a small pack the first three queries could have missed, and to refresh prices. Merged with v4 it is the 102-record set the widened claim patterns were measured on. |
| `validation-amazon-de-mounting-paste-2026-09-15-v5.manifest.json` | That crawl's manifest. |
| `validation-amazon-de-mounting-paste-2026-09-15-v6.jsonl.gz` | 53 product records, three brand-targeted queries (`rema tip top montagepaste`, `rema tip top reifenmontierpaste`, `remaxx montierpaste`). Crawled after a reader named an ASIN none of the six earlier queries had ever surfaced — not in the feeds and not in the discovery logs. It is the set that contains the 5 g tube, and the answer to "how much does a keyword crawl miss". |
| `validation-amazon-de-mounting-paste-2026-09-15-v6.manifest.json` | That crawl's manifest. |
| `validation-amazon-de-mounting-paste-2026-09-15-v7.jsonl.gz` | 54 records: a deeper brand crawl (3 queries, 2 pages) plus the first two products fetched by ASIN rather than found by search. It contains `B086BX8M3C`, which **thirteen queries across five crawls never surfaced** — including the three that name the brand. |
| `validation-amazon-de-mounting-paste-2026-09-15-v7.manifest.json` | The manifest of the ASIN fetch, kept in preference to the search run's because it is the first run in this repository whose `arguments.asin` is populated. |
| `probe-amazon-de-smartwatch-2026-09-18-class.jsonl.gz` | 20 product records from two class queries (`Smartwatch Tauchcomputer`, `Tauchcomputer Uhr GPS NFC`), first page each, on Amazon.de: the shelf-discovered baseline of the third R13 conversational trial. It holds the three dive-capable smartwatches the class queries surfaced (Suunto Ocean, Suunto Nautic S, Garmin Descent G2), five pure dive computers and cheap 5 ATM watches that a `smartwatch` classifier would have to decline. The `smartwatch` task-experiment category was built and tested against it through R15's procedure, and the committed brief `tests/intake/smartwatch-brief.json` reads all three probe feeds as the gate's eighth example. |
| `probe-amazon-de-smartwatch-2026-09-18-class.manifest.json` | That crawl's manifest: 22 responses, 2 search pages retained, no challenges. |
| `probe-amazon-de-smartwatch-2026-09-18-named.jsonl.gz` | 30 product records from five named-model queries (Garmin Descent Mk3, Descent G1, fenix 8, tactix 8, Huawei Watch Ultimate). The candidates here were supplied by the operating agent from manufacturer documentation and confirmed on the shelf, not discovered — the session ledger of the trial records that as selection bias. It contains the counterexamples a smartwatch category needs: accessories and straps returned for watch queries, the fenix E (no dive features), Apple Watch Ultra 3 (iPhone only) and Garmin Instinct models (10 ATM, no scuba mode). |
| `probe-amazon-de-smartwatch-2026-09-18-named.manifest.json` | That crawl's manifest: 35 responses, 5 search pages retained, 184 discovery occurrences. |
| `probe-amazon-de-smartwatch-2026-09-18-asin.jsonl.gz` | 7 product records fetched by ASIN: the models the named-model search pages sighted but did not open (Descent Mk3 43 mm in steel and bronze titanium, Descent Mk3i 51 mm, Descent G1, fenix 9, fenix 8 Pro, Huawei Watch Ultimate 2). Two of them list without a price. |
| `probe-amazon-de-smartwatch-2026-09-18-asin.manifest.json` | That crawl's manifest: 7 responses, `arguments.asin` populated, no search. |
| `probe-amazon-de-smartwatch-2026-09-18-{class,named,asin}-v2.jsonl.gz` | The same three runs **re-extracted offline from their retained pages** on 2026-09-18 under R15's third adaptation (`content.aplus.prose` and `content.aplus.comparison`): the same bytes read by newer code, no second request. 20 + 29 + 7 = 56 records — one page of the named run (`B0H8P8FT5Q`, a strap) no longer matched the digest its run recorded and the replay refused it, which is the check working. The as-crawled feeds above stay as they are; the gate's ninth example, `smartwatch-dive-nfc-reextracted`, reads these. |

## Reading them

```bash
uv run python -m shopping_advisor.analysis summary \
    data/evidence/validation-amazon-de-2026-09-14.jsonl.gz

uv run python -m shopping_advisor.analysis rank \
    data/evidence/validation-amazon-de-mounting-paste-2026-09-15-v4.jsonl.gz \
    --category tyre_mounting_paste --unit g
```

`--unit g` is required here and the refusal without it is the point: 22 of the
25 rankable pack sizes in this feed are in grams and 3 are in millilitres, and
one ordering over both would place a 50 ml tin among the tubs as though a
density had been supplied.

```python
from shopping_advisor import run
occurrences = run.load_discovery('data/runs/<run_id>')   # a live run
```

The manifests committed here predate T1, so `run.run_state(manifest)` reports
them as `legacy`: they have no page digests, no per-page fetch times and no
feed bindings. They are still the record of what those crawls asked for and
what came back; they are not evidence of the freshness of anything.

## Why the discovery log is separate from the records

One ASIN can be seen many times: under several queries, on several pages, and
twice on a single page — once organic and once sponsored. Fetching its detail
page repeatedly is waste, so the crawler de-duplicates. But the sightings
themselves are the answer to "what does a shopper actually see", and they used
to be discarded before anything was written down.

Measured on the crawl above: **213 occurrences of 170 distinct ASINs — 20% of
sightings are repeats**, 12 ASINs turned up under more than one query, and
**69 of 213 placements (32%) are sponsored**.

## Schema

The 2026-09-14 set is schema v2 and has no `variation` key; the 2026-09-15
pasta set is v3; the mounting-paste sets are v4 and v5.

**The v4 set is schema v4 and carries five prices that schema v6 no longer
publishes** — `B000RW5FVA`, `B000UJB2GW`, `B001B0EIYM`, `B01LX0NO1X` and
`B0FCY5C48Y`, each of which is one end of a price range that the extractor
read as a price (see CONTRACT.md §7, schema v6). It is kept as crawled anyway,
because it is the evidence for the R2 figures *at that schema* and rewriting it
would make those figures unreproducible. v5 is re-extracted at schema v6, so
the two sets deliberately disagree about those ASINs; the run's retained pages
are the tiebreak, and re-extracting v4 offline reproduces v5's behaviour
exactly.

The two mounting-paste sets are three hours apart and are kept separately for
the same reason the pasta ones are. v5 is not a replacement: it re-crawled 36
of v4's ASINs — which is how the prices in any report built on them are
current — and it answers a question v4 could not, because a search that never
used the words "fluid" or "wasserlöslich" cannot show you that it missed
nothing. Of 48 records, 12 ASINs were new and 3 of those are mounting paste, all of
them 5 kg kits.

**That conclusion was wrong, and v6 is why it is worth leaving in writing.**
Six queries across two crawls agreed that the smallest pack on the shelf was
50 ml, and a reader then named `B087WQJQDS` — a 5 g tube, ten times smaller
than anything either crawl had seen. It is absent from both feeds *and* from
both discovery logs, so it was never sighted and then dropped; it simply never
ranked on page 1 for any query used. A brand-name query found it at position
14 immediately. Two crawls agreeing about a shelf is evidence about the
queries, not about the shelf.

v7 then found the floor of that argument. `B086BX8M3C` is a 50 ml REMA TIP TOP
mounting gel, and **no query ever reached it** -- not the three brand-name ones
in v6, not three more in v7 over two pages each. Its Amazon title is "Rema Tip
Top 501004 - Schwammdose, Transparent, 50 ml": it names the container, the
colour and the volume, and no word a shopper or a crawler would search for. A
listing can be invisible to search *and* to a title-based classifier at the
same time, and for the same reason. That is what `-a asin=` exists for.

The pasta sets are kept **as crawled**, because re-crawling does not reproduce
a measurement — the two are eighteen hours apart and already disagree in a way
worth knowing about:

| | v2, 2026-09-14 | v3, 2026-09-15 |
|---|---:|---:|
| Records with a price | 195/195 | 141/195 |
| Records with `availability` | 190/195 | 137/195 |

Not an extraction change — the code produces identical output on the older set
today. Those 54 products had no purchasable offer at the later crawl time, and
the discovery log agrees: search did not price them either. Product
availability moves, and a coverage figure is a measurement of one moment.

The mounting-paste set is a different case and worth stating plainly. It was
crawled under v3 and the schema moved to v4 inside the same milestone, so it
was **re-extracted offline from that run's retained pages** — the same bytes,
read by newer code, no second request to Amazon. That is not a re-crawl and it
does not disturb a measurement; it is the capability R1 was built for, used
for the first time. Nothing else was touched: the lineage, the crawl time and
the page store are the originals.

Older records stay readable. The validation layer reads v2 and v3 records
unchanged; they simply carry fields it ignores, such as the removed
`nutrition.confidence`. Every R2 figure quoted for dry pasta was measured on
the v3 set with v4 code.
