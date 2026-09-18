# Shopping Advisor roadmap

The plan of record for this repository. It supersedes the P0–P6 hypothesis
that preceded it. The revised product vision and dependency order below govern
future work; completed milestones and the superseded hypothesis retain their
measurements as history.

**Status legend:** `DONE` · `IN PROGRESS` · `NEXT` · `PLANNED` · `DEFERRED` ·
`DROPPED`

| | Milestone | Status |
|---|---|---|
| **R0** | Pasta V1 — evidence-backed comparison over existing records | **DONE** |
| **R1** | Crawl provenance and evidence preservation | **DONE** |
| **R2** | Generic validation layer + published extraction contract | **DONE** |
| **R3** | Variation-aware product families | **DONE** (one criterion unmet — see below) |
| **R4** | Amazon.com as a validated marketplace | DEFERRED |
| **R5** | Reviews as an evidence source | **DONE** (cost estimate was wrong — see below) |
| **R6** | A command line for the things every category needs | **DONE** (two of four items were already shipped — see below) |
| **R7** | Attributed search: finding a claim vs crediting it | **DONE** |
| **R8** | Marketplace-aware text matching | **DONE** |
| **R9** | A second pass for missing prices | PLANNED (behind a decision test) |
| **R10** | Scoring as a shared facility | **DEFERRED** — one consumer is not two |
| **R11** | Category synthesis as a default step | PLANNED (first R15 application) |
| **R12** | Discovery that states its own coverage | PLANNED |
| **R13** | The conversation as the entry point | **DONE (2026-09-18)** — INTAKE §16 machinery shipped; three conversational trials recorded, the third graded against a record written before its first message and carried through three independent intake reviews; the defaults the trials suggested decided the same day |
| **R14** | A recommendation in a category nobody validated | PLANNED (R11–R13, R15, R16 gates) |
| **R15** | Controlled task-driven capability adaptation | PLANNED (R13 done 2026-09-18; T4's local maintenance gate and the first control case, `axis_bound`, have shipped) |
| **R16** | Capability lifecycle and architectural review | **IN PROGRESS** (index, lifecycle records and the first review shipped 2026-09-18; the task-experiment entry waits for R15) |
| **R17** | Portability evidence: a second platform and a second provider | **DEFERRED** — gates the portability claim only |

## Product vision — the shopping conversation

**What the product is for, whose side the agent is on and what the product is
not are stated once, in [PURPOSE.md](PURPOSE.md). This section plans how the
product grows — the extension operating model, revised 2026-09-16 — and that
model is planned; the shipped scope remains in [README](README.md#supported-scope).**

Shopping Advisor is a **durable, continuously extensible research harness for
an AI software agent**. Its permanent user interface is an AI coding interface,
such as Codex CLI or Claude CLI. Each purchasing request is a research task
and, when necessary, an opportunity to extend the harness. It succeeds when
previously unseen problems can be accommodated through small, safe, reusable
extensions without destabilizing what already works.

The system is **permanently incomplete by design**. A finite catalogue of
categories is accumulated capability, never the boundary of the product.
New needs may require software adjustments; they should rarely require a
redesign. The harness is both an execution environment and organizational
memory: tested code, contracts, retained evidence, studies and dated decisions.

The user's experience is:

**intent → useful questions → research → evidence → comparison → recommendation**

The agent understands the purchase decision, identifies relevant characteristics
and sufficient evidence, asks only questions that materially improve the answer,
then uses the harness. It detects missing capabilities, makes bounded additions,
validates them, completes the research and retains what proved useful. This
includes new categories, marketplace behavior, sources, extraction techniques,
comparison methods and research procedures. Category synthesis alone is not the
operating model.

The user need not know what modules exist or whether engineering happened.
Explain engineering only when it changes cost, time, confidence, limitations or
the purchasing decision. A conditional comparison, tie or precise
insufficient-evidence answer is a valid outcome. Missing software should normally
trigger bounded adaptation; unavailable decisive evidence must never trigger
invented certainty.

### Two kinds of request, one interface

The same coding interface receives engineering and maintenance requests, and
an engineering dialogue often ends in a roadmap or architectural decision rather
than a change. Neither kind gets an intake artifact of its own inside the
repository. The agentic harness already records the request, authorises each
action and keeps the transcript; git keeps the diff and the review; the
maintenance gate and its tracked baseline are the acceptance check. A parallel
record would duplicate all three and would be the free-form memory store
[R16](#r16--capability-lifecycle-and-architectural-review) prohibits.

What the repository retains is the decision and its measured effect: a dated
entry here for a discussion that changed direction, a commit whose baseline
diff is argued in its message for a change. That is what property 6 below
demands of engineering exactly as it demands it of research — another agent
resumes from the files, never from a private chat. The one place the harness's
affordances do not suffice is engineering the agent spawns *inside a study*,
where scope, authority and effect must bind to the study and survive replay.
That is [R15](#r15--controlled-task-driven-capability-adaptation), not a new
milestone. Decided 2026-09-17; the rejected alternative is recorded under
[deferred and rejected work](#deferred-and-rejected-work).

### Architectural properties that make this possible

1. **Local change.** Source adapters acquire and extract; generic validation
   owns trust; category methods interpret; briefs own user preferences; studies
   preserve decisions. A new extraction technique may change extraction, but
   never insert a buyer's preferences there. Locality means the narrowest
   responsible layer, not a promise that only category files ever change.
2. **Inspectable contracts.** Source identity, units, provenance, applicability
   and unknowns survive each boundary. Briefs remain data, not executable
   imports. Deterministic arithmetic and replay stay in software.
3. **Controlled execution.** Agent-authored code is executable code, including
   imports and tests. Isolate changes, bound resources and access, check the
   diff, test success and counterexamples, review semantic output, then adopt
   reversibly. A provisional label is not an execution safeguard.
4. **Regression protection.** Existing categories, generic snapshots and saved
   studies are gates on a change. Version changed meanings and preserve the
   prior evidence/method so changed decisions can be explained or rolled back.
5. **Earned reuse.** Distinguish a task experiment, a maintained capability and
   a stable shared foundation. Passing one task does not establish generality;
   neither repeated code generation nor more categories proves a shared design.
6. **Portable memory.** Repository instructions, files and CLI contracts are
   canonical. Provider adapters stay thin; another agent can resume using
   artifacts without private chat history. Replay requires no model provider.
7. **Bounded research.** Separate a software gap from an evidence gap, preserve
   partial results and stop when further work cannot justify its cost. Trust
   statuses do not improve because a deadline or a shortlist demands it.

### Roadmap assessment — 2026-09-16

**Verdict: the architecture is a credible starting point; the previous roadmap
was not yet a credible delivery sequence for continuous extension.** R0–R8
and T0–T3 establish reusable research primitives and an evidence trail. R11–R14
recognised unseen categories, but omitted a general adaptation lifecycle,
placed conversation late, and made R14 depend on deferred R10 while calling
R14 its justification. This revision removes that circular dependency.

The assessment uses the complete R0–R14 and transition-stage plans, the
deferred work, E1–E4, the current runbook and contracts, and these
implementation seams:
[category registration](shopping_advisor/analysis/categories/__init__.py),
[category interface](shopping_advisor/analysis/category.py),
[brief](shopping_advisor/study/brief.py),
[bundle](shopping_advisor/study/bundle.py),
[audit](shopping_advisor/study/audit.py), and
[provenance](shopping_advisor/provenance.py).
Historical crawl measurements below are prior project evidence, not newly
verified marketplace facts or buying advice.

| Requirement | What exists / remaining gap | Roadmap decision |
|---|---|---|
| Conversation as entry point | Shared agent instructions and CLI tools exist; no end-to-end conversation acceptance trial | R13 begins now inside the coding interface; no new frontend |
| Purchasing intent and criteria | T2 records assumptions and defaults; category defaults still encode past buyers' preferences | R13 evaluates material questions and explicit criteria before collection |
| Dynamic evidence discovery | T3 audits declared sources; it does not decide what evidence a new question needs | R13 adds a requirement-to-evidence plan; R12 measures collection against it |
| Capability-gap detection | Brief requires an already registered category and feeds; registry lookup is not a gap analysis | R13 records gaps before an executable brief; do not loosen unknown-key/import safeguards |
| Task-driven adaptation | Maintenance process exists; R11 covered categories only | New R15 covers all capability types; R11 is its first category application |
| Safe execution and validation | Locked runtime, local tests and, since T4, one local gate over them; no validated extension isolation workflow | The T4 gate has shipped and is the executable baseline; R15's isolated execution still precedes default execution of new capabilities |
| Architectural locality | Extraction/validation/category boundaries work for existing consumers; records and identities remain Amazon-shaped | Extend the demonstrated seam; a new retailer earns a source-native adapter, not fake ASINs |
| Regression protection | Corpus, category cases and study replay exist, run by one gate with a tracked baseline | T4 automated them and made weakening them explicit; R15 records semantic before/after decisions and rollback |
| Capability reuse | Static registration finds three categories, without lifecycle/applicability metadata | R16 adds a small discoverable capability index tied to code and cases |
| Evidence-based promotion | Runbook requires scope, counterexamples and measured effect | R16 separates retention, maintained local capability and shared abstraction promotion |
| Lessons without uncontrolled growth | Durable homes already defined; promotion/disposal outcomes not tracked | R16 records reuse, rejection, expiry and supersession beside existing homes |
| Architectural review / debt | Deferral principles exist; no review cadence or accountable output | R16 adds a recurring review gate with measured simplification decisions |
| Provider independence | Canonical instructions, ordinary CLIs and a gate needing no model API exist; portability is not demonstrated | Keep the design provider-neutral; the two-provider study, repair and handoff trials are **[deferred to R17](#r17--portability-evidence)** and gate only the portability claim, not R15 |
| Traceability of research and changes | T1–T3 bind evidence and reports; code revision/dirty flag do not preserve an exact uncommitted patch | R15 binds base, patch, method, checks and resulting study revision |
| Insufficient evidence | T2 refusal and T3 audits exist; extension-budget failure is not integrated | R12/R15/R14 distinguish missing evidence, failed adaptation and a valid qualified result |

The existing seams also have limits. `Category.extras` can expose evidence, but
the study currently shortlists on one axis and T3 external claims do not alter
eligibility. A new comparison method must enter deterministic study decisions,
serialization, rendering and replay together; adding a score to a card or prose
to a report is insufficient. R15 should make the smallest tested extension to
that path when an actual brief demands it. The Amazon-shaped record model is
another boundary to test, not a reason to design a universal schema now.

### Priorities and true dependencies

Identifiers retain their historical meaning; their numeric order is not the
execution order. T0–T4 and completed R milestones remain delivered, not work to
repeat. Demand-driven expansion is a standing rule rather than a final
catalogue phase — see [decision principle 9](#decision-principles).

| Order | Deliverable | Dependency and reason |
|---|---|---|
| 1 — done (2026-09-18) | R13 intake/evidence/gap planning | INTAKE §16's ten stages shipped on 2026-09-17 on top of T2/T3 and T4's gate; three conversational trials are recorded (2026-09-17 by the documentation's author, 2026-09-18 by a reader who had not read it, 2026-09-18 on an unsupported category graded against a record written before its first message and carried through three independent intake reviews); the defaults the trials suggested were decided on 2026-09-18 |
| 2 | R15 bounded adaptation, with R11 as the first category case | Needs R13's recorded gap. T4's executable baseline is in place. Prove isolation, validation, traceability and rollback before making adaptation routine |
| 3 | R12 coverage and R16 minimum lifecycle/index | The index and the lifecycle records shipped on 2026-09-18 over the four registered categories, ahead of R15, because nothing in them depends on a patch artifact; what waits for R15 is the task-experiment entry and the promotion evidence that flows from it. R12 evidence planning can start with R13. Coverage and deliberate retention are necessary before claiming the full loop works |
| 4 | R14 unseen-problem and reuse acceptance trials | Needs R11–R13, R15 and R16's minimum lifecycle, on top of the shipped maintenance gate. [R17](#r17--portability-evidence)'s trials — cross-platform paths, provider interchangeability and handoff — test these same artifacts afterwards, and gate only the portability claim |
| Ongoing | R16 architectural reviews; study-driven expansion | Use measurements from completed studies to simplify or extend; there is no final supported-category count |

R12 design can proceed earlier and need not wait for synthesis.
[R17](#r17--portability-evidence)'s provider and cross-platform trials are a
release gate for the portability claim only: they do not block R15, and they
are not a reason to postpone the first local extension experiment. Nothing in this sequence needs
remote CI; the local gate is the authority, and no current constraint argues
for a second one.
R10 is **not** a prerequisite for any of the above: a local comparison method
can be sufficient, and a generator is not a demonstrated second consumer.

**Useful but secondary:** R4 marketplace expansion and R9 price refresh remain
conditional on a real task and measured value. R10 shared scoring stays deferred.
R3's retired variation-conflict criterion remains retired: missing source data
cannot be fixed by adding software. E1 remains a scoped quantity audit; E2 is
resolved; E3 supplies R12's discovery cases; E4 was answered in R0. Fresh studies
must not treat those old samples as current market coverage.

**Conflicting assumptions to retire:** a runbook-following agent is not an
inferior precursor to a separate conversational product; it is the interface
we intend to keep. An unseen category does not imply a numeric score. Historical
pasta findings do not rule out OCR or browser extraction for a future task.
Adding enough categories cannot complete the product. Conversely, extensibility
does not justify speculative ontologies, plugin loaders or shared scoring.

### Minimum viable operating model and success measures

The minimum is one complete, repeatable extension loop, not an autonomous
platform. It needs conversational intake, an evidence/gap plan, a bounded and
isolated patch, regression and semantic review, a replayable result and an
explicit retention decision. Files, existing CLIs and a small capability index
are sufficient; a database, scheduler and agent orchestration are not required.

R14 must demonstrate the thought experiment: an unanticipated category needs
both a new extraction technique and a different comparison method. The agent
adds them in the responsible layers, validates them, completes the study and
leaves the next agent reusable evidence and code. A later distinct request
must discover and reuse or narrowly adapt that work. A missing-evidence variant
must correctly refuse, and a failed-patch variant must restore the baseline.

Record, per trial: material versus unused questions; research/engineering time
and resource budget; files/layers and shared contracts changed; applicable
claims and unresolved gaps; old-study decision diffs; regression failures;
manual interventions; rollback outcome; and capability reuse versus duplication.
Initial acceptance requires **zero unexplained old-study decision changes**,
all required checks passing, a replayable outcome, and an explicit promotion
or disposal decision. Report locality and cost rather than inventing a universal
line-count target; establish cost targets from these trials. Do not count a
qualified refusal as a recommendation success, or a correct refusal as failure.

These are planned acceptance measures, not measured improvements. Current
unsupported-category instructions remain in force until R11 and R15 gates ship;
this product review changes direction and sequencing, not runtime authority.

Review effect: assessed all 15 operating-model requirements, added R15/R16,
re-scoped R11–R14 and removed R10 from the acceptance dependency chain. Five
current documents were aligned; 91 local file/anchor links and the whitespace
diff check passed. Code, contracts, dependencies and snapshots are unchanged.
No runtime tests or live research were run for this documentation-only review;
new operating-model outcomes remain unmeasured until the planned trials.

## Agent-operation transition

**Delivered, and its plan retired (2026-09-16).** This section is the history
of how the repository became agent-operable, not a plan anything still follows.
T0–T4 shipped; the dated records below carry their measurements and their
stated limits, and they are why "since T1" or "since T2" is readable elsewhere
in these documents. The separate transition plan is retired to version control
— the [closing record](#documentation-review--2026-09-16-one-plan-of-record)
says what moved and what was dropped. Current operating rules are in
[AGENTS.md](AGENTS.md), with the research workflow in
[RESEARCH.md](RESEARCH.md) and a thin `CLAUDE.md` entry point.

| Stage | What it delivered | Where it lives now |
|---|---|---|
| **T0** | Canonical instructions, the thin provider adapter, the runbook and a no-network walkthrough; `amazon_search` removed | [AGENTS.md](AGENTS.md), [RESEARCH.md](RESEARCH.md), [README.md](README.md) |
| **T1** | Run identity, manifest state and provenance, per-page digests, failure capture, redaction, marketplace-scoped identity | `run.py`, `provenance.py`, `redaction.py` |
| **T2** | The validated brief, structured ranking and exclusions, complete category JSON, the replayable study bundle, refusal as a result | `study/`, [CONTRACT.md](CONTRACT.md) |
| **T3** | External-evidence ledger, applicability and claim checks, full report replay, separate semantic review | `study/audit.py`, [CONTRACT.md](CONTRACT.md#8-study-audit-contracts-t3) |
| **T4** | One local maintenance gate over all of it, with a tracked baseline that has to be argued with | `maintenance/`, [AGENTS.md](AGENTS.md#environment-and-checks) |

### Product identity — 2026-09-16

The crawler-era name `amazon-scrapy-scraper` described acquisition but omitted
the brief, validation, category reasoning, comparison and saved-study layers
already delivered. The project is now **shopping-advisor**, with the Python
namespace `shopping_advisor` and a product entry point:
`python -m shopping_advisor study|analysis|run ...`. Each command delegates
to its existing layer; Amazon-specific source names remain explicit.
See [migration instructions](README.md#project-name-and-migration).

Measured effect: 41 existing modules moved to the product namespace; their
logic is unchanged. The offline suite passes **433 tests** (428 existing,
five product CLI integration tests), including the unchanged extraction and
validation snapshots. The bronze-die example still produces study ID
`pasta-bronze-die-501d864a1a0c`, five eligible offers and three shortlisted
offers, and its saved bundle verifies through the product CLI. Only the root
project name changed in the lockfile; dependency versions remain pinned.
Schema, validation and study contract versions are unchanged because their
data and decision semantics did not move. R11–R14 remain planned.


**T0 — DONE (2026-09-16): make the current system navigable.**

- Added canonical instructions, the provider adapter, and a no-network research
  walkthrough using the committed pasta cases, including a refusal example.
- Replaced the stale README with current setup, architecture, supported scope,
  commands and limitations. Corrected schema versions, `validated` profile
  semantics, basmati rank/JSON claims, and original-report reproducibility claims.
  Historical investigations now identify their age and current successors.
- Removed `amazon_search` after the tracked-reference inventory found no import,
  code consumer or test dependency outside the spider. The README explains the
  migration to `amazon_product` and the different output/acquisition scope.
- Verification: locked environment check succeeded with a writable local uv
  cache; **323 tests passed**. All seven documented offline analysis commands
  succeeded with the stated counts, evidence and refusals. Spider discovery
  returned only `amazon_product`. PowerShell configuration and Git Bash POSIX
  configuration/refusal commands passed; local documentation links and whitespace
  checks passed. No extractor or trust-rule behavior changed.
- Verification limits: used the existing Windows environment, not a fresh
  Linux installation; no live crawl or model-provider acceptance trial was run.
  Provider interchangeability trials were deferred, and now live in
  [R17](#r17--portability-evidence). T1–T4 were not yet implemented.

**T1 — DONE (2026-09-16): make acquisition and replay safe to build upon.**

- **Run identity.** The ID was a digest of second-resolution time, marketplace
  and arguments — the three things two concurrent crawls of one shelf agree on
  — and `open()` accepted an existing directory. It now carries random bytes
  and the directory is created exclusively; a collision raises
  `RunDirectoryExists` and writes nothing.
- **Manifest.** Written through a temporary file and renamed, and carrying its
  own `state`, so a crawl killed mid-flight reads as `interrupted` rather than
  as one that was never asked to close. It records the code revision and dirty
  flag, the lock digest, schema/contract versions, an **allowlist** of
  acquisition settings — never a credential — and the feeds the crawl was told
  to write. New `run inspect` reads all of it back.
- **Per-observation metadata.** `pages.jsonl` records each retained artefact's
  fetch time, request/final URL, HTTP status and the SHA-256 of the bytes
  actually stored, documented as a digest of the *redacted* text rather than of
  Amazon's reply. Replay reads fetch time from there, so copying a bundle no
  longer makes its pages look freshly fetched; a store written before T1 has no
  index and its records carry `fetched_at: null` with
  `fetched_at_source: "unknown"` instead of a filesystem timestamp.
- **Feed and page bindings.** Replay refuses a feed belonging to another crawl
  or marketplace, reports `mixed`/`legacy` lineage rather than inventing
  provenance, and fails the individual page whose stored bytes no longer match
  the recorded digest. Replayed records carry `extracted_at`, which is how a
  merge distinguishes a new reading of old bytes from a new observation.
- **Failure capture.** Challenge pages, titleless PDPs and — on request —
  search responses are retained, redacted, truncated to 256 KB and capped at
  five samples per reason, with the over-cap count recorded.
- **Redaction.** Moved from `tests/corpus/redact.py` into
  `shopping_advisor/redaction.py`; the corpus CLI imports it. The silent
  `except Exception: return html` fallback is gone: a failure is counted and
  the page is quarantined out of the export/promotion path.
- **Marketplace-scoped identity.** Listing identity is the normalised host plus
  the ASIN, in feed merging and in variation family/offer grouping. A two-row
  probe that previously discarded the `.de` observation in favour of a newer
  `.com` one now keeps both. Merge ties fall through a declared order
  (schema, then `extracted_at`, then run id and record digest), so argument
  order never decides. This moved `offer` in the published validated record,
  so **contract v2** with a CONTRACT §7 entry; the corpus diff touched exactly
  `contract_version` on 39 records and `offer[0]` on the 27 with a family.
- **No unrequested comparison.** `rank` refuses an axis the category declares
  no better direction for, and refuses one ordering across two units — on the
  committed mounting-paste cases that was 12 gram packs and 3 millilitre ones
  sorted together — asking for `--unit`. The analysis CLI stops on feeds
  spanning several marketplaces until `--marketplace` names one, and reports
  how many records were set aside.
- **Profiles.** The proxy-free local profile is the Scrapy default;
  `SCRAPY_PROJECT=baseline` still resolves to it for existing commands, and the
  ScrapeOps integration is `SCRAPY_PROJECT=scrapeops` with the key read from
  the environment and no literal in the repository. Verified that none of the
  three ScrapeOps components can be imported on a checkout without the extra,
  which is where the old default failed — at crawl time, not at `scrapy list`.
- Verification: **381 tests passed** (323 before), locked environment, no
  network. All seven documented offline walkthrough commands reproduce their
  stated counts, exclusions and refusals. A scratch run store exercised
  manifest, page index, failure capture, `inspect` and `reextract` end to end.
  `scrapy list` returns `amazon_product` with no `SCRAPY_PROJECT` set and with
  `baseline`.
- Verification limits: still no live crawl, so challenge retention, search-page
  retention and page-write failures were exercised with constructed responses
  rather than against Amazon. Feeds are bound by the run id on their records
  and by the declared feed path, not by a digest taken at close — the feed
  exporter and the run both close on `spider_closed` and nothing orders them.
  Cross-marketplace comparison stays unsupported by decision, not by
  limitation. T2–T4 were not yet implemented.

**T2 — DONE (2026-09-16): persist and replay a complete offline study.**

- **The brief.** A study now starts from a TOML or JSON brief with a validated
  schema (`shopping_advisor/study/brief.py`, `brief_version = 1`): question,
  category, marketplace, feeds, constraints, freshness policy, assumptions,
  questions, declared sources and limits. Unknown keys are **refused**, not
  ignored — a misspelt constraint that silently does nothing was the failure
  mode this exists to prevent. The brief is data: it names a category by its
  registry key and never by an import path, and a brief naming
  `shopping_advisor.analysis.categories.dry_pasta` gets the same refusal as a
  typo. Feed paths resolve against the brief's own directory, so a brief and
  its feeds travel together and no absolute path enters a committed file.
- **Constraints kept apart from category defaults.** The failure this repays
  is recorded in this file: tyre mounting paste ranks the smallest pack first
  because one reader was fitting one scooter tyre, and that is now
  indistinguishable from a fact about the product class. `report.ranking()`
  reports `axis.stated` and `axis.unit_stated`, and the study report's *What
  decided it* table says of every decision whether the brief chose it or the
  category supplied it.
- **Structured ranking and exclusions.** `rank_text` was the only place a
  ranking existed; it prints twenty rows and **ten** exclusions, and a
  requirement filter removed records with no mention at all. `ranking()` now
  returns the rows, the complete exclusions with a stable `reason_code` each,
  and the requirement-filtered records separately. Measured on the committed
  pasta cases with `--require bronze_die`: 5 rows, 3 exclusions, and **14
  records the text view never named**. `rank --json` exposes it; `rank_text`
  renders it and its output is byte-identical to before.
- **Complete category JSON.** `card_json` named `drying` and `suitability` by
  hand, so basmati's JSON card omitted the whole of what that category knows.
  A category now declares its card keys in `Category.extras`; basmati
  publishes **6** more sections — grain type, cultivar, declaration conflict,
  review signals, external test, and the seven-part score — taking its JSON
  card from 5,483 to 9,974 bytes on the module's own test record. A key a
  category adds and does not declare is not published.
- **The bundle.** `data/studies/<study_id>/` holds `manifest.json`,
  `brief.json`, `candidates.jsonl` (one line per considered record, with the
  reason for its fate), `cards.jsonl` (the complete card of every classified
  candidate), `ranking.json` and a generated `report.md`. On the worked
  example that is 25 candidates and 22 cards, against a text ranking that
  showed 14 rows and truncated its exclusions.
- **A derived identity.** Unlike a crawl id, which must carry random bytes
  because two identical crawls are two observations, a study is a pure
  function of a brief and some pinned bytes. The id is a digest of the brief,
  the input digests and the published schema/contract versions:
  `pasta-bronze-die-501d864a1a0c` is what any checkout produces. It
  deliberately does **not** cover the analysis code, and `verify` is what
  catches a decision that moved because a rule changed.
- **Determinism.** Every artefact except the manifest is byte-identical
  between two runs, and between two directories: the report carries no
  timestamp and no hostname, and the persisted brief carries the file's name
  rather than the path it was invoked by. The manifest declares its own
  variation in a `volatile` list (`started_at`, `finished_at`, `code`,
  `directory`, `brief_source`), and a test asserts that nothing else moves.
- **Refusal as a result.** `minimum_candidates` and `decisive_margin` are
  declared in the brief before the data is seen, so `insufficient_evidence`
  and `no_decisive_winner` are criteria that were met rather than judgements
  improvised at the end. A refusing study puts nobody forward and still
  accounts for all 25 records. Two refusals are instead *errors* that write
  nothing: a brief naming a unit nothing is measured in while other units
  are, and a brief leaving the unit open where several are measured. Filing
  an operator's slip as insufficient evidence would record it as a fact about
  the shelf.
- **`verify`.** Re-derives the decisions from the bundle's own brief and
  inputs and reports, in order: an unsupported manifest or brief version, a
  missing or altered artefact, an input whose digest moved, a code revision
  that changed, and finally the decision or numeric claim that no longer
  reproduces — named, not counted. `--input-root` is authoritative when given.
- **Two worked examples**, both offline over `tests/cases/pasta_v1.jsonl.gz`.
  `pasta-bronze-die` recommends `B0DQ2N5HRW` at 2.96 EUR/kg, 9.1% ahead of the
  runner-up. `pasta-low-temperature-drying` refuses: two listings state the
  requirement and **both** have a disputed price per kilogram, because Amazon
  quotes a unit price per piece and the pack size contradicts it.
- Verification: **428 tests passed** (381 before), locked environment, no
  network. Both bundles reproduce byte-identically across two directories.
  Every failure path was exercised — tampered input, missing artefact,
  unsupported manifest and brief versions, seven kinds of invalid brief, an
  absent unit — and each names what to change. The seven documented offline
  walkthrough commands still reproduce their stated counts, and `rank`'s text
  output is unchanged.
- Verification limits: no live crawl and no second provider stack. The study
  id does not cover the analysis code, by design. Nothing checks that the
  report's *prose* claims are supported by evidence, and a brief's declared
  `[[sources]]` are reproduced with a heading saying they were not verified —
  both are T3. `report.md` is generated, so a hand-written section on top of
  it is unchecked. T3 and T4 were not yet implemented.

**Runbook — requirement elicitation and the improvement loop (2026-09-16).**
Audit of the documents against the actual end-to-end flow found two gaps that
T0 and T1 had left: elicitation was one policy sentence in each of `AGENTS.md`
and `RESEARCH.md` with no procedure under it, and the improvement cycle existed
only in the transition plan, which is a reviewed proposal rather than operating
instruction.

- `RESEARCH.md` now has **Agree the brief**: inspect before asking; a
  blocking / assumable / not-worth-asking test for missing information; one
  batched round with stated defaults so silence is still usable; the
  unsupported-category conversation as an explicit choice; read-back before
  collection; and what to do when a requirement changes mid-study.
- `RESEARCH.md` now has **the improvement cycle** — observation → reproducible
  case → proposed change → review → versioned adoption → measured effect —
  with the promotion table and a closing step that revises the *questions*
  against what actually decided the answer. `AGENTS.md` requires a measured
  effect in the maintenance report.
- Measured while writing it: running the 34 committed mounting-paste records
  under dry pasta's plausibility profile moves **14 values**, mostly `trusted`
  to `disputed` (a 252 EUR/kg paste is outside pasta's 0.80–40 band). That is
  the quiet half of the `--category` default; the classifier makes the loud
  half obvious. An earlier draft of this warning overstated the loud half and
  was corrected against the measurement.
- Documentation change only: no code, no snapshots, 381 tests unchanged and
  green. Links, anchors and the CLI defaults were verified.
- **Superseded in part (2026-09-17, R13 stage 2.)** The blocking test is now
  "could invalidate the decision *and* existing context offers no defensible
  default"; the answered-but-unused pruning rule and the hindsight promotion
  beside it were replaced by an expectation recorded when the question is asked;
  and the unsupported-category conversation is no longer an implementation
  choice put to the user. See
  [INTAKE.md §13](INTAKE.md#13-replacement-operating-text).

**T4 — DONE (2026-09-16): one local maintenance gate, at reduced scope.**

The stage was cut down before it was built. The reviewed plan bundled a hosted
CI workflow, Windows and Linux command paths, a research-evaluation set and
two-provider interchangeability trials into one stage. Only the first
question — *can a clean checkout establish, in one command, that this
repository still does what it says?* — blocks R15. The rest is
[deferred to R17](#r17--portability-evidence) and gates the portability claim
alone.

- **One entry point.** `python -m shopping_advisor maintenance check` runs the
  locked-runtime check, the offline suite, the published contract and schema
  versions, the category registry, the four committed study examples replayed
  through their own documented commands, and the local documentation links.
  Developers and coding agents run the same command; `--json` is the same run
  for a reader that parses. `AGENTS.md` now names it as the check step.
- **Local, not remote, and not a hook.** No hosted runner was added: no current
  constraint needs one, and a second definition of the gate can drift from
  this one. A Git hook was rejected as the authority for a plainer reason —
  it is per-clone state, invisible in review and skippable with `--no-verify`.
- **The gate is reusable, not a second copy.** It calls the existing suite, the
  existing contract constants, the existing category registry and the existing
  study CLI. What is new is the inventory that says they are all still there.
- **A baseline that has to be argued with.** `shopping_advisor/maintenance/`
  `baseline.json` is tracked and records what the gate is entitled to find:
  the required check list, the runtime and lock digest, the six published
  contract versions, the three categories, the test-module inventory and
  count, each example's study ID and decisions, and the indexed documents.
  A task-local change that deletes a test module, drops below the count,
  changes a contract version, loses a category or moves an example's decision
  fails with the baseline field that would have to change. `baseline --update`
  is the only way to lower a floor, it writes one reviewable file, and it
  refuses while the gate is failing — a red tree cannot become the new normal.
- Measured effect: the gate passes in **15 seconds** on the development
  machine. **491 offline tests** in 17 modules (460 existing, 31 added for the
  gate itself), no snapshot updates and no contract-version changes. The four
  examples reproduce their recorded identities — `pasta-bronze-die-46127870314d`,
  `pasta-low-temperature-drying-d309972b3bd0`, `basmati-audit-positive-571cca1a2d4b`
  and `basmati-audit-insufficient-18b88dc2bd3c`, the manifest v2 ids that R13
  stage 10 later moved once; the current ones are in the baseline — with their
  outcomes, offer counts, exclusions and shortlists, and the two T3 examples pass
  `validate-report --require-review`. The link check resolves **128 local
  links and 247 anchors across all 16 tracked documents** and found none
  broken; the 2026-09-16 documentation review counted 91 local file and anchor
  links by hand, over the documents it touched. The automated count covers all
  of them and is now the one that gets repeated.
- The 31 new tests exercise the gate the way a weakening change would: a
  deleted test module with the rest green, a count below the floor, a silent
  contract bump, an untracked published version, a lost category, a moved
  example decision, a dead link and a dead anchor, a check dropped from the
  baseline, a check required but not implemented, an empty check list, a
  missing or incompatible baseline file, and `--update` refusing a failing
  tree. They never run the `tests` check against this repository's own suite,
  which the gate already runs and which contains them.
- Limits: this is one machine, one shell and one interpreter. Nothing here
  establishes that the gate behaves the same on Windows or Linux, and nothing
  establishes provider interchangeability — both are deferred and neither is
  claimed. The gate checks that the repository still does what it says; it
  cannot check that what it says is true of any marketplace. `uv sync --locked`
  is still a separate bootstrap step and is the only one that uses the network.

### Documentation review — 2026-09-16: one plan of record

The transition plan was retired to version control, and the repository now
presents a single current product model: the [product vision](#product-vision--the-shopping-conversation),
the [priorities](#priorities-and-true-dependencies), the delivered history
above, the [decision principles](#decision-principles), and the deferred work
with the evidence each item still owes. Nothing an agent must read in order to
operate or extend this repository describes a migration any more.

- **Retired:** 739 lines of second plan. Its current-state assessment described
  one snapshot (`95b8bbd`) that T0–T4 has since answered, and the residue it
  could not close — untracked original basmati inputs and reports — is already
  carried in [RESEARCH's limitations](RESEARCH.md#current-limitations). Its
  target operating model and improvement cycle had moved into `AGENTS.md` and
  `RESEARCH.md`; its architecture sections are built and published in
  `CONTRACT.md`; its sequencing this file had already superseded in writing.
  Keeping it meant every future agent had to read a migration framework to find
  out what the system is.
- **Preserved, in homes that outlive the migration:** the deferred portability
  trials and the rule against claiming portability nothing has measured, now
  [R17](#r17--portability-evidence) with its own scope, acceptance conditions
  and out-of-scope decisions; and expand-on-demand, now
  [decision principle 9](#decision-principles) rather than a stage that could
  never complete. The retired stage's per-capability guidance was already
  stated by R4, R9, R10, R16 and the deferred-work table, and was not copied a
  second time.
- **Dropped deliberately:** the snapshot assessment, the gap-and-risk table,
  the target operating model, the architecture proposals, the first
  implementation priorities and the definition of done — the last of these
  because every clause it tested is either delivered above or is now R17's.
  Version control holds them; documentation does not owe them a second copy.
- **Measured effect:** the gate passes. The tracked documentation index went
  from 16 documents, 128 local links and 247 anchors to **15 documents, 123
  links and 221 anchors**, with no broken link or anchor and no reference left
  pointing at the retired file. **491 offline tests**, unchanged and green. No
  code, contract version, snapshot or example decision moved. The only baseline
  change is the document removed from its index, which is the reviewable claim
  that this repository no longer publishes it.

### Documentation review — 2026-09-18: the purpose gets an owner

Onboarding a business analyst exposed a gap the 2026-09-16 review had left
open. An agent no longer had to read a migration framework to learn what the
system is, but what the system is *for* still had no owner. It was split
across README's first paragraph, the vision section above — a paragraph dated
as a direction revision, inside a section about a planned model — one link in
AGENTS whose first screen was the Scrapy acquisition path, and the
brief-agreement section of the runbook. The ownership list in AGENTS named
CONTRACT, RESEARCH and ROADMAP, and nobody for purpose. Read from those
fragments, three readers got three products: a stakeholder a harness, an
operator an acquisition path, a maintainer an extension model. The buyer — the
shelf too wide to read by hand, the requirement forgotten until the first dark
morning, the test result that is not on the page — appeared in none of the
openings, and the agent's role was named only in passing, as a researcher.

- **Added:** [PURPOSE.md](PURPOSE.md), owning the buyer's problem; the agent's
  role as an independent researcher on the buyer's side, with its five limits;
  what a finished outcome owes the buyer, as an index into the contracts that
  enforce each item; what the product is not; and a glossary that points at
  owners rather than redefining terms. It carries no numbers that go stale. It
  is indexed in the gate's baseline, which is the reviewable claim that the
  repository publishes it.
- **Moved:** *What the product is not*, from this section to PURPOSE, with a
  fifth boundary — the agent is not a product expert who knows the range. This
  section keeps the extension operating model, the assessment and the
  priorities, and its opening note now says so.
- **Reordered:** AGENTS opens with whom the agent works for and five
  tie-breakers for rules that pull apart, before the acquisition path; its
  ownership list names PURPOSE; its maintenance workflow links the decision
  principles it had paraphrased without naming.
- **Runbook:** *Agree the brief* now says what the questioning step is for from
  the buyer's side, and where candidate requirements come from — the buyer, the
  agent's reading, a cited source such as a professional test's criteria list,
  and the category's defaults — each recorded where it belongs, with the
  school-backpack visibility requirement as the worked case and the
  default-step version left as R11's unadopted proposal.
- **README:** opens with the buyer before the harness; *Start here* gains a row
  per reader and a row for a finished outcome; *Supported scope* is named the
  canonical written list, with the registry the gate checks as the truth behind
  it; the category table gains its fourth row.
- **Measured effect:** the gate passes. The tracked documentation index went
  from 17 documents, 215 local links and 276 anchors to **18 documents, 281
  local links and 284 anchors**, with no broken link or anchor. 774
  offline tests, unchanged and green. No code, contract version, snapshot or
  example decision moved. The only baseline change is the document added to
  its index.

---

## Decision principles

These are the tie-breakers. When a proposal conflicts with one of them, the
principle wins unless new measurement overrides it.

1. **Product value over scraper sophistication.** Extraction complexity is
   only worth what it changes in a research answer.
2. **Evidence over speculation.** Measured crawl behaviour, real records and
   the corpus test beat assumptions about Amazon.
3. **Correctness over coverage.** A missing value is better than a
   confidently wrong one. `unknown` is a legitimate output.
4. **Preserve evidence.** Never discard source material because the parser
   does not yet understand it.
5. **Avoid unnecessary re-crawling.** Prefer offline interpretation of
   records we already hold.
6. **Keep category logic downstream.** The acquisition layer must never learn
   what "good pasta" means.
7. **Avoid premature marketplace abstraction.** Generalise where commonality
   is observed; adapt where structural difference is measured.
8. **Traceability matters.** Every value and every recommendation must be
   traceable to the source text it came from.
9. **Capability grows on demand.** A named research need earns a capability; an
   anticipated one does not. Categories, sources, extraction techniques and
   comparison methods accumulate as evidence of demand, never as a coverage
   target, and no count of them completes the product. A first bounded
   experiment needs no second consumer to justify it, and neither does a
   reproducible correctness fix; promotion into maintained or shared capability
   does — see [R16](#r16--capability-lifecycle-and-architectural-review). What
   this roadmap defers, it defers against a measured workload, so
   [a named task may reopen it](#deferred-and-rejected-work).

---

## R0 — Pasta V1: evidence-backed comparison over existing records

**Status: DONE** · no crawl required · runs offline over existing JSONL

Shipped as `shopping_advisor/analysis/`, with `tests/test_analysis.py` and the
evidence it was built from in `tests/cases/`.

### Outcome

A user can ask "which of these is better dry pasta, and why?" and get an
answer traceable to the exact source sentence.

### Why this is first

The repository contains no consumer of the extraction output. A contract
cannot be stabilised (R2) and provenance cannot be prioritised (R1) without
one — and measurement shows the current trust semantics are wrong in a way
only a consumer exposes:

- `nutrition.confidence: "high"` records fail plausibility checks **more**
  often than `"medium"` ones — 5/45 vs 2/40 on the 195-record validation set.
  Confidence currently describes the extraction *method*, not the value.
- Price per kg, the axis the whole use case rests on, is silently wrong on at
  least 8 of 163 dry-pasta records. `B08JLSVW3J` (16 × 500 g Garofalo
  Gragnano) reports **€62.56/kg** instead of ≈€3.91/kg; `B0173KFFIG` (12 ×
  500 g Gragnano box) reports **€0.32/kg** instead of ≈€6.47/kg. Both would
  be ejected from any ranking.

### Scope

- Dry-pasta classification from breadcrumbs and the ingredient declaration.
  (The 195-record search output also contains a toilet brush, a cookbook,
  ready meals, chilled pasta and spice blends. Classification is not
  optional.)
- Comparison axes, each carrying the verbatim source quote and its field of
  origin: **price per kg**, **raw material**, **production-method claims**
  (bronze die, slow drying, low-temperature drying), **origin claims** (Italy,
  Gragnano IGP/DOP, Italian wheat), **protein per 100 g**.
- Validation of exactly those axes: package-quantity conflict detection,
  price-per-kg plausibility, nutrition mass balance and Atwater coherence,
  unit-versus-field agreement, and rejection of a matched number that is
  itself part of the basis phrase.
- An explicit `unknown` state, distinct from "absent" and from "conflicting".

### Explicitly out of scope

A general validation framework; a numeric quality score; variation/family
grouping; any change to the spider; any new marketplace; nutrition coverage
work; touching `amazon_search.py`.

### Done when

- [x] Every product is classified or explicitly unclassified.
- [x] Every surfaced price per kg either passes conflict detection or is
      shown as disputed with the conflicting evidence attached.
- [x] The nine known-bad quantity records are each corrected or flagged, and
      none is silently ranked: `B08JLSVW3J`, `B08HQSZR3D`, `B0173KFFIG`,
      `B0BG28G6SZ`, `B0C3WCFKHT`, `B0C5XK2QFR`, `B0BTPZ7TXJ`, `B0CH3MHVF8`,
      `B0GQ5BKHPT`.
- [x] The seven implausible nutrition records are suppressed or marked, never
      presented as fact: `B0C3WCFKHT`, `B089HJPK5T`, `B0FWXQ6NWM`,
      `B0FWXCDCYV`, `B07NZ1K8L3`, `B086K1MFSL`, `B0BP2QDLPQ`.
- [x] A regression test pins each of those cases to the rule that catches it.

> `B0CH3MHVF8` is listed because a crude detector flagged it; the reconciler
> shows it as **corroborated**, not disputed — its 2 500 g total is correct
> ("(1 x 500 g) (Packung mit 5)"). It is in the list as a false-positive
> guard.

### Measured on completion

Over the 195-record Amazon.de validation set:

| | |
|---|---|
| Classified | 161 dry pasta · 34 other · **0 unclassified** |
| Price per kg | 137 trusted · 12 disputed · 5 unverified · 7 unknown |
| Pack quantity | 88 trusted · 12 disputed · 54 unverified · 7 unknown |
| Raw material | 88 trusted (ingredient declaration) · 50 unverified (marketing text) · 23 unknown |
| Protein per 100 g | 52 trusted · 8 disputed · 1 unverified · 6 unknown · 94 not published |
| **Comparable** | **143 of 161** have at least one trusted comparison axis |

Claims found, of 161: made in Italy 62 · bronze die 56 · Gragnano IGP 46 ·
Italian wheat 42 · low-temperature drying 28 · slow drying 22.

Two findings worth carrying forward:

- **Building the consumer changed the rules.** An earlier reconciler disputed
  19 prices; six of those were its own false positives. Multiplying a title's
  pack count by the attribute table's item weight is circular — whether that
  weight is per item or per pack is the question under dispute — and
  `"Packung mit 500g"` read as a fifty-pack because a regex backtracked
  `500` down to `50`. Both are now guarded by named tests. This is the
  argument against promoting these rules to a generic layer (R2) before a
  second category has exercised them.
- **E4 is answered: 143 of 161, far above the 60 threshold.** V1 does not need
  to reframe as an evidence-gap report.

---

## R1 — Crawl provenance and evidence preservation

**Status: DONE.** It was a gate on the next production crawl, and it landed
before one ran.

Shipped as `shopping_advisor/run.py` plus the spider wiring, with
`tests/test_run.py` and the first saved search page in
`tests/corpus/amazon_de_search/`.

### Outcome

A crawl becomes reproducible and auditable, and future extraction work stops
requiring a re-crawl.

### Scope

- `run_id`, run start time, spider arguments and the **acquisition locale**
  (today implicit in `Accept-Language` in `settings_baseline.py`) written to a
  run manifest and onto every record.
- One discovery-occurrence record per (run, query, search page, position,
  ASIN, sponsored flag, search-result title, search-result price), emitted
  **before** the dedupe check. PDP fetching stays deduplicated; today a repeat
  sighting is dropped before anything is recorded, so the evidence is lost.
- The raw `dimensionValuesDisplayData` / twister blob captured verbatim, with
  no interpretation. It is present on 24 of 35 corpus pages and carries the
  labels that resolve the quantity conflicts R0 can only flag
  (`"500 g (16er Pack)"`).
- Retain fetched PDP HTML — measured at 390 KB gzipped / 2.1 MB raw per page,
  ≈76 MB for a 195-product run.
- Version the product evidence set: `data/` is gitignored, so the corpus this
  roadmap rests on exists on one machine only.

### Explicitly out of scope

Separate entity files or tables for hits versus products; any locale
abstraction layer; any change to pacing, proxying or headers; interpreting the
variation blob.

### Done when

- [x] A fresh three-query crawl produces a run manifest.
- [x] A complete occurrence log in which one ASIN found under two queries
      appears twice.
- [x] A locale field on every record.
- [x] An offline re-extraction from retained HTML with no network access.

### Measured on completion

Verification crawl: 3 queries, 1 search page each, 10 products per query,
Amazon.de, no proxy. 34 requests, 34 × HTTP 200, 0 retries, 0 challenges,
`finish_reason: finished`.

| | |
|---|---|
| Discovery occurrences | **213**, of **170** distinct ASINs |
| Repeat sightings | **43 (20% of occurrences)** — 21 same-query pairs, 12 ASINs under more than one query |
| Sponsored placements | **69 of 213 (32%)** of what a shopper is shown |
| Outside the result grid | 33 of 213 (carousels and ad slots) |
| PDPs fetched | 30 — fetching stayed de-duplicated |
| Records with `run_id` and `locale` | 30/30 |
| Pages retained | 30, 11.6 MB gzipped (≈387 KB each, as estimated) |
| Offline re-extraction | **30/30 identical**, no network |
| Variation matrix captured | 16/30 records; 24/34 corpus pages |

Three findings worth carrying forward:

- **A latent locale bug was already in the repository.** Scrapy ships
  `Accept-Language: en` by default and the non-baseline settings profile never
  overrode it, so every Amazon.de crawl on that profile asked Amazon for
  English while reading the answer with German label lists. Nothing failed;
  records would simply have carried an empty `attributes` block beside a full
  `raw_tables`. The gate now refuses to start, with a message naming the fix.
  Only the validated baseline profile was ever correct, and by accident of
  having been written for amazon.de.
- **The discovery selector was never the result list.** On a live search page
  it matches 82 nodes, of which 60 are the result grid and 22 are carousels
  and ad slots — 12 of those with an empty `data-asin`. That is why position 1
  was missing from every query in the last validation run. Discovery
  behaviour is unchanged; both the raw index and the grid rank are now
  recorded, and the grid rank is the one that means anything.
- **A third of placements are advertising.** Not actionable yet, but it is the
  kind of fact that changes what "what does Amazon show for this query" means,
  and it was previously unrecordable.

---

## R2 — Generic validation layer + published extraction contract

**Status: DONE.** The hold is released: the milestone's premise was that a
rule earns promotion once a *second* consumer has exercised it, and this
milestone built the second consumer first and promoted afterwards.

Shipped as `shopping_advisor/validation/` and `shopping_advisor/analysis/
categories/`, with **[CONTRACT.md](CONTRACT.md)**, `tests/test_validation.py`,
`tests/test_mounting_paste.py`, a validation snapshot in the corpus test, and
the crawl it was measured on in `data/evidence/`.

### Outcome

Downstream analyzers — the second category, not just pasta — inherit trust
semantics instead of reinventing them, against a documented, versioned record.

### The second category

Tyre mounting paste for a 10-inch pneumatic scooter tyre with an inner tube,
on an aluminium rim. Chosen because it shares almost nothing with dry pasta:
non-food, no nutrition, sold in tubs, tubes, bottles and aerosols, filed by
Amazon under four unrelated departments, and judged on criteria that are not
numeric at all — the paste must *dry after mounting and stop lubricating*, be
safe on rubber, and be free of mineral oil.

Its economics invert too. Pack size is not a discount axis: one scooter tyre
needs a few grams, the shelf is five-kilogram workshop tubs, and the cheapest
paste per kilogram is the worst buy. So it ranks on **smallest pack first**
and refuses price per kilogram as a ranking while still showing it.

### Scope

- Promote the category-neutral rules proven in R0 into a generic layer between
  extraction and category analysis — **done**, as `validation/`, which now
  also owns the *ordering* (`detect → category bands → resolve → promote`)
  that was previously a comment inside the pasta module.
- Replace `nutrition.confidence` with value-level semantics: separate `source`
  from `status` — **done**, schema v4.
- Publish the schema with a stated compatibility policy; bump
  `SCHEMA_VERSION` — **done**, CONTRACT.md, schema v4 / contract v1.

### Done when

- [x] A second category analyzer consumes the contract without re-deriving
      trust rules. Asserted mechanically, not by inspection:
      `tests/test_mounting_paste.py` parses the module's imports and fails if
      it reaches past the contract into `validation.quantity`,
      `validation.pricing` or `validation.nutrition`.
- [x] The corpus regression test covers validation output — a second snapshot,
      `validated.jsonl.gz`, over all 39 saved pages, produced with **no**
      category profile so that what is pinned is the layer belonging to nobody.

### Measured on completion

Second-category crawl: 3 queries, 1 search page each, 30 products per query,
Amazon.de, no proxy. 93 requests, 93 × HTTP 200, 0 retries, 0 challenges,
`finish_reason: finished`. 90 records.

| | dry pasta (195 records) | tyre mounting paste (90 records) |
|---|---|---|
| Classified | 165 · 30 other · **0 unclassified** | 43 · 47 other · **0 unclassified** |
| Pack quantity | 131 trusted · 13 disputed · 14 unverified · 7 unknown | 25 trusted · 1 disputed · 6 unverified · 11 unknown |
| Price per base unit | 100 trusted · 9 disputed · 2 unverified · 54 unknown | 13 trusted · 1 disputed · 1 unverified · 28 unknown |
| **At least one trusted axis** | **117 of 165** | **32 of 43** |

Effect on dry pasta of the two rules the second category forced — same
records, same code path:

| | before | after |
|---|---:|---:|
| Pack quantity trusted | 108 | **131** |
| Pack quantity unverified | 37 | **14** |
| Pack quantity disputed / unknown | 13 / 7 | 13 / 7 *(identical)* |
| Price per base unit trusted | 100 | 100 *(identical)* |
| Protein trusted | 61 | 60 |

Five findings worth carrying forward.

- **Three of the four things the layer had to learn were bugs, not
  generalisations.** The plan assumed promotion would be mostly a move. What
  the second category actually produced was: a price-per-unit path hard-wired
  to kilograms that silently discarded Amazon's own figure whenever it was
  quoted per litre; an extraction bug reporting a 50 ml tin as 50 g, because
  `total_quantity_unit` was inferred from any volume field on the page rather
  than from the row the total came from; and a missing generic rule that would
  have let a *trusted* "100 g of fat per 100 g" through. None of these were
  visible with one consumer, and none of them is category-specific. That is
  the argument R2 was waiting for, and it came out stronger than expected.
- **The missing rule is the cleanest measurement in this repository.**
  German *Fett* means grease as well as fat, so `"Fett wird in einer 100 g
  Tube geliefert"` on bicycle grease parses as a nutrition declaration — with
  the per-100 g basis apparently confirmed. Dry pasta was protected only by
  having a plausibility band. The rule that was missing is category-neutral:
  a declaration carrying a single nutrient has nothing on the page to confirm
  it, so it may be shown and never trusted. **Thirteen lone-nutrient blocks
  exist across the two validation sets and all thirteen are artefacts of
  matching a word** — nine in dry pasta, six of them reporting 100 g of
  protein per 100 g and one reporting 534.
- **R0's refusal to read a bare title weight was right, and too broad.** The
  reasoning was multipacks: `"Garofalo Fusilli 500g"` on a sixteen-pack states
  the weight of one box. Take the multipack away and the ambiguity goes with
  it. Mounting paste does not use multipack phrasing at all — it writes
  `"Reifenmontagepaste 5 kg"` and means it — and only 2 of 43 pastes had a
  confirmable pack size. The rule added is narrow and **asymmetric**: when
  nothing on the page claims more than one unit, a bare weight in the
  listing's own text may *confirm* the attribute total and may never
  contradict it. On dry pasta it moves 23 records from unverified to trusted
  and leaves every disputed and every unknown exactly as it was.
- **A profile is data, and that had to be enforced rather than intended.**
  The first draft let a category pass a callable. The version that shipped
  accepts plausibility bands and a label, and nothing else, because the
  ordering the bands participate in is the part a second category has no way
  to know is load-bearing. `price_band=None` is a legitimate answer: mounting
  paste spans 50 ml tubes and 5 kg tubs two orders of magnitude apart per
  kilogram, and inventing a band to have one would reject real listings.
- **The category answer is an evidence-gap report, and honestly so.** The
  criterion that decides this purchase — does the paste dry out and stop
  lubricating — is stated on **3 of 43 listings**. "Free of mineral oil" and
  "solvent-free" are claimed by **none**. Water-solubility, the usable proxy,
  appears on 6. One listing declares a mineral-oil base, which is the only
  *disqualifying* evidence on the page and is surfaced as an adverse claim.
  A ranking that did not say this would be inventing confidence.

### What the second category could not fix

`price_per_base` is `unknown` on 28 of 43 mounting pastes, because 23 have no
price at all — no purchasable offer at crawl time, the same volatility R3
measured on the pasta set. Not an extraction gap and not fixable downstream.

### Retired from scope

Nothing. The one thing deliberately not built is a `nutrition: bool` flag on
the profile: a non-food record has no food block, the nutrition rules cost it
nothing, and adding a switch would have been a category telling the generic
layer which rules to run — exactly what the profile is shaped to prevent.

---

## R3 — Variation-aware product families

**Status: DONE**, with one of its two completion criteria **not met** and the
reason recorded rather than worked around.

Shipped as `shopping_advisor/analysis/variation.py` plus the reconciler and
report wiring, with `tests/test_variation.py`.

### Outcome

Pack-size variants of one product are compared as a single offer family, and
the "same pasta, sixteen ASINs" distortion disappears from rankings.

### Scope

Interpret the variation blob R1 now captures into a family identity and a
pack-size dimension, and use it as an additional quantity-conflict resolver —
`"500 g (16er Pack)"` is the independent statement that settles the disputes
R0 can only flag.

Also the part of the discovery model R1 deliberately left alone: occurrences
are now persisted separately from products, but nothing *joins* them. Build
that join when there is a consumer for it, and not before.

### Explicitly out of scope

Crawling sibling ASINs that were never discovered.

### Done when

- [x] Variants collapse into one comparison row with per-pack price per kg.
- [ ] **Not met:** family evidence resolves at least the quantity conflicts R0
      could only flag. Seven of R0's eight flagged ASINs reappeared in the
      verification crawl and **none of them has a variation matrix at all**.
      The evidence this milestone was meant to apply does not exist on those
      pages. No amount of further work on variations changes that, so the
      criterion is retired rather than chased.

### Measured on completion

Re-ran the original three-query validation crawl under schema v3: 195 records,
201 requests, 201 × HTTP 200, 0 retries, 0 challenges, `finished`.

| | |
|---|---|
| Variation matrix present | **68/195 (35%)** |
| Dry pastas → offers | 165 listings → **159 offers**; 6 offers hold more than one crawled pack size |
| Pack quantity improved | **22 unverified → trusted**, **2 unverified → disputed** (24 records, 12%) |
| Only pack-size label on the page | 26 records |
| R0's flagged conflicts resolved | **0 of 7** — none carries a matrix |

Four findings.

- **The corpus overstated how common variation data is, and I had used that
  figure to justify this milestone.** "Present on 24 of 35 corpus pages" is
  71%; on records from an ordinary search crawl it is **35%**. The corpus
  pages were chosen for layout diversity, which is exactly the bias that makes
  them a bad basis for a frequency claim. Checked against the retained pages,
  not assumed: where the matrix is missing it is genuinely absent from the
  HTML, not missed by the extractor.
- **The premise in the original review was wrong.** "Sixteen ASINs of the same
  Garofalo pasta crowd the ranking" — those listings are different *shapes*
  under one parent, not pack sizes. Amazon files spaghetti, penne and fusilli
  under a single family, so collapsing by family would have merged different
  products. Grouping is by size dimension only, and the corpus proves that is
  necessary rather than fastidious.
- **The real payoff was the quantity side, not the comparison side.** One case
  matters on its own: `B0DM21MLWV` (Barilla Integrale) was shown by R0 at
  **€38.56/kg** as an unverified but plausible price, because Amazon's
  attribute table says 1 kg and its own unit price is quoted *per piece*. The
  variation matrix says `10kg`. The real price is **€3.86/kg** — a tenfold
  error on a flagship brand, invisible to every source R0 had.
- **Price coverage is volatile between crawls.** The September run had a price
  on 195/195 records; this one on 141/195. Investigated rather than assumed:
  no price payload keyed to the main ASIN exists anywhere in those responses,
  and the discovery log shows search did not price them either. They had no
  purchasable offer at crawl time. The extractor is right to return nothing,
  and §1.4's finding — that no high-value field needs browser execution —
  still holds.

### Retired from scope

The discovery/product *join* stays unbuilt. R1 persists occurrences separately
and nothing reads them yet; this milestone did not create a reader, so the
reasoning that put R0 ahead of P0 applies unchanged — do not model what
nothing consumes.

---

## R4 — Amazon.com as a validated marketplace

**Status: DEFERRED.** Reconsider when a stated user need for US product
research exists. "Architecturally supported" is already true and costs nothing
to keep.

### Scope when it starts

A `.com` validation crawl from a US IP; the US nutrition parser
(`#nic-nutrition-facts`, reversed and merged cells, per-serving basis) plus
serving-size conversion **with validation attached** — per-serving → per-100 g
is a derivation, and derivations produced the worst values on `.de`; `.com`
price and unit-price re-measurement; delete or validate the speculative
`amazon.co.uk` and `amazon.it` profiles (`amazon.it` currently declares German
as its label language, which would map nothing on Italian pages and emit an
empty `attributes` block beside a full `raw_tables`).

### Done when

`.com` coverage and validation figures are comparable to the `.de` run, and US
nutrition either converts correctly or returns `unknown`.

---

## R5 — Reviews as an evidence source

**Status: DONE.** The decision test passed decisively, and the milestone cost
roughly a tenth of what this entry budgeted, for a reason worth recording.

Shipped as `shopping_advisor/extraction/reviews.py` and
`shopping_advisor/validation/reviews.py`, with `tests/test_reviews.py` (33 tests)
and schema v5. Driven by the third category, basmati rice, where the properties
that decide the purchase — does it smell of basmati, does it arrive with moths
in it — are stated nowhere except in reviews.

### The decision test, run

Threshold was ~30% of comparisons ending in "both claim the same thing and
nothing distinguishes them". On 239 basmati listings: **137 (57%) claim
"extra long", 104 (44%) claim a growing region**, and outside price per
kilogram almost nothing on the page separates them. Far over the bar.

### Why the estimate was wrong, and in which direction

This entry priced reviews as **"crawl-graph expansion"** — following
`/product-reviews/` pagination. That was wrong twice:

- **The data was already in hand.** Eight to thirteen review cards and the
  complete ratings histogram are in the PDP HTML the crawler has retained
  since R1. **Zero additional requests**, and both production crawls were
  re-extracted offline to get them.
- **The expensive version is not available at any price.**
  `/product-reviews/<ASIN>` redirects to sign-in. The PDP widget is the only
  review evidence reachable without an account, so there is no larger version
  of this milestone to come back for. Recorded here so nobody re-scopes it.

### What the two structures are, and why they are not interchangeable

| | histogram | rendered sample |
|---|---|---|
| Covers | **every rating the listing ever received** | 8–13 cards Amazon selected |
| Carries | five percentages | the words |
| Sums to 100 | **38 of 38 corpus pages** | — |
| Reconstructs the published average | **within 0.08 stars, worst case** | — |
| May support a rate | **yes** | **never** |

Because the histogram is an independent statement of the same fact the average
asserts, it promotes the average from `unverified` to `trusted` under the
layer's existing corroboration rule — no new rule was needed. And because the
sample is a sample of Amazon's choosing, a complaint found in it establishes
**presence, never frequency**, which the Value says in its own notes.

### The vocabulary needed no extension, and that is the result

The category needed `not_claimed` and `unknown` to mean opposite things for
the same missing sentence:

- a **vendor** controls the whole page, so an absent claim is `not_claimed`;
- **buyers** control nothing — Amazon picked which 13 of 3 446 reviews to
  render — so an absent complaint is `unknown`.

R2's vocabulary already expressed that. Nothing was added to it.

### Measured on completion

| | |
|---|---|
| Corpus pages carrying a review block | **38 of 39** |
| Pages carrying a histogram | **38** |
| Review cards extracted | **277** |
| Written on *another* marketplace | **82 (30%)** — machine-translated onto the page |
| Carrying a variant label | 201 |
| Marked verified purchase | 271 |
| Schema v4 → v5 | **purely additive**; corpus diff touched only `reviews.*` and `blocks_present` |

Three findings worth carrying forward.

- **30% of the "reviews" on an amazon.de page were not written for
  amazon.de.** They are real, and they are about a different importer, a
  different batch and occasionally a different product. Counted apart rather
  than dropped.
- **Amazon pools reviews across pack sizes, and the page says so if you
  read the format strip.** Tilda Pure Original's 10 kg listing shows reviews
  from three pack sizes. This was previously invisible; it is now a flag on
  the value.
- **Splitting the search by star rating was not a refinement, it was
  required.** Searching all reviews for stickiness complaints matches "die
  Körner kleben überhaupt nicht" — a five-star endorsement — and it was the
  single commonest false positive in the category. Positive signals are now
  searched in 4–5★ reviews and negative ones in 1–2★, pinned by test.

---

## R6 — A command line for the things every category needs

**Status: DONE.** The cheapest item on this roadmap and the best evidenced:
four scripts were written and thrown away in the course of one research
question. Nothing new was needed, only exposing capability that already
existed.

```
shopping_advisor.run reextract <run_dir> [--feed old.jsonl] -o new.jsonl
shopping_advisor.analysis <cmd> feed1.jsonl feed2.jsonl ...   # merge by ASIN
```

Two of the four scripts were built. The other two were not, because they are
partly served under other names: `cards ASIN ASIN` is `card`, which takes more
than one, and a one-axis shortlist is `rank`. **T0 correction:** `rank` does
not reproduce a composite basmati shortlist; its basmati default is price per
kg. The completion measurement below establishes the fusilli one-axis workflow.

**Offline re-extraction was documented in README.md as a code sample** — proof
that it worked, and a sign that it should be a command. It reads the
marketplace and locale from the run's own manifest rather than from a flag,
because re-extracting a German page against an English label vocabulary is
the silent under-extraction R1's locale gate exists for. `--feed` supplies
what a stored page cannot know: which query found the product, where it
ranked, and when it was fetched. Without it search context is absent and
fetch time fell back to filesystem mtime, which is not reliable freshness
evidence after copying a page. T1 removed that fallback: fetch time is
recorded per page when it is fetched, and a run store written before that
reports unknown freshness rather than a filesystem timestamp.

**`fetched_at` is carried across, never refreshed.** A re-extraction stamped
with today's clock would make every old page the freshest evidence in a study
— which is exactly what the merge below is built to believe.

**The analysis CLI took exactly one feed path**, so a three-crawl study needed
a merge-by-ASIN loop the user wrote themselves. Every command now takes as
many feeds as the study has, and the newest `fetched_at` wins — deliberately
*not* the order the feeds were named in. `data/fusilli_*.jsonl` expands
alphabetically, which has nothing to do with when each crawl ran, and price
and availability are precisely the fields an arbitrary argument order would
get wrong. What the merge did heads the report, so a number in it can be
traced back to a crawl.

### Done when

- [x] A finished run re-extracts from shipped commands, with no scratch script.
- [x] Several feeds are one corpus, merged by evidence rather than by argument
      order.
- [x] The fusilli shortlist reproduces from one command line.

### Measured on completion

The fusilli study was reproduced from three local feeds at completion. These
paths are **not committed inputs** in the current repository; use the
[committed-case walkthrough](RESEARCH.md#offline-walkthrough) for onboarding:

```
uv run python -m shopping_advisor.analysis rank \
    data/validation_v3_amazon_de.jsonl data/fusilli_broad.jsonl \
    data/fusilli_brands.jsonl --category dry_pasta
```

| | |
|---|---|
| Records read | 582 from **3 feeds** |
| After merge | **471** — matching the study's own count exactly |
| ASINs crawled more than once | **95**, resolved to their freshest copy |
| Classified dry pasta | **404**, 67 excluded — again the study's own numbers |
| Shortlist products reproducing at the published €/kg | **8 of 9** |
| Offline re-extraction of the broad fusilli run | **224/224 records byte-identical** to what the crawl wrote |

The ninth is Garofalo Fusilli n.63 (`B08JLSVW3J`), and it is not a regression:
its page states 500 g in Amazon's attribute table and 16 × 500 g in the title,
so price per kilogram is `DISPUTED` and the ranking refuses to guess. **The
card already prints both numbers** — "64.98 EUR/kg" beside "if the pack size
stated on the page is right, this is 4.06 EUR/kg" — which is the honest
output. Promoting that derivation to a rankable value is a quantity-
reconciliation decision in the validation layer, and it belongs to R9, not
here. It affected **4 of the 54 fusilli** in the study.

---

## R7 — Attributed search: finding a claim vs crediting it

**Status: DONE.** Two categories independently hit the same bug:
text on an Amazon page is not necessarily *about the product the page sells*.

Measured on basmati: searching every text field for the milling degree marked
**53 of 239** records parboiled and **29 were wrong** — cross-sell copy ("Neben
unseren PURE BASMATI Reis haben wir auch bereits vorgekochte …", which marked
the Stiftung Warentest winner as parboiled), A+ comparison tables listing a
brand's entire shelf, recipe suggestions, and the outright negation
"Non-parboiled for authentic basmati". Restricting to title, ingredient
declaration and attribute rows took it to **0**.

Mounting paste hit the same class of error and solved it positionally, in its
own module. That is the second occurrence R2's promotion rule waits for.

### Scope review (2026-09-15)

At review, the motivating fixes already shipped with category regressions: basmati's
`GRAIN_FIELDS` and `_negated`, mounting paste's `NEGATED` drying exclusions,
and basmati's brand/manufacturer gate for the Tilda/Kajal laboratory result.
The historical 29 errors are not outstanding defects. The combined saved
basmati feed now contains 359 records, of which 239 classify as basmati.

What remained was shared search policy and a real gap in the local fixes:
search selected the first match per field and categories filtered the cropped
quote afterwards. A negated first mention can hide an affirmative one later
in the same field; unrelated negations in the quote can also discard it.

### Scope

- Add `search(..., scope='self' | 'page')` to the validation contract, keeping
  `page` as the compatible default. `self` restricts to title, ingredients
  and raw attribute rows; `fields` further narrows either scope. This is a
  conservative field policy, not proof that every sentence concerns this
  product. Reviews remain a separate search.
- Add opt-in affirmative matching against full-text match positions, before
  quote cropping and result limits. Share bounded German/English prefix
  negations and suffixes such as `mineralölfrei`; preserve affirmative
  absence claims when the pattern itself includes `ohne` or `frei`.
  Category-specific exclusion patterns remain data and reject only overlapping
  matches. Continue through rejected mentions within the same field.
- Migrate basmati milling/declaration checks and mounting-paste claim search.
  Keep mounting-paste prose searchable: restricting its drying evidence to
  `self` would remove legitimate bullets and descriptions. Preserve its
  positional product classifier and kit caveats.
- Retain external laboratory matching in basmati: one consumer does not
  justify a generic external-evidence framework. Test the existing identity
  gate and use literal whole-brand matching with identity evidence attached.

### Explicitly out of scope

General linguistic negation or cross-sell resolution; reattributing all
category claims; changing laboratory findings, scoring policy, acquisition,
marketplace word boundaries or the extraction schema. A brand match does
not establish that a listing's batch or pack was independently tested.

### Done when

- [x] Shared search tests cover scopes, intersecting field filters, negation,
      positive absence claims, later affirmative mentions and quote provenance.
- [x] Both category suites pin the motivating false positives and retained
      true positives, including the external identity gate.
- [x] Offline before/after comparison of saved category feeds accounts for
      every changed card; no known true positive is lost. This is a regression
      check, not a claim of measured classification accuracy.
- [x] The full suite, including extraction/validation snapshots, passes and
      the public search contract documents the boundaries.

### Measured on completion

All **323 tests pass** (296 before R7), including extraction/validation
snapshots, all three categories, and the new `tests/test_attributed_search.py`.
No crawl, dependency upgrade or snapshot regeneration was needed.

Offline comparison covered **1,885 record occurrences across 14 saved files**:

| Saved files | Occurrences | Changed cards |
|---|---:|---:|
| Five `basmati_*.jsonl` feeds (all, brands, broad, and v5 variants) | 1,361 | 61 |
| `paste.jsonl`, `paste_rema.jsonl`, `paste_v2.jsonl`, `paste_v7.jsonl` | 245 | 1 |
| Four archived mounting-paste feeds, v4–v7 | 245 | 1 |
| `tests/cases/mounting_paste_v1.jsonl.gz` | 34 | 1 |

These are overlapping feeds, not distinct products. All **64 changed cards**
only gained evidence; their existing evidence remains intact. The 61 basmati
cards now quote the brand/manufacturer supporting the existing laboratory
attribution. The other three occurrences are `B0BJRG3K8Y`: its A+ text says
`trocknet nicht aus` about storage, then `Abtrocknungsverhalten: langsam
trocknend` about the same Premium white paste. Search now reaches the latter
statement and adds it beside the existing bullet evidence.

Removing evidence arrays from the serialized cards makes the complete
before/after output identical: no changed classification, milling degree,
claim status, laboratory verdict, score, suitability, measured axis or note.
New synthetic regressions separately exercise negated absence claims, later
affirmative mentions, and brand substrings that the saved feeds do not contain.

---

## R8 — Marketplace-aware text matching

**Status: DONE.** The motivating bug was already fixed locally; R8 shares
the boundary policy and makes reporting honest.

### Scope review (2026-09-15)

`basmati_rice.py` already uses `\bbasmati`, and
`test_the_german_compound_noun_is_basmati` protects AKASH, Tilda and Alnatura
titles. The original lost-listing count describes the first implementation,
not the current classifier. Its denominator also differs between the old
roadmap (239) and test commentary (216), so it is not a reproducible current
acceptance measure. The saved `basmati_all.jsonl` now contains **359 records:
239 classified basmati and 120 other products**.

The remaining defect is that the German prefix rule also applies to English
records. `Marketplace` already owns a language and `for_domain()` resolves
profiles, but neither is used by this match. The summary still prints
`0 unclassified` under “Corpus quality”; that measures whether a decision was
made, not whether it was correct.

### Scope

- Add `Marketplace.word(stem)`, returning a regex fragment for a non-empty
  **literal** stem: leading word boundary for German, both boundaries for
  English and other languages. Escape regex metacharacters; callers choose
  case sensitivity. This is an opt-in prefix policy, not a German compound
  parser: exclusions and negations remain the category's responsibility.
- Use it for basmati in both titles and ingredient declarations. Resolve the
  profile per record from `marketplace`, falling back to `product_url` or
  `canonical_url` for legacy feeds and then the existing English fallback.
  Follow the acquisition profile's language; do not infer language from text
  or introduce a new locale override. R1 already gates conflicting crawls.
- Label summary counts as **classification decisions**, with **no decision**
  replacing **unclassified**, and state that accuracy is not measured.

### Explicitly out of scope

A blanket rewrite of category regexes; compound splitting; R7 attribution or
negation work; changes to acquisition locale, extraction schema or marketplace
validation. In particular the provisional `.it` profile is not repaired or
validated by this milestone.

### Done when

- [x] German compounds and standalone English words match; English suffixes
      and embedded stems do not, with literal escaping covered by tests.
- [x] Basmati title and ingredient matching use each record's profile,
      including mixed-marketplace input and legacy URL fallback.
- [x] Every saved German basmati feed retains its complete classification
      output, including evidence and notes; existing category and corpus
      regressions pass.
- [x] Summary tests distinguish decisions from accuracy and cover records
      with no classification decision.

### Measured on completion

All **296 tests pass** (282 before R8), including extraction/validation corpus
snapshots and all three category suites. The compound-title regression now
uses an empty ingredient declaration, so a separate “Basmati Reis” ingredient
cannot hide a broken title match.

Offline before/after comparison of the full classification value, status,
evidence and notes found **zero changes** across all five saved German feeds:

| Feed | Record occurrences | Changed classifications |
|---|---:|---:|
| `basmati_all.jsonl` | 359 | 0 |
| `basmati_brands.jsonl` | 243 | 0 |
| `basmati_brands_v5.jsonl` | 243 | 0 |
| `basmati_broad.jsonl` | 258 | 0 |
| `basmati_broad_v5.jsonl` | 258 | 0 |

The **1,361 occurrences overlap across feeds**, not 1,361 distinct products.
The combined feed remains 239 basmati / 120 other / 0 no decision. English
boundaries are covered by synthetic records, not a newly validated English
marketplace crawl. No new acquisition or snapshot regeneration was needed.

---

## R9 — A second pass for missing prices

**Status: PLANNED**, behind a decision test.

**73 of 239 basmati (31%) had no purchasable offer at crawl time** — among them
Rapunzel, Spielberger demeter and two Tilda Pure Original pack sizes. R3
measured the same volatility on pasta (195/195 priced in one run, 141/195 in
the next) and correctly concluded the extractor is right to return nothing.

The product consequence was never drawn: **a study built from one crawl
silently omits a third of its category**, and the omission is invisible in the
output.

A second kind of missing price arrived with the fusilli study and belongs
here rather than in R6: **4 of 54 fusilli carry a price per kilogram the page
itself contradicts**, because the seller filled "Anzahl der Einheiten" with
the weight of one pack and Amazon computed its own €/kg from that same wrong
row. Garofalo 16 × 500 g reports €64.98/kg, Barilla n.98 10 × 1 kg reports
€0.37/kg. The card already prints the derivation from the title beside the
contradiction; what is unresolved is whether that derivation may be *ranked
on*, which is a quantity-reconciliation decision in the validation layer and
not a reporting one.

### Decision test, before building anything

Re-fetch the 73 unpriced basmati ASINs once, some hours later, and count how
many price. **Below ~30% recovered**, defer an automated second pass for that workload;
one unsuccessful refresh does not establish that a listing is genuinely dormant.
Use fresh, explicitly comparable inputs if the historical 73-ASIN set is unavailable.
Keep quantity-reconciliation changes separate from refresh automation, with their
own evidence, counterexamples and CONTRACT version review. T2 now exposes
exclusions, so the earlier invisible-omission finding is historical.

---

## R10 — Scoring as a shared facility

**Status: DEFERRED — deliberately, and the reasoning is the point.**

Basmati needed a composite score; `report.py` refuses to offer one, and its
stated reason is right: a score "could not answer why A is better than B".
Three properties made one defensible anyway, and all three look general:

- every component published with its evidence, never just the total;
- a missing input scores **neutral**, never zero — absence of data is not an
  adverse finding;
- the total is **shrunk toward neutral in proportion to how much is unknown**,
  so a listing whose entire case is its own adjectives cannot outrank one with
  an independent measurement.

The third is not theory. The first draft ranked first a 10 kg bag with **five
ratings** whose feature bullet claimed every heavy metal was below the limit of
detection — a sentence no reader can check, scored as though it were a test
report.

But one category is one data point, and this repository's own experience says
promotion before a second consumer produces bugs dressed as generalisations —
in R2, three of the four things the layer "had to learn" were bugs. Dry pasta
and mounting paste both refuse to score, so there is no second consumer asking.
It stays in `basmati_rice.py`.

---

## R11 — Category synthesis as a default step

**Status: IN PROGRESS. The first category application of the general
adaptation loop landed on 2026-09-18 (`smartwatch`, through R15's procedure);
synthesis as a *default* step still waits for its own gates below.** This is
the first category application of the general adaptation loop, not a
standalone generator project.

**2026-09-18 — First category written through R15 (smartwatch).** Recorded in
full under [R15](#r15--controlled-task-driven-capability-adaptation); what
belongs here is the R11 reading of it. Created within a recorded study budget:
14 400 s of engineering allowance, 22.8 s used, one attempt of three. Positive
cases, false-positive guards and missing-evidence cases: 39 smartwatches, 16
declined listings each with its reason and the six declines proven by case
records, and every unstated criterion `not_claimed` rather than false. The
report distinguishes established observations from provisional interpretation
by saying, beside its conclusion, that it rests on an experiment — and
maturity upgraded no value's status. No plausibility band was invented. What
this does not yet show: that a changed buyer preference changes the brief and
not the category (the study revision is Phase 2), and that R16 records a
promotion — this one stays `experiment`, retained.

**2026-09-17 — First category written mid-study, as reviewed maintenance
(school backpack).** The intake conversation recorded under R13 ended with the
buyer asking for the category and a full comparison; with no R15 gate shipped it
was built under the maintenance workflow, on the authorisation the conversation
already carried, and this entry is the record. Measured: 43 unique records from
two bounded probes, 23 classified school backpacks and 20 other, each with its
reason; a positional title classifier separating a secondary-school backpack
from a first-grader's satchel set, an adult's laptop pack and a trekking pack;
four vendor statements (reflectors 13 of 23, manufacturer warranty 4, adjustable
back 10, hip or chest strap 13). The category needed two generic changes, each
confirm-only and each with zero effect on the 39 committed corpus pages: the
extractor reads the weight Amazon.de appends to the dimensions row when no
Artikelgewicht row exists (`item_weight_origin`), and A+ copy joins bullets and
description as a source that may confirm a single-unit weight and never
contradict one. Usable bag weights went from 3 to 10 of 43. Not established:
classifier accuracy beyond these 43 titles, anything about durability, or fit
for a given child — the body-height range a vendor states is shown and ranked on
by nobody. This does not make synthesis a default step; the R15 gates are still
the missing piece, and the case set is in
[tests/cases](tests/cases/README.md). **Lifecycle recorded 2026-09-18:** a
task experiment, retained and nominated for reuse; the
[capability index](#r16--capability-lifecycle-and-architectural-review) says so,
and promotion to a maintained capability waits for a distinct subsequent use.

### Scope

Use a maintained category where it fits the brief; otherwise create the smallest
provisional category needed for the study. Keep classifier, claims, axes and
interpretation downstream of extraction, and plausibility profiles as data.
A task requiring new extraction also uses R15 in that responsible layer.
Do not assume existing fields can express every future product characteristic.

A category may contain scoped domain knowledge and explicit method defaults;
a buyer's constraints stay in the brief. Every new criterion needs a source or
a labelled hypothesis and applicability limits. Provisional categories default
to no invented plausibility band. In the existing 34 mounting-paste cases,
using pasta's profile moves 14 values: a plausible-looking default can silently
change trust without a classifier error.

### Done when

- An unseen category is created within the recorded study budget, through R15,
  with positive cases, false-positive guards and missing-evidence cases.
- Reports distinguish established observations from provisional interpretation;
  maturity does not automatically upgrade or downgrade individual value status.
- The profile cannot add rules or bypass validation ordering. New units, axes
  and applicability limits are checked; old categories still pass their gates.
- A changed buyer preference changes the brief or declared study method, not a
  permanent fact about the category. The resulting decision difference replays.
- R16 records whether the tested capability stays task-local or is promoted.
  Becoming the default research step requires these gates, not a wording change
  in the runbook alone.

---

## R12 — Discovery that states its own coverage

**Status: PLANNED.** Builds on R13 evidence planning and T1/T3 provenance.
Promoted from [E3](#e3--discovery-coverage-of-the-category) for its demonstrated
discovery blind spots, not a proven completeness threshold.

### Scope

Turn the evidence plan into bounded candidate and source discovery. Report
what was requested, reached, failed or left unexamined, and why collection
stopped. Counts describe the inspected sources, never the entire market.
A brand expansion seeded only from the first crawl cannot discover a brand
absent from that crawl: include justified independent catalogues, manufacturer
sources and named candidates where the plan requires them.

### Why it is not free: two measurements, both negative

- **Eight generic queries in German and English, two pages each, never
  surfaced AKASH at all.** It took a query naming the brand. AKASH is one of
  only two basmatis Stiftung Warentest rated "gut" in 5/2026 — so a
  researcher who did not already know the answer would not have reached the
  product the study ended up recommending.
- **Thirteen queries across five crawls never surfaced a 50 ml Rema Tip Top
  tin**, because its title is "Rema Tip Top 501004 - Schwammdose,
  Transparent, 50 ml" and contains no word anyone would search for. It is a
  bicycle tyre mounting gel and its title never says so.

The measured two-page sweep did not solve these omissions. It does not prove
that greater depth could never help. The basmati finding motivates testing
whether generic queries under-sample diaspora brands; generalization to rice,
pulses, spices or flour remains a hypothesis. Compare bounded query/source
expansion with depth using decision-relevant yield, not raw result count.

### Done when

- A brand-expansion pass, seeded from the first crawl's own `brand` field, is
  a bounded and measured step rather than something a researcher remembers.
- A study report states its discovery coverage as a fact: which queries ran,
  what they returned, which products arrived only through a named-ASIN or
  brand-expansion path, and what the method is known not to reach.
- Coverage also maps decisive requirements to evidence found or missing,
  including source-access failures, freshness, variant identity and budget stops.
- Test a named candidate and a relevant brand absent from initial search, plus
  a case where decisive evidence remains unavailable after bounded expansion.
- Historical basmati evidence was **1 of 8 finalists (12.5%)**, below E3's
  original 20% shortlist threshold. **2 of 3 externally tested products** is a
  different denominator. The priority is the demonstrated decision-relevant
  blind spot; record that revised rationale rather than claiming the old test passed.

---

## R13 — The conversation as the entry point

**Status: DONE (2026-09-18). Depended on shipped T2/T3; did not wait for R11.**
The machinery of [INTAKE §16](INTAKE.md#16-implementation-sequence), stages
1–10, shipped on 2026-09-17; the conversational acceptance trials the Done-when
asks for ran on 2026-09-17 and 2026-09-18 and are recorded below. No fixture
here stands in for them.

**2026-09-17 — INTAKE §16 stages 1–10 shipped.** Six dated entries recorded the
stages as they landed; the same day they were consolidated into this one, keeping
every measurement and dropping the "stages N–10 remain planned" scaffolding, since
this roadmap owns decisions and measured effects and
[CONTRACT §8–§14](CONTRACT.md#8-study-audit-contracts-t3) own the semantics.
The commit history holds the entries as written.

| Stage | Shipped | Measured effect, and what is not established | Floor |
|---|---|---|---|
| 1–2 | The [case register](tests/intake/README.md) with the three inert qualifications of INTAKE §1 pinned; the §13 operating text in the runbook and AGENTS | Two briefs differing only in `cost_basis`, `unacceptable` or `limits` decide identically; a budget through `max_axis_value` caps unit price and through `unacceptable` changes nothing; the bronze-die study thirty days on has five stale ranked candidates and an unchanged shortlist. The blocking quantifier falsified by its own first example is gone | 491 → 515 |
| 3–4 | `LEDGER_VERSION`, `AUDIT_VERSION` and `REVIEW_VERSION` split and each pinned by the gate; the controls catalogue over the live registry, `study controls --category CATEGORY` | Three independently movable contracts where there was one; a catalogue for three categories covering all five candidate-set mechanisms, with cases sensitive to each control's meaning. Not established: arbitrary-language understanding, or an unsupported requirement turned into a predicate | — |
| 5 | Plan v1: user messages retained by provenance, requirement roles, settlements, provenance, assessment paths and stage effects, prospective questions, deterministic read-back with a separate response status; the plan-to-brief binding consumed by `check`, `analyse` and `run`; storage decided (private `data/plans/`, mandatory bundle snapshot, sanitized `tests/intake/`) | A dropped bronze-die requirement or filter, a changed role, unit, cap or axis attribution, or an unrecorded filter refuses at the boundary; replay works after the originating plan is deleted. Not established: natural-language interpretation — this is preservation machinery | 515 → 553 |
| 6 | Stage gates at intake, comparison support and conclusion; three stop kinds kept apart from the analytical outcomes; the bounded-finding heading; requirement rows and the attribution sentence in plan-backed reports; two plan-backed examples in the gate | The delivered-cost recommendation is withheld while the item-price finding survives at identical eligibility and ordering; budget-plus-unit-price is detected without changing units and the budget on the per-kilogram cap refuses. Not established: that a plan captured every requirement, or that `enforced` means adequate | 553 → 587 |
| 7 | Declared `freshness.scope` with silence historical; `study deliver` freezing the reference in `delivery.json`; current advice a structural condition `validate-report` enforces past any semantic review; replay never reads the clock | The case set under current-advice scope is permitted at its build date and blocked thirty days on naming all five governed observations, while the analysis against `as_of` finds nothing stale; the fixtures deliver as history at either reference; a completed review lifts no block. Not established: an honest clock or a true declaration | 587 → 613 |
| 8 | The session ledger: limits in observed units, action records from run manifests, reconciliation that keeps unknown unknown, `session-authorise`, `session-record`, `session-check`, `run --session`, `study resume` from the bundle's own snapshot | The delivered-cost example resumes with the working ledger deleted, the interrupted collection listed as interrupted, the resumed collection prevented by name (55 of 300 responses remaining) and the engineering proposal retained unexecuted; `resumable` pinned. Not established: that a declared consumption is true, or that money or tokens can be measured here | 613 → 652 |
| 9 | The intake review bound to the plan digest, the retained evidence, the resolved mappings, the read-back status and the live catalogue; five checks, with `limited` forced by a review-limiting redaction; `run --intake-review` refusing a failed plan; `review-intake`; `--require-review` needing a pass | Case 7's semantic limit has a record and a consequence: the budget on the cap passes the gates as `enforced` and an intake review failing `adequacy` refuses the run with the finding quoted; a review of another revision refuses as superseded; `intake_review: pass` pinned. Not established: that a reviewer's pass is right | 652 → 676 |
| 10 | Manifest v3 with the artifact inventory; the review basis as a contract; final review v2 resting on valid intake findings, with `conclusion_presentation`; the identity decision; the delivery review with the deliverer's attestation; the dirty-tree caveat | Six ids moved once; every decision artifact is byte-identical before and after and each report differs in one line; both T3 reviews reissued under v2 with unchanged basis digests; the intake review and session ledger fixtures did not move. Not established: that an attestation is true | 676 → 712 |

Through stages 1–9 the four pre-existing study identities, decisions, report
bytes and both completed reviews stood unchanged, because the plan is an optional
input and absent one every byte is identical. Stage 10 moved the ids and reissued
the reviews deliberately — the one commit INTAKE §16 priced for exactly that —
and no decision moved with them. No runtime lock, extraction or generic
validation semantics changed in any stage.

**Closed 2026-09-18, on the maintainer's review and decision.** Three trials are
recorded below: the first (2026-09-17) by the user who wrote the documentation,
the second (2026-09-18) by a reader who had not, and the third (2026-09-18) on
an unsupported category by a buyer who recorded his intent, requirements, chosen
product and acceptable outcomes privately **before** his first request and
graded the result against that record afterwards — the grading INTAKE §12 and
§14 ask for, once. The question close of the runbook was repeated on each, the
defaults the trials suggested were decided the same day, and the third trial's
plan went through three independent intake reviews: two fails and their
repairs, then a review that passes faithfulness, adequacy, assumptions and stage
effects and is `limited` on omissions by the plan's own missing-context
declaration, which CONTRACT §13 never lets pass. Each Done-when bullet has a
recorded trial behind it; the review chain is the measured effect INTAKE §11
asked for. What R13 does **not** establish: understanding of arbitrary purchase
requests, a second provider or platform ([R17](#r17--portability-evidence)),
or any control for the smartwatch requirements — that category is a retained,
unfunded proposal for [R15](#r15--controlled-task-driven-capability-adaptation).
A passing gate protects the tested machinery and nothing more.


**2026-09-17 — Observation from the first unsupported-category conversation
(school backpack).** One requirement that neither the buyer's request nor the
agent's reading of it produced came from a professional test's criteria list:
Stiftung Warentest's satchel test rates traffic visibility against DIN 58124,
the agent asked whether that mattered, and the parent confirmed it as a hard
constraint. The two bounded probes then found the criterion stated in the
listings of every in-class ergonomic brand and in none of the daypacks, so it
separated the shelf where the request alone would not have. **Proposal, not
adopted:** when a category is unsupported or new, read the criteria lists of
professional tests for the class or an adjacent one as a source of *candidate*
requirements to ask the buyer about, recorded as agent-authored questions that
name their source; a criterion enters the plan only when the buyer confirms it.
This is [R11](#r11--category-synthesis-as-a-default-step)'s synthesis applied to
the questions rather than the classifier, under the runbook's rule that
[questions are revised from what decided past answers](RESEARCH.md#improve-the-questions-not-only-the-code).
Not established: that a test's criteria transfer across classes — the same
test's durability drum is specified for satchels, not backpacks — or that the
retailer "tests" dominating search results are usable sources.

**2026-09-17 — One conversational trial run end to end (school backpack).**
The unsupported-category conversation recorded above continued through a
buyer's six messages to a saved, audited, delivered outcome, within one
provider and with the agent as reviewer. Measured: seven plan revisions, each
read back with its response recorded (five corrections, no confirmation);
five crawls in the session ledger, 285 of 400 responses; a category built as
reviewed maintenance mid-study; four study bundles, of which the first three
withheld the recommendation on a decisive requirement without a control and
the fourth, after the buyer settled that requirement outside the study,
delivered a no-decisive-winner shortlist as permitted current advice with
`validate-report --require-review` valid. Two harness defects surfaced and
were fixed with regression tests: a plan-check column overflow, and a stale
delivery review blocking its own replacement. The first Done-when bullet is
met once, by a user who wrote the documentation. Not established: a reader
who had not; an independent reviewer; a second provider.

**2026-09-18 — Second conversational trial (school backpack, a reader who had
not read the documentation).** A buyer referred by the maintainer, using the
maintainer's account, opened with one sentence naming the product class and
the marketplace and nothing else; the operating agent had read AGENTS, the
runbook and the capability index, and the buyer had read none of it. Measured:
three user messages; three plan revisions, each read back — revision 1
corrected by the buyer's answers, revision 2 **confirmed** (the first confirmed
read-back on record), revision 3 recording the answers with no response; one
batched round of four questions, then one of three; zero marketplace requests,
because the shelf retained on 2026-09-17 was reused (192 listings, 94 in
class) and the buyer accepted day-old prices; two bundles under a session
ledger with a zero engineering allowance, both **bounded**: the recommendation
withheld on four decisive requirements without a control — a budget on the
delivered price, a rating-and-count threshold, reliability as an objective, fit
for 130 cm — and the weight ranking delivered as a bounded finding with each
condition read by a person and attributed as such (23 rows ranked, 13 above the
budget, two under the rating threshold, eight surviving both, three of those
stating a height range that includes 130 cm). Intake review, semantic review
and delivery review pass; `validate-report` is invalid on `current_advice_blocked`
alone; `verify` is clean; `resume` reads the state from the files. The decision
artifacts of the two bundles are byte-identical except the plan digest inside
`ranking.json`. The written result is in the buyer's language under
`reports/`, gitignored like the bundles.

The questions, reviewed at close against the uncertainty and expected effect
recorded when they were asked, as
[the runbook requires](RESEARCH.md#improve-the-questions-not-only-the-code):

| Question | What depended on the answer | Verdict |
|---|---|---|
| Amazon.de with delivery in Germany? | Nothing changed: the default was accepted, and it is the only default that leads anywhere | Asked because the blocking list says so; two trials, two German-context confirmations; not enough to remove it |
| Grade and height? | Load-bearing: settled the product class (fifth grade → secondary-school backpack) and supplied the number every fit reading used | Keep |
| What orders the shelf, and is there a budget? | Load-bearing: the no-cap default became a hard budget, and the buyer volunteered the rating threshold nobody asked for — the requirement behind the software gap below | Keep; the ordering half went unanswered and the agent's axis stayed an assumption |
| Must the listing state reflective elements? | Confirmed as a must; enforced; filtered 49 of 94 in-class listings | Second buyer to confirm the test-derived candidate criterion; keep |
| Round two: proxies, fit settlement, design | All three defaults accepted; one round trip, no decision moved | Across both trials a stated warranty as a reading rather than a filter (u5 of the first, u3 of the second) and the design as the child's choice (both) were accepted every time: candidates for stated defaults in a school-backpack brief. Fit was settled by the first buyer and left open by the second: stays a question |

Graded against [INTAKE §14](INTAKE.md#14-worked-cases-and-acceptance-gates)
after the fact: cases 2, 3, 5, 7, 8 and 12 were exercised and the behaviour
stayed inside the acceptable boundaries — the budget was never routed onto the
weight cap, the agent's axis is recorded as its own and non-decisive, the
threshold without a control withheld selection and removed nobody by hand. No
expectation for this buyer was written before the conversation, so this is a
grading against the generic boundaries, not the independently stated
expectation §12 asks for; that is what the third trial is for.

**The third bundle, the same day, after the control landed** (the R15 entry
has the change): plan revision 4 maps the budget to a bound on `price` (EUR,
at most 100) and the rating threshold to bounds on `review_rating` (at least
4 stars) and `review_count` (at least 50), nothing else moving. Of the 45
in-class listings stating reflectors, 24 fall outside a bound — 18 list above
100 EUR, one averages 3.9 stars, five have no trusted average to check (two
Satch Pack colours under 100 EUR whose histogram disputes the published 4.4,
two listings rated by 19 and 6 buyers, one unrated); the count floor removed
nobody on its own. 13 of the remaining 21 keep no usable weight and **8 rank:
the same eight a person had read by hand in the first two bundles, in the same
order**, the three Baagl rows on top. The recommendation stays withheld on
`reliability` and `fit`, as the buyer accepted; intake, semantic and delivery
reviews pass, `verify` is clean. Stricter than asked, and said so: a bound
admits only trusted values, so a listing whose average the histogram disputes
leaves as unassessable rather than passing on the published number.

Observations for the tooling, logged and not adopted (the improvement cycle's
first step): (1) the report's attribution sentence reads the *current*
revision's response status, so a confirmed read-back followed by a revision
that only records the answers renders as "no response" — as it did at revision
7 of the first trial; the confirmation survives in the retained message and
the question answers, not in the sentence. (2) `session-record --result`
takes JSON and fails a prose result with a bare JSON error. (3) **The software
gap**: a purchase budget or a rating threshold has no control because the one
cap binds the ordering axis, which is [INTAKE §4](INTAKE.md#4-current-capability-boundaries)'s
case 7 met by a second buyer on a category that *does* publish a price axis;
the proposal retained in the ledger as `engineer-1` is a bound on any rankable
axis at candidate assessment plus rating and rating-count axes on
`school_backpack`. The maintainer asked for it to be built next, ahead of R15's general gates,
as reviewed maintenance; it landed the same day and is recorded under
[R15](#r15--controlled-task-driven-capability-adaptation) as its first
control case.
**2026-09-18 — Third conversational trial (smartwatch with a scuba dive
computer and NFC payment; unsupported category; graded against a record written
before the first message).** A buyer referred by the maintainer, using the
maintainer's account, first asked whether to disclose the product he had
already chosen; the agent asked him to record intent, requirements, the chosen
product and acceptable outcomes outside the conversation before his request,
and to withhold the choice. The request then named the class, three sports, an
annual two-week scuba trip to 30 m the watch should cover instead of a separate
dive computer, and NFC payment; it named no phone, marketplace, budget, ordering
criterion or definition of "stylish". Measured: four user messages; four plan
revisions, each read back — revision 1 corrected by the answers, revision 2
recording them, revision 3 adding 26 cited sources, revision 4 recording the
grading; one round of five questions, no second round; the plan `blocked` on
one decisive unresolved requirement (the phone platform) until answered, then
`bounded` on six requirements without a control; three probes under a session
ledger with a zero engineering allowance — two class queries (22 responses),
five named-model queries (35), seven ASIN fetches (7) — 64 responses, 57 product
pages, no challenges; no study bundle, because no category exists, so the
comparison was a person's reading of listings and manufacturer manuals,
attributed as such, with the recommendation withheld and a conditional reading
delivered under each of the buyer's two ordering criteria. The written result is
in the buyer's language under `reports/`, gitignored like the plans and ledger;
the engineering proposal (a `smartwatch` task-experiment category) is retained
in the ledger unfunded.

Class queries surfaced three dive-capable smartwatches (Suunto Ocean, Suunto
Nautic S, Garmin Descent G2); the Garmin Descent Mk3, fenix 8/9 and Huawei
Watch Ultimate candidates were supplied by the agent from manufacturer
documentation and confirmed on the shelf by name, recorded in the ledger as
agent-supplied candidates (selection bias) with no criterion moved. Two
candidates were excluded on manufacturer evidence of absence (no payment
feature anywhere in Suunto's documentation), one on incompatibility (Apple
Watch, iPhone only). Two facts decided more than any listing: every
manufacturer disclaims use as a sole dive computer, and Huawei's NFC payment in
Germany runs through a third-party wallet since 2026-03, sourced from an
enthusiast blog and marked so.

**Graded by the buyer (u4).** Every candidate in the report was on his private
shortlist. He chose the Huawei Watch Ultimate 2 on style with a suit and sensor
richness — fourth under his stated "battery, then display" ordering, first under
display-first. In a second message (u5) he said style had been a **pre-filter**,
ahead of both ordering criteria: the agent had proposed style as a reading that
excludes nobody, the buyer answered "with a suit" without objecting, and the
agent recorded a stated preference — silence on a default read as wider
agreement than it was. Applied to the delivered table the filter removes one
candidate (the polymer-cased Descent G2) and leaves the ordering. He added a
criterion the plan never carried: reliability, proxied by the maximum stated
depth rating, which he expects to be assumed important unless a buyer excludes
it — then withdrew the proxy himself: depth rating is a proxy for water and dust
ingress protection, a durability property, not for reliability. Recorded in
revisions 4 and 5; the depth ratings were already in the table and were not
read that way because nobody had named durability. The second trial's buyer had
named reliability unprompted and it went unsupported there too.

The questions, reviewed at close against the uncertainty and expected effect
recorded when asked:

| Question | What depended on the answer | Verdict |
|---|---|---|
| Amazon.de with delivery in Germany? | Nothing changed; payment-service availability depends on the country | Third German-context confirmation in a row; keep until repeated evidence says otherwise |
| iPhone or Android? | Load-bearing: excluded Apple Watch Ultra 3, which the searches returned four times, and fixed the candidate payment services | Keep; it was the one blocking question |
| Primary dive computer or backup gauge; certification? | Load-bearing: set the reading of the dive requirement and the evidence bar (manufacturer documentation, never a water-resistance rating) | Keep |
| What does "stylish" mean? | "With a suit" became a reading shown per candidate and filtered nobody; the buyer later said it had been his pre-filter and decided his choice | Keep, and ask the missing half: when a buyer names a quality no field carries, is it a condition or a reading? The stated default was not enough |
| Budget, and what orders the survivors? | "No budget" removed the price question; "battery and display" replaced price as the ordering and shaped the table, yet did not predict the choice | Keep; the runbook's absent-budget default was confirmed by being overridden |

Observations, logged and not adopted: (1) a reliability proxy was expected by
this buyer by default and named by the previous one unprompted — a candidate
default question for unsupported-category intakes, whose proxies (depth rating,
warranty, materials) are each contestable and none of which the harness can
assess; (2) the ordering question's answer and the actual decision diverged,
which the report's dual-ordering presentation happened to cover; (3) tooling:
`sources[].id` must be a lowercase slug, `garmin.com` and `suunto.com` are
refused by the built-in browser while Garmin's static manual pages read fine,
and a PDF manual cannot be read on this machine without poppler.

**2026-09-18 — The third trial's plan under independent intake review:
fail.** A second agent (Codex, GPT-6), given AGENTS, the runbook's review
section, CONTRACT §13, INTAKE §11/§12/§14, the buyer's five retained messages
and his private pre-trial record, wrote its own intent oracle before opening
the plan's requirements and then graded revision 5. Result, bound to the
revision's digest by `plan-review`: adequacy **pass** (every `unsupported`
disposition is a genuine absence of an executable method, no other category
substituted, nothing falsely marked enforced); omissions **limited** (the
plan's own missing-context limit forbids a pass); faithfulness, assumptions and
stage effects **fail**. The failures share one shape, and it is INTAKE §4's
case 7 in a softer form — an assessable proxy substituted for the condition the
buyer stated: sensor *presence* (GPS, optical heart rate, barometer) recorded as
the buyer's hard constraint while measurement *quality*, which he stated and
his private record makes an exclusion condition, was filed as a non-decisive
preference because nothing in the harness can assess it; a 40 m depth margin
recorded as if stated when the buyer said 30 m; suit-wearability first recorded
as a reading the buyer had "stated" after he did not object to that default,
then in revision 5 turned into a filter that removed one candidate on case
material the buyer never named; delivery in Germany recorded as confirmed when
only Amazon.de was; the display criterion given no comparison-stage effect
while the report excluded the MIP-display variant as if it were a condition;
the payment effect dropping "usable in Germany". The report's heading
"candidates that passed every hard condition" therefore overclaims, although
its limits section says quality was not assessed and the comparison is a
person's reading. The buyer's own grading (every candidate on his shortlist,
his chosen model among them) had not surfaced any of this: outcome feedback
graded the search, the review graded the reading. That is the separation
INTAKE §11 asked for, observed once. The reviewer changed nothing; the review
and its oracle are retained beside the plan revisions under `data/plans/`.

**2026-09-18 — The repair and two more reviews.** Revision 6 answered the
failed review's findings: measurement quality became the buyer's decisive hard
constraint on an evidence path with nobody admitted as meeting it; sensor
presence, the 40 m margin and the no-filter style reading were relabelled as
the agent's hypotheses; the style pre-filter kept no per-candidate verdict;
Germany became an assumption; payment gained "usable in Germany"; the report
dropped its "passed every hard condition" heading and put the Solar and G2 rows
back. The same reviewer, reusing its oracle, **failed revision 6 again** on
three items that were all new in the repair: a "within about a fifth" runtime
threshold under which the display could outweigh the battery, invented by the
agent; candidates whose manufacturers state runtime on different scales given
places in one order; Huawei carried under a "documented payment" heading on a
blog's word. Revision 7 removed the threshold (display decides only equal
runtime on one manufacturer's scale), listed other-scale candidates unranked
with their mode named, and required manufacturer or payment-service
documentation for payment, so both Huawei models moved to a "payment not
resolved" block. The third review passed faithfulness, adequacy, assumptions
and stage effects, confirmed that none of the nine earlier repairs had
regressed, and recorded three editorial contradictions in the report, fixed
afterwards without touching the plan; omissions stayed `limited` because the
plan declares the maintainer's conversation with the buyer as missing context,
and CONTRACT §13 refuses a pass over a declared limit. Measured across the
chain: seven plan revisions, three reviews bound to three digests, nine
findings answered, three new ones introduced by the first repair and answered
by the second. The reviewer's closing characterisation is the one the report
now carries: a bounded study with insufficient evidence, a permitted conditional
outcome, not a finished purchase recommendation and not an audited approval.
Two lessons for the operating agent, both about the repair rather than the
intake: a repair is a new revision and gets the same review, because it can
add misreadings as easily as remove them; and once a review or a ledger has
bound a revision's digest, that revision is not edited again — supersession is
recorded in the next revision, or the binding reads as superseded (hit once,
reverted).

**2026-09-18 — Defaults decided after three trials.** Four decisions, all
about questions and stated defaults, none about code; the runbook's
[agree-the-brief](RESEARCH.md#agree-the-brief) section carries the operating
text. (1) `school_backpack`: a stated warranty is a reading, not a filter, and
the design is the child's choice — stated assumptions in the plan and brief,
accepted by both buyers, never a category fact; fit stays a question. (2) A
quality no field carries is asked about as **condition or reading** in the same
round; the third buyer's pre-filter had been recorded as a reading after he did
not object to that default. (3) **Durability** is raised as one agent-authored
candidate question for durable goods, where the class is expected to serve for
years or a failure costs real money or time, and not for consumables; the
distinction is the agent's reading of expected service life and failure cost,
recorded as a hypothesis, and the buyer's proxy enters the plan as theirs.
Rejected: a reliability default for every category, and any agent-chosen proxy
presented as a fact. A registry-level distinction between durable and
consumable classes is not built; if the reading repeats across trials it is a
candidate for the R16 index. (4) The **marketplace** is stated in the read-back
as a default with its if-wrong consequence and no longer asked as a separate
question; three buyers confirmed it unchanged, and a correction still stops the
study. Measured effect: none yet — the next trial's question count and close
are where these are graded.

### Scope

Make the existing coding-agent conversation the tested product entry point.
The user describes a purchase; the agent inspects capabilities and evidence,
asks one useful batch of questions where possible, records assumptions and
produces a brief. Further questions are justified only by a newly material gap.
There is no separate frontend or provider-specific orchestration requirement.

Before collecting, map each decisive requirement to its sufficient evidence:
which characteristic, acceptable source class, identity/variant applicability,
freshness, comparison method, and what happens if the evidence is missing.
Use the T3 ledger for acquired evidence; a source plan is not verified evidence.

Compare this plan with the actual harness. Record whether each gap needs a
source, fresh acquisition, parser/adapter, category interpretation, comparison
method or user decision. First reuse existing capability. For remaining gaps,
record the narrowest change, expected decision value, validation cases and
finite research/engineering limits, then hand off to R15. Unknown evidence
availability is a reason for a bounded probe, not automatic software work.

The current executable brief requires a known category and input feeds. Start
with a retained intake/evidence plan before those exist, then bind it to the
validated brief once the capability and inputs are ready. Do not bypass the
brief's registry or introduce arbitrary import paths. Any new persisted shape
needs a tested contract before becoming part of the executable workflow.

[INTAKE.md](INTAKE.md) is the pre-implementation assessment for this milestone:
requirement semantics, stage effects, conclusion rendering, the two identities,
review phases, retention and the worked cases. It is a design assessment, not an
adopted contract — implementing any of it is separate work under the maintenance
workflow.

### Done when

- A user who has read no project documentation can initiate a supported study
  in the coding interface and receive a saved, auditable outcome.
- An unsupported problem produces a useful evidence/gap plan without asking
  the user to select a module or understand implementation details.
- Questions/defaults and subsequent material revisions persist. A question
  records the uncertainty it resolves and its expected effect when it is asked,
  and the close reviews observables against that record rather than inferring
  necessity from the outcome; questions that repeated evidence shows add no
  material value are removed.
- The plan distinguishes software gaps from unavailable evidence and has a
  stopping rule for each. The final report explains decision-relevant limits.

---

## R14 — A recommendation in a category nobody validated

**Status: PLANNED. Depends on R11, R12, R13, R15 and R16's minimum lifecycle,
on top of T4's shipped maintenance gate. Does not depend on R10.**

### Scope

This is the acceptance milestone for the operating model. Start from a purchase
problem not used to design the existing categories, requiring a new extraction
technique and a different comparison method. Use R13's plan and R15's bounded
adaptation to complete the research, then exercise reuse in a distinct request.

Select the simplest defensible method: requirements and one declared axis,
explicit tradeoffs, or a local multi-criteria method if the brief requires it.
A scalar score is optional. If weights or missing-data conventions are used,
state their origin, show components and test sensitivity. Neutral imputation
and shrinkage are basmati choices, not universal laws; missing evidence for a
hard requirement must remain missing regardless of any score.

### Done when

- One unseen-problem study yields an evidence-backed recommendation or
  conditional comparison, with applicable support and a replayable method.
- A separate case lacking decisive evidence returns insufficient evidence;
  failed adaptation is distinguished from evidence absence and exercises rollback.
- A later distinct brief discovers and reuses or narrowly adapts the capability,
  recording what transferred and what did not. No redesign is required; shared
  contract changes, if needed, are small, justified and versioned.
- Old studies have zero unexplained decision changes. R16 records retention or
  promotion based on actual reuse, not the fact that code was generated twice.
- The trial records the measures in the product vision. Repeating research,
  scoped repair and artifact handoff across both provider environments is
  [deferred to R17](#r17--portability-evidence) and is required only before
  claiming provider interchangeability, not before R14 itself.

---

## R15 — Controlled task-driven capability adaptation

**Status: IN PROGRESS. Phase 0 — the procedure — Phase 1 — the first
category written through it, `smartwatch` — Phase 2 — the first study resting
on it, committed as the gate's eighth example — and Phase 3 — the second
adaptation, the dive claim repaired as method version 2 with the first record
as its predecessor — shipped on 2026-09-18 and are recorded below. T4's local
maintenance gate is the baseline R15 validates against; the provider and
platform trials deferred from T4 are not a dependency. Still open: the
extraction case decided by inspection, a plan revision 8 with a fresh intake
review if the maintainer wants the category's controls mapped, the
source-embedded-instruction and `harness-only` cases, and a faulty patch
withdrawn on a real regression.**

**2026-09-18 — Phase 5: the fourth adaptation, the payment claim repaired
on the independent reviewer's finding.** Plan revision 8 — the classifier
mapped to `classification` and three agent-authored listing filters on the
dive, payment and Android claims — went to the independent intake reviewer
and **failed** on faithfulness, adequacy and assumptions: a function being
necessary does not make its mention in this Amazon listing necessary, and the
filters excluded silence before manufacturer evidence could inform selection
(the Descent Mk3 and Mk3i fell to the Android filter, the fenix 8 to an alt
text the search does not read). The maintainer decided: revision 9 drops all
three filters and keeps the classifier — a longer table is a presentation
defect, not grounds to declare a further constraint necessary — and the one
finding that named a category defect goes through the procedure. That
finding (A8.1): the `nfc_payment` pattern was a disjunction that included a
bare "NFC" and a bare "Wallet", so a connectivity row "Bluetooth, GPS, NFC"
was credited as a payment statement, against the claim's own `why`.

Funded as `engineer-5` (3 600 s, 3 attempts) and opened as record
`nfc-payment-claim`, layer `category`, origin plan revision 7, predecessor
the third record. The patch, three files from base `703be57`: the pattern
reads a payment service or a contactless-payment phrase (Garmin, Huawei,
Apple, Samsung Pay, Google Pay or Wallet, a vendor's wallet, "kontaktlos
bezahlen", "NFC-Zahlung"), `method_version` 3 with the reason beside it, two
tests and the cases README rows. **Three attempts, all spent, all on the
record.** Each was the full gate inside the kernel boundary. The first two
failed on the declared move and on the new real-card test: the hypothesis,
read from the revision-8 study's first quote per card, filed the Amazfit
Active Max under the bare word, but its bullet says "Mit Zepp Pay und NFC
bezahlst du" and the narrowed pattern rightly keeps it — five listings rest
on NFC alone, not six, all Huawei. The pins were corrected between checks
and nothing in the code moved. The third check failed on exactly the declared
move and nothing else: `capability_lifecycle_changed` for `method_version` 3
and the five baseline-pinning tests; 902 tests in 30 modules, 9 of 9 examples
with their recorded decisions. Review, adoption on the maintainer's decision,
rollback demonstrated, the ledger accounted 85.3 s. The budget of three
attempts was exhausted by the third; had it failed, the record would have
closed as `interrupted` with the patch on file.

**Measured.** On the 39 cards of the re-extracted study, `nfc_payment` moves
on five and on no other: both Huawei Watch Ultimate 2 listings, both GT 7
Pro and the Watch D3 lose it, fifteen keep it — among them the Amazfit on its
payment sentence, the Descent G2, Mk3 and Mk3i, the fenix 8 sizes and the
Instinct 3 on "Garmin Pay", the fenix 9 on its own comparison-table cell. No
other claim, no axis, no ranking row and no outcome moved. The ninth gate
example rebinds to the fourth record: `smartwatch-dive-nfc-reextracted-d83a15c291ca`
where the same brief under method version 2 was `…-92117d8f7fef`; the third
record stays committed as its predecessor. Baseline diff: `method_version`
2 → 3, the example's adaptation and id, the floor 900 → 902. Revision 9 of
the plan, over the as-crawled feeds with the classifier alone, gives 39 of 55
and the same 35 priced offers as revision 7; it waits for its own independent
review against the live catalogue, which this adaptation moved.

**Not established, and not claimed.** That a payment service named on the
page works with the buyer's card in Germany — the claim is the vendor's
sentence, as before. That the five Huawei listings lack payment: Huawei's
own documentation is not the page, and `not_claimed` says so. The `harness-only`
path and the source-embedded-instruction case remain open; the count of
extension-bearing studies stands at two.

**2026-09-18 — Phase 4: the extraction case, decided by inspection and
run through the procedure.** The plan's second Done-when case had to change
extraction or evidence acquisition, and the plan said it would be built only
if a bounded inspection of the retained pages found a defect the category
could not fix by itself. The inspection was funded as `engineer-3` (2 700 s
declared, no marketplace request) and read the three run stores behind the
57 committed records. What it found was not the hypothesis it started from.
The runtime sentences are retained and searchable — the category already
reads "bis zu 10 Tage im Smartwatch-Modus" from a description — but **16 of
the 55 product pages carry an A+ comparison table** (`premium-module-5`), one
product per column, and the extractor flattened every cell into
`content.aplus.text`, which the vendor-text search reads as this product's
statement. The page's own product is not always a column and not the first
when it is: the first column carries `active`, which is the scroller's state,
and only the ASIN a header links identifies a column (10 of 16 tables link the
page's own). On the Instinct 3 50 mm AMOLED page the table compares five
*other* Instincts, and the card showed a 40 h GPS runtime that belongs to the
45 mm. On the fenix 9 page the `nfc_payment` claim rested on the row label
"Garmin Pay" in the flattened text, not on the fenix 9's own cell. That is a
property of the page any category faces, lost by the current path, and it
changes what a card can say: the layer test answered *extraction*.

Funded as `engineer-4` (3 600 s, 4 attempts) and opened as record
`aplus-comparison`, layer `extraction`, origin plan revision 7. The patch,
captured whole from a worktree at base `3e8dc56`: `content.aplus.prose`, the
A+ copy without table cells, and `content.aplus.comparison`, each comparison
table as columns with the ASIN their headers link, its rows, and
`self_column` — the own column by exact ASIN or `null`, never by position,
because Amazon's variation families put different models in one family and a
sibling's column is another product's. The vendor-text search reads `prose`
where a record has it and the own column's rows as labelled statements
("Akkulaufzeit GPS-Modus: Bis zu 47 Stunden"), skipping a cell that is a
cross or a dash; a record without the keys reads exactly as before. `text`
and `tables` are unchanged, so the change is additive within schema v6. The
corpus updater gained `--output DIR` so that snapshots can be regenerated
inside a boundary whose one writable directory is never the tree. Ten files,
patch digest `7f7ca546f535`, method descriptor `e498a14eb525`; the evaluator
set byte-identical to the base; the boundary probe demonstrated all six
refusals.

**Three attempts, all on the record.** Check 0 regenerated the corpus
snapshots inside the kernel boundary (2.3 s, exit 0): the 38 + 1 expected
records gained `prose` and, on the six pages with A+ tables, `comparison`, and
no key changed or disappeared; the validated snapshots came back byte-for-byte
the base's and were left out of the patch. Check 1, the full gate, failed on
one test: the new fixture named eleven-character ASINs and the extractor,
correctly, read ten — a fixture defect, corrected without touching the code,
and the first check the procedure has withdrawn for a genuine test failure
rather than a declared move or a runner fault. Check 2 was the full gate at
exit 0 inside the boundary in 25.6 s: 900 tests in 30 modules against the
floor of 890, 8 of 8 examples with their recorded decisions, every contract
version unchanged. Review, adoption on the maintainer's decision of the same
day (the second case is the runtime bound to its mode as a stated value, once
the page inspection confirms the layer; one to three redacted pages may enter
the corpus), the rollback demonstrated, then the ledger accounted 53.1 s.

**Measured.** The three runs were re-extracted offline from their retained
pages under the adopted code — the same bytes, no request — into the `-v2`
evidence feeds: 56 records, because one page of the named run
(`B0H8P8FT5Q`, a strap) no longer matches the digest its run recorded and
the replay refused it. On the 39 cards, ten values moved and no decision: the
Instinct 3 50 mm's GPS runtime (40 h) and the Instinct 2X Solar Tactical's
four A+-sourced values (145 h, 21 days, 10 ATM, "E-ink") became `unknown`,
because neither page's table links the page's own ASIN — the Tactical's links
the plain Instinct 2X Solar, a different product; the fenix 8 in three sizes
and the Instinct 3 Solar keep 47, 84, 28 and 40 h, now read from their own
column with the mode in the field name; the fenix 9's `nfc_payment`, the
fenix 8 43 mm's and the Instinct 3 Solar's rest on their own "Garmin Pay ✔"
cell, and two more claims gained an own-column source beside the one they
had. The study over the v2 feeds, `analyse-5`, is the gate's **ninth
example**, `smartwatch-dive-nfc-reextracted-92117d8f7fef`: 39 of 54
classified, 35 priced offers, 3 unpriced, 1 folded, the recommendation
withheld on the same six conditions and the price order unchanged. Two of the
retained pages entered the corpus under its rules — the Instinct 3 50 mm,
whose table does not contain it, and the fenix 9, whose own column is the
third — bringing it to 40 Amazon.de pages; the 38 earlier records are
unchanged to the byte. Baseline diff: the example row and the test floor 890
→ 900; nothing else moved, and the eight earlier ids are unchanged.

**Not established, and not claimed.** That a runtime read from the own
column is comparable to another vendor's: the field carries the vendor's
mode label and ranks nothing, as before. Image alt text is still not read:
the fenix 8's "Tauchfunktion" stays where Phase 3 left it, and reading A+
captions is a separate hypothesis, because the same `images` list holds the
brand carousel's other products. A comparison table whose header links a
sibling ASIN is not read, by design, and the Tactical's four lost values are
the price of that. The re-extraction's one refused page is a finding about
the page store, not about the page. With this, both cases of the first
Done-when bullet have completed the loop; the faulty-patch case is covered by
a test-fixture withdrawal, not yet by a regression in product behaviour; the
`harness-only` path and the source-embedded-instruction case remain open. The
three adaptations have consumed 101 s of runner time and 2 700 s of declared
inspection against the 14 400 s engineering allowance.

**2026-09-18 — Phase 3: the second adaptation, the dive claim repaired
through the procedure.** The gap is Phase 2's finding: the category's
`scuba_dive_mode` pattern read "tauchfähig bis 40m" (a water-resistance
sentence, which plan revision 7's `dive_computer` says never satisfies it),
"Tauchgänge", "Freitauchen" and "Apnoe" as a stated dive function, and
credited a 178 EUR KOSPET Tank T4 with one. Funded as `engineer-2` (3 600 s
against the same engineering limit, authorised through `session-authorise`)
and opened as record `smartwatch-dive-claim` — origin plan revision 7 and
that action, **predecessor the first record** (`kind: adaptation`, its
canonical digest), the first use of that link. The patch, captured whole from a
worktree at base `f45879d`: the pattern narrowed to a stated scuba function (a
dive mode, function or technology, a dive computer, scuba, nitrox, a
decompression model), its `why` rewritten, `method_version` 2 with the reason
beside it, one new unit test and the pinned dive claims restated in the
category tests, and the cases README rows — three files, digest
`d2eaafa9c8cd`, method descriptor `7f39fb9959f9`. Static inspection flagged
the module-level declarations and one pre-existing write; the evaluator set
was byte-identical to the base; the boundary probe demonstrated all six
refusals and the scratch write.

**Two attempts, both on the record.** The first check exited 71 in 0.019 s
without importing anything: the CLI's default `--venv .venv` was resolved
against the worktree, which holds no virtual environment, and `sandbox-exec`
could not exec the interpreter. It counted as an attempt, as the record's
rule says a finished check does, and the boundary was then re-probed with the
locked environment named by absolute path. The second check — the full gate
inside the kernel boundary, 25.1 s — failed on exactly the declared move and
nothing else: `capability_lifecycle_changed` for `method_version` 2 against
the baseline's 1, and the five baseline-pinning tests in `test_maintenance`;
889 tests in 30 modules, 5 failed, 0 errored, 8 of 8 examples replaying with
their recorded decisions under the patched tree, the smartwatch study
included. The review read that output and passed; adoption was recorded by
the maintainer's role on the maintainer's instruction; the rollback was
demonstrated **before** the ledger accounted for the attempt, in the order the
runbook now prescribes, and `engineer-2` completed at 25.1 s from the record.
The CLI defect went through ordinary maintenance in the same change, outside
the trial: `adaptation-probe` and `adaptation-run` resolve the environment
and the interpreter where the command was typed, with a regression test.

**Measured.** On the 55 committed records the claim moves on five and on no
other: the fenix 8 in three sizes, the fenix 8 Pro and the KOSPET lose it,
fifteen keep it — the Suunto Ocean in three colours, the Descent G1, G2, Mk3
and Mk3i, the Huawei Watch Ultimate (on "Bühlmann ZHL-16C
Dekompressionsalgorithmus") and Ultimate 2 (on "Tauchtechnologie"). The
fenix 8's A+ image alt text does say "Tauchfunktion", and the search does
not read image alt text: Garmin's manual documents the dive apps, and a manual
is not the page. The study of Phase 2, re-derived under the new method as
`analyse-4`, is `smartwatch-dive-nfc-8f62da3c1256` where the same brief over
the same bytes under method version 1 was `smartwatch-dive-nfc-2d5b51c7d0d9`:
39 of 55 classified, 35 priced offers, 3 unpriced, 1 folded, the
recommendation withheld and the price order kept — every decision unchanged
and the id moved, because the method did. The eighth gate example now binds
the second record and the first stays committed as its predecessor, named by
digest. Baseline diff: `smartwatch` `method_version` 1 → 2, the example's
adaptation and id, and the test floor 888 → 890 (one test in the category,
one for the CLI); nothing else moved, and the seven earlier ids are unchanged.

**Not established, and not claimed.** That the fifteen positives *are* scuba
computers: the claim is the vendor's sentence, and whether the watch may
replace a dive computer on a real dive is on no page. The faulty-patch
Done-when case is still not covered by a withdrawal: the first attempt here
was a runner defect, not a regression, and the second passed; a patch
withdrawn on a real regression remains to be recorded. The two adaptations
have consumed 47.9 s of the 14 400 s engineering allowance. The extraction case (Phase 3 of
the plan as written) is still undecided by inspection and is not this entry.

**2026-09-18 — Phase 2: the study revision over the trial's plan, and what
the category's table says next to the hand-read one.** The third trial's plan
revision 7 (`1d3e02631869`), committed as it is by the maintainer's decision,
was bound to a brief over the three retained probe feeds (`plan-bind` refused
the first draft until the brief carried the plan's question and use case
verbatim) and run on the `smartwatch` category through its accepted adaptation
record (descriptor `e184aad39bab`) and the v2 ledger that funded it, under a
new analysis action `analyse-3` (600 s allocated, 407 s declared). The study is
`smartwatch-dive-nfc-2d5b51c7d0d9`: 57 records merged to 55 (two ASINs in two
feeds), 39 classified `smartwatch` and 16 `other` with the reason, 35 offers
ranked on `price`, 3 unpriced listings excluded, 1 folded, 0 shortlisted; stop
`requirement_unsupported` on six decisive requirements and `data_quality`
awaiting evidence, the recommendation withheld, and the price order kept as the
bounded finding. It verifies, delivers as a historical comparison at a fixed
reference and resumes from its own ledger snapshot. Brief, plan, ledger and
record are committed under [tests/intake](tests/intake/README.md) and replay as
the gate's **eighth example**, with the seven earlier ids unchanged.

**What the plan's own words do to the report.** Revision 7 maps no control
to any requirement — it was written when no category existed — so the brief
could declare no required claim and no explicit axis (`plan-bind` refuses a
filter the plan does not carry), the price order is the *category default*
on a plan whose `price_shown` says price ranks nobody, and the report's
withholding paragraph quotes gap reasons that begin "No smartwatch category
is registered" while the same report rests on one. That is what "revision 7
as it is" costs, and it is stated in the brief's limits rather than hidden.
The plan's intake review could not be attached at all: `run --intake-review`
refuses it because its basis recorded no control catalogue and the live
`smartwatch` catalogue is `015add66fb87`, so its adequacy was judged against
other controls. The study is therefore plan-backed and unreviewed, and
`validate-report --require-review` is not claimed for it. Mapping the
category's controls onto `watch_class`, `dive_computer`, `nfc_payments` and
`phone_platform` is a plan revision 8 with a fresh independent review; a
review template bound to the live catalogue was written privately for that.

**The category's table against the hand-read one (`analyse-2`).** Same
outcome where the page states what the manual stated: the Descent G2 (two
listings, 587.74 and 649.97 EUR, dive, NFC and Android all stated), the
fenix 8 (47 mm at 635.99), the Descent Mk3i 51 mm (1441.35 and 1647.27 with
all three; 1852.99 without NFC on its page), the Mk3i 43 mm bronze at 1598
(dive and NFC, Android unstated), the Mk3 43 mm steel unpriced, the Huawei
Watch Ultimate 2 (799 twice with NFC stated, 899 in green without), the
Ultimate at 544.78 (dive stated, NFC not — the hand table's "payment not
resolved" reached from the page side), the Suunto Ocean (dive stated, no NFC,
which is why the hand table excluded it), the Apple Watch Ultra 3 (Android
not stated), and the Suunto Nautic S declined by its title where the hand
table excluded it for having no optical sensor and no payment. Requiring the
three page claims together — outside the study, through the analysis CLI —
admits 8 of the 39 (7 priced): the hand table's block A without its two
manual-only rows and without the bronze Mk3i, plus the Ultimate 2. Eight
differences, each explained:

| Difference | Explanation |
|---|---|
| fenix 8 Solar 51 mm (985.20) and fenix 9 51 mm (1079) are in the hand table's unranked block and state no dive function, no NFC (Solar) and no Android (fenix 9) on their pages | The hand table read Garmin's manuals and a press release, which are the plan's sources; the category reads the listing. Evidence source, not error |
| The 1014 EUR end of the hand table's fenix 8 range (`B0DFLYZ28M`) is `other` | Its title names no class; the classifier's declared limit from Phase 1 |
| The fenix 8 51 mm (732.26) is folded into the 47 mm listing as "another pack size" | Generic offer grouping treats case size as pack size; the fold hides a runtime the hand table kept apart (47 h against 84 h GPS). Not the category's decision and not one it can opt out of: `offer_grouping` is not optional. A generic gap, recorded |
| The hand table filed 636 EUR under "fenix 8 43 mm, variant" | The listing priced at 635.99 is titled 47 mm; the 43 mm Steinweiss listing carries no price. The record decides |
| KOSPET Tank T4 (178.49) carries `scuba_dive_mode: trusted`; the hand table had no cheap watch with a dive mode | The claim's pattern admits "Freitauchen bis zu 45 Metern" (freediving under an IP69K sentence) and, on the fenix 8, "tauchfähig bis 40m" — a water-resistance statement, which the plan's `dive_computer` says never satisfies it. **A semantic defect in the category**, not pinned by its tests (the five positives are Suunto Ocean, G2, Ultimate 2, Mk3 and fenix 8). With the dive claim alone required, 20 of 39 are admitted and the KOSPET leads on price |
| Galaxy Watch Ultra2 (651, "not checked further" in the hand report) is nowhere in the study | It is in none of the 57 records; the words appear only in other listings' compatibility text. The hand report's row came from a search sighting, not a fetched page |
| Depth ratings: 200 m on two Ultimate 2 pages and 150 on the third, 100 m on the Suunto Ocean title where its manual says 60 m EN 13319, 100 m on the Apple | The axis reads the page's "Wasserdichte Tiefe" row or a title, which is water resistance, not a dive rating, and the vendor's own pages disagree. Another reason it is shown and ranked on by nobody |
| The hand table ordered its block A on GPS hours; the study orders on price | The plan gives runtime no control and the brief may not invent one; the study says beside the table that the order is the category's default and answers a narrower question than the buyer's |

**What the procedure found about itself.** The first real ledger digest
broke: `adaptation-rollback` writes its demonstration into the record after
`session-record` has digested it, so `resume` reported `engineer-1`'s manifest
as altered. The private ledger was re-pointed by hand at the record as it
stands (`9674533ae156` → `256fcf6bda72`, the only field changed) and the
runbook now demonstrates the rollback before it accounts for the attempt.
The committed ledger fixture points the three probes at their committed
manifests under `data/evidence` — the same bytes, the digests agree — and
`engineer-1` at the committed record, whose runner paths are the only fields
made repository-relative; its patch, checks, review and adoption are the
private record's byte for byte. The record is 751 KB, because the patch
archive carries the 55-record case feed; that is the price of an exact patch.

**Measured.** 888 tests in 30 modules unchanged, 8 of 8 examples with the
seven earlier ids unchanged, gate 30 s; the baseline diff is the eighth
example's row and nothing else; the plan-backed examples are three; the
extension-bearing study count under [R16](#r16--capability-lifecycle-and-architectural-review)
moves to two. **Not established, and not claimed.** That the category's
reading is right where it agrees with the hand table: both read the same
pages, and the manuals the hand table added are not in the study. Any
ordering on runtime. That a plan revision 8 would pass an independent review.
The next adaptation is named by this study, not assumed: the dive claim's
pattern, as method version 2 through the procedure with the KOSPET listing as
its counterexample, which is also the first chance to run the faulty-patch
Done-when case on a real regression.

**2026-09-18 — Phase 1: the first adaptation through the procedure, a
`smartwatch` task-experiment category.** The gap is the third R13 trial's
`engineer-1`, funded the same day by the maintainer's decision as ledger
revision 5 (session ledger v2, `1c511ecaebfc`, bound to plan revision 7): the
engineering allowance moved from 0 to 14 400 s, the action was authorised
through `session-authorise`, and the adaptation record `smartwatch-category`
(private under `data/adaptations/`, digest `fb9a5b1b5ca1`, method descriptor
`e184aad39bab`) was opened against it. The patch — 10 files, digest
`e6aeed0a6859`, captured whole from a clean worktree against base `37a922b` —
is the category module, its 55-record case feed and 30-test module, its
registration, the provisional-method status in the analysis result, the
ranking artifact and the report, and the documentation that names a fifth
category. Static inspection before any import flagged seven module-level
constructions (the declarations every category makes) and fifteen pre-existing
writes in the modified bundle module, nothing else; the evaluator set was
byte-identical to the base. One check ran inside the kernel boundary — the
full gate, 22.8 s — and failed on exactly the two moves the record had
declared at capture: `capability_untracked` for the new category and the
five tests in `test_maintenance` that pin the tree's capabilities to the
committed baseline; 888 tests in 30 modules, 5 failed, 0 errored, the six
committed studies replaying with their recorded decisions under the patched
tree. The review read that output and passed; adoption was recorded by the
maintainer's role; the ledger records `engineer-1` completed at 22.8 s from
the record; the patch was applied to the main checkout and the baseline
re-recorded there as the explained part of this change; rollback was
demonstrated against the untouched base worktree (tree and evaluator digests
equal to the record's, the gate green at the base).

**What the procedure changed on the way.** The first real patch found the
adoption rule of record v1 wrong for the case R15 exists for: the evaluator
set is frozen inside a trial and its own tests pin the tree to the baseline,
so a patch that *adds* a capability cannot pass the gate before adoption.
Record v2 (`baseline_moves`, [CONTRACT §15](CONTRACT.md#15-adaptation-record-v1-and-session-ledger-v2-r15-phase-0))
lets the patch say so in the same diff, and accepts a failing last check only
with the moves declared and a passing review; that change and two test
repairs went through ordinary maintenance *before* the trial captured its
base, so the procedure never judged its own change.

**What the category is.** A positional title classifier: an accessory noun
before the watch word or with a compatibility phrase, a band or tracker word
before it, or a dive computer that names no smartwatch function, each files
the listing as `other` with the reason; a title naming no class is accepted
from the Smartwatches node or from a body text that says so, as `unverified`.
Six vendor statements, named as the ledger named them — `gps`,
`heart_rate_sensor`, `barometric_altimeter`, `scuba_dive_mode`,
`nfc_payment`, `android_compatible` — each the vendor's sentence and none a
verified property; the dive claim reads a dive *function* and not the word
"Tauchen" in a list of sport apps or in "Schlafapnoe". `price` is the one
ranked axis; the stated depth rating in metres, the ATM rating, the GPS
runtime and the watch-mode runtime in the vendor's own mode, and the display
technology are shown and ranked on by nobody, because the trial's plan review
failed a runtime ranking across vendor scales twice. A report resting on this
or any `experiment` category now carries a **provisional-method paragraph**
beside its conclusion and a `method` entry in `ranking.json`, both absent for
a maintained category so that no committed byte moved — the debt the first
R16 review assigned here.

**Measured.** On the 55 unique records: 37 smartwatches `trusted`, 2
`unverified` (one from the node, one from a description that says
"Edelstahl-Smartwatch"), 16 `other` — 6 dive computers including the Suunto
Nautic S, whose title names only a dive computer while its bullets list GPS
and maps, 7 accessories including a dive-computer interface, 2 bands and
trackers, and one fenix 8 listing whose title, node and bullets never name a
class. Among the 39 smartwatches: 20 state a dive function, 20 NFC or a
payment service, 31 Android, 9 a barometer; 34 carry a price and 3 do not;
31 a depth in metres, 15 an ATM rating, 12 a GPS runtime, 15 a watch-mode
runtime, 34 a display name. Development and check sets: 48 unique records
from the two search feeds, 7 ASIN-fetched records held back and run once
when the rules were fixed — all seven classified as the titles read, one of
them `unverified` from its body text. After adoption: 888 tests in 30 modules
(858 → 888), 5 capabilities pinned (2 experiments), 7 of 7 examples with
their ids unchanged, gate 25 s. The runner's second measured fact: the
kernel boundary's own tests skip inside a nested boundary (the probe fails
there as it does in the reviewing agent's container), and say so.

**Not established, and not claimed.** Classifier accuracy beyond these 55
titles; anything about measurement quality, dive suitability or payment in
Germany, which stay withheld conditions; any ordering of battery life. That
the category is *right* is the study's question (Phase 2): the hand-read
table of the trial's `analyse-2` has not yet been compared with the
category's, and the R13 report's shortlist included the Nautic S that this
classifier declines — a difference the study revision must explain. The
extraction case (Phase 3) is still undecided by inspection. This is the first
shipped adaptation for the purposes of [R16](#r16--capability-lifecycle-and-architectural-review)'s
review trigger, and the second architectural review is now due.

**2026-09-18 — Phase 0: the procedure, built as reviewed maintenance before
any adaptation used it.** The maintainer accepted the plan the same day, with
seven decisions: an additive `adaptation` key in manifest v3 whose method
digest enters the study id only when bound; session ledger v2 so that
engineering can run against its own allowance; a `sandbox-exec` runner
measured where the trial runs, with a stop rather than a weaker fallback and a
recorded, labelled exception as the maintainer's override; a frozen evaluator
set a patch may not touch; the third trial's plan revision 7 committed as it
is with its `limited` review; runtime-bound-to-its-mode as the extraction
case if the page inspection confirms the layer, with redacted pages permitted
in the corpus; and the 14 400 s already proposed in the trial's ledger as the
category's envelope. The operating context that shaped the threat model —
every user is an IT professional driving the harness, and an engineer reviews
every change — is recorded in [PURPOSE](PURPOSE.md#who-operates-it): the
runner and the frozen evaluator defend against agent-written code
misbehaving and against a patch widening its own checks, not against the
operator, and they make the review mechanical and replayable rather than
stand in for it.

What shipped, under [CONTRACT §15](CONTRACT.md#15-adaptation-record-v1-and-session-ledger-v2-r15-phase-0)
and [adapt inside a study](RESEARCH.md#adapt-inside-a-study): **the adaptation
record** (`study/adaptation.py`, tracked as `adaptation_record` v1) — origin
in a plan revision and a ledger action, budget in seconds and attempts, the
patch as a complete archive with every added or modified file's content, the
digests of both trees and the lock, a method descriptor that excludes the
review, the evaluator set and whether it stayed frozen, a static inspection
computed before any import, every check with its exit or its kill, a review
bound to the patch and checks it read, an adoption recorded once by a role,
and a rollback with its demonstration; **the trial procedure**
(`study/trial.py`) — tree identity, patch capture, static inspection for
import-time work, network, subprocess, file writes, moved version constants,
dependencies and the evaluator set, a deny-by-default profile, execution with
a process-group watchdog, and the boundary probe; **session ledger v2** — an
engineering action is authorised, runs, completes or is interrupted against an
`engineering` limit in seconds, recorded from its adaptation record as
`consumption_source: adaptation_record`, while a v1 file keeps refusing to
execute engineering; **the study binding** — `run --adaptation` (refusing an
unadopted record unless `--trial`), the record as a `semantic` artifact in the
inventory, `verify` requiring the manifest to name exactly it and the id to
re-derive with its descriptor, and `code_caveats` naming the record instead of
the dirty flag; seven `study adaptation-*` commands and `session-record
--adaptation`; the gate replaying an adaptation-backed example.

**Measured.** Step 0, before any patch: the gate at `1626b49` passed in 23.2 s
with 814 tests in 28 modules and 6 of 6 examples; the full suite and the full
gate then passed *inside* the deny-by-default profile (814 tests, 22.6 s; gate
23.2 s), after two facts the profile forced into the open — `TMPDIR` must point
inside the scratch directory or 50 tests find no temporary directory, and six
test modules write `tests/studies/.tmp-*` briefs beside the fixtures, now the
one write the profile admits beside the scratch directory — and `git` does not
run inside it (its shim writes a cache under `TMPDIR` and reads the user's
configuration), so tree and patch identity are computed outside. Boundary
probes, inside the profile: a read outside, a write outside, a write to the
tree, a socket connection and a read of the home directory refused with
`EPERM`; the scratch write allowed; the identical `sandbox-exec` probe exits 0
here and 71 inside the reviewing agent's own container, which forbids nested
sandboxes. The loop end to end on a synthetic method patch (one new test
module and one README line against a clean worktree at `1626b49`): captured as
2 files, nothing flagged, evaluator frozen; the whole offline suite run inside
the boundary as one attempt, 815 tests, 21.6 s, exit 0; reviewed, adopted,
accounted in a v2 ledger revision that names its predecessor's digest and
records 21.6 s consumed; the bronze-die brief bound to it is
`pasta-bronze-die-306e33f25417` where the unadapted study is
`pasta-bronze-die-bde2b027b117`, with the same decisions, and it verifies and
resumes; rollback demonstrated — base tree and evaluator digests unchanged,
the gate green at the base. That loop is committed as the fixtures under
[tests/intake](tests/intake/README.md) and the gate's seventh example. After
the change: 857 tests in 29 modules (814 → 857, +43 in `test_adaptation.py`),
7 of 7 examples with the six earlier ids unchanged, `session_ledger` 1 → 2
and `adaptation_record` 1 recorded in the baseline as the two explained
contract moves, manifest v3 unchanged, gate 26.4 s. Negative cases, in the
suite: a patch or a check after the review makes the record refuse to load; a
timed-out check has no exit and no pass, and a hung check's child died with
it; an evaluator rewritten in the worktree is refused before anything runs; a
patch touching the evaluator set is captured and refused at capture; the
budget spent refuses the next attempt; a tampered record, a manifest naming
another adoption, an id without the method and a reader without the inventory
row all fail `verify` by name.

**Not established, and not claimed.** No real adaptation has passed through
the procedure: the fixture patch is semantic-free by design, so this entry is
not "R15's first shipped adaptation" for R16's review trigger, and the first
Done-when bullet is untouched. Of the others: the faulty-patch case is covered
only as a recorded non-zero exit, not yet as a real regression a category
patch introduces; the source-embedded-instruction case waits for a category
with text to carry it; the `harness-only` exception path is specified and
tested for its label, never exercised. The static inspection reads names, not
intent. `sandbox-exec` is deprecated by Apple and was measured on one machine
(R17 owns the rest). The `.tmp-*` write beside the fixtures is a boundary
decision, stated, not a boundary proven necessary: moving those six modules to
`TMPDIR` is open. What R16 review 1 assigned to R15 — the report-level
provisional status — is Phase 1's, with the category.

**2026-09-18 — The first control case, built as reviewed maintenance ahead
of the gates: `axis_bound`.** The second school-backpack trial recorded under
[R13](#r13--the-conversation-as-the-entry-point) met INTAKE §4's case 7 on a
category that publishes the bounded axis: a buyer's budget on the price and a
threshold on the rating had no control because the one cap binds the ordering
axis, and the study was bounded on both. The maintainer asked for the gap to be
closed at once; this is the change, and the R15 procedure it did *not* pass
through is the reason it is recorded here.

What shipped: `axis_bound`, a sixth mechanism in the controls catalogue — a
floor and/or ceiling on any category axis, named explicitly with an optional
exact unit, applied per card at candidate assessment before grouping, on
trusted values only, with a card that has no trusted value in that unit
excluded as unassessable rather than admitted; `constraints.axis_bounds` in
brief v1, present in the persisted brief only when declared; the plan-to-brief
transition refusing a bound no requirement maps to and a mapped bound that did
not reach the brief with the same axis, unit, floor and ceiling; the
`out_of_bounds` candidate fate with its own heading in the report; and, so a
rating threshold has axes to bind, `review_count` in the validation layer
(trusted when the rating block's histogram accounts for every rating) with
`review_rating` and `review_count` published by `school_backpack` as axes that
rank nothing by default. No contract version moved: the new brief key and the
new validated field are additive within their versions, and the validated
field is deliberately kept out of `as_dict()` because that one key would move
every committed card digest the two T3 semantic reviews bind — INTAKE §16's
priced migration, deferred to the next one and said so in CONTRACT §3.

**Measured:** every committed example's decision artifacts and report bytes
unchanged, because every new key is absent when undeclared; the `dry_pasta`
control catalogue digest moved once and the delivered-cost intake review
fixture was reissued against it with its findings re-read (six controls, none
of which reads a shipping quantity); the pack-size ceiling over the bronze-die
brief is a new gate example in `tests/test_gates.py`: the ordering is untouched
and the packs above a kilogram leave with the reason; on the second trial's
retained shelf, the budget of 100 EUR on `price` and the threshold of 4 stars
from 50 ratings on `review_rating` and `review_count` become enforced and the
23 ranked rows fall to the eight a person had counted by hand, with the
recommendation still withheld on `reliability` and `fit` — measured in the
trial's third bundle, whose numbers are in the R13 entry. Tests 797 → 814,
the floor re-recorded in the same change and nothing else in the baseline
moved. **Not established:** that a
bound answers the requirement it is mapped to — a semantic-review judgement, as
for every control; isolation, rollback and patch-binding of a mid-study change,
which are this milestone's gates and were not exercised: the change went
through the ordinary maintenance workflow on the maintainer's instruction, and
that is the honest label for it.

### Scope

Make a bounded engineering operation part of a study. Cover category modules,
source acquisition/adapters, extraction patterns, evidence handling, comparison
methods and procedures. Use the existing maintenance workflow, with an explicit
link between the observed gap, patch and resulting research revision.

For each adaptation retain the originating requirement/source, base revision
and exact patch digest, affected layer, hypotheses, budget, reproduction cases,
commands/check results, semantic decision diff, review findings and rollback
instructions. Preserve the patch itself or a retrievable revision: a dirty flag
cannot reproduce code. Bind these to the study and method revision without
silently changing historical bundle IDs or overwriting previous results.

Before executing new imports or tests, inspect the diff and use an isolated
checkout/worktree plus restricted execution appropriate to the environment.
A worktree isolates files, not credentials or network access: code validation
needs a runner with declared filesystem, network, secret and time limits.
Offline tests should need neither network nor credentials; bounded collection
runs separately under existing pacing and authorized access. No new agent
framework is required. Document and test the boundary instead of treating
agent-generated code as safe because it was generated locally.

Test the new behavior and counterexamples, run the maintenance gate — which is
the full offline suite, the contract versions and the study replays in one
command — inspect changes in eligibility/trust/prose, then record review and
versioned adoption before using the changed method for a recommendation. An
adaptation that needs the gate baseline lowered says so in the same diff: the
gate refuses to establish less than the tracked baseline without one.
Ordinary authorized local work needs no new permission ritual. Changes to trust
semantics, dependencies, permissions or foundational contracts need explicit
scope and review; the task cannot expand its own authority or weaken its gates.
Retrieved text remains evidence, never execution instructions.

### Done when

- A category case and a case changing extraction or evidence acquisition both
  complete the patch → checks → review → study-revision loop within stated limits.
- A faulty patch fails a meaningful regression and is withdrawn; a timeout or
  interrupted operation preserves evidence and resumes from verified artifacts.
- A patch that would weaken the verification baseline — a deleted test module,
  a lowered count, a changed contract version, a moved example decision — fails
  the gate and can only proceed by recording the new baseline explicitly.
- The baseline and previous studies can be restored without losing original
  inputs; new outputs identify the exact code and method that produced them.
- Execution restrictions are demonstrated with failure cases, including an
  attempted access outside the allowed boundary and source-embedded instructions.
- At the budget limit, the agent reports a qualified result or a specific blocker.
  It does not retry indefinitely, lower trust or turn a failed patch into success.

---

## R16 — Capability lifecycle and architectural review

**Status: IN PROGRESS.** The capability index, the lifecycle records of the four
registered categories and the first architectural review shipped on 2026-09-18
and are recorded below. The count toward the five-study cadence stands at
**two** since R15's Phase 2 (the smartwatch study), and the second review is
due: R15's first shipped adaptation was its trigger. The *task-experiment entry* — a capability arriving
inside a study with a patch digest, a scope bound to the study and isolated
checks — happened on 2026-09-18: `smartwatch` is the first capability whose
lifecycle record points at an adaptation record rather than at reviewed
maintenance ([R15](#r15--controlled-task-driven-capability-adaptation),
Phase 1). What still waits is the promotion evidence that flows from being
reused, and the second architectural review that the first shipped adaptation
triggers. The minimum lifecycle precedes R14; periodic review continues after
the first operating-model release.

**2026-09-18 — Capability index, lifecycle records and the first review.**
The question put to this milestone was whether it was blocked or could start.
The answer was that it has three parts with three different dependencies, and
two of them depended on nothing that was missing.

- **The index is the registry, read with more questions.** A category now
  registers with a `Lifecycle` declaration beside its code — state, last
  decision and date, responsible role, applicability, evidence paths, roadmap
  anchors, last review, method version — and `register()` refuses one without
  it. `study capabilities` publishes every registered capability from that
  declaration and the live registry on each call, so there is no second list
  to drift, exactly as the R13 controls catalogue is built; `--marketplace`
  compares hosts and `--category` narrows. Applicability is falsifiable:
  each `Decline` cites committed case ASINs, and `tests/test_capabilities.py`
  re-classifies all **36** of them as `other` on every run, and checks that
  every marketplace a case names is one the category declares. The index is
  inspection, not authorisation, and it names its own limits, the first being
  that maturity is not trust.
- **The promotion gate is executable.** The maintenance gate gained a
  `capabilities` check and its baseline moved to **version 2**, which pins
  each capability's `state`, `decision` and `method_version`. A declaration
  that is incomplete, cites evidence the tree does not hold or a roadmap
  heading that does not exist fails by field; a state that moved without the
  baseline moving fails as a `capability_lifecycle_changed` finding naming
  ROADMAP as the place the decision is recorded first. A new category is
  `capability_untracked` until the baseline records what it declared:
  retention is a decision, and the baseline is where the repository records
  one reviewably.
- **The four lifecycle records.** `dry_pasta`, `tyre_mounting_paste` and
  `basmati_rice` are **maintained**, each with the evidence its declaration
  cites and with what it does not establish written next to it: mounting
  paste has never had a second buyer, and basmati has no committed acquired
  record set. `school_backpack` is a **task experiment**, retained and
  nominated for reuse — one study, one buyer, one shelf of 43 records, built
  as reviewed maintenance with no R15 gate to pass through. It is registered
  and usable, and the index says what that is worth.
- **Measured effect.** Offline tests 774 → 797 in 27 → 28 modules;
  36 decline ASINs proven on the committed cases; six committed studies
  cross-referenced onto the categories their briefs name (four pasta, two
  basmati, none for the other two — the review below records that debt);
  290 local links and 285 anchors across 18 documents on the tree merged
  with the same day's purpose review, from its 281 and 284; every
  example decision, every contract version and every snapshot unchanged. The
  gate baseline diff is two deliberate parts — the version and the pinned
  lifecycles — and one re-recorded floor, the test count.
- **Not established, and not claimed.** That a state is deserved: the three
  `maintained` records rest on the evidence they cite, and the judgement is
  this entry's, not the gate's. That an agent will consult the index before
  deciding fit: the runbook now says to, and R13's conversational trials are
  where that is graded. The first Done-when bullet — a second study finding a
  capability through the index — has a fixture (a foreign marketplace finds
  no applicable category, and every declined class stays declined) and no
  conversational trial yet. Nothing here binds a method version into a study
  manifest; that is R15's.

### Architectural review 1 — 2026-09-18

**Trigger.** INTAKE §16's ten stages shipped on 2026-09-17, which is an
operating-model milestone, and the same week produced the first
extension-bearing study (the school backpack). The count toward the
five-study cadence stands at **one**. Reviewer: the operating agent, on the
maintainer's request; owner of every decision below: the **repository
maintainer**. Supporting study IDs are the six the gate replays —
`pasta-bronze-die-bde2b027b117`, `pasta-low-temperature-drying-48df9d940ced`,
`pasta-delivered-cost-43425b41286a`, `pasta-purchase-budget-5c28fb92681b`,
`basmati-audit-positive-49ef55740633`, `basmati-audit-insufficient-50e21e1c7b99`
— and the four private school-backpack bundles recorded under
[R13](#r13--the-conversation-as-the-entry-point), whose IDs are not in the
repository.

**Measurements.** Import edges were read from the AST of every module under
`shopping_advisor/`; leakage and usage counts are greps over the tree; times
are one run each on this container.

| Item | Measured |
|---|---|
| Cross-layer imports | Categories import `validation` and `category` only, except `basmati_rice`, which also reaches `extraction.marketplaces` for word boundaries and `evidence` for its legacy ledger. `analysis`, `study` and `study/delivery` import `read_jsonl` from `run.py`: three downstream layers depend on the acquisition module for a JSONL reader. `validation` imports two text utilities from `extraction` (downstream, correct direction). `maintenance` imports everything, by design. No layer imports `spiders`, and none imported `maintenance` until this change: the study CLI's `capabilities` command now reads the gate's committed examples through a local import, so that the index can list the replayed studies without owning a second list of them |
| Category leakage | 43 lines in generic layers mention a category by name; 42 are comments citing the measurement a rule was built from. Three are code: `study/bundle.py` merges the legacy basmati ledger behind `brief.category == 'basmati_rice'`; the spider's default query is `spaghetti hartweizen`; the analysis CLI's `--category` defaults to `dry_pasta` (documented, and the runbook says to name it on every command) |
| Duplication | The `claims()` loop appears in all four categories (four copies of 12–20 lines, two variants: mounting paste adds a negation exclusion and a kit note, school backpack an affirmative scope); `stated()` appears twice; the two positional title classifiers share a rule shape and no code; three modules write `source='text'` where one imports the `TEXT` constant |
| Unused capabilities | `Category.render_extra`: one consumer (basmati). `Axis.render`: two categories (pasta's raw-material axis, school backpack's height and warranty axes). Marketplace profiles `amazon.co.uk` and `amazon.it`: unvalidated, documented as such, `.it` referenced by no test. `settings_scrapeops`: opt-in, unvalidated, import isolation tested. `keep_search_pages`: used. Nothing is obsolete |
| Replay compatibility | Six committed studies replay through their documented commands with the recorded decisions; a manifest v1/v2 bundle refuses with `unsupported_manifest_version` by the stage-10 decision; no pre-v3 bundle is tracked |
| Test cost | The full gate: 50 s on this container against the 15 s recorded on the development machine, 797 tests in 28 modules. Of it the suite alone is 46 s, the six example replays 1 s and the documentation index under a second: the suite is the cost, and the replays are nearly free |
| Unresolved debt | Two of four categories have no committed replayable study (mounting paste, school backpack): the gate pins their verdicts per record and replays no decision of theirs. Basmati has no committed acquired record set. A task-experiment category has delivered permitted current advice without a report-level provisional status ([INTAKE §15](INTAKE.md#15-what-stays-owned-elsewhere) places that contract under R11/R15). `cost_basis`, `unacceptable` and `limits` remain narrative. Weights in pounds stay text. The README's category table listed three of four categories when measured |

**Decisions.** Each is retain, simplify or retire, with its evidence, its
owner (the repository maintainer throughout) and a next checkpoint. No code
was refactored in this review; every simplification below is scheduled
against a change that will touch the file anyway, so that it carries a
semantic diff of its own rather than riding on this one.

| Decision | Subject | Evidence and reasoning | Next checkpoint |
|---|---|---|---|
| **Retain** as maintained | `dry_pasta`, `tyre_mounting_paste`, `basmati_rice` | Cases with counterexamples, per-record tests, recorded reviews (R0–R8, T3), and for pasta and basmati committed audited studies. Mounting paste's second-buyer gap and basmati's missing record set are written into their declarations, not hidden | Review 2 |
| **Retain** as experiment, nominated for reuse | `school_backpack` | One study, one buyer, 43 records; the two generic extraction changes it needed entered the maintained layer as within-version additions with zero effect on the 39 corpus pages (CONTRACT §4). Promotion needs a distinct subsequent use | The next backpack-class or school-bag study |
| **Simplify later** | `read_jsonl` housed in `run.py` | A generic reader in the acquisition module, imported by three layers. Moving it carries no semantic diff and nothing a study needs today; doing it inside an unrelated change would hide it | The next change to `run.py` moves it to a neutral module in the same diff |
| **Retain** | `study/bundle.py`'s basmati branch | The one category-named line of code in a generic layer. It exists because retained external evidence has one consumer, and INTAKE §4 records that a general eligibility path is net-new machinery. One consumer is not two | The second category to carry retained external evidence; generalise then |
| **Retain** the copies | Four `claims()` loops, two `stated()` helpers | They differ in what they exclude and annotate; a shared loop would carry parameters for negations, kit notes and source labels to save roughly 40 lines. The argument that will change this is R15's, not size: a helper reduces what an agent-written category has to get right | R15's first agent-written category, or the fifth category |
| **Retain**, documented as unvalidated | `amazon.co.uk` and `amazon.it` profiles, `settings_scrapeops` | Unproven is not obsolete; README states the limit and nothing depends on the profiles being right | R4, on a stated need |
| **Retain** | Spider default query, CLI default category | Defaults, documented, and the runbook says to name the category on every command. Changing the spider default would silently change a documented command | None; revisit if a study is ever run on the default by mistake |
| **Debt, recorded** | No committed replayable study for mounting paste or school backpack | Their cases exist, so a brief over them is cheap; it was not added here because a study example is a claim about a decision and deserves its own change and its own baseline row | The next change touching either category adds a committed brief and its baseline example |
| **Debt, recorded** | Provisional-method report status | A task experiment has delivered current advice. Until R11/R15 add the report-level contract, the index is where its maturity is visible, and the runbook tells a report resting on an `experiment` to say so | R15 |
| **Fixed on main** | README category table | Listed three of four categories when measured; the [documentation review of the same day](#documentation-review--2026-09-18-the-purpose-gets-an-owner) added the row on main, and this branch merged it rather than adding a second | — |

**Next review.** [R15](#r15--controlled-task-driven-capability-adaptation)'s
first shipped adaptation, or the fifth extension-bearing study, whichever
comes first; the count stands at one. Owner: the repository maintainer.
**Triggered 2026-09-18:** the `smartwatch` adaptation shipped through the
procedure; review 2 is due and has not been held.

### Scope and promotion gates

Keep a small repository index linking capabilities to code, method version,
applicability, source/study evidence, regression cases, maturity and last review.
Use it during R13 inspection; do not create a parallel free-form memory store or
a dynamic loader for source-provided code. Experiments live with their study and
patch; maintained knowledge stays in the durable homes named in RESEARCH.

| State | Entry / exit evidence |
|---|---|
| Task experiment | Named gap, bounded change and tests; usable only within its validated scope after R15 review. Retain for audit, withdraw or nominate for reuse at study close |
| Maintained local capability | Demonstrated value in a distinct subsequent use, applicability/counterexamples, regression protection, recorded review and maintenance responsibility. One success remains provisional |
| Shared foundation | Multiple real consumers demonstrate the same semantics and benefit from sharing. Compare local duplication with proposed coupling; migrate only with compatibility tests and measured effect |
| Retired or superseded | Record reason, replacement and replay implications. Remove obsolete executable paths where safe while preserving historical artifacts and method identity |

A correctness fix may enter the existing maintained layer through its normal
regression workflow; it does not need a second customer to justify fixing a bug.
The broader-use gate applies to promoting an experimental capability or shared
abstraction, not to retaining useful evidence.

### Done when

- A second study finds a prior capability through the index and checks its
  applicability before reuse. A superficially similar but incompatible case
  declines reuse without changing generic rules to fit it.
- Every trial extension has a recorded keep/promote/reject/retire decision,
  evidence and responsible maintainer role; unresolved hypotheses stay labelled.
- At each operating-model milestone and every five extension-bearing studies,
  the maintainer reviews duplication, cross-layer imports, category leakage,
  unused capabilities, replay compatibility, test cost and unresolved debt.
  No background scheduler is needed for this review gate.
- Each review records concrete retain/simplify/retire decisions in ROADMAP with
  supporting study IDs, an owner and a next checkpoint. Any refactoring carries
  semantic diffs and rollback; a reasoned no-change decision is acceptable.
- Shared scoring, storage and adapter frameworks are reconsidered from these
  measurements, not from an ambition to make the system complete.

---

## R17 — Portability evidence

**Status: DEFERRED, not cancelled. It gates one claim and nothing else.**

The design is provider-neutral and stays that way: the interface is repository
files and ordinary CLI commands, no provider SDK sits in the core, and the
maintenance gate needs no model API and no credential. None of that has been
*measured*. The gate has run on one machine, one shell and one interpreter,
driven from one provider stack. Nothing establishes that the same command paths
behave the same way on Windows or on Linux, or that two provider environments
reach the same decisions and can hand a study to each other.

So, until these trials run: **no claim of proven portability or provider
interchangeability may be made** — not in this repository's documentation, not
in a study report, not in a report's stated limits. "Provider-neutral by design,
unmeasured" is accurate. "Operable by agents using either provider stack" is
not; it is the one sentence the delivered transition could not support, and it
is the reason this milestone exists rather than quietly disappearing with the
plan that held it.

### Scope when it starts

- The documented command paths on Windows and on Linux: setup, the maintenance
  gate, the offline walkthrough and a study replay — recording the environment,
  the failures and every manual intervention each one needed.
- Two provider environments, for example a Claude CLI and a Codex CLI, each
  loading the same canonical instructions: run a study from the same brief,
  make one scoped repair through the maintenance workflow, then hand the
  artifacts to the other to continue without the originating conversation.
- A research-evaluation set spanning the three shipped categories, so that the
  comparison between environments is made against stated expectations rather
  than against an impression of two transcripts.
- Prompt-injection fixtures: source text carrying instructions stays content in
  both environments. Passing is regression evidence, never a guarantee.

### Done when

- Both environments complete the research and the maintenance exercise, and
  each resumes the other's study from the bundle alone. The result records the
  tested scope, the method versions, the failures and the human interventions.
- Provider, model and tool configuration appear only as execution metadata. A
  status, a plausibility band or a decision that moved because of the
  environment it ran in fails this milestone; it is not a finding about a
  product.
- The gate reports the same findings on each platform, or a difference is
  recorded as known platform behaviour with its reason.

### Explicitly out of scope

Remote CI and a Git hook as the authority, for the reasons recorded in the T4
delivery note: a hosted runner becomes a second definition of the gate that can
drift from this one, and a hook is per-clone state, invisible in review and
skippable with `--no-verify`. Multi-marketplace support, multi-agent roles and
a hosted platform are out of scope too — two-provider operation needs none of
them.

### Not a dependency

R13, R15, R16 and R14 do not wait for this. What they needed from the
transition was one executable local gate, and it shipped. Reopen R17 when a
second platform or a second provider is actually in use: these trials are worth
running against real use, not against an imagined one.

---

## Deferred and rejected work

These decisions describe the measured workloads, not permanent limits on future
research. R15 may test a previously deferred technique when a named task needs
it, within budget and authorization. Revisit the evidence, not just the label.

| Capability | Decision | Reconsider when |
|---|---|---|
| Browser automation (Playwright, Selenium) | **DEFERRED; rejected for the measured workload** | A named task needs evidence unavailable through the current adapter, demonstrated by a bounded probe. Historical 201/201 HTTP 200 and duplicate client-loaded data justify the old decision, not a universal ban. Challenges alone do not authorize bypassing access limits. |
| Proxy rotation, fingerprinting | **REJECTED** | Sustained 429/503 on **PDP** requests under current pacing. The measured 503s were a `/s?` burst artifact, fixed by sequential search pacing. |
| OCR of product / A+ images | **DEFERRED; dropped from pasta V1** | A decisive requirement in a named task needs image-only evidence and a bounded extraction/validation trial shows value. The historical 0/60 bronze-die and 0/50 Gragnano findings apply to pasta; do not require 20 V1 records to justify a different task. |
| Reviews | **DONE → R5** | Decision test passed at 57% against a 30% bar. Cost a tenth of the estimate: the data is in the retained PDP HTML, and the larger version is unavailable — `/product-reviews/` needs an account. |
| Amazon.com completion | **DEFERRED → R4** | A stated user need for US research. |
| Framework / runtime upgrade | **DEFERRED (maintenance)** | A product goal is blocked by the runtime. The last upgrade silently dropped an attribute table from two corpus pages; the corpus test is the gate. Never mix an upgrade with product work. |
| `amazon_search.py` | **REMOVED in T0** | No supported code/test consumer found in the tracked-reference inventory. Use `amazon_product`; see the [migration note](README.md#legacy-search-spider-migration) for its different feed shape and acquisition scope. |
| Nutrition coverage beyond validation | **DEFERRED** | Never as a coverage goal. 44% is Amazon's ceiling, not the parser's. |
| Engineering intake record, symmetric to the R13 plan | **REJECTED (2026-09-17)** | Proposed after R13 stage 6 as a retained artifact for maintenance requests: request kind, interpreted scope, acceptance criteria written before the change, authorisation scope, retention decision. Rejected because the harness, git and the maintenance gate already hold each of those, and a repository copy would be the parallel memory store R16 forbids; see [two kinds of request, one interface](#two-kinds-of-request-one-interface). Reconsider only for engineering spawned inside a study, which is R15's binding problem, not an intake problem. |

---

## Product boundaries

| Boundary | Decision |
|---|---|
| Generic extraction | Preserve raw evidence and keep category preferences out. The fourteen measured pasta signals fit existing fields; new tasks may justify local source parsers or new fields through R15 and contract review. Existing coverage does not establish architectural completeness. |
| Food extraction | **Correct placement**, one change: the food layer must stop asserting values it cannot defend. |
| Validation | **Two layers, never inside extraction** — shipped in R2 as `shopping_advisor/validation/`, published as [CONTRACT.md](CONTRACT.md). Extraction stays faithful to the source. *Generic:* unit-versus-field disagreement, basis-phrase-as-value, mass balance, Atwater, single-nutrient corroboration, quantity-versus-price coherence, on-page source conflict. *Category:* plausibility bands, claim/ingredient contradictions, price floors — supplied to the generic layer as **data**, never as procedure. |
| Category analysis | **Downstream of the JSONL.** The acquisition layer never learns what good pasta is. Confirmed by a second category in R2: tyre mounting paste needed no change to the crawler, the extractor, or any trust rule — only a profile, a classifier and a list of claims. **This boundary survives [R11](#r11--category-synthesis-as-a-default-step):** category interpretation stays in this layer; a task that also requires new extraction or evidence handling changes the corresponding layer through R15. |
| Who writes a category | **Changing, deliberately — see [R11](#r11--category-synthesis-as-a-default-step).** Today an agent or human can write one through reviewed maintenance, and the runbook offers that as a choice. The target is that the agent writes one by default, within R15 gates, carrying its evidence and applicability. R16 distinguishes **task experiment, maintained capability and shared foundation**. Report limitations of provisional interpretation without conflating maturity with value-level trust. |
| Marketplace-specific | `shared structural extraction + marketplace profile + adapters where measured evidence demands`. Correct, but currently over-applied: two profiles exist that nobody validated. |
| Discovery / Product | **Separate the record now (R1), defer the entity (R3).** The requirement is that a repeat sighting must not cost a repeat fetch and must not be erased. |
| Locale | **Record it, do not abstract it.** Justification is correctness: the request locale and the label vocabulary are chosen independently today and can disagree with no error at all. German stays the authoritative Amazon.de discovery locale. |

---

## Open experiments

Questions the repository cannot currently answer. Each blocks a specific
decision; none blocks R0.

### E1 — True package-quantity error rate

- **Blocks:** whether price per kg can remain V1's primary axis.
- **Why unresolved:** conflict detection needs an independent pack hint. After
  R0, 100 of 161 dry-pasta records carry one (88 corroborated, 12 disputed);
  the other 61 are unverified or unknown and could hide errors of the same
  kind. The 12 found are a floor, not the rate.
- **Experiment:** hand-verify extracted total quantity against the live PDP
  for a random 30 of the 163 records. Half a day, no crawl changes.
- **Threshold:** >15% wrong or unresolvable → price per kg cannot be a trusted
  axis; V1 leads with raw material and claim evidence, and R3 is pulled
  forward.

### E2 — Cross-query discovery overlap — **RESOLVED**

**43 of 213 sightings (20%) are repeats**, against a threshold of 10%. The
earlier position-gap estimate was too low, because it could only see
cross-query repeats and missed the larger source: the same ASIN listed twice
on one page, once organic and once sponsored.

Over the threshold, so the persistence split moved into R1 and is done —
occurrences live in `discovery.jsonl` and are never collapsed, products live
in the feed. What stays in R3 is the part with no consumer yet: a model that
*joins* them, and offer families. The reasoning is the same one that put R0
before R2 — do not model what nothing reads.

### E3 — Discovery coverage of the category

- **Blocks:** whether query design becomes a roadmap item of its own.
- **Sharpened by R2.** On the mounting-paste crawl, 47 of 90 results were not
  the product searched for, and the *criterion that decides the purchase* is
  stated on 3 of the 43 that were. Whether that is a discovery problem (the
  right products exist and these queries do not surface them) or a category
  ceiling (Amazon listings simply do not say) is now the more interesting
  version of this question, and it is answerable with a hand check.
- **Answered in part by R5's category, and the answer is "discovery".** Eight
  generic queries in German and English, two result pages each, **never
  surfaced AKASH at all** — the brand took a query naming it. AKASH
  Basmatireis is one of only two basmatis Stiftung Warentest rated "gut" in
  5/2026. A researcher who did not already know that result would not have
  reached the product it recommends.
- **The sharper hypothesis now:** generic queries may under-sample diaspora
  brands beyond the observed basmati case. The two-page sweep did not resolve
  that case; it does not measure other categories or rule out deeper discovery.
  R12 compares bounded source/query expansion against that limitation.
- **Experiment:** for a category, take the brands that only brand-specific
  queries discovered, and measure their share of the final shortlist. On
  basmati: **1 of 8 finalists, and 2 of the 3 products with external
  laboratory evidence.**
- **Threshold:** brand-only-discovered products taking more than ~20% of a
  shortlist → query design becomes a roadmap item, most likely as a
  brand-expansion pass seeded from the first crawl's own brand field.
- **Promoted to [R12](#r12--discovery-that-states-its-own-coverage), with
  rationale corrected in the 2026-09-16 product review.** 1/8 is 12.5%, so the
  original shortlist threshold was not crossed. Missing decision-relevant
  candidates and 2/3 externally tested products justify a coverage experiment;
  they do not prove exhaustive coverage or the original numeric hypothesis.

### E4 — Does the trust bar leave enough to compare?

- **Blocks:** the framing of V1 itself.
- **Experiment:** measured inside R0 — count products with at least one
  trusted comparison axis.
- **Threshold:** <60 of 163 comparable → V1 reframes to "here is what Amazon
  does and does not tell you about these products", and evidence-gap
  reporting becomes the user-visible feature.

---

## Superseded hypothesis (P0–P6)

Kept for the reasoning, not as a plan.

| Item | Verdict | Became | Rationale |
|---|---|---|---|
| P0 stabilise generic extraction contract | **CHANGE** | R2 | Already pinned by `SCHEMA_VERSION`, the schema table in EXTRACTION.md and the 35-page corpus test. What was missing is a consumer. Freezing first would have ratified `confidence` semantics that measurement shows are inverted. |
| P1 improve discovery/product modelling | **SPLIT** | R1 (additive provenance) / R3 (entity separation) | Recording occurrences is cheap and irreversible if skipped. Promoting them to separate entities is a storage decision with no consumer demanding it. |
| P2 add validation / trust layer | **MERGE** | R0 (axis-specific) + R2 (generic) | Validation is a precondition for an honest first ranking, but a general framework with no consumer repeats P0's mistake. |
| P3 build dry-pasta analysis | **MOVE_EARLIER** | R0 | The only item producing user value, and it needs no crawl. |
| P4 product variations / twisters | **SPLIT** | R1 (raw capture) / R3 (family modelling) | The twister blob is validation evidence first and a grouping feature second. |
| P5 validate / complete Amazon.com | **DEFER** | R4 | No product need; `.de` has produced no user-facing output yet, and the unvalidated `.co.uk`/`.it` profiles are already the debt this creates. |
| P6 optional enrichment (OCR, reviews) | **SPLIT** | OCR dropped / reviews R5 | A+ content contributes zero unique evidence for V1's top claims. |

### T3 — DONE (2026-09-16): external evidence and recommendation audits

- Ledger v1 retains source metadata, permitted text/digests or explicit access
  limits, product/batch identity, matching evidence, conflicts and supersession.
  Indexed claims enforce historical/current-batch/vendor/sample/access scopes.
  Three basmati executable constants are now `legacy_unverified` ledger entries;
  missing original URLs/documents remain missing. No real source was newly
  accessed or verified in this maintenance change.
- Study manifest v2 adds ledger, claim index, deterministic validation and a
  separately completed semantic review. Full replay now checks ranking order,
  exclusions, constraints, freshness, every card/score and exact report bytes.
  Reviews bind both report and evidence/decision digests, record findings and
  unresolved limits, and distinguish pending from approval. `validate-report`
  emits JSON; `--require-review` additionally requires semantic approval.
- Adopted method: existing single-axis ranking, normally EUR/kg. No score-based
  shortlist or external-evidence-driven price eligibility is introduced.
  Basmati score method v2 removes unverified laboratory credit and unsupported
  safety bonuses from milling/origin/vendor assertions. Its starting health
  value is neutral, and existing adverse review adjustments remain heuristics.
- Measured effect on the three synthetic basmati fixtures (same pinned product
  inputs evaluated with HEAD before T3 and the new module):

  | Fixture brand | External status before → after | Total score before → after | Health before → after |
  |---|---|---|---|
  | Tilda | trusted → unverified | 60.5 → 54.5 | 0.9 → 0.5 |
  | Akash | trusted → unverified | 60.0 → 54.1 | 0.9 → 0.5 |
  | Gepa | trusted → unverified | 40.2 → 53.7 | 0.0 → 0.5 |

  The old health lookup also assigned Akash Tilda's 0.9 by selecting the first
  matching verdict. Removing unverifiable credit removes that false precision.
  These are software fixture measurements, not product ratings or buying advice.
  Price order remains 3, 4, 5 EUR/kg. A separate regression changes the third
  price to 2.5 EUR/kg and reproduces its move to first place.
- Two complete [basmati examples](tests/studies/t3/README.md) include sanitized
  synthetic records, retained synthetic source text and separate semantic review
  findings. The positive example selects B000000001, 33.3% ahead on listed
  EUR/kg; the second requires four candidates, finds three and recommends none.
  Both pass `validate-report --require-review`. Existing pasta examples retain
  their decisions; manifest v2 gave the positive example the ID
  `pasta-bronze-die-46127870314d` (the T2 IDs above are historical, and so is
  this one since R13 stage 10's manifest v3 moved every id once; the current
  ids are in the baseline).
- Verification: locked setup, **460 offline tests passed** (27 added for T3),
  no extraction/generic validation snapshot updates. Covered wrong reseller,
  variant, marketplace and batch; conflicts, supersession, absent/fabricated
  support, stale/future dates, vendor overreach, sampled-review population claims,
  digest tampering, rehashed score/rank/claim changes and semantic-review binding.
- Limits: automated checks establish reproducibility and declared applicability,
  not semantic truth. The real legacy sources remain access-limited. Real buying
  advice requires fresh acquisition and source review. T4 has since automated
  these checks into one local gate; provider interchangeability trials remain
  [deferred to R17](#r17--portability-evidence).
