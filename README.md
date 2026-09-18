# Shopping Advisor

Shopping Advisor turns a purchasing need into a decision the buyer can defend,
or into a precise account of why the evidence does not support one. An AI
agent does the research through a coding interface, working for the buyer: it
gathers the shelf, checks the vendors' numbers, brings in independent tests
where the page cannot answer, and keeps what it learned for the next question.
[PURPOSE.md](PURPOSE.md) says what that is for, whose side the agent is on and
where its role ends; this file says what has shipped and how to run it.

Underneath, it is a durable research harness for an AI software agent, with
an AI coding interface as its permanent user interface, extended through
small, tested changes when a request needs a capability that does not yet
exist. It is permanently incomplete by design: success means accommodating
unseen problems safely, not implementing every category in advance.

Today it provides briefs, retained evidence, validation, category analysis and
replayable studies. Routine task-driven extension remains planned.

Data collection from Amazon.de through Scrapy is the current source integration. Its
**`amazon_product`** spider handles search, pagination, and direct ASIN fetches.
The supported scope below distinguishes shipped tools from the product vision.

## Start here

A buyer or a stakeholder starts at PURPOSE; an operating agent at AGENTS; a
maintainer at CONTRACT and the roadmap's decision principles.

| Need | Read |
|---|---|
| Understand what the product is for, and for whom | [PURPOSE.md](PURPOSE.md) — the buyer's problem, the agent's role and its limits, what a finished outcome owes the buyer, and a glossary |
| See what a finished outcome looks like | [tests/studies](tests/studies/README.md) — two committed studies over one feed: one reaches a recommendation, one refuses and says exactly why |
| Operate or maintain the repository as an agent | [AGENTS.md](AGENTS.md) — canonical, provider-neutral instructions |
| Research a product or try the offline example | [RESEARCH.md](RESEARCH.md) — current runbook and commands |
| Understand fields and trust semantics | [CONTRACT.md](CONTRACT.md) — extraction schema **6**, validation contract **2** |
| Understand priorities and previous decisions | [ROADMAP.md](ROADMAP.md) — the one plan of record |
| Design the conversational entry point | [INTAKE.md](INTAKE.md) — what intake must preserve, assessed before R13 |
| Run or replay a saved study | [RESEARCH.md](RESEARCH.md#a-saved-study-end-to-end) — worked examples under [tests/studies](tests/studies/README.md) |
| Verify the repository before finishing a change | [AGENTS.md](AGENTS.md#environment-and-checks) — one local gate, `maintenance check` |

`CLAUDE.md` is a thin entry point to the same instructions. If an agent does
not automatically discover repository instructions, tell it to read
`AGENTS.md` and `RESEARCH.md` before starting. There is no provider SDK or API
credential required for crawling, analysis, or tests.

## Supported scope

This section is the canonical written statement of scope. Where another
document repeats a fact from it and the two disagree, this section wins and
the other is corrected; the registry the gate checks is the truth behind the
category list.

- **Amazon.de** is the validated research marketplace, with an explicit German
  acquisition locale. Its baseline profile uses no proxy or browser.
- Amazon.com has one committed product-page regression fixture and historical
  probes; full marketplace support remains deferred (R4). Amazon.co.uk and
  Amazon.it profile entries are not validated support. The `.it` profile uses
  German labels; unknown domains fall back to English. Do not treat successful
  parsing or a profile entry as proof that a marketplace is supported.
- Four category analyzers ship: `dry_pasta`, `tyre_mounting_paste`,
  `basmati_rice` and `school_backpack`. Their defaults reflect particular use
  cases; a ranking alone
  does not establish suitability for a new question. `study capabilities`
  publishes what each has earned, where it was measured and what it declines:
  three are maintained capabilities and `school_backpack` is a task
  experiment with one study behind it.
- Study reports now have deterministic evidence checks and a separate semantic
  review. The researcher still establishes requirements, verifies sources and
  their meaning, and records the limits. Automated checks do not establish truth.

### Where this is going

The user describes a purchase and receives useful questions, research, evidence,
a comparison and a recommendation—or a precise account of insufficient evidence.
The agent discovers what matters, reuses existing capabilities, detects gaps,
adds and validates what is needed, and retains demonstrated learning. Categories,
sources, extraction techniques and comparison methods can all evolve this way.
Engineering is visible to the user when it affects cost, confidence or the decision.
What all of that is for, and what the product is not, is stated once in
[PURPOSE.md](PURPOSE.md).

The [product vision and roadmap assessment](ROADMAP.md#product-vision--the-shopping-conversation)
define the minimum operating model, architectural safeguards and delivery order.
The local maintenance gate, R13's intake machinery and R16's capability index
with its lifecycle records have shipped; R13's conversational trials come next,
then R15 controlled adaptation, R11 category synthesis, R12 coverage, R16's
task-experiment entry for task-born capabilities and R14 unseen-problem trials.
The supported scope above remains the operational limit until those gates ship. Cross-platform and provider-interchangeability
trials are [deferred to R17](ROADMAP.md#r17--portability-evidence) and block
only the claim that either provider stack can operate this repository; the
repository is provider-neutral by design, and that has not been measured.

## Setup and first check

Run commands from the repository root. The project uses CPython **3.14** and
Scrapy **2.19.x**, with dependencies declared in `pyproject.toml` and pinned in
`uv.lock`. Install `uv` using your environment's package manager if absent.
Setup may download the interpreter and packages; the example below is offline
after setup.

Both PowerShell and POSIX shells:

```text
uv sync --locked
uv run --offline --locked python -m shopping_advisor maintenance check
```

`--locked` checks that the committed lock matches the project; do not regenerate
it as a side effect of ordinary research. No virtualenv activation is needed.

The second command is the repository's one verification gate, and the only
check a change has to pass. It runs the offline suite, the published contract
and schema versions, the category registry and each category's lifecycle
record, the committed study examples replayed through their documented
commands, and the local documentation links, and it compares them against the
tracked `shopping_advisor/maintenance/baseline.json`. It takes about fifteen seconds,
needs no network after setup, and needs no credentials or model provider. A
green run on a clean clone is the evidence that this repository still does what
the rest of this file says it does.

There is no hosted CI and no Git hook behind it: the gate is local and
version-controlled so that it is the same command for everyone, visible in
review, and impossible to skip by accident. Run the suite alone with
`python -m unittest discover -s tests` while iterating; finish with the gate.
[AGENTS.md](AGENTS.md#environment-and-checks) has the rules that go with it,
including when re-recording the baseline is legitimate.

**The default crawl profile is the validated, proxy-free local one** (T1). It
needs no API key and no optional packages, it asks Amazon.de for German, and
the crawl process contacts no host but the marketplace: the public suffix list
that cookie handling consults is the snapshot bundled with the locked
`tldextract`, not a download.
`SCRAPY_PROJECT` no longer has to be set; `SCRAPY_PROJECT=baseline` still
selects the same profile, so existing commands keep working.

PowerShell:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
uv run --offline --locked scrapy list
```

POSIX shell:

```sh
export PYTHONIOENCODING=utf-8
uv run --offline --locked scrapy list
```

The expected spider list is just `amazon_product`. Listing spiders makes no
marketplace requests. The encoding variable applies to subsequent commands in
the same shell; a newly opened shell needs it again.

Start with the [offline research walkthrough](RESEARCH.md#offline-walkthrough).
It uses committed evidence, requires no account, and shows both a usable
comparison and a disputed value that must not decide a purchase.

## Project name and migration

The project is **shopping-advisor**, formerly **amazon-scrapy-scraper**.
The Python package is now `shopping_advisor`; update imports, commands and
any explicit `SCRAPY_SETTINGS_MODULE` values from `amazon_scraper` to
`shopping_advisor`. The old Python namespace is no longer provided.

Use the product entry point from the repository root:

```text
uv run --offline --locked python -m shopping_advisor --help
uv run --offline --locked python -m shopping_advisor study check tests/studies/pasta-bronze-die.toml
uv run --offline --locked python -m shopping_advisor analysis summary tests/cases/pasta_v1.jsonl.gz --category dry_pasta
```

`study`, `analysis`, and `run` dispatch to the existing layer CLIs; direct
`python -m shopping_advisor.study` (and `.analysis` / `.run`) commands also
work. Collection remains `scrapy crawl amazon_product` with the documented
bounds. Scrapy profiles, source-specific names, feed fields, contract versions
and study IDs retain their meanings. Existing evidence does not need rewriting;
commands printed in older reports need the namespace substitution above.
Historical documentation uses current module paths for navigation.

The checkout directory may have any name; an existing directory named
`amazon-scrapy-scraper` does not affect imports or commands. Repository hosting
names and local checkout locations are managed separately from this code.

## Architecture

| Layer | Entry points | Responsibility |
|---|---|---|
| Acquisition | `shopping_advisor/spiders/amazon_product.py` | Search and direct ASIN requests, deduplication, challenge detection, coverage stats |
| Run evidence | `shopping_advisor/run.py` | Manifest, discovery log, retained PDPs and their fetch metadata, bounded failure samples, offline re-extraction |
| Provenance | `shopping_advisor/provenance.py`, `shopping_advisor/redaction.py` | Code/settings identity, artefact digests, atomic manifest writes, page redaction |
| Extraction | `shopping_advisor/extraction/` | Amazon structures and locale profiles; raw and normalized data, per-block diagnostics |
| Validation | `shopping_advisor/validation/` | Quantity, pricing, nutrition, review and variation checks; evidence-bearing values |
| Category analysis | `shopping_advisor/analysis/categories/` | Classification, meaningful claims and comparison axes; category plausibility profiles |
| Analysis CLI | `shopping_advisor/analysis/__main__.py`, `report.py`, `feeds.py` | Feed merging, evidence cards, rankings, comparisons and summaries |
| Study | `shopping_advisor/study/` | The written brief, its stated constraints, every candidate and its fate, the outcome, the report, and replay |
| Maintenance gate | `shopping_advisor/maintenance/` | One local verification entry point over the suite, contracts, categories, examples and documentation, against a tracked baseline |

`items.py`, `pipelines.py`, and `middlewares.py` are inherited scaffolding;
they are not the research data model. The product spider emits dictionaries.
The core contract is `PdpExtractor.extract(...) -> record`, followed by
`validate(record, profile) -> Validated`, then a category's `evaluate(record)`.

### Evidence and trust

Every validated value distinguishes **source** (how it was obtained) from
**status** (which checks it survived), with quotes and field references.
`trusted`, `disputed`, `unverified`, `unknown`, and `not_claimed` have distinct
meanings; see [the contract](CONTRACT.md#status-vocabulary).

A trusted vendor declaration establishes that the page makes the claim; it is
not independent proof of product performance. Absence of a claim is not proof
it is false. The sampled review cards cannot establish a complaint rate.
Disputed numeric values are shown with their contradictions and are not used
as ranking values.

### Category behavior

| Category | Default `rank` axis | Additional evidence |
|---|---|---|
| `dry_pasta` | Price per kilogram, lower first | Ingredients, processing claims, nutrition plausibility |
| `tyre_mounting_paste` | Pack quantity, lower first | Drying, material compatibility, adverse lubricant claims |
| `basmati_rice` | Price per kilogram, lower first | Cultivar, review signals, historical external findings, a seven-component score |
| `school_backpack` | Weight of the bag, lower first | Reflective elements, manufacturer warranty, height-adjustable back, hip or chest strap; volume and stated body-height range shown, not ranked |

Each category also declares its `Lifecycle`: what it has earned, where it was
measured, what it declines and the evidence behind that. `study capabilities`
publishes the four declarations as one index, and the maintenance gate pins
each state so that a promotion is a reviewed diff. Maturity is not trust: a
value's status comes from validation whatever the category's state.

`rank` sorts one axis. **It does not rank by basmati's composite score**, and
no CLI produces a score-ordered shortlist. The score is a category method that
basmati's cards show — in text and, since T2, in JSON — beside the inputs it
had to guess at. Every section a category renders is now published in
`card --json`: a category declares the card keys it adds in `Category.extras`,
and one it does not declare is not published.
`--require` filters on an observed trusted claim, not independent certification.
Use explicit `--category`; the CLI otherwise defaults to `dry_pasta`.

`rank` produces one ordering over one axis in one unit, and refuses rather
than inventing a comparison: an axis the category declares no better direction
for is not ranked at all, and an axis measured in more than one unit needs
`--unit`. Both refusals name what to do instead.

Variants are grouped using Amazon's variation matrices: pack sizes can share
an offer, while non-size dimensions are retained. Missing matrices do not
justify guessed product identity. Listing identity — merging and family
grouping alike — is the normalised marketplace plus the ASIN. An analysis
still covers one marketplace: feeds spanning several stop the command until
`--marketplace` names one.

### Commands

| Command | Output |
|---|---|
| `python -m shopping_advisor.analysis summary FEED --category CATEGORY` | Classification decisions, evidence availability and trust statuses; not classifier accuracy |
| `... rank FEED --category CATEGORY --limit 10` | One-axis ranking, pack variants and exclusions; `--json` emits the whole ranking with every exclusion and its reason code |
| `... card FEED ASIN [ASIN ...] --category CATEGORY` | Text evidence cards; `--json` emits one pretty-printed object per ASIN |
| `... cards FEED --category CATEGORY --json` | JSONL cards for category matches, including every section the category declares |
| `... compare FEED ASIN ASIN --category CATEGORY` | Differences supported by comparable values and reasons for refusal |
| `... validated FEED --category CATEGORY` | JSONL validation using that category's plausibility profile; no category claim evaluation |
| `python -m shopping_advisor.run reextract RUN_DIR --feed ORIGINAL_FEED -o NEW_FEED` | Offline extraction from retained pages; refuses a feed belonging to another crawl or marketplace |
| `python -m shopping_advisor.run inspect RUN_DIR` | What a run did, which code and settings produced it, how it ended, what it retained |
| `python -m shopping_advisor.study check BRIEF` | Whether a brief is usable, and every default it will fall back to |
| `python -m shopping_advisor.study controls --category CATEGORY` | JSON catalogue of the live category's candidate controls, parameters and limits; no feed required |
| `python -m shopping_advisor.study capabilities` | The capability index as JSON: each registered capability's lifecycle state and decision, marketplaces, what it declines with the proving case records, evidence, committed studies and roadmap records; `--category KEY` narrows, `--marketplace HOST` compares hosts |
| `python -m shopping_advisor.study plan-check PLAN` | Validate an intake plan before category support or feeds exist; optional `--brief BRIEF` checks preservation |
| `python -m shopping_advisor.study plan-readback PLAN` | Render the authoritative plan revision; `--record` saves presented bytes with no-response status |
| `python -m shopping_advisor.study plan-bind BRIEF --plan PLAN -o NEW.json` | Check existing brief controls and bind the plan's requirements into a new brief |
| `python -m shopping_advisor.study plan-review-template PLAN -o REVIEW.json` | Write a pending intake review bound to the plan revision and the live controls, and print its five questions |
| `python -m shopping_advisor.study plan-review PLAN REVIEW.json` | Check an intake review against its plan and print what it records; exits 1 on a recorded failure |
| `python -m shopping_advisor.study review-intake BUNDLE REVIEW.json` | Attach a separate intake review to a plan-backed bundle; a recorded failure fails `validate-report` |
| `python -m shopping_advisor.study run BRIEF` | Analyses the feeds the brief names and writes a study bundle; collects nothing |
| `python -m shopping_advisor.study deliver BUNDLE` | Freeze the delivery instant and record whether current advice is permitted, blocked or not in scope |
| `python -m shopping_advisor.study delivery-review-template BUNDLE -o REVIEW.json` | Write a pending delivery review bound to the latest delivery event, with its three questions and the attestation |
| `python -m shopping_advisor.study review-delivery BUNDLE REVIEW.json` | Attach a delivery review to the event it binds; a recorded failure fails `validate-report` |
| `python -m shopping_advisor.study validate-report BUNDLE --require-review` | Validate indexed claims, replay decisions and require a separate completed semantic review, plus a passing intake review on a plan-backed study and a passing delivery review of a permitted current-advice event |
| `python -m shopping_advisor.study verify BUNDLE` | Re-derives the decisions from the bundle's own inputs and reports what moved |
| `python -m shopping_advisor maintenance check` | The gate: runtime, offline suite, contract versions, categories and their lifecycle records, replayed examples and documentation links, against the tracked baseline |
| `python -m shopping_advisor maintenance baseline --update` | Deliberately re-record the floors, from a tree that passes; refuses otherwise |

Run these with `uv run --offline --locked`. The analysis commands accept
multiple JSONL or `.jsonl.gz` feeds. They merge by marketplace and ASIN and
choose the newest `fetched_at`; a tie falls to a declared order (newer schema,
then a later re-extraction of the same bytes, then run id and a record digest),
so the argument order never decides. Feeds from several marketplaces stop the
command until `--marketplace` names one. JSON output puts the provenance
summary on stderr; do not combine stderr with the data stream. `--json`
formats cards and the ranking; `summary` remains text only.

A **study** is the envelope around those commands: a brief that states the
question and its constraints, and a bundle holding every candidate considered
with the reason for its fate, the decisions, and a generated report. The study
id is derived from the brief, the input digests and the published contract
versions, so the same inputs produce the same bundle on any machine; `verify`
re-derives it and reports a tampered input, a missing artefact, an unsupported
version, or a decision that moved. `run` exits non-zero only when the brief or
the bundle cannot be used — an insufficient-evidence outcome is a result, not
a failure. Two worked examples, one of each outcome, are in
[tests/studies](tests/studies/README.md).

For a plan-backed study, `study check` and `study run` require `--plan PLAN`.
The full plan snapshot travels inside its bundle and is checked during replay.
The [intake workflow](RESEARCH.md#retain-an-intake-plan-before-the-executable-brief)
explains capture, read-back, storage and structural preservation. When a
decisive requirement has no executable control, the stage gates withhold the
recommendation and keep the ranking on the available axis under a separate
bounded-finding heading. A brief declares whether it is a historical comparison
or current advice; `study deliver` freezes the delivery instant and blocks
current advice on stale, undated or withheld decisive inputs, and
`validate-report` refuses a current-advice study without a passing record. A
session ledger declares research and engineering limits in the units crawls
report, records what each probe and collection consumed from its run manifest,
refuses a next action that does not fit, and travels inside the bundle so that
`study resume` can verify the retained artifacts and say what the budget still
permits without the originating conversation. A separate intake review binds
the plan revision and the live controls: `run --intake-review` refuses a plan
its review says misreads the request, and an audited plan-backed report needs a
passing one. The final semantic review is v2 and rests on it; the manifest is
v3 and records how every artifact is bound; a permitted current-advice delivery
is audited through its own delivery review with the deliverer's attestation.
INTAKE §16's ten stages have shipped; R13's conversational trials have not been
run.

The `validated` CLI always supplies a category profile (default `dry_pasta`).
For neutral validation, the Python API is `validate(record)` with no profile;
that is also what the saved-page validation snapshots test. There is no
neutral CLI switch today.

## Collecting and retaining evidence

Use the [bounded live workflow](RESEARCH.md#live-collection) after recording the
question and collection limits. Keep the baseline pacing: concurrency 1,
9-second configured delay with jitter and AutoThrottle. Do not infer that an
old successful fast crawl is a current rate recommendation.

| Spider argument | Meaning |
|---|---|
| `keyword` | Semicolon-separated queries; defaults to `spaghetti hartweizen` |
| `asin` | Named ASINs or product URLs; explicit ASINs alone suppress the default query |
| `domain` | Defaults to `www.amazon.de` |
| `max_pages` | Search pages per query, default 2 |
| `max_products_per_query` | Per-query discovery cap; default 0 means unlimited |
| `keep_pages` | Default 1; keep it enabled for replay |
| `keep_search_pages` | Default 0. Retains search responses, which are the only witness to what a query returned — and the largest thing a crawl downloads |

The product feed is written wherever `-O` specifies; there is no automatic CSV
feed. `-O` overwrites that output, so choose a new path for each collection.
Nested product records should be stored as JSONL. Each crawl separately writes:

```text
data/runs/<run_id>/manifest.json      arguments, locale, code, settings, feeds, state
data/runs/<run_id>/discovery.jsonl    every sighting, before deduplication
data/runs/<run_id>/pages.jsonl        per artefact: fetch time, URLs, status, digest
data/runs/<run_id>/pages/<ASIN>.html.gz
data/runs/<run_id>/quarantine/        pages whose redaction failed — not exportable
data/runs/<run_id>/failures/          bounded samples of challenges and parse failures
data/runs/<run_id>/search/            search responses, with keep_search_pages=1
```

Failure samples are capped per reason and truncated, and are retained whether
or not `keep_pages` is set: a crawl that retains nothing still has to be able
to explain what it did not get.

Run IDs are unique and the directory is created exclusively, so two crawls
started in the same second cannot share one. The manifest is written
atomically and carries its own state: a crawl that never closed reads as
`interrupted` rather than as a finished one. It also records the code revision,
lock digest, schema/contract versions and an allowlist of acquisition settings
— never a credential — so a later reader can say which code produced the
evidence.

`pages.jsonl` records when each page was fetched and the SHA-256 of the bytes
actually stored. That digest is over the **redacted** text, not over Amazon's
reply. Because fetch time is recorded rather than read from the filesystem,
copying a run directory no longer makes its pages look freshly fetched.
A study bundle records the digest of every feed it read, so replay detects a
feed that changed underneath it. It does not bind a feed to a run by a digest
taken at close; see the [runbook limitations](RESEARCH.md#current-limitations).

## Maintenance and reference material

Use [AGENTS.md](AGENTS.md#maintenance-workflow) for the change and verification
sequence; `maintenance check` is its verification step. The regression suite
includes 39 saved PDPs (38 `.de`, one `.com`), a search page, and category
cases. Read [corpus instructions](tests/corpus/README.md) before promoting a
capture or regenerating snapshots. A snapshot update is a reviewed behavior
change, not a routine way to fix a failing test.

`shopping_advisor/maintenance/baseline.json` records what the gate is entitled
to find: the required checks, the runtime and lock digest, the published
contract versions, the registered categories, the test-module inventory and
count, each committed example's study ID and decisions, and the indexed
documents. It is tracked so that establishing *less* than before is a visible
diff rather than a quieter test run. Re-record it with `maintenance baseline
--update` when a change legitimately moves a floor, in the same change that
moves it, with the reason; the command refuses to record a tree that does not
pass.

Adding a category normally means a module under `analysis/categories/`, registered
through that package's `__init__.py`, plus tests. Start at `Category`, `Axis`,
`Claim`, and `CategoryProfile`; keep generic trust rules in validation. Use
`Marketplace.word(stem)` for supported locale-aware word boundaries and the
contract's attributed search controls where appropriate. See R7/R8 in the roadmap.

Historical evidence and its limits:

- [BASELINE.md](BASELINE.md): original 2026-09-14 setup and smoke measurement.
- [EXTRACTION.md](EXTRACTION.md): extraction investigation and dated coverage.
- [USABILITY.md](USABILITY.md): basmati research postmortem and later resolutions.
- [data/evidence](data/evidence/README.md): committed crawl evidence for decisions.
- [reports](reports/README.md): output conventions; complete original study
  inputs and finished reports are not all committed.

### Legacy search-spider migration

T0 removed `amazon_search` after a tracked-reference inventory found no code or
test consumer outside the spider itself. It hardcoded an iPad query on `.com`
and emitted a different CSV record shape. Use `amazon_product` with explicit
`keyword`/`asin`, locale and bounds. Its `discovery.jsonl` records search
sightings; its JSONL feed contains product details. This is not a drop-in
replacement for the old CSV shape or a search-only crawl. Historical documents
retain the old name as part of their original measurements.

### Troubleshooting

| Symptom | Action |
|---|---|
| `ModuleNotFoundError: scrapeops_scrapy` | Only the opt-in ScrapeOps profile needs it. Unset `SCRAPY_PROJECT` (or set it to `baseline`) and check `scrapy list`. |
| Locale conflict on startup | Confirm baseline/German headers and `.de`; do not bypass the check. |
| No or few records | Inspect manifest challenge/HTTP/parse counters, query coverage, and caps. HTTP 200 or `finished` is not proof of usable coverage. |
| uv cache is not writable | Set `UV_CACHE_DIR` to a writable directory; `data/.uv-cache` is an ignored local option. Retry locked setup. |
| Offline dependency error | Complete `uv sync --locked` first; offline mode cannot download missing packages or Python. |
| Unicode output error | Set `PYTHONIOENCODING=utf-8` as above; use UTF-8 when saving reports. |

For the cache override, use `$env:UV_CACHE_DIR = 'data/.uv-cache'` in PowerShell
or `export UV_CACHE_DIR=data/.uv-cache` in a POSIX shell. Do not delete a shared
cache or change dependency versions to work around a filesystem error.

The optional ScrapeOps profile is `SCRAPY_PROJECT=scrapeops` and requires
`uv sync --locked --extra scrapeops` plus `SCRAPEOPS_API_KEY` in the
environment; no key is stored in the repository. It is **not validated**:
every measurement here was taken without a proxy, so its pacing, challenge
rate and the prices a proxied IP is shown are unknown. Treat a study collected
through it as a different acquisition path and say so in the report. The run
manifest records which profile answered and whether a proxy middleware was in
the request path.

## License and origin

See [LICENSE](LICENSE). Partially inspired by the Amazon scraper from
`python-scrapy-playbook/amazon-python-scrapy-scraper`, with optional ScrapeOps
integrations retained. Dependency source of truth is `pyproject.toml` plus
`uv.lock`; no separate requirements file is maintained.

T3 external-evidence schema and a complete basmati audit example are documented
in [CONTRACT](CONTRACT.md#8-study-audit-contracts-t3) and
[the audit examples](tests/studies/t3/README.md). Basmati legacy findings are
unverified access-limited citations and receive no laboratory score credit.
