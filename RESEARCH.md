# Product research runbook

This is the current workflow for the shipped tools. Read [AGENTS.md](AGENTS.md)
first. T0 makes the existing workflow discoverable and T1 makes acquisition and
replay trustworthy; structured study artifacts and automated report validation
in the [transition plan](AGENT_TRANSITION_PLAN.md) are not implemented yet.

## Offline walkthrough

After [setup and shell configuration](README.md#setup-and-first-check), run the
following commands from the repository root. Each is a single line that works
in PowerShell or a POSIX shell. `--offline` prevents uv downloads; these analysis
commands themselves only read local feeds and perform no network requests.

**Example question:** Among the dry pastas in the committed case set, which
have a usable price per kilogram, and what makes a comparison defensible?
This demonstrates evidence handling, not current buying advice or exhaustive
market discovery. The feed deliberately includes known defects and controls.

### 1. Inspect quality and exclusions

```text
uv run --offline --locked python -m amazon_scraper.analysis summary tests/cases/pasta_v1.jsonl.gz --category dry_pasta
```

Expect a provenance line reading 25 records from one feed on `amazon.de`, then
25 records, 22 classified as dry pasta, three other products, and no
undecided classification. The summary explicitly says accuracy is not measured:
a wrong rejection could still be a confident decision. Inspect the status
counts rather than treating a populated numeric field as usable.

### 2. Rank on the declared axis

```text
uv run --offline --locked python -m amazon_scraper.analysis rank tests/cases/pasta_v1.jsonl.gz --category dry_pasta --limit 3
```

Expect price-per-kg ranking, 14 offers with a trusted ranking value, and eight
excluded records. The first result is `B0CT3Q17FP` at the historical fixture
price of 1.58 EUR/kg. This establishes cheapest within these rankable fixture
records; it does not establish best pasta for a user or a currently purchasable
offer. Read the exclusion reasons below the ranking.

### 3. Inspect a card and its evidence

```text
uv run --offline --locked python -m amazon_scraper.analysis card tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 --category dry_pasta
```

Locate the quantity, price-per-kg value, statuses, and source quotations.
For this category the same card can be inspected as JSON:

```text
uv run --offline --locked python -m amazon_scraper.analysis card tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 --category dry_pasta --json
```

The provenance summary goes to stderr and JSON goes to stdout. A single
`card --json` is a pretty-printed object; use `cards --json` for JSONL across
category matches. Do not generalize this example's JSON completeness to basmati.

### 4. Compare two usable products

```text
uv run --offline --locked python -m amazon_scraper.analysis compare tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 B0DQ2N5HRW --category dry_pasta
```

Expect a `Differences` section including the cheaper-per-kilogram comparison.
Read the individual axes and caveats before turning that into purchase advice.

### 5. Exercise a refusal

```text
uv run --offline --locked python -m amazon_scraper.analysis compare tests/cases/pasta_v1.jsonl.gz B08JLSVW3J B08WJGD5Z5 --category dry_pasta
```

Expect `Price per kg` under `Cannot be compared`: the first product's pack
quantity is disputed. The card can show an alternative calculation without
promoting it to a trusted ranking value. Do not remove the contradiction to
force a comparison.

### 6. Inspect the underlying validation

```text
uv run --offline --locked python -m amazon_scraper.analysis validated tests/cases/pasta_v1.jsonl.gz --category dry_pasta
```

Expect 25 JSONL records with `contract_version: 2` and
`category_profile: "dry_pasta"`. This command applies the selected category's
plausibility bands; it does not run its classifier/claim evaluator. For neutral
validation, use the Python API `validate(record)` without a profile. There is
no neutral CLI option.

### 7. Locate the evidence and explain the result

- The input is [tests/cases/pasta_v1.jsonl.gz](tests/cases/pasta_v1.jsonl.gz);
  [its README](tests/cases/README.md) explains why the named products were chosen.
- Cards identify record fields and quote the supporting text. Raw fields remain
  in the source JSONL; validated outputs do not retain every raw field.
- The separate [saved-page corpus](tests/corpus/README.md) tests extraction and
  neutral validation. Not every case-feed product has a saved HTML fixture.
- [data/evidence/README.md](data/evidence/README.md) describes larger committed
  historical crawls; these are not a complete archive of every study.

A defensible example conclusion distinguishes the lowest usable historical
price from a suitability recommendation, explains the disputed pack exclusion,
and labels the dataset as selected regression cases. No fresh crawl is needed
to answer this offline question.

## Live research workflow

### Agree the brief

A request arrives underspecified and that is normal: "I need a new vacuum
cleaner" is a real starting point, not a defective one. The job of this step is
to end with a written brief, not to interrogate.

Write the brief down **separately from the code**. This repository has already
paid for not doing that: tyre mounting paste ranks the *smallest* pack first
because one reader was fitting one scooter tyre, and basmati's score weights
come from one particular question. Both are now facts about a category module,
where a later reader cannot tell a user's constraint from a property of the
product class. A constraint belongs in the brief; only what is true for every
buyer of that product belongs in a category.

#### Look before you ask

Two minutes of inspection changes which questions are worth asking, so do it
first: is the category supported, what evidence is already on disk, what can
the tools actually decide. Ask nothing that inspection would have answered.

#### Three kinds of missing information

| Kind | Test | What to do |
|---|---|---|
| **Blocking** | Under *every* plausible answer the work would be wrong or useless | Ask, and wait. Do not collect. |
| **Assumable** | A wrong guess costs a paragraph, not the study | Choose the safer default, state it as an assumption, continue |
| **Not worth asking** | The evidence will answer it, or the tools decide it deterministically | Do not ask |

Blocking in practice: the marketplace and delivery region (an Amazon.de answer
is useless to someone buying elsewhere); a hard requirement that eliminates
most of the shelf; the cost basis when the question is "cheapest"; and whether
an unsupported category should be built at all — see below. Nearly everything
else is assumable, including budget: absent one, assume no cap, say so, and let
the ranking show prices.

#### How to ask

One batched round, at most about four questions, each stating **why it changes
the answer** and **what happens if it goes unanswered**. Not a questionnaire,
and not one question per turn. While waiting, do the work that does not depend
on the answer: inspect retained evidence, check what the category module knows,
read the existing cases.

"You decide" is an answer. Record it as an assumption with the default you
chose, and make the report show what would change if that default were wrong.

#### Say so when the category is not supported

Three categories ship: `dry_pasta`, `tyre_mounting_paste`, `basmati_rice`. For
anything else — a vacuum cleaner, a display — the generic layer still works
(price, pack quantity, contradictions between the vendor's own statements) but
nothing in the repository knows what makes one *good*. Surface that as a choice
rather than working around it:

- build and test a category module first, as a scoped maintenance change, and
  then research; or
- answer within stated limits, using only what the generic layer can check, and
  label it as not a suitability judgement.

Name the category on **every** command: `--category` defaults to `dry_pasta`.
The two ways that goes wrong are not equally visible.

- `summary`, `rank`, `card` and `compare` run the category's classifier first,
  so a wrong category usually produces an empty or nearly empty result. The
  committed mounting-paste cases come out as `0 dry pasta · 0 offers`, which is
  hard to mistake for an answer.
- `validated` applies the category's **plausibility profile regardless of
  classification**, and that failure is quiet. Running the same 34
  mounting-paste records under dry pasta's bands moves **14 values**, mostly
  `trusted` → `disputed`, with notes like *"252 EUR/kg is outside the 0.8-40
  range dry pasta sells in"*. The values were right; the bands were the wrong
  product's.

#### Read it back before spending

Collection is the only step that touches Amazon, cannot be undone and costs
real requests. Before it, restate the brief in a few lines — question, hard
requirements, assumptions, limits — and get agreement. Keep existing user
authorization: this is a confirmation of *what* is being researched, not a new
permission ritual.

#### The brief itself

Create a dated working note under `reports/`. There is no enforced brief
schema yet — that is T2 — so a note with these headings is the current form:

- Question/use case, category, marketplace and delivery region.
- Hard requirements versus preferences, budget/cost basis, and unacceptable
  alternatives. Record what evidence would establish each decisive requirement.
- Freshness needed for price, availability, and other time-sensitive claims.
- Known ASINs, planned generic/brand queries, external sources, and why chosen.
- Query/page/product/time limits, assumptions, and material unresolved questions.
- Which questions were asked, which were answered, and which defaults were used.

If a requirement changes after collection has started, do not quietly re-rank.
Either finish under the recorded brief and report the change, or record a new
brief revision and show which decisions moved. An unrecorded requirement change
is indistinguishable from a result.

#### Worked example

> **User:** I need a new vacuum cleaner.
>
> **Agent:** Before I collect anything: this repository has category knowledge
> for dry pasta, tyre mounting paste and basmati rice only. For vacuum cleaners
> I can check prices, pack/unit quantities and contradictions in the vendors'
> own statements, but nothing here knows what makes a vacuum cleaner good, so I
> cannot rank suitability yet. Two options: I build and test a vacuum-cleaner
> category first, or I give you a deliberately limited price/claims overview
> and say what it does not establish.
>
> Either way, two things change the answer and I cannot guess them:
> (1) Are you buying on Amazon.de for delivery in Germany? Everything here is
> validated for that one marketplace. (2) Is there a hard requirement that
> rules most models out — pet hair, mostly carpet, stairs, or a noise limit?
>
> Unless you say otherwise I will assume: no budget cap (prices shown in the
> ranking), corded or cordless both acceptable, and current listings rather
> than historical ones.

Three properties make this effective: it names what the tools cannot do before
asking for anything, it asks two questions instead of ten, and it states the
defaults so silence is still a usable answer.

### Live collection

Inspect existing feeds/pages first. Fresh prices require a new observation;
new parser fields can often be obtained by re-extraction. Keep the default
profile's pacing and the encoding variable from README. Choose a new output
path for every run; the example path below must not already contain evidence
you need.

The proxy-free profile is the default since T1, so no profile variable is
needed. `SCRAPY_PROJECT=baseline` still selects the same profile if a written
command already sets it. Both shells run the same line:

```text
uv run --offline --locked scrapy crawl amazon_product -a keyword="spaghetti hartweizen" -a domain="www.amazon.de" -a max_pages=1 -a max_products_per_query=5 -s CLOSESPIDER_TIMEOUT=180 -O data/research-example-01.jsonl
```

Here **`--offline` applies to uv, not the crawler**: Scrapy makes marketplace
requests. `CLOSESPIDER_TIMEOUT` bounds crawl duration, but in-flight requests
can take time to finish; timeout closure means partial results. The product cap
bounds discovery, not retries or the exact number of HTTP requests. The baseline
uses concurrency 1, configured delay 9 seconds with jitter/AutoThrottle, and two
retries. Keep page retention enabled and run crawls sequentially.

For a named product, replace the `keyword` argument with `-a asin="B086BX8M3C"`
and choose another output path. Several queries or ASINs use semicolon-separated
strings. An ASIN-only run does not perform the default pasta search. Named
products matter: search can miss a relevant product even across brand queries.

Record the logged run ID and the feed path together; the manifest also names
the feed the crawl was told to write. Read the run back with:

```text
uv run --offline --locked python -m amazon_scraper.run inspect data/runs/ACTUAL_RUN_ID
```

It reports the run state (`complete`, `interrupted`, or `legacy` for a store
written before T1), the code revision and settings profile that produced the
evidence, challenge/HTTP/parse counters, retained failure samples, and any
quarantined pages. A run that never closed its manifest is `interrupted`: its
coverage is partial regardless of how many records the feed holds.

Inspect `discovery.jsonl` to distinguish never-sighted products from repeated
sightings, and `pages.jsonl` for each retained page's fetch time, URLs, status
and stored-bytes digest. Direct ASIN seeds do not appear as search sightings;
their feed `search_query` is `asin:<ASIN>` and the arguments are in the
manifest. Add `-a keep_search_pages=1` when the study needs to show what a
query returned; it is off by default because search pages are large.

Challenge pages and titleless responses are retained as bounded, truncated
samples under `failures/`, capped per reason. A page whose redaction failed is
kept under `quarantine/`: it is still evidence and still re-extracts, but it
must not be exported or promoted into the corpus.

A `finished` crawl or HTTP 200 response does not prove adequate research
coverage. If challenges or failures leave decisive gaps, record them, stop
repeated collection, and use a bounded later attempt or a qualified answer.
Do not fix a source absence by changing trust rules.

### Re-extract and analyze

For a retained run, replace these paths with the actual run directory, original
feed, and a new destination. The command works in either shell:

```text
uv run --offline --locked python -m amazon_scraper.run reextract data/runs/ACTUAL_RUN_ID --feed data/research-example-01.jsonl -o data/research-example-01-reextracted.jsonl
```

Supply the original feed so the discovery lineage — which query found the
product, and at which position — survives. Fetch time comes from the run's own
page index and survives the bundle being copied; a run store written before T1
has no index, and its replayed records then carry `fetched_at: null` with
`fetched_at_source: "unknown"` rather than a filesystem timestamp. Treat those
as unknown freshness. Keep original feeds unchanged.

Replay refuses a feed that belongs to another crawl or another marketplace,
and reports a page whose stored bytes no longer match the digest the run
recorded. A replayed record carries `extracted_at`, which is how a merge tells
a new reading of old bytes from a new observation.

Use the walkthrough's analysis commands with your feed and explicit category.
Multiple feeds go in the positional list. Merging keys on marketplace and ASIN,
so a mixed set no longer loses records — but an analysis still covers one
marketplace, and the command stops until `--marketplace` names one. A newer
record without a price must not be silently replaced with an old priced record
in the recommendation.

Read cards for known candidates, excluded candidates, and the shortlist.
`summary` counts classifier decisions, not accuracy. Compare units, variants,
pack sizes and cost assumptions before preferring a ranking row. `rank` does
not enforce a complete user brief: it orders one axis, in one unit, and states
the exclusions. It refuses an axis with no declared better direction, and asks
for `--unit` when the axis is measured in more than one — name the unit the
use case actually needs rather than taking the larger group. `compare` refuses
incompatible units and can expose the limitation.

### Check external evidence and write the report

Read manufacturer specifications, independent tests, or other relevant sources
when the question needs facts absent from Amazon. Record URL, title/publisher,
publication and access dates, the exact supporting location, product/variant
identity, and limits. Preserve a permitted source/excerpt locally where useful.
Distinguish a vendor declaration from a measured property and a historical test
from evidence about the current batch. Unavailable sources remain unverified.

Basmati's embedded external-test constants lack complete source provenance and
applicability controls. Its text cards show its seven-part score, but `rank`
still sorts price per kilogram and JSON omits material basmati extras. Do not
claim that the CLI reproduces a composite shortlist or that an embedded
`trusted` external match establishes current product safety.

Follow [reports/README.md](reports/README.md) for output conventions. Include the
question, as-of dates, recommendation/alternatives, suitability and tradeoffs,
comparison values, exclusions, sources per material claim, and unresolved gaps.
Record exact feed paths, run IDs, commands/options and relevant code revision in
the working note. Assess freshness and delivered cost explicitly; absent
shipping data is unknown, not zero.

Before delivery, check that decisive numeric values are usable, units/currency
agree, citations support the selected variant and claim, sample reviews are
not used for rates, and conclusions say “among sources/products inspected”
where coverage is limited. Record the checks and remaining uncertainty.
There is no automated report validator today. An honest insufficient-evidence
answer is a valid result.

### Close and capture improvements

Keep working notes and reports at explicit locations and tell the user where
they are. `reports/` and most of `data/` are gitignored; this is not a backup or
portable study archive. Do not claim that another checkout can reproduce a
report unless its inputs are available there.

A study does not end at the report. Every study so far has produced at least
one finding about the *tooling* — R5's reviews, R7's claim attribution, R8's
German compounds, T1's identity and replay gaps — and those are only worth
anything if they leave the conversation.

#### The improvement cycle

```text
observation → reproducible case → proposed change → review → versioned adoption
     ↑                                                                    │
     └──────────────────── measured effect ───────────────────────────────┘
```

1. **Observation.** Log it with the originating study, run ID and ASIN or
   source, observed versus expected behaviour, the affected layer, and a
   reproduction command. A plausible idea with no evidence stays a hypothesis
   and is recorded as one. **The log itself never changes live behaviour.**
2. **Reproducible case.** Reproduce it offline from retained evidence before
   proposing anything. If the evidence was never retained, that is itself the
   finding — record it and say what would have to be kept next time.
3. **Proposed change.** Scope it to the narrowest responsible layer, following
   [the maintenance workflow](AGENTS.md#maintenance-workflow).
4. **Review and versioned adoption.** Tests, a readable diff, `CONTRACT.md`'s
   version rules when a published meaning moves, and a dated roadmap entry for
   anything that changes policy rather than fixing a defect.
5. **Measured effect.** State what actually changed: a count, a snapshot diff,
   a failing case that now passes. "Contract v2 moved exactly `contract_version`
   on 39 records and `offer[0]` on the 27 with a family" is a measured effect;
   "improved provenance" is not. A change with no measurable effect was
   cosmetic, and recording that is also useful.

#### Where each learning goes

| Learning | Durable home |
|---|---|
| A parser, quantity, attribution or classifier defect | Code, plus a regression test and a sanitized corpus/case input |
| Category reasoning or a new preference method | The category module and its cases, with applicability limits |
| A time-sensitive external product finding | Dated evidence with its source and applicability — never a permanent instruction |
| A repeatable operator procedure | This runbook or `AGENTS.md`, with the commands verified against the committed example |
| An architectural or collection-policy decision | A dated entry in `ROADMAP.md`, linked to the measurement that argues for it |
| An unproven improvement | A roadmap candidate with an experiment **and a stopping criterion** — R9 and R10 are the precedent |

Promote to the narrowest home that holds. Every promoted rule needs its scope
and a counterexample, not just the product that suggested it. Do not create a
separate memory store that competes with these files.

#### Improve the questions, not only the code

At close, check the brief against what actually decided the answer:

- Which questions changed the recommendation? Those belong in the blocking list
  in [Agree the brief](#agree-the-brief).
- Which were answered and then never used? Those are noise — stop asking them.
- Which assumptions turned out to be load-bearing? Those should have been
  questions, and the report should have said what would change if they were wrong.
- Which defaults did the user silently accept every time? Those can become
  stated defaults rather than questions.

This is the part of the loop that is easy to skip, because nothing fails when
it is skipped. A study that took four rounds of clarification and a study that
took one produce the same report; only this step tells the next agent which
one to imitate.

Keep the study's original evidence and explain any changed analysis after a
fix. Do not weaken a trust rule, a plausibility band or an elicitation default
to make a preferred product win.

## Current limitations

| Limitation | What to do now | Planned stage |
|---|---|---|
| One analysis covers one marketplace; cross-marketplace comparison is unsupported | Name the marketplace with `--marketplace` and report only that shelf | R4/T5 |
| Evidence collected before T1 has no page digests, recorded fetch times or feed bindings | `inspect` reports such a run as `legacy`; label its freshness unknown rather than inferring it | — (historical data) |
| Feeds are bound by the run id on their records, not by a digest taken at close | Keep original feeds unchanged and record their paths; a merged multi-run feed reports `mixed` lineage | T2 |
| Failure capture is bounded, and search pages are retained only on request | Read the capped counters in the manifest; re-collect with `keep_search_pages=1` when discovery itself is in question | — (by design) |
| A quarantined page is evidence but not exportable | Re-extract it if needed; never promote it into the corpus or attach it to a report | — (by design) |
| No structured study brief, complete category JSON, or report checks | Keep explicit working notes and perform documented manual verification | T2/T3 |
| Original full studies/reports and basmati source documents are not all tracked | Use the committed walkthrough for onboarding; request/rebuild missing evidence only when the task needs it | T2/T3 |
| No two-provider acceptance trial yet | Load the same canonical instructions; do not claim proven provider handoff | T4 |

## Failure diagnosis

| Symptom | First evidence to inspect |
|---|---|
| Setup/profile/locale failure | README troubleshooting, `scrapy.cfg`, current shell variables, `settings.py` |
| Challenge, failed download or missing candidates | `run inspect`, the manifest stats, retained `failures/` samples, discovery occurrences, planned queries/ASINs |
| A crawl that stopped without a summary | `run inspect`: an `interrupted` state means the manifest never closed and coverage is partial |
| Missing or wrong extracted field | `extraction.errors`, raw content/tables, retained page; reproduce with `reextract` |
| A replay that refuses a feed or a page | The feed belongs to another crawl/marketplace, or the stored bytes no longer match the run's recorded digest |
| Disputed number | Evidence card and source fields, quantity/price units, category profile |
| Expected product classified out | Title, ingredients/body, the category classifier and existing cases |
| Test snapshot mismatch | Field-level diff and saved page; explain the change before updating any expected output |

Do not recrawl just to reproduce a parser error whose page is already retained.
If the required evidence was never retained, record that limitation explicitly.
