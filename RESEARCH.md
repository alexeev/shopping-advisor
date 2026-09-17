# Product research runbook

This is the current workflow for the shipped tools. Read [AGENTS.md](AGENTS.md)
first. Acquisition and replay are provenance-bound, studies persist and replay,
external sources go through a ledger with claim checks and a separate semantic
review, and every automated check sits behind
[one local command](AGENTS.md#environment-and-checks). The stages that built
this are recorded in the
[roadmap](ROADMAP.md#agent-operation-transition); provider and cross-platform
trials are [deferred to R17](ROADMAP.md#r17--portability-evidence).

The permanent product interface is the coding-agent conversation. The
[revised product vision](ROADMAP.md#product-vision--the-shopping-conversation)
plans routine, controlled extension during research, including new sources,
extractors and methods. R13/R15/R16 define the missing planning, execution and
reuse gates; this runbook describes current operation until those gates ship.

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
uv run --offline --locked python -m shopping_advisor.analysis summary tests/cases/pasta_v1.jsonl.gz --category dry_pasta
```

Expect a provenance line reading 25 records from one feed on `amazon.de`, then
25 records, 22 classified as dry pasta, three other products, and no
undecided classification. The summary explicitly says accuracy is not measured:
a wrong rejection could still be a confident decision. Inspect the status
counts rather than treating a populated numeric field as usable.

### 2. Rank on the declared axis

```text
uv run --offline --locked python -m shopping_advisor.analysis rank tests/cases/pasta_v1.jsonl.gz --category dry_pasta --limit 3
```

Expect price-per-kg ranking, 14 offers with a trusted ranking value, and eight
excluded records. The first result is `B0CT3Q17FP` at the historical fixture
price of 1.58 EUR/kg. This establishes cheapest within these rankable fixture
records; it does not establish best pasta for a user or a currently purchasable
offer. Read the exclusion reasons below the ranking.

### 3. Inspect a card and its evidence

```text
uv run --offline --locked python -m shopping_advisor.analysis card tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 --category dry_pasta
```

Locate the quantity, price-per-kg value, statuses, and source quotations.
For this category the same card can be inspected as JSON:

```text
uv run --offline --locked python -m shopping_advisor.analysis card tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 --category dry_pasta --json
```

The provenance summary goes to stderr and JSON goes to stdout. A single
`card --json` is a pretty-printed object; use `cards --json` for JSONL across
category matches. Since T2 a card's JSON carries every section its text card
does, basmati's score and cultivar included: a category declares the card keys
it adds, and one it does not declare is not published. `rank --json` likewise
emits the whole ranking — every row, and every exclusion with its reason code,
where the text view stops at ten.

### 4. Compare two usable products

```text
uv run --offline --locked python -m shopping_advisor.analysis compare tests/cases/pasta_v1.jsonl.gz B08WJGD5Z5 B0DQ2N5HRW --category dry_pasta
```

Expect a `Differences` section including the cheaper-per-kilogram comparison.
Read the individual axes and caveats before turning that into purchase advice.

### 5. Exercise a refusal

```text
uv run --offline --locked python -m shopping_advisor.analysis compare tests/cases/pasta_v1.jsonl.gz B08JLSVW3J B08WJGD5Z5 --category dry_pasta
```

Expect `Price per kg` under `Cannot be compared`: the first product's pack
quantity is disputed. The card can show an alternative calculation without
promoting it to a trusted ranking value. Do not remove the contradiction to
force a comparison.

### 6. Inspect the underlying validation

```text
uv run --offline --locked python -m shopping_advisor.analysis validated tests/cases/pasta_v1.jsonl.gz --category dry_pasta
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

## A saved study end to end

The walkthrough above is a sequence of commands somebody has to remember
having run. A **study** is the same work with the question, the constraints and
the outcome written down beside the evidence, so that it survives the terminal.
Two briefs ship, both over the same committed feed and both offline:
[tests/studies](tests/studies/README.md) explains why there are two.

### 1. Check the brief before spending anything on it

```text
uv run --offline --locked python -m shopping_advisor.study check tests/studies/pasta-bronze-die.toml
```

Expect a valid `pasta-bronze-die` brief for `dry_pasta` on `www.amazon.de`,
ranking `price_per_base` in `EUR/kg`, requiring `bronze_die`, needing at least
three candidates that are 5.0% apart, as of 2026-09-16. Every line it prints
that says *(the category default)* is a decision the brief did not make.

Unknown keys are refused, not ignored: change `shortlist` to `shortlst` and the
command names it rather than quietly ranking without one.

### 2. Run it

```text
uv run --offline --locked python -m shopping_advisor.study run tests/studies/pasta-bronze-die.toml
```

Expect study `pasta-bronze-die-46127870314d` with outcome `recommendation`:
22 of 25 records classified as dry pasta, 5 offers ranked, 3 excluded, 14 short
of the required claim, 3 shortlisted. It writes
`data/studies/pasta-bronze-die-46127870314d/` and collects nothing — every byte
it read was on disk before the command started.

The bundle holds `manifest.json`, the validated `brief.json`, one line per
considered record in `candidates.jsonl`, the complete evidence card of every
classified candidate in `cards.jsonl`, the structured decisions in
`ranking.json`, `report.md`, `ledger.json`, `claim-index.json`,
`validation.json`, and `semantic-review.json`. The report's *What decided it* table is the
part worth reading first: it says of every decision whether the brief stated it
or the category supplied the default.

The study id is derived from the brief, the input digests and the published
schema/contract versions — not from the clock — so the id above is what a clean
checkout produces, and running it again in another directory writes
byte-identical artefacts. What the id deliberately does **not** cover is the
analysis code: a category rule can change a decision without changing the id,
which is what the next command is for.

### 3. Verify it without collecting again

```text
uv run --offline --locked python -m shopping_advisor.study verify data/studies/pasta-bronze-die-46127870314d
```

Expect `verified`: every artefact matches its digest, and every decision and
numeric claim re-derives from the declared inputs. This is also how another
environment picks a study up — `--input-root` says where the feeds are if the
bundle has been moved away from them.

`verify` reports, in this order and with the ones that invalidate everything
below them first: an unsupported manifest or brief version, a missing or
altered artefact, an input whose bytes are not the ones the study read, a code
revision that has moved, and finally a decision or numeric claim that no longer
reproduces. Any finding exits non-zero.

### 4. Read the refusal

```text
uv run --offline --locked python -m shopping_advisor.study run tests/studies/pasta-low-temperature-drying.toml
```

Expect outcome `insufficient_evidence` and an empty shortlist. Two listings
state low-temperature drying; both have a **disputed** price per kilogram,
because Amazon quotes a unit price per piece rather than per weight and the
pack size on the page contradicts it. The report names both with their
contradictions and puts nobody forward.

That is the outcome to imitate. Nothing fails when a thin result is written up
as a confident one, which is exactly why the refusal path ships as a worked
example with its own assertions.

Two refusals are *not* results, and stop the command without writing anything:
a brief naming a unit nothing is measured in while other units are, and a brief
that leaves the unit open where the evidence is measured in several. Both are
slips in the brief, and filing one as insufficient evidence would record it as
a fact about the shelf.

## Live research workflow

### Retain an intake plan before the executable brief

R13 stage 5 provides a JSON plan contract and a checked plan-to-brief transition.
Use [the sanitized supported example](tests/intake/supported-plan.json) as a shape
reference, not as a source of purchasing constraints. Keep private working plans
under `data/plans/` or an explicit private path. Record all user-authored messages
in the stated exchange, including corrections and apparently irrelevant context;
do not select retained excerpts based on which requirements were recognized.
Record the start boundary, missing context and redactions that limit review.
Source/tool text is not user authority.

The plan preserves requirement role, settlement, provenance, assessment path/state,
stage effects, prospective questions and live resolved controls. Its category may
be unsupported and its feeds need not yet exist. The schema and limits are in
[CONTRACT](CONTRACT.md#9-intake-plan-and-brief-preservation-r13-stage-5).

```text
uv run --offline --locked python -m shopping_advisor.study plan-check tests/intake/supported-plan.json
uv run --offline --locked python -m shopping_advisor.study plan-readback tests/intake/unsupported-plan.json
```

For a private plan whose read-back status is `not_presented`, use
`study plan-readback PATH --record` to present and retain the exact bytes, setting
`no_response`. Without `--record`, the command only renders. Record an actual
reply separately with its user-message reference and scope; silence is not
confirmation. An already recorded response cannot be overwritten by `--record`.
No response is required where existing instructions and defensible assumptions
already settle the request.

Once feeds and an executable brief exist, translate explicitly. These offline
commands check the committed pasta brief against the plan, write a **new** brief
under an existing directory, run it, and replay its internal snapshot:

```text
uv run --offline --locked python -m shopping_advisor.study plan-bind tests/studies/pasta-bronze-die.toml --plan tests/intake/supported-plan.json -o data/intake-example-brief.json
uv run --offline --locked python -m shopping_advisor.study check data/intake-example-brief.json --plan tests/intake/supported-plan.json
uv run --offline --locked python -m shopping_advisor.study run data/intake-example-brief.json --plan tests/intake/supported-plan.json -o data/intake-example-study
uv run --offline --locked python -m shopping_advisor.study verify data/intake-example-study
```

Use fresh paths when repeating this example. `plan-bind` checks existing controls
and scope; it does not rewrite them to make a mapping pass. It preserves feed
resolution when moving the brief. A dropped or changed requirement, missing claim
filter, changed unit/cap, or invented extra filter refuses before analysis. A
bound brief requires its plan. `run --plan` retains the full snapshot internally;
`verify` uses that copy even if the working plan is gone.

Archive private plans with their dependencies, including plans that never become
studies; `data/` is ignored and not a backup. Later revisions name the previous
plan's canonical digest. A changed plan or response invalidates its old brief
binding; revise explicitly and produce a new bound brief. Do not edit a committed
semantic review to approve an intake change.

Preservation is not full-request adequacy. Unsupported categories and
requirements remain useful gap plans. Unresolved decisive requirements and
unreconciled corrections cannot cross the bridge; `plan-check` reports them as
`blocked` and names the next action. A settled decisive requirement with **no
executable control** does cross it, into a bounded study: the
[stage gates](CONTRACT.md#10-stage-gates-r13-stage-6) withhold the purchasing
recommendation, put no candidate forward, and keep the ranking on the available
axis under its own `Bounded finding` heading that names the narrower question it
answers. `plan-check` reports that plan as `bounded`, `run` prints the stop
beside the analytical outcome, and the manifest records both. The committed
delivered-cost case is the reference:

```text
uv run --offline --locked python -m shopping_advisor.study plan-check tests/intake/delivered-cost-plan.json --brief tests/intake/delivered-cost-brief.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/delivered-cost-brief.json --plan tests/intake/delivered-cost-plan.json -o data/intake-delivered-study
```

Write the bounded axis into the plan as the agent's own requirement — author
`agent`, not decisive, with its rationale — rather than mapping the user's
unsupported objective onto it: the second is the substitution the comparison
gate refuses when it can see it, and cannot see when the plan disguises it. A
decisive hard constraint whose bound assessment `failed` renders as "Requirement
cannot be met"; one still `awaiting_evidence` is routed to collection or a
coverage stop, not to a capability gap. The intake review is the next
subsection; delivery freshness and the session ledger follow it. A passing
`plan-check` is neither
semantic approval nor authorization for engineering, and a gate that reports
every requirement `enforced` has not established that the controls answer them.

### Review the plan in a separate pass

A structurally valid plan is not a faithful one. The
[intake review](CONTRACT.md#13-intake-review-r13-stage-9) is the semantic pass
the gates cannot perform: whether every instruction in the retained messages
reached the plan, whether each requirement's role and settlement are what the
words support, whether each control answers the requirement it is mapped to —
the budget mapped onto the per-kilogram cap passes the gates as `enforced` and
fails here — whether each assumed default was defensible, and whether the stage
effects are the ones the meaning implies.

```text
uv run --offline --locked python -m shopping_advisor.study plan-review-template data/plans/<plan>.json -o data/plans/<plan>-review.json
uv run --offline --locked python -m shopping_advisor.study plan-review data/plans/<plan>.json data/plans/<plan>-review.json
uv run --offline --locked python -m shopping_advisor.study run BRIEF --plan data/plans/<plan>.json --intake-review data/plans/<plan>-review.json
uv run --offline --locked python -m shopping_advisor.study review-intake data/studies/<study_id> data/plans/<plan>-review.json
```

Fill each check with findings and name the reviewer; a failure names the
requirements or user messages it concerns. Record `limited`, not `pass`, where a
redaction or missing context kept wording from you: the template lists those
limits and the contract refuses a pass over them. The review binds the plan
revision and the category's live control catalogue — revise the plan and it is
superseded, change the catalogue and its adequacy finding is stale, and neither
is carried forward. `run --intake-review` refuses a plan its review says
misreads the request; `review-intake` attaches a review to a study that has
already run; `validate-report --require-review` needs a passing one on a
plan-backed study. A passing review is not the buyer's confirmation — the
read-back response status stays what it was — and it authorises no engineering.
The committed delivered-cost review is the reference:

```text
uv run --offline --locked python -m shopping_advisor.study plan-review tests/intake/delivered-cost-plan.json tests/intake/delivered-cost-intake-review.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/delivered-cost-brief.json --plan tests/intake/delivered-cost-plan.json --intake-review tests/intake/delivered-cost-intake-review.json -o data/intake-reviewed-study
```

### Deliver the study, and say what it is

A report does not stay current because it was current once. The analysis
measures every observation against the brief's `as_of`, which is the historical
question and the one the brief's author controls; the
[delivery record](CONTRACT.md#11-declared-scope-and-the-delivery-record-r13-stage-7)
measures the shortlisted and ranked observations against the instant the answer
is actually handed over, which they do not.

Declare what the study is in the brief. `freshness.scope = "historical"` says
these observations are not offered as current advice however recent they are —
every committed example is historical, and a brief that says nothing is read as
historical. `freshness.scope = "current_advice"` says the buyer will act on this
now, and needs `as_of`, `price_max_age_days` and a `note` saying why that bound
is adequate. Then, at each delivery event:

```text
uv run --offline --locked python -m shopping_advisor.study deliver data/studies/<study_id>
uv run --offline --locked python -m shopping_advisor.study validate-report data/studies/<study_id> --require-review
```

`deliver` reads the execution clock, freezes it in `delivery.json` and records
whether current advice is `permitted`, `blocked` or `not_in_scope`; pass
`--reference ISO` only to replay or test, and the record then says the reference
was declared rather than read. A blocked current-advice study fails
`validate-report` whatever its semantic review says: deliver a separately scoped
historical comparison with its reference date, or recollect. Delivering an old
study again is a new event and a new assessment; `verify` recomputes every event
from its frozen reference and never reads today's clock. None of this proves the
clock honest, and none of it can tell that a declaration is false.

### Keep the session's resource ledger, and resume from the files

Per-crawl provenance says what one run spent; the
[session ledger](CONTRACT.md#12-session-resource-ledger-and-resumption-r13-stage-8)
says what the session was allowed, what it has spent across inspections, probes,
collections and interrupted runs, and what it may still do. Keep the working
ledger under `data/sessions/` or an explicit private path, and snapshot it into
every study it funds with `run --session`. Declare limits in the units the run
manifest reports — responses, requests, items, seconds, retained pages, runs —
and keep research and engineering allowances apart: willingness to investigate
products does not fund development, and an engineering proposal is recorded
against its own allowance and never authorised here. Say whether a limit stops
new work or is a strict ceiling, and for a ceiling name the closure setting and
its known overshoot; a monetary or token figure is an estimate and can only stop
new work.

Before a probe or a collection, check it, and record what it did from the
manifest the crawl wrote:

```text
uv run --offline --locked python -m shopping_advisor.study session-authorise data/sessions/<session>.json <action> --record
uv run --offline --locked python -m shopping_advisor.study session-record data/sessions/<session>.json <action> --run data/runs/<run_id>
uv run --offline --locked python -m shopping_advisor.study session-check data/sessions/<session>.json
```

Give a completed probe its `--result` and `--promotion` record in the same step;
the contract refuses a completed probe without them.
A crawl that never closed is recorded as interrupted with unknown consumption,
and unknown is not zero: the limit stays unreconciled and nothing new is
authorised until you record the manifest or, conservatively, count the whole
allocation as spent with `--assume-allocation`. A replay of retained bytes is
not acquisition. Resume an interrupted action as a new one that names it; the
predecessor's consumption is counted once. A completed probe records the result
that determined the next action and whether its evidence was promoted into the
declared inputs, whether seeing it changed the criteria, and whether it supplied
candidates — provenance alone does not make a comparison unbiased, and a material
change asks explicitly whether broader discovery is needed. Exhaustion refuses
the next action and names it; it deletes nothing.

Resumption needs the files, not the conversation:

```text
uv run --offline --locked python -m shopping_advisor.study resume data/studies/<study_id>
```

`resume` verifies the retained artifacts, checks the plan revision the ledger
names against the bundle's snapshot, reconciles the resources, confirms every
linked run manifest is present and unaltered, reads the review state, and
rechecks delivery freshness at the current instant without recording an event —
issue current advice only through `study deliver`. It either reports the
verified state with the next actions the ledger permits and prevents, or names
the precise missing dependency. Interrupted work is listed as interrupted, never
assumed complete. The committed
[delivered-cost example](tests/intake/README.md) is the reference: its session
ledger holds an interrupted collection recorded conservatively, a resumed
collection the remaining responses prevent, and a retained engineering proposal.

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
| **Blocking** | It could invalidate the purchase decision or cause substantial avoidable work, **and** existing context offers no defensible default | Ask before dependent work, collection included; meanwhile continue whatever does not depend on the answer |
| **Assumable** | A defensible default exists, and a wrong guess costs a paragraph rather than the study | State the default and what changes if it is wrong, then proceed |
| **Not worth asking** | The evidence will answer it, or the tools decide it deterministically | Do not ask |

Weigh the magnitude and likelihood of the consequence, the available budget and
the cost of asking. A question does not block because it is important; it blocks
because nothing in the existing context settles it. "You decide" permits a
reasoned choice within the delegated scope, and silence is not confirmation:
proceed on the default, and do not describe what follows as confirmed.

The marketplace and delivery region, a requirement that eliminates most of the
shelf, and the cost basis of a "cheapest" question are the common sources of
material divergence — worth checking every time, but not a fixed questionnaire
to read out. Each passes the test on its own. Nothing in a request settles which
marketplace a stranger buys on, and an Amazon.de ranking is useless to someone
buying elsewhere — the answer there is that only
[Amazon.de is validated](README.md#supported-scope), not a `.de` ranking handed
over anyway. An absent budget goes the other way: assume no cap, say so, and let
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
nothing in the repository knows what makes one *good*.

Say that, and say what it costs in time, confidence or the answer. Then produce
the evidence and gap plan: what each decisive requirement would need, whether
each gap wants a source, fresh acquisition, a parser, a category interpretation
or a comparison method, and what the next step is. Answering within stated
generic limits stays available where it helps, labelled as not a suitability
judgement. What does not belong in the conversation is an implementation menu —
choosing between building a module and doing without is not the buyer's decision
to make, and it is the step the
[product vision](ROADMAP.md#product-vision--the-shopping-conversation) removes.

Planning authorizes no engineering, and removing the question does not remove
the boundary. Building a category module is a scoped maintenance change under
the [maintenance workflow](AGENTS.md#maintenance-workflow) and the authorization
that already exists; it is not a new permission to ask for. R15's execution
gates will make that boundary explicit.

The plan carries why a category written in one sitting is weaker than a shipped
one. Every shipped category was built against real records, and `tests/cases/`
asserts its false-positive guards as loudly as its true positives — five pasta
records are committed *only* because an earlier reconciler disputed them
wrongly. Making category synthesis the default step, with the evidence behind
it, is [R11](ROADMAP.md#r11--category-synthesis-as-a-default-step).

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

Write it as a **brief file** — TOML or JSON — next to the feeds it will read.
`shopping_advisor/study/brief.py` holds the schema; the two committed examples
in [tests/studies](tests/studies/README.md) are the shape to copy. It
carries:

- Question, use case, category, marketplace and delivery region.
- `[constraints]`: the ranking axis and unit, the claims a candidate must
  state, a limit on the axis, the cost basis, the shortlist length, and the
  two stopping criteria — `minimum_candidates` and `decisive_margin`.
- `[freshness]`: an `as_of` date and how old a price may be. Age is measured
  against `as_of` and never against today, so the same study decides the same
  way tomorrow. `scope` says what the study is: `historical`, or
  `current_advice`, which also needs the policy and a `note` saying why the
  bound is adequate. Absent means historical. Whether current advice may
  actually be issued is decided at `study deliver`, against the clock, not here
  — see [delivering the study](#deliver-the-study-and-say-what-it-is).
- `[[assumptions]]`, `[[questions]]` and `[[sources]]`: the defaults taken and
  what changes if each is wrong, which questions were asked and which went
  unanswered, and the external sources named — declared, not verified.
- `limits` and `unacceptable`: what the study does not establish, and what was
  ruled out before it started.

Three of those fields are **recorded and rendered, not enforced**. `cost_basis`,
`unacceptable` and `limits` are prose: they reach the report and change no
decision. Two briefs differing only in them produce identical eligibility,
ordering and outcome — measured, and pinned by
[tests/test_intake.py](tests/test_intake.py). A brief whose `cost_basis` says
*delivered cost* still ranks on the listed price, and a budget written into
`unacceptable` excludes nobody. The stage gates read none of them either: a
requirement that exists only in those fields is one the plan never recorded, and
[tests/test_gates.py](tests/test_gates.py) checks that rewriting them neither
lifts nor causes a withheld recommendation.

`max_axis_value` **is** enforced, and caps the axis being ranked rather than
anything else. On a `EUR/kg` axis, a limit of 100 is a hundred euros per
kilogram — which excludes nothing from a shelf priced in single figures — and an
exclusion it does produce names `EUR/kg` in its reason. There is no control for
a purchase budget; [INTAKE.md](INTAKE.md#4-current-capability-boundaries) is
where that gap is being worked.

Check it before running anything: `python -m shopping_advisor.study check BRIEF`
prints every default it will fall back to. Unknown keys are refused rather
than ignored, because a misspelt constraint that silently does nothing
produces a study with no sign anything was asked. The brief is **data**: it
names a category by its registry key, never by an import path, and nothing in
it is imported, evaluated or interpolated into a command.

The two stopping criteria are the part worth writing before looking at the
data. `minimum_candidates = 3` says how many usable candidates it takes to
choose at all, and `decisive_margin = 0.05` says how far apart the top two
have to be. Written afterwards, they are a rationalisation of whatever the
evidence happened to support.

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
uv run --offline --locked python -m shopping_advisor.run inspect data/runs/ACTUAL_RUN_ID
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
uv run --offline --locked python -m shopping_advisor.run reextract data/runs/ACTUAL_RUN_ID --feed data/research-example-01.jsonl -o data/research-example-01-reextracted.jsonl
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

Use `study run BRIEF --evidence LEDGER.json` to retain the external ledger
and its indexed claims. The source schema, matching rules and explicit access
limits are in [CONTRACT](CONTRACT.md#8-study-audit-contracts-t3); a complete
[basmati example](tests/studies/t3/README.md) runs offline. Brief `[[sources]]`
alone remain declarations. The basmati legacy ledger preserves the old findings
as unverified, with no inferred URLs or current-batch applicability.

`study validate-report BUNDLE` checks schemas, source digests, claim scope,
listing matches and full replay including cards, scores and rendered prose.
It emits JSON and exits 1 for failed checks, 2 for unreadable input. Positive
and insufficient-evidence outcomes both pass when correctly framed. Stale or
unknown-age observations produce an explicit historical/incomplete label
against `as_of`; whether the study may be issued as current advice is the
delivery record's question, and a current-advice study without a passing
`delivery.json` fails validation with `delivery_missing` or
`current_advice_blocked`, review or no review.

Review `semantic-review.json` in a separate pass against the actual source,
variant and user priorities. Fill each checklist finding, name the reviewer
and preserve unresolved limits. Keep its report/evidence digest bindings.
Attach it with `study review BUNDLE COMPLETED_REVIEW.json`, then run
`study validate-report BUNDLE --require-review`; on a plan-backed study the
same flag also requires a passing
[intake review](#review-the-plan-in-a-separate-pass). Generated pending
checklists are not approvals. Arbitrary hand-written report additions fail exact rendering
checks; revise the structured evidence/brief and generate a new report instead.

Basmati's seven-part score remains optional category interpretation, completely
serialized and replayed. `rank` and study shortlists still use the declared
single axis, normally EUR/kg; no score-ordered shortlist is implemented.
External claim annotations do not change price eligibility or promote trust.
Assess delivered cost explicitly: absent shipping data is unknown, not zero.

Before delivery, check that decisive numeric values are usable, units/currency
agree, citations support the selected variant and claim, sample reviews are
not used for rates, and conclusions say “among sources/products inspected”
where coverage is limited. Record the checks and remaining uncertainty.
Automated report validation does not establish semantic truth. An honest
insufficient-evidence answer is a valid result.

### Close and capture improvements

Keep the study bundle and any hand-written report at explicit locations and
tell the user where they are. `data/studies/` and `reports/` are gitignored, so
a bundle is not backed up by existing: a study that has to survive is copied
somewhere it will, together with the feeds its brief names. A bundle replays
in another checkout only if those feeds are available there — the committed
examples are, and a study over a private crawl is not. Do not claim otherwise.

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
4. **Review and versioned adoption.** A green
   [`maintenance check`](AGENTS.md#environment-and-checks), a readable diff,
   `CONTRACT.md`'s version rules when a published meaning moves, and a dated
   roadmap entry for anything that changes policy rather than fixing a defect.
   If the change moves a floor the gate records, re-record the baseline in the
   same diff and say why. Lowering the bar to fit the change, silently, is the
   one thing this step exists to prevent.
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

Record, **when asking**, the uncertainty a question is meant to resolve and its
expected effect on the next action or decision. Expected value is the right test
for whether to ask and is not observable afterwards, which is why it is written
down first — the same reason the two stopping criteria are.

At close, review the observables against that record:

- What action depended on the answer? Did it establish eligibility, change scope
  or ordering, prevent avoidable work, or confirm a named load-bearing
  assumption? A question need not change the winner to be useful.
- What did asking cost — a round trip, a delay, four questions where one would
  have done?
- Which assumptions turned out to be load-bearing? Those should have been
  questions, and the report should have said what would change if they were wrong.
- Which defaults did the user accept every time? Those can become stated
  defaults rather than questions.

Remove or simplify a question when repeated evidence across studies shows it
adds no material value, and promote one to the blocking list in
[Agree the brief](#agree-the-brief) on the same footing. Do not infer necessity
from a single outcome observed afterwards — retrospectively almost any question
can be justified — and do not read explicit agreement out of silence.

This is the part of the loop that is easy to skip, because nothing fails when
it is skipped. A study that took four rounds of clarification and a study that
took one produce the same report; only this step tells the next agent which
one to imitate.

Keep the study's original evidence and explain any changed analysis after a
fix. Do not weaken a trust rule, a plausibility band or an elicitation default
to make a preferred product win.

## Current limitations

### Inspect executable controls before mapping requirements

```text
uv run --offline --locked python -m shopping_advisor.study controls --category dry_pasta
uv run --offline --locked python -m shopping_advisor.study controls --category tyre_mounting_paste
uv run --offline --locked python -m shopping_advisor.study controls --category basmati_rice
```

This read-only JSON catalogue resolves axes, directions, defaults and claim keys
from the live category registry. It describes all five mechanisms that move the
candidate set: required trusted claims, the selected-axis cap, classification,
value usability and offer grouping, including their parameters, stages and limits.
It reads no feeds and does not establish that evidence exists or that a mechanism
adequately represents the user's requirement.

The Python interface is `shopping_advisor.study.controls.catalogue(category_key)`
and `resolve(category_key, control, **parameters)`. For example,
`resolve('dry_pasta', 'max_axis_value', value=100, unit='EUR/kg')` resolves a cap
on the default price-per-kilogram axis, **not** a €100 purchase budget.
Unknown category/control/claim/axis keys and unsupported parameters refuse;
directionless axes cannot resolve as ranking controls. Units are exact measured
units, checked against cards during ranking, without conversion. Classification
and grouping are fixed mechanisms with no buyer-supplied predicate parameters.

`cost_basis`, `unacceptable` and `limits` remain narrative, and external claims
remain outside candidate eligibility. This catalogue is R13 stage 4 inspection.
Stage 5 consumes it for
[intake plans and preservation](#retain-an-intake-plan-before-the-executable-brief),
and stage 6's [gates](CONTRACT.md#10-stage-gates-r13-stage-6) withhold a
recommendation when a decisive requirement resolves to no control at all.

### Operational limits

| Limitation | What to do now | Planned stage |
|---|---|---|
| One analysis covers one marketplace; cross-marketplace comparison is unsupported | Name the marketplace with `--marketplace` and report only that shelf | R4, on demand |
| Evidence collected before T1 has no page digests, recorded fetch times or feed bindings | `inspect` reports such a run as `legacy`; label its freshness unknown rather than inferring it | — (historical data) |
| Feeds are bound by the run id on their records, not by a digest taken at close | Keep original feeds unchanged and record their paths; a merged multi-run feed reports `mixed` lineage. A study bundle does digest the feeds it read, so replay detects one that changed | — (acquisition ordering) |
| Failure capture is bounded, and search pages are retained only on request | Read the capped counters in the manifest; re-collect with `keep_search_pages=1` when discovery itself is in question | — (by design) |
| A quarantined page is evidence but not exportable | Re-extract it if needed; never promote it into the corpus or attach it to a report | — (by design) |
| A study id pins the brief, the input digests and the contract versions, but not the analysis code | Run `study verify`: a decision that moved because a rule changed is a finding, not a silent difference | — (by design) |
| Deterministic report checks cannot prove that source prose supports an interpretation | Complete the separate digest-bound semantic review | — (semantic judgment) |
| A brief's `[[sources]]` are declarations | Use the external ledger and indexed claims for checked applicability | — (by design) |
| Original full studies/reports and basmati source documents are not all tracked | Use the committed study examples for onboarding; request/rebuild missing evidence only when the task needs it; migrated citations remain unverified | — (historical access limits) |
| A bundle replays only where the feeds its brief names are available; `data/studies/` is gitignored | Copy the bundle and its feeds together, or build the study over committed cases | — (retention policy) |
| No two-provider acceptance trial, and no run on a second platform | Load the same canonical instructions; keep the work provider-neutral; do not claim proven provider handoff or cross-platform behaviour | [R17](ROADMAP.md#r17--portability-evidence) |
| The maintenance gate establishes that the repository still does what it says, not that what it says is true of any marketplace | Use it to finish a change; it replaces no part of source review or freshness judgement | — (by design) |

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
| A brief that will not load | The message names the field and lists what is allowed; `study check` is the cheap way to see it |
| A study that will not verify | The finding codes, in order: version, then artefact, then input, then code revision, then the decision that moved |

Do not recrawl just to reproduce a parser error whose page is already retained.
If the required evidence was never retained, record that limitation explicitly.
