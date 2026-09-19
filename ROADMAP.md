# Shopping Advisor roadmap

The plan of record for this repository: what each milestone is for, what it
must demonstrate, what it has established and what is still open. The dated
entries that earned those lines — measurements, trial records, review chains,
retired reasoning — live in [HISTORY.md](HISTORY.md) under the same milestone
headings, and this file links to them rather than repeating them.

**Status legend:** `DONE` · `IN PROGRESS` · `NEXT` · `PLANNED` · `DEFERRED` ·
`DROPPED`

| | Milestone | Status |
|---|---|---|
| **R0** | Pasta V1 — evidence-backed comparison over existing records | **DONE** |
| **R1** | Crawl provenance and evidence preservation | **DONE** |
| **R2** | Generic validation layer + published extraction contract | **DONE** |
| **R3** | Variation-aware product families | **DONE** (one criterion retired, not met) |
| **R4** | Amazon.com as a validated marketplace | DEFERRED — on a stated need |
| **R5** | Reviews as an evidence source | **DONE** |
| **R6** | A command line for the things every category needs | **DONE** |
| **R7** | Attributed search: finding a claim vs crediting it | **DONE** |
| **R8** | Marketplace-aware text matching | **DONE** |
| **R9** | A second pass for missing prices | PLANNED — behind a decision test |
| **R10** | Scoring as a shared facility | DEFERRED — one consumer is not two |
| **R11** | Category synthesis as a default step | **IN PROGRESS** — four of five acceptance conditions met by the smartwatch category; one open |
| **R12** | Discovery that states its own coverage | **NEXT** after R15 closes |
| **R13** | The conversation as the entry point | **DONE (2026-09-18)** |
| **R14** | A recommendation in a category nobody validated | PLANNED — after R12; the acceptance trial of the operating model |
| **R15** | Controlled task-driven capability adaptation | **IN PROGRESS** — procedure and four adaptations shipped 2026-09-18/19; one acceptance condition partly open |
| **R16** | Capability lifecycle and architectural review | **IN PROGRESS** — index, lifecycle records and two reviews shipped; waits for a first reuse |
| **R17** | Portability evidence: a second platform and a second provider | DEFERRED — gates the portability claim only |

---

## Product vision — the shopping conversation

**What the product is for, whose side the agent is on and what the product is
not are stated once, in [PURPOSE.md](PURPOSE.md). This section plans how the
product grows — the extension operating model, revised 2026-09-16 — and that
model is planned; the shipped scope remains in [README](README.md#supported-scope).
The assessment that produced the model is in
[HISTORY.md](HISTORY.md#roadmap-assessment--2026-09-16).**

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

---

### Priorities and true dependencies

Identifiers retain their historical meaning; their numeric order is not the
execution order. T0–T4 and completed R milestones remain delivered, not work to
repeat. Demand-driven expansion is a standing rule rather than a final
catalogue phase — see [decision principle 9](#decision-principles). Order
revised 2026-09-19, after R15's fourth adaptation and the second architectural
review.

| Order | Deliverable | Dependency and reason |
|---|---|---|
| 1 — done (2026-09-18) | R13 intake, evidence and gap planning | INTAKE §16's ten stages on top of T2/T3 and T4's gate; three conversational trials, the third graded against a record written before its first message and carried through independent intake reviews |
| 2 — closing | [R15](#r15--controlled-task-driven-capability-adaptation) | The procedure and four real adaptations have shipped. What closes it: a faulty patch withdrawn on a real category regression, the `.tmp-*` write allowance removed from the kernel profile, and the maintainer's decision on a tenth gate example under plan revision 10 |
| 3 | [R11](#r11--category-synthesis-as-a-default-step) close-out | One acceptance condition open — a changed buyer preference changes the brief, not the category, and the decision difference replays. One test over two briefs on the smartwatch cases, then the runbook makes synthesis the default step |
| 4 | [R12](#r12--discovery-that-states-its-own-coverage) | The next real capability gap: the third trial's plan reached its review ceiling on the `missing_context` it declared, and its decisive candidates arrived agent-supplied, not from the class queries. Without stated coverage every further trial ends `limited` for the same reason |
| 5 | [R14](#r14--a-recommendation-in-a-category-nobody-validated) | The acceptance trial of the operating model, after R12. Before it, review 2's dated debts: committed gate examples for mounting paste and school backpack, and the `.tmp-*` removal |
| Ongoing | [R16](#r16--capability-lifecycle-and-architectural-review) reviews at cadence | Review 3 at the fifth extension-bearing study or R14's first trial, whichever first; promotion needs a distinct second use of a capability |
| Conditional | R9, R4, R10, R17 | R9 behind its decision test; R4 and R10 on a stated need and a demonstrated second consumer; R17 only before a portability claim is made |

R10 is **not** a prerequisite for any of the above: a local comparison method
can be sufficient, and a generator is not a demonstrated second consumer.
Nothing in this sequence needs remote CI; the local gate is the authority.
R3's retired variation-conflict criterion remains retired: missing source data
cannot be fixed by adding software. E1 remains a scoped quantity audit; E2 is
resolved; E3 supplies R12's discovery cases; E4 was answered in R0. Fresh
studies must not treat those old samples as current market coverage.

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

---

## Agent-operation transition

**Delivered, and its plan retired (2026-09-16).** T0–T4 made the repository
agent-operable; their dated records, measurements and stated limits, the
product renaming and the two documentation reviews are in
[HISTORY.md](HISTORY.md#agent-operation-transition). Current operating rules
are in [AGENTS.md](AGENTS.md), the research workflow in
[RESEARCH.md](RESEARCH.md), with a thin `CLAUDE.md` entry point.

| Stage | What it delivered | Where it lives now |
|---|---|---|
| **T0** | Canonical instructions, the thin provider adapter, the runbook and a no-network walkthrough; `amazon_search` removed | [AGENTS.md](AGENTS.md), [RESEARCH.md](RESEARCH.md), [README.md](README.md) |
| **T1** | Run identity, manifest state and provenance, per-page digests, failure capture, redaction, marketplace-scoped identity | `run.py`, `provenance.py`, `redaction.py` |
| **T2** | The validated brief, structured ranking and exclusions, complete category JSON, the replayable study bundle, refusal as a result | `study/`, [CONTRACT.md](CONTRACT.md) |
| **T3** | External-evidence ledger, applicability and claim checks, full report replay, separate semantic review | `study/audit.py`, [CONTRACT.md](CONTRACT.md#8-study-audit-contracts-t3) |
| **T4** | One local maintenance gate over all of it, with a tracked baseline that has to be argued with | `maintenance/`, [AGENTS.md](AGENTS.md#environment-and-checks) |

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

**Status: DONE** · no crawl required · runs offline over existing JSONL. Shipped as `shopping_advisor/analysis/`, with `tests/test_analysis.py` and the evidence it was built from in `tests/cases/`.

A user can ask "which of these is better dry pasta, and why?" and get an answer traceable to the exact source sentence.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r0--pasta-v1-evidence-backed-comparison-over-existing-records).

---

## R1 — Crawl provenance and evidence preservation

**Status: DONE.** Shipped as `shopping_advisor/run.py` plus the spider wiring, with `tests/test_run.py` and the first saved search page in `tests/corpus/amazon_de_search/`.

A crawl is reproducible and auditable, and extraction work no longer requires a re-crawl: pages are retained with their digests and can be re-read by a later extractor.

**Open (2026-09-19):** the manifest does not count seeds requested against fetched or discovered listings against fetched, and `run_state` reads any closed manifest as complete even when `finish_reason` is `shutdown`; both are bucket B in [HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19).

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r1--crawl-provenance-and-evidence-preservation).

---

## R2 — Generic validation layer + published extraction contract

**Status: DONE.** Shipped as `shopping_advisor/validation/` and `shopping_advisor/analysis/categories/`, published as [CONTRACT.md](CONTRACT.md), with a validation snapshot in the corpus test. The rule that earned promotion was the one a *second* category had exercised: tyre mounting paste needed no change to the crawler, the extractor or any trust rule.

Downstream analyzers inherit trust semantics instead of reinventing them, against a documented, versioned record.

Not fixable downstream: `price_per_base` is `unknown` on 28 of 43 mounting pastes because 23 had no purchasable offer at crawl time. Deliberately not built: a `nutrition: bool` profile switch — a category telling the generic layer which rules to run is what the profile is shaped to prevent.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r2--generic-validation-layer--published-extraction-contract).

---

## R3 — Variation-aware product families

**Status: DONE**, with one of its two completion criteria **not met** and retired rather than worked around: a variation conflict that the source does not state cannot be detected by adding software.

Pack-size variants of one product are compared as a single offer family, and the "same pasta, sixteen ASINs" distortion disappears from rankings. The discovery/product *join* stays unbuilt until something reads it.

**Rule confirmed 2026-09-19:** Amazon variation parents mix distinct products — one held two Baseus models with two Qi certificates as "colours", another 15,000 and 20,000 mAh — so a generic fold by parent was rejected ([HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19)); the record view lists siblings with their model numbers instead.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r3--variation-aware-product-families).

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

**Status: DONE.** The decision test passed at 57% against a 30% bar, and the milestone cost roughly a tenth of its estimate: the review data is in the retained PDP HTML, and the larger version behind `/product-reviews/` needs an account. Shipped as `shopping_advisor/extraction/reviews.py` and `shopping_advisor/validation/reviews.py`, schema v5.

Review-only properties — does the rice smell of basmati, does it arrive with moths — enter the evidence as sampled, attributed statements with their population limits, never as facts about the product.

**2026-09-19:** a record view (bucket D in [HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19)) shows a listing's whole sampled review set with its size and source, so the operator reads all of it or none; a keyword search over the sample was rejected because it invites cherry-picking and counting a widget sample as a rate.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r5--reviews-as-an-evidence-source).

---

## R6 — A command line for the things every category needs

**Status: DONE.** The cheapest item on the roadmap and the best evidenced: four scripts were written and thrown away in one research question. Two of the four items were already shipped; the rest exposed capability that existed.

`shopping_advisor.run reextract` re-reads a retained run with the current extractor, and the analysis commands merge several feeds by ASIN. Every category gets both without code.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r6--a-command-line-for-the-things-every-category-needs).

---

## R7 — Attributed search: finding a claim vs crediting it

**Status: DONE.** Two categories hit the same bug: text on an Amazon page is not necessarily *about the product the page sells*. Measured on basmati, a field-wide search marked 53 of 239 records parboiled and 29 were wrong — cross-sell copy, A+ tables listing a brand's whole shelf, recipes, outright negations.

Finding a claim and crediting it are two decisions: `search` reports where a phrase was read and under which scope, and a category credits only what the page states about its own product.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r7--attributed-search-finding-a-claim-vs-crediting-it).

---

## R8 — Marketplace-aware text matching

**Status: DONE.** The motivating bug — a German compound noun (`Basmatireis`) lost to an English word boundary — was already fixed locally; R8 made the boundary policy a marketplace profile and the reporting honest about it.

Text matching reads the marketplace's language rules from its profile, and a listing lost to a boundary rule is reported as such rather than silently absent.

Scope, acceptance conditions and what was measured on completion: [HISTORY.md](HISTORY.md#r8--marketplace-aware-text-matching).

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

**Status: IN PROGRESS.** The first category application of the general
adaptation loop landed on 2026-09-18: `smartwatch`, written through
[R15](#r15--controlled-task-driven-capability-adaptation)'s procedure inside a
recorded study budget (22.8 s of 14 400 engineering seconds, one attempt of
three), with 39 positive cases, 16 declined listings each with its reason, and
every unstated criterion `not_claimed`. A day earlier the school backpack was
written mid-study as reviewed maintenance, with no gate to pass through. Both
records: [HISTORY.md](HISTORY.md#r11--category-synthesis-as-a-default-step).

**Established:** the first, second, third and fifth conditions below — created
within budget through R15 with cases and guards; the report says the method is
provisional and no value's status moved for it; the profile adds no rule and
the old categories pass their gates; R16 records the capability as an
experiment, retained. **Open:** the fourth — a changed buyer preference changes
the brief or the declared method and the decision difference replays. One test
over two briefs on the committed smartwatch cases would close it; then the
runbook makes synthesis the default step. A candidate second case waits in the
powerbank review of 2026-09-19 ([HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19), bucket H): 58 retained
Amazon.de records whose tables say "kabellos: Nein" on certified Qi2 banks and
swap dimension axes — knowledge that belongs in a category, not in generic code.

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

**A third blind spot, measured 2026-09-19.** In the iPhone 15 Qi2 powerbank
review the recommended model was discovered four times and never fetched,
because every query carried the buyer's minimum capacity as a literal and five
products per query were taken; the two 20,000 mAh leads came from press and the
certifier's database, not from the marketplace search. The postmortem and the
consolidated plan are in [HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19).
**Consequences for this milestone:** a read-only discovery reconciliation over
run directories (bucket E: named ASIN or model → fetched, discovered-unfetched
with query/position/sponsored, or absent; a near-miss list against the plan's
brands and models; named candidates carry a recorded source; search-only
crawling is an option, never the default); manifest counts for seeds
requested/fetched and discovered fetched/unfetched (bucket B, with R1); and two
evidence-ledger source kinds, certificate and safety notice, with a **declared**
model mapping the tool checks for consistency and never infers (bucket F). A
generic fold-and-sort shelf table and automatic model-number matching were
rejected against counterexamples from the same run — see
[deferred and rejected work](#deferred-and-rejected-work).

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
- Every candidate the plan names has a recorded source and a disposition from
  the discovery log alone — fetched, discovered but not fetched, or absent —
  before any report is written; the manifest states how many seeds and
  discovered listings were fetched and how many were not.
- An external certificate or safety notice enters the evidence ledger with a
  declared model mapping and renders per candidate as declared, checked or not
  looked up; a certificate that applies is never rendered as safety.

---

## R13 — The conversation as the entry point

**Status: DONE (2026-09-18). Depended on shipped T2/T3; did not wait for R11.**
The machinery of [INTAKE §16](INTAKE.md#16-implementation-sequence), stages
1–10, shipped on 2026-09-17; three conversational trials ran on 2026-09-17 and
2026-09-18. The stage table, the trial records, the review chain and the
defaults decided afterwards are in
[HISTORY.md](HISTORY.md#r13--the-conversation-as-the-entry-point).

**Closed 2026-09-18, on the maintainer's review and decision.** Three trials are
recorded in HISTORY: the first (2026-09-17) by the user who wrote the documentation,
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

**Open after close (2026-09-19).** The powerbank review, the fourth
unsupported-category conversation, found two gaps in this milestone's
machinery, recorded in [HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19): the session ledger wrote `completed`
for a crawl the user stopped, because `run_state` maps any closed manifest to
complete (bucket B: map `finish_reason`, add `collections` as a limit unit, and
let a dependent cite an interrupted predecessor when it declares it builds on
partial evidence — without that companion the honest state blocks work); and
the unsupported-category procedure has no report template, so one review folded
safety, warranty, thickness and fit into one light, read missing evidence as
red, inferred fit from an image and buried the shortlist (bucket C: a
bounded-review template and checklist in RESEARCH.md, with the rewritten
powerbank report as the worked example). Neither reopens the Done-when list;
both are maintenance under it.

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

**Status: IN PROGRESS, closing.** The procedure (Phase 0), the `smartwatch`
category as the first adaptation (Phase 1), the study resting on it (Phase 2),
the dive claim repaired (Phase 3), the extraction case decided by inspection
(Phase 4), the payment claim repaired on the independent reviewer's finding
(Phase 5), the plan revision 8–10 review chain and the two remaining failure
cases shipped on 2026-09-18 and 2026-09-19. Every dated entry, with its
numbers, is in
[HISTORY.md](HISTORY.md#r15--controlled-task-driven-capability-adaptation).
T4's local maintenance gate is the baseline R15 validates against; the
provider and platform trials deferred from T4 are not a dependency.

**Established.** A patch is captured between a base tree and a worktree,
inspected statically before anything imports it, run inside a kernel boundary
(`sandbox-exec`, deny by default, an external watchdog) against a frozen
evaluator set, reviewed, adopted by a role once, and rolled back at the base;
a study binds the record's method descriptor into its id and carries the
record. Four real adaptations passed through it: a category (method v1), two
claim repairs (method v2 and v3 — five listings lost a dive claim, five a
payment claim, each on a finding a review or an inspection made), and an
additive extraction change (schema v6: A+ prose and comparison tables read as
structure; ten card values moved, no decision). The gate replays three studies
resting on them. Failure cases in the suite: a write, a read and a network
attempt outside the boundary fail; an instruction planted in a product page
stays source text with its provenance, and a planted *statement* is credited
lexically and quoted where the engineer reads it; a check killed at the timeout
has no pass; a patch touching the evaluator set is refused at capture; a spent
budget refuses the next attempt; a `harness-only` exception is labelled in the
check, the runner, the binding and the bundle's caveats and counts toward
nothing below. Two attempts were burnt on wrong pins during Phase 5 and stayed
on the record. The first control case, `axis_bound`, was built ahead of the
gates as reviewed maintenance and is recorded as such.

**Not established, and open.** A faulty patch withdrawn on a *real* category
regression — so far only fixture-defect withdrawals and a recorded non-zero
exit. The boundary is measured on one machine, with a tool Apple deprecates
([R17](#r17--portability-evidence)); the static inspection reads names, not
intent. The plan a category can answer reached its ceiling under independent
review at revision 10 (`limited` on the `missing_context` it declares), which
is [R12](#r12--discovery-that-states-its-own-coverage)'s problem. The
maintainer's open decisions: a tenth gate example under revision 10, and the
`.tmp-*` write allowance the
[second architectural review](#architectural-review-2--2026-09-19) scheduled
for removal before R14.

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

**Status: IN PROGRESS.** The capability index, the lifecycle records of the
five registered categories and two architectural reviews have shipped
(2026-09-18 and 2026-09-19); their entries and measurement tables are in
[HISTORY.md](HISTORY.md#r16--capability-lifecycle-and-architectural-review).
The *task-experiment entry* — a capability arriving inside a study with a patch
digest, a scope bound to the study and isolated checks — happened on
2026-09-18: `smartwatch` is the first capability whose lifecycle record points
at an adaptation record rather than at reviewed maintenance. What still waits
is the promotion evidence that flows from being reused: no capability has had a
distinct second use. The minimum lifecycle precedes R14; periodic review
continues after the first operating-model release.

### Architectural review 1 — 2026-09-18

Held at the operating-model milestone (INTAKE §16 shipped) with the count of
extension-bearing studies at one. Every decision was retain, with a
checkpoint; two of those checkpoints later fired and were missed, which review
2 records. Full record with measurements:
[HISTORY.md](HISTORY.md#architectural-review-1--2026-09-18).

### Architectural review 2 — 2026-09-19

**Trigger.** R15's first shipped adaptation (`smartwatch`, Phase 1,
2026-09-18), which review 1 named as its next checkpoint; held after the
fourth, once the extraction case and the plan revision 8–10 chain were on
record, so that the review reads a procedure that has been used rather than
one that has been used once. Reviewer: the operating agent, on the
maintainer's request; owner of every decision below: the **repository
maintainer**. Supporting study IDs are the nine the gate replays —
`pasta-bronze-die-bde2b027b117`, `pasta-low-temperature-drying-48df9d940ced`,
`pasta-delivered-cost-43425b41286a`, `pasta-purchase-budget-5c28fb92681b`,
`basmati-audit-positive-49ef55740633`, `basmati-audit-insufficient-50e21e1c7b99`,
`pasta-bronze-die-306e33f25417` (the fixture adaptation),
`smartwatch-dive-nfc-8f62da3c1256` and
`smartwatch-dive-nfc-reextracted-d83a15c291ca` — the four private
school-backpack bundles and the smartwatch scratch bundles under R13 and R15,
whose IDs are not in the repository, and the four adaptation records
(`data/adaptations/`, two of them committed as fixtures under
[tests/intake](tests/intake/README.md)).

**The count.** The cadence counts *extension-bearing* studies, and until now
nothing said what one is. The rule used here: a committed study whose manifest
binds an adaptation record with a method descriptor no earlier committed study
bound, or a study for which a category entered as reviewed maintenance. That
gives the school backpack (one), `smartwatch-dive-nfc` (two; records one and
two), `smartwatch-dive-nfc-reextracted` (three; records three and four). The
fixture adaptation carries a semantic-free patch and does not count.

Measurements — import edges, leakage, duplication, unused capabilities, replay, test cost, size and debt — are in [HISTORY.md](HISTORY.md#architectural-review-2--2026-09-19). The decisions below are the live ones.

**Decisions.** Retain, simplify or retire, each with its evidence, its owner
(the repository maintainer throughout) and a next checkpoint. One
simplification was carried out in this review as its own commit, because its
checkpoint had already fired and been missed; everything else is scheduled
against a change that will touch the file anyway, or against a date.

| Decision | Subject | Evidence and reasoning | Next checkpoint |
|---|---|---|---|
| **Retain** as maintained | `dry_pasta`, `tyre_mounting_paste`, `basmati_rice` | Nothing since review 1 moved their evidence or their decisions; the gate replays six of their studies unchanged. Mounting paste's second buyer and basmati's committed record set are still absent, and still written in their declarations | Review 3 |
| **Retain** as experiment | `school_backpack` | No distinct second use. The `axis_bound` control was built on its cases as reviewed maintenance — a control the category publishes, not a reuse of the category | The next backpack-class study |
| **Retain** as experiment | `smartwatch` | Method version 3 after four adaptations; two committed studies from one brief lineage and one buyer. One buyer is not a distinct subsequent use, and the plan revision 8–10 chain established that the category answers one control, the classifier | A second buyer or a distinct brief |
| **Simplified now** | `read_jsonl` housed in `run.py` | Review 1's checkpoint fired at `89c854b` and was missed. Moved to `shopping_advisor/jsonl.py`; `run.py` keeps the documented name; three importers switched. Measured: the `analysis → run` and `study.delivery → run` edges gone, `study → run` down to the one manifest-reading edge; no test changed; every example decision unchanged | — |
| **Retain** the copies, checkpoint moved with reasons | Five `claims()` loops, three `stated()` helpers | Both of review 1's triggers fired — the fifth category, and it agent-written — and the evidence points the other way: the agent reproduced the loop correctly at the first attempt, and the four adaptations changed a classifier boundary and two claim patterns, never a loop. A shared helper would not have prevented any of the four and would carry parameters for three variants. The argument that changes this is a defect *in* a loop | A loop-level defect, or the sixth category |
| **Retain** | `study/bundle.py`'s basmati branch; spider and CLI defaults; `render_extra`; the two unvalidated marketplace profiles; `settings_scrapeops` | Unchanged since review 1: one consumer, documented defaults, unproven is not obsolete | Review 3; R4 on a stated need |
| **Retain** as the v6 structure | `content.aplus.comparison`, `aplus.prose` | One consumer each, in the layer that reads text; the change moved ten card values on 16 of 55 pages and no decision. The A+ alt-text hypothesis (image captions versus the brand carousel) stays labelled and unbuilt | The next extraction adaptation |
| **Retain**, and decide the open question | The `harness-only` exception path | Exercised end to end in the suite; the bundle now names it wherever it is read. **No ledger field for the exception:** the record's `runner.exception` names the maintainer's message and travels with the study; a ledger field would be a second copy of a decision the record already binds | A real exception, if one is ever needed |
| **Simplify, scheduled to a date** | The `.tmp-*` write allowance in the kernel profile | Nine brief writes beside fixtures in seven test modules exist only for relative input resolution; `brief.py` resolves absolute inputs, so the briefs can live in `TMPDIR` and the profile's regex can go. A boundary tightening deserves its own change with the probe re-run, not a ride on this review | Before R14's first trial; review 3 verifies |
| **Debt, hardened** | No committed replayable study for mounting paste or school backpack | The soft checkpoint ("the next change touching either category") was missed once. A brief over each committed cases file, as gate examples with baseline rows | Before R14's first trial; review 3 verifies |
| **Debt, recorded** | `study/__main__.py` growth | 1 106 lines and 28 commands is a size, not a defect; each milestone has added a block of commands to one file | The next milestone that adds commands moves its block to its own module in the same diff; review 3 verifies |
| **Fixed 2026-09-19** | A `harness-only` study looked like a kernel one wherever the bundle was read | `code_caveats` names the boundary; the label in the binding is verified | — |
| **Closed** | Provisional-method report status | R15 Phase 1: the report and the ranking artifact say the method is provisional; `ProvisionalMethod` pins it | — |

**Next review.** The fifth extension-bearing study under the rule above, or
the next operating-model milestone — R15 closing or R14's first trial —
whichever comes first; the count stands at three. Owner: the repository
maintainer.

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
| Generic fold-and-sort shelf table over feeds | **REJECTED (2026-09-19)** | Folding by variation parent merged two Baseus models with two Qi certificates and a 15K with a 20K bank; sorting on table dimensions ranks swapped axes; sortable rating columns are the shared scoring R10 defers. Replaced by a per-record view with no fold, sort or category ([HISTORY.md](HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19)). Reconsider when a category declares which fields fold and sort. |
| Review-sample keyword search | **REJECTED (2026-09-19)** | The 13 sampled reviews are Amazon's widget selection; a search invites cherry-picking, counting the sample as a rate and reading absence as evidence — the review's own over-read of one iPhone 15 Pro remark is the case. The record view shows the whole sample instead. |
| Automatic model-number matching of certificates and recalls to listings | **REJECTED (2026-09-19)** | Exact matching yields false negatives (`PB763` vs `PB763 v2`, `BPD014hqBK` vs `BPD014`); fuzzy matching conflates E0028Z with E0028V, two certificates; recalls by serial range over-flag by model. Replaced by a declared mapping the tool checks for consistency (bucket F). |
| Search-only two-phase crawl as the default | **DEFERRED; kept as an option** | Doubles search requests and hands the buyer the shelf to read. Use when a buyer wants to steer; read back near-misses, never the shelf. |
| Category-free bundle for bounded reviews (`verify`/`resume` without a category) | **DEFERRED (bucket G)** | A second bounded review that has to survive a handoff. Until then the correction-notes file is the handoff and the procedure says so. |

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

E2 (cross-query discovery overlap) is **resolved** — 20% of sightings were
repeats, over the 10% threshold, and the persistence split moved into R1 — and
E4 (does the trust bar leave enough to compare?) was answered inside R0; both
records are in [HISTORY.md](HISTORY.md#open-experiments--resolved). The
superseded P0–P6 hypothesis is kept there for its reasoning.
