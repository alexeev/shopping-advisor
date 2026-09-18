# Intake cases

The expectations R13 is graded against, written before the fields that will
carry them exist. [INTAKE.md](../../INTAKE.md) argues why these are the cases;
this file says what each one asks for and what an acceptable answer may and may
not claim.

Two rules govern how they are used, and both come from failures this repository
has already paid for.

**The expectation is written independently of the produced plan.** A reviewer
who grades an interpretation against the interpretation's own output certifies
its blind spots. Each case below states the request and the acceptable outcome
boundary in the buyer's terms, not in the vocabulary of whatever artifact ends
up representing it.

**They are graded as behavioural boundaries, not as wording.** Two agents may
reach the same acceptable outcome in different sentences. What is testable is
which outcome is reached, what it claims, and what it refuses.

A case marked **characterised** has its *current* behaviour pinned in
[test_intake.py](../test_intake.py) — today's answer, which is the wrong one in
every case so pinned. Those tests are expected to change when the stage that
repairs them lands, and that diff is the measured effect. A case marked
**conversational trial** has structural coverage from the stage named and no
fixture for the interpretation itself: that is graded in R13's acceptance
trials, which nothing here stands in for. The stages are
[INTAKE.md §16](../../INTAKE.md#16-implementation-sequence).

**Stage 5 structural coverage (2026-09-17).** The cases marked stage 5 below now
have a contract and executable preservation boundary in
[test_intake_plan.py](../test_intake_plan.py). This does not claim a conversational
trial or arbitrary-language understanding. `supported-plan.json` is a sanitized
synthetic exchange mapped to the existing historical pasta brief, including a
user message not selected as requirement evidence. `unsupported-plan.json` retains
the hedge-trimmer request, a capability gap, next step and consequential question
without requiring a category module or feed. Both include deterministic read-back
with **no response**, not fabricated user confirmation.

```text
uv run --offline --locked python -m shopping_advisor.study plan-check tests/intake/supported-plan.json
uv run --offline --locked python -m shopping_advisor.study plan-readback tests/intake/unsupported-plan.json
```

**Stage 6 gate coverage (2026-09-17).** The cases marked stage 6 below are
exercised by [test_gates.py](../test_gates.py), against the expectations stated
here and never against a produced plan. `delivered-cost-plan.json` with
`delivered-cost-brief.json` is case 6: the user's delivered-cost objective is
recorded as unsupported, the agent's listed-price axis is recorded as the agent's
own non-decisive choice, and the study withholds the recommendation while the
item-price ranking survives as a bounded finding. `budget-plan.json` with
`budget-brief.json` is case 7: the hundred-euro purchase budget is an unsupported
hard constraint, is never routed through the per-kilogram cap, and nothing is put
forward. Both are baseline examples the maintenance gate replays.

```text
uv run --offline --locked python -m shopping_advisor.study plan-check tests/intake/delivered-cost-plan.json --brief tests/intake/delivered-cost-brief.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/budget-brief.json --plan tests/intake/budget-plan.json -o data/intake-budget-study
```

**Stage 8 resumption coverage (2026-09-17).** `session-ledger.json` is the
sanitized session for the delivered-cost study, case 18: two research limits in
observed units (responses, and seconds as a strict ceiling naming its overshoot),
a zero engineering allowance, a completed inspection and probe with declared
consumption, a collection recorded as interrupted with its whole allocation
conservatively counted, the analysis, a resumed collection the remaining 55
responses prevent, and an engineering proposal that is retained and never
authorised. [test_session.py](../test_session.py) exercises the contract, records
from real run manifests, reconciliation and resumption; the maintenance gate runs
the study with this ledger and resumes it from the bundle's own snapshot.

```text
uv run --offline --locked python -m shopping_advisor.study session-check tests/intake/session-ledger.json --reference 2026-09-17T00:00:00+00:00
uv run --offline --locked python -m shopping_advisor.study run tests/intake/delivered-cost-brief.json --plan tests/intake/delivered-cost-plan.json --session tests/intake/session-ledger.json -o data/intake-resumption-study
uv run --offline --locked python -m shopping_advisor.study resume data/intake-resumption-study --reference 2026-09-17T00:00:00+00:00
```

**Stage 9 review coverage (2026-09-17).** `delivered-cost-intake-review.json` is a
completed intake review of the delivered-cost plan, written as a separate pass
against the case 6 expectation below and the retained message, never against the
plan's own output: five checks passed with findings that name the requirements and
message they concern, one agent-authored assumption assessed, the historical-scope
sentence recorded as carried by the brief's undeclared scope rather than by a
requirement row, and unresolved limits saying the reviewer is an agent and nothing
is user-confirmed. It binds the plan's canonical digest and the live `dry_pasta`
control catalogue; editing either supersedes it. Like the T3 reviews, it is a
fixture approval and must never be reused for another plan.
[test_intake_review.py](../test_intake_review.py) exercises the contract, the
redaction limits, the bundle snapshot, `verify`, `validate-report`, `resume`, and
case 7's semantic limit: a plan that maps the budget onto the per-kilogram cap
passes the gates as enforced, and an intake review that fails `adequacy` on
`budget` refuses the run. The maintenance gate runs the delivered-cost example
with this review and records `intake_review`.

```text
uv run --offline --locked python -m shopping_advisor.study plan-review tests/intake/delivered-cost-plan.json tests/intake/delivered-cost-intake-review.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/delivered-cost-brief.json --plan tests/intake/delivered-cost-plan.json --intake-review tests/intake/delivered-cost-intake-review.json -o data/intake-reviewed-study
```

**Stage 10 migration coverage (2026-09-17).** [test_migration.py](../test_migration.py)
holds the migration to "ids move; decisions must not": the six pre-migration
decisions are written into the test rather than read from the baseline, every
committed example is replayed against them under its new id, and the intake
review and session ledger fixtures are shown not to have moved. It also covers
the artifact inventory (a file without a binding row is refused by the writer
and reported by `verify`), the review basis as the inventory's `semantic` rows,
final review v2 refusing a v1 review outright and refusing approval over a
pending, limited, failed or absent intake review, the intake-review-then-final-
review order, the identity decision, and the dirty-tree caveat.
[test_delivery_review.py](../test_delivery_review.py) covers the delivery review:
the template bound to one event, the attestation a pass requires, bindings that
name what moved, `validate-report` owing a passing review only for a permitted
current-advice event delivered as audited, a later event as a new review while
the semantic review stands, and `verify` on a review that no longer binds.

**R15 adaptation coverage (2026-09-18).** `adaptation-session.json` is a
**session ledger v2**: the same shape as the v1 fixture above with an
engineering allowance the maintainer funded, so its `engineer-1` is
authorisable rather than a retained proposal. `adaptation-record.json` is the
committed **adaptation record** of a synthetic method patch — one new test
module and one README line against the base revision `1626b49` — captured
whole, inspected statically, checked once inside the kernel boundary (the full
offline suite, 815 tests, 21.6 s), reviewed, adopted and demonstrated
reversible. `adaptation-session-r2.json` is the ledger revision that names the
first one's digest and records what the attempt spent, from the record. The
three replay together as the gate's `pasta-adaptation` example: the bronze-die
brief over the same case feed, whose study id is `pasta-bronze-die-306e33f25417`
where the unadapted study is `pasta-bronze-die-bde2b027b117`, with the same
decisions — the method moved the id and nothing else did.
[test_adaptation.py](../test_adaptation.py) covers the record's closed fields
and bindings (a patch or check after the review supersedes it; acceptance needs
a passing review, a frozen evaluator and a finished passing check), tree
capture and static inspection, the boundary profile and — where `sandbox-exec`
runs, skipped and said so where it does not — the six refused probes and the
timeout that kills a hung check with its child, ledger v2 beside a v1 that still
refuses, and the study binding: a bound study's id, a tampered or renamed
record, an id without the method, and a reader without the inventory row.

```text
uv run --offline --locked python -m shopping_advisor.study adaptation-check tests/intake/adaptation-record.json
uv run --offline --locked python -m shopping_advisor.study session-check tests/intake/adaptation-session-r2.json --reference 2026-09-18T12:00:00+00:00
uv run --offline --locked python -m shopping_advisor.study run tests/studies/pasta-bronze-die.toml --adaptation tests/intake/adaptation-record.json --session tests/intake/adaptation-session-r2.json -o data/adaptation-example-study
```

**R15 phase 2 coverage (2026-09-18).** The first study resting on a real
adaptation. `smartwatch-plan.json` is the third R13 trial's intake plan,
revision 7, committed as it is (case 20 below is its lesson); it maps no
control to any requirement, because it was written when no category existed,
and its independent review is not committed because `run --intake-review`
refuses it: the review's basis recorded no control catalogue and the live
`smartwatch` catalogue exists now. `smartwatch-brief.json` is the plan-bound
brief over the three retained probe feeds under `data/evidence`, with the
plan's question and use case verbatim, no required claim and no explicit axis —
the plan carries none, and `plan-bind` refuses a filter it does not. It says in
its limits that the price order is the category's default and not the buyer's
ordering. `smartwatch-adaptation.json` is the **accepted adaptation record** of
the category (R15 phase 1) — the 10-file patch archived whole, one gate run
inside the kernel boundary that failed on exactly the declared baseline moves,
the review, the adoption and the demonstrated rollback; only the runner's
interpreter and temporary-directory paths were made repository-relative, and
the check's output path names the scratch directory of the run, whose output
is identified by its digest. `smartwatch-session.json` is the trial's v2 ledger
at revision 5 with `engineer-1` completed from that record, the three probes
pointing at their committed manifests (the same bytes) and `analyse-3`, the
study run, completed with its declared seconds. Together they replayed as the
gate's `smartwatch-dive-nfc` example under method version 1:
`smartwatch-dive-nfc-2d5b51c7d0d9` (phase 3 below moved it), 39 of
55 classified, 35 priced offers, the recommendation withheld on six decisive
requirements, the price order as the bounded finding, delivered as history and
resumable from its own snapshot. The comparison with the trial's hand-read
table is in [ROADMAP](../../ROADMAP.md#r15--controlled-task-driven-capability-adaptation).

```text
uv run --offline --locked python -m shopping_advisor.study plan-check tests/intake/smartwatch-plan.json --brief tests/intake/smartwatch-brief.json
uv run --offline --locked python -m shopping_advisor.study adaptation-check tests/intake/smartwatch-adaptation.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/smartwatch-brief.json --plan tests/intake/smartwatch-plan.json --session tests/intake/smartwatch-session.json --adaptation tests/intake/smartwatch-adaptation.json -o data/smartwatch-example-study
uv run --offline --locked python -m shopping_advisor.study verify data/smartwatch-example-study
uv run --offline --locked python -m shopping_advisor.study resume data/smartwatch-example-study --reference 2026-09-18T20:00:00+00:00
```

**R15 phase 3 coverage (2026-09-18).** `smartwatch-dive-claim.json` is the
**second adaptation record**: the dive claim repaired as method version 2 —
three files captured whole, a first check that exited 71 without importing
anything (the runner's relative `.venv`, since fixed in the CLI) and a second
that failed inside the kernel boundary on exactly the declared method-version
move, the review, the adoption and the rollback demonstrated before the ledger
accounted for it. Its `predecessor` names `smartwatch-adaptation.json`'s
private original by canonical digest, the first use of the `adaptation` link;
the committed copy differs from that original only in the runner's two paths,
as this one does from its own. `smartwatch-session.json` now carries
`engineer-2` completed from the second record and `analyse-4`, the
re-derivation of the study under the new method. The gate's
`smartwatch-dive-nfc` example binds the second record: its id is
`smartwatch-dive-nfc-8f62da3c1256` where the same brief under method version 1
was `smartwatch-dive-nfc-2d5b51c7d0d9`, with every decision unchanged — the
claim that moved on five cards is not among the decisions the baseline pins.

```text
uv run --offline --locked python -m shopping_advisor.study adaptation-check tests/intake/smartwatch-dive-claim.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/smartwatch-brief.json --plan tests/intake/smartwatch-plan.json --session tests/intake/smartwatch-session.json --adaptation tests/intake/smartwatch-dive-claim.json -o data/smartwatch-v2-example-study
```

**R15 phase 4 coverage (2026-09-18).** `aplus-comparison.json` is the **third
adaptation record** and the first outside the category layer: the A+
comparison table published as structure (`content.aplus.prose` without table
cells, `content.aplus.comparison` with the ASIN each column links and the own
column by exact ASIN or none) and the vendor-text search reading prose and
the own column's rows, so that another product's cell is no longer this
product's statement. Ten files captured whole from base `3e8dc56`, three
checks inside the kernel boundary — the corpus snapshots regenerated to the
scratch directory, a gate failed on one test-fixture defect and withdrawn, a
gate at exit 0 — the review, the adoption and the rollback before the ledger
accounted for it. The committed copy differs from the private original only
in the runner's two paths. `smartwatch-brief-v2.json` is the same plan-bound
brief over the three `-v2` evidence feeds, re-extracted offline from the
retained pages under the adopted code (56 records: one page of the named run
no longer matches its recorded digest and the replay refused it), and the
gate's ninth example binds it: `smartwatch-dive-nfc-reextracted-92117d8f7fef`,
39 of 54 classified, the same 35 offers and the same withheld recommendation,
with ten card values moved and no decision — the Instinct 3 50 mm's 40 h GPS
runtime, read from a table that does not contain it, is `unknown` now.
`smartwatch-session.json` carries `engineer-3` (the bounded inspection,
declared), `engineer-4` (completed from the third record) and `analyse-5`.

```text
uv run --offline --locked python -m shopping_advisor.study adaptation-check tests/intake/aplus-comparison.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/smartwatch-brief-v2.json --plan tests/intake/smartwatch-plan.json --session tests/intake/smartwatch-session.json --adaptation tests/intake/aplus-comparison.json -o data/smartwatch-v3-example-study
uv run --offline --locked python -m shopping_advisor.study verify data/smartwatch-v3-example-study
```

**R15 phase 5 coverage (2026-09-18).** `nfc-payment-claim.json` is the
**fourth adaptation record**, predecessor the third: the category's
`nfc_payment` claim narrowed to a payment service or a contactless-payment
phrase after the independent review of plan revision 8 found a connectivity
row's bare "NFC" credited as a payment statement. Three files from base
`703be57`, three checks inside the kernel boundary — the whole budget — the
first two failing on a pin the hypothesis had wrong (the Amazfit states
"Mit Zepp Pay und NFC bezahlst du" and rightly keeps the claim), the third on
exactly the declared `method_version` move; review, adoption and rollback
before the ledger accounted 85.3 s. The ninth example now binds this record:
`smartwatch-dive-nfc-reextracted-d83a15c291ca`, with five Huawei cards losing
`nfc_payment`, fifteen keeping it, and every decision unchanged.
`smartwatch-session.json` carries `engineer-5` and `analyse-6`.

```text
uv run --offline --locked python -m shopping_advisor.study adaptation-check tests/intake/nfc-payment-claim.json
uv run --offline --locked python -m shopping_advisor.study run tests/intake/smartwatch-brief-v2.json --plan tests/intake/smartwatch-plan.json --session tests/intake/smartwatch-session.json --adaptation tests/intake/nfc-payment-claim.json -o data/smartwatch-v4-example-study
```

The [runbook](../../RESEARCH.md#retain-an-intake-plan-before-the-executable-brief)
contains the full bind/run/verify sequence. The test suite exercises those CLIs,
checks the expected original decisions, and replays after deleting the originating
plan. Mutation cases independently drop the bronze requirement or its executable
claim filter: both refuse before feed processing. No generated plan is used as
the oracle for what the user meant. Private conversations do not belong here;
record only sanitized synthetic or explicitly reviewed examples.

---

## Requests that should simply work

**1 — Enough context to proceed.** *"I cook pasta most weeknights and I've
decided bronze-die is worth paying for. Cheapest per kilo on Amazon.de,
delivered in Germany."* — Acceptable: the study proceeds with no questions and
no confirmation ritual. Not acceptable: a questionnaire, or a confirmation step
presented as a permission gate. **Stage 5** carries the structure — settlement, questions with their expected effect, delegation, assumed constraints that still bind, an unsupported category as a valid plan; **conversational trial** pending for the interpretation.

**2 — One clarification that is consequential.** *"I want the cheapest good
pasta."* — Acceptable: one question whose answer changes the next action, asked
with what it changes and what happens if it goes unanswered; work that does not
depend on the answer continues meanwhile. Not acceptable: a fixed set of
questions asked because the runbook lists them, or proceeding as though
"cheapest" and "good" were already reconciled. **Stage 5** carries the structure — settlement, questions with their expected effect, delegation, assumed constraints that still bind, an unsupported category as a valid plan; **conversational trial** pending for the interpretation.

**3 — Delegated choice.** *"You decide on the pack size."* — Acceptable: a
visible choice, its rationale, and what changes if it is wrong. Not acceptable:
recording the delegation and then describing the result as user-confirmed.
**Stage 5** carries the structure — settlement, questions with their expected effect, delegation, assumed constraints that still bind, an unsupported category as a valid plan; **conversational trial** pending for the interpretation.

**4 — No defensible default exists.** A decisive choice where every option is
as likely as the others and the consequences diverge. — Acceptable: ask before
dependent work, or stop with the choice recorded as unresolved. Not acceptable:
proceeding on a disclosed guess. Disclosure does not make an indefensible
default acceptable. **Stage 5** carries the structure — settlement, questions with their expected effect, delegation, assumed constraints that still bind, an unsupported category as a valid plan; **conversational trial** pending for the interpretation.

**5 — An assumption that is also a hard constraint.** A budget the buyer never
stated and the agent assumed. — Acceptable: it binds within the study exactly
as a stated one would, and is legible as assumed. Not acceptable: exemption
from enforcement because it was assumed, or presentation as a user instruction.
**Stage 5** carries the structure — settlement, questions with their expected effect, delegation, assumed constraints that still bind, an unsupported category as a valid plan; **conversational trial** pending for the interpretation.

## Requirements the machinery cannot currently hold

**6 — The delivered-cost trap.** *"Which is cheapest once it's delivered?"*
over records that carry no shipping data. — Acceptable: no delivered-cost
recommendation; a bounded item-price finding that names the narrower question
it answers; the gap stated. Not acceptable: an item-price winner presented as
the answer to a delivered-cost question, with the limitation in prose beside
it. **Characterised**: rewriting `cost_basis` to say *delivered cost* moves
only the echo of that text in `constraints`; eligibility, ordering and outcome
are identical — and that stays true, because prose is not a requirement.
**Stage 6**: with the objective recorded in the plan as unsupported, the
recommendation is withheld, the leader appears only under the bounded-finding
heading, and its ordering is the legacy ordering unchanged.

**7 — A budget and an ordering on different dimensions.** *"Under 100 EUR in
total, then cheapest per kilogram."* — Acceptable: a supported independent
constraint, or an explicit gap plan, or a comparison whose limits are stated.
Not acceptable: substituting units, or treating a narrative exclusion as
enforced. **Characterised**: `max_axis_value = 100` against a EUR/kg axis
excludes nothing from a shelf running 2.96 to 8.78 EUR/kg, and a cap that does
fire reports the product as "above the 5 EUR/kg this brief set as its limit".
Routing the budget through `unacceptable` instead moves no recorded decision at
all. Dry pasta and basmati publish no price axis to move the cap to; mounting
paste does, which is why this is not a fact about every category — and it still
orders on pack size, so the cap would land on the wrong quantity there too.
**Stage 6**: the budget recorded as an unsupported hard constraint withholds the
recommendation; the brief carries no cap; adding one refuses at the transition
as a cap no requirement maps to; writing the budget into `unacceptable`
satisfies nothing. A plan that maps the budget onto the cap passes as enforced,
which is the semantic-review limit, stated in the report. **Stage 9**: an intake
review that fails `adequacy` on `budget`, naming the cap as euros per kilogram
rather than a purchase total, refuses the run and nothing is written; the same
plan without the review still runs, enforced and wrong, as stage 6 documented.
**2026-09-18**: the first acceptable branch now exists — `axis_bound`, a floor
or ceiling on any published axis at candidate assessment — and
[test_gates.py](../test_gates.py) exercises it on a pack-size ceiling over the
bronze-die brief. This case's plan is unchanged: dry pasta still publishes no
pack-price axis to bound, so the budget stays an unsupported hard constraint
and nothing here is routed anywhere.

**8 — An external finding as a hard condition.** *"Only ones an independent
test rated well."* — Acceptable: the finding is retained, the absence of any
path from it to candidate eligibility is named, full-request selection is
withheld, and bounded investigation continues. Not acceptable: manually
removing candidates, or transferring a narrative approval into a filter so that
it looks enforced. **Stage 6**: an `evidence_review` hard constraint withholds
selection whether its state is `supported` (a scoped explanation, not
selection) or `not_assessed` (routed to collection or a coverage stop, not a
gap); candidate accounting is untouched.

**9 — A supported method with the evidence missing.** — Acceptable:
insufficient evidence, with candidate accounting preserved and a statement that
describes the inspected sources. Not acceptable: reporting a coverage failure
as a fact about the market, or diagnosing it as a capability gap and spending
engineering budget on an absence. **Stage 6**: under a fully enforced plan the
insufficient-evidence outcome stands with no stop, its diagnosis reads
"coverage", and the candidates are the plain study's candidates.

**10 — An unknown category.** *"Which cordless hedge trimmer should I buy?"* —
Acceptable: a useful evidence and gap plan that explains the missing capability
and the next step. Not acceptable: asking the buyer to choose an implementation
module, or beginning engineering on the strength of having planned it.
**Stage 5**: an unknown category is a valid plan with its gap kind and next step,
the sanitized hedge-trimmer example; **conversational trial** pending for the
explanation a buyer actually receives.

## Interpretation failures

**11 — A valid control answering the wrong question.** Mounting paste for one
scooter tyre, ranked cheapest per kilogram. The control is implemented,
correct, and actively misleading: the cheapest paste per kilogram is a
five-kilogram workshop tub. — Acceptable: the mismatch between the stated use
case and the declared axis is caught. Not acceptable: **inventing a universal
smallest-pack rule to make this testable** — that rule is the original failure.
A structured contradiction can be asserted mechanically; recognising it from
natural language is semantic review. **Stage 6**: the one-tyre objective
recorded as decisive and unsupported is refused at comparison support and the
price ordering is a bounded finding; the category's smallest-pack default is
left exactly as it is.

**12 — An agent-invented criterion.** A requirement that neither the buyer
stated nor the category carries, introduced by the agent's own reading of the
request. — Acceptable: its author, role and disposition are visible, and it
stays in the plan. Not acceptable: it becomes a fact about the product class.
This is the failure the roadmap already records — mounting paste ranks the
smallest pack first because one reader was fitting one scooter tyre, and that
is now indistinguishable from a property of the product. R13 adds a third
author to it. **Stage 5** makes author, role and disposition structural;
**conversational trial** pending for the reading itself. **Stage 9**: the
`faithfulness` check asks whether anything the agent introduced is presented as
the user's, and a failure must name the requirement; the committed review
assesses the agent's listed-price axis as its own, non-decisive assumption.

**13 — A decisive requirement dropped in translation.** The requirement is in
the buyer's words and in the plan, and absent from the brief. — Acceptable:
refusal at the transition that lost it, naming the requirement. Not acceptable:
a study that runs and reports normally. **Stage 5**: the transition refuses
before analysis and names the requirement; the independently specified case is
in [test_intake_plan.py](../test_intake_plan.py).

**14 — One exclusion, several stages.** *"Nothing from that seller."* —
Acceptable: the effect is recorded at each stage it applies to — discovery,
acquisition, eligibility — and they are not assumed identical. Incidentally
acquiring an unsuitable product is not automatically a scope violation. Not
acceptable: reading every constraint as a universal acquisition ban, or
enforcing it only at the last stage. **Stage 6**: discovery and collection
effects render as recorded with a note that this study performs neither, the
candidate-assessment effect as unsupported, and the recommendation is withheld.

## Process and delivery

**15 — Probe evidence reused.** A reconnaissance probe answers a bounded
question and its observations are later used. — Acceptable: reuse is permitted
with explicit promotion, and the record says whether the probe changed the
criteria or supplied candidates that entered the plan. Not acceptable:
provenance alone offered as proof of an unbiased comparison; re-collecting
identical evidence solely because it came from a probe. **Stage 8**: a completed
probe must record its result and a promotion record — promoted or not, into
what, whether it changed the criteria or supplied candidates — and a material
change requires an explicit assessment; promotion moves evidence into the plan
and never consumption out of the ledger. What the ledger cannot do is tell that
an operator recorded the record falsely.

**16 — Age, and the difference between two reference dates.** Three requests:
decisive prices that breach the declared policy; an old study delivered again
today; and a regression fixture whose timestamps would satisfy any age
calculation. — Acceptable: no current buying advice in the first two unless the
policy passes against a reference the brief's author does not supply; a
historical comparison with its reference date is fine; the fixture stays
historical in scope however fresh its dates look. Not acceptable: a disclosure
in place of a block. **Characterised**: moving the committed study's reference
date thirty days on leaves five ranked candidates in breach at thirty-two days
old, with an identical shortlist, an identical `recommendation`, and the leader
still shortlisted while flagged stale — and that analysis stays as it is, because
it answers the historical question against `as_of`. **Stage 7**: the block moved
to the delivery event, in [test_delivery.py](../test_delivery.py). A
current-advice brief delivered at the build date is permitted and thirty days on
is blocked naming every governed observation; a later delivery is a new event
that blocks; the fixtures, whose briefs declare no scope, deliver as history at
any reference with that reference stated; and a completed semantic review does
not lift a block. **Stage 10**: a permitted current-advice event is delivered as
audited only with a delivery review bound to that event, carrying the
deliverer's named attestation; a later event is a new review while the semantic
review stands, in [test_delivery_review.py](../test_delivery_review.py).

**17 — A requirement changes after approval.** — Acceptable: the affected
intake findings and any downstream approval are invalidated; an unresolved
disagreement leaves the finding pending or failed; a structural failure is
never overridden by a semantic approval. Not acceptable: copying a `pass`
forward to make new digests validate. **Stage 9**, the intake half: a review
bound to a superseded plan revision, or relabelled with the new digest without
re-review, refuses; a `fail` leaves the plan blocked at `run`; a `limited` check
is not approval. **Stage 10**, the final half: the final review binds the plan
snapshot and the intake review and records the intake findings it rests on; a
completed final review is superseded by a changed intake review, and
`review-intake` refuses that order; a v1 review is refused outright rather than
reinterpreted; findings are not reused across plan revisions mechanically, since
a revision is a new review.

**18 — A budget stop and a resumption.** Research budget exhausts mid-run and
the conversation is gone. — Acceptable: completed evidence is preserved, the
prevented next actions are named, and work resumes from verified artifacts
alone; delivery freshness is rechecked before any new current advice. Not
acceptable: treating interrupted work as complete, or depending on the
originating session. **Stage 8**: the interrupted collection stays interrupted
with its allocation counted as spent, `resume` runs from the bundle's snapshot
after the working ledger and plan are deleted, names the resumed collection the
55 remaining responses prevent, keeps the engineering proposal unexecuted, and
rechecks freshness at its reference without recording a delivery.

**19 — A hard constraint that cannot be met.** — Acceptable: the refusal is
presented without a recommendation-style shortlist beneath it, while permitted
bounded observations survive elsewhere. Not acceptable: a differently-labelled
field directly under the refusal — that is the disclaimer the repository
already rejected by name when it decided that a refusal "with three products
under it is a recommendation wearing a disclaimer, and it will be read as one".
**Stage 6**: a decisive hard constraint whose assessment `failed` headlines
"Requirement cannot be met", the result slot holds no table, and the bounded
observations appear only under their own heading — asserted on the rendered
text, not on a field.

**20 — An assessable proxy in place of the stated condition.** *"It must
measure my training data well."* — the buyer states a quality; every listing
states only the hardware. Acceptable: the quality stays the buyer's decisive
hard constraint on an evidence path, the recommendation is withheld while it is
unassessed, and the hardware checklist (GPS, optical heart rate, barometer) is
recorded as the agent's own non-decisive proxy with its basis; the same for a
depth margin the buyer did not name, and for a material reading standing in for
"wearable with a suit". Not acceptable: the proxy recorded as the buyer's hard
constraint and the stated quality filed as a preference because nothing can
assess it — a report can then head its table "passed every hard condition"
while the condition was never tested. The distinction from case 7 is that no
unit or control is misused; the substitution happens in the plan's roles and
settlement, where only the intake review sees it. **Conversational trial**
(2026-09-18, third R13 trial): the operating agent made the substitution three
times, the buyer's outcome grading (his shortlist matched) did not surface it,
and the independent intake review failed the plan on it; the repair introduced
a new unstated threshold that the next review caught. No fixture stands in for
it; the acceptable outcome above is what a review grades against.
