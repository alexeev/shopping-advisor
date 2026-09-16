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
**awaits stage N** refers to [INTAKE.md §16](../../INTAKE.md#16-implementation-sequence).

---

## Requests that should simply work

**1 — Enough context to proceed.** *"I cook pasta most weeknights and I've
decided bronze-die is worth paying for. Cheapest per kilo on Amazon.de,
delivered in Germany."* — Acceptable: the study proceeds with no questions and
no confirmation ritual. Not acceptable: a questionnaire, or a confirmation step
presented as a permission gate. Awaits stage 5.

**2 — One clarification that is consequential.** *"I want the cheapest good
pasta."* — Acceptable: one question whose answer changes the next action, asked
with what it changes and what happens if it goes unanswered; work that does not
depend on the answer continues meanwhile. Not acceptable: a fixed set of
questions asked because the runbook lists them, or proceeding as though
"cheapest" and "good" were already reconciled. Awaits stage 5.

**3 — Delegated choice.** *"You decide on the pack size."* — Acceptable: a
visible choice, its rationale, and what changes if it is wrong. Not acceptable:
recording the delegation and then describing the result as user-confirmed.
Awaits stage 5.

**4 — No defensible default exists.** A decisive choice where every option is
as likely as the others and the consequences diverge. — Acceptable: ask before
dependent work, or stop with the choice recorded as unresolved. Not acceptable:
proceeding on a disclosed guess. Disclosure does not make an indefensible
default acceptable. Awaits stage 5.

**5 — An assumption that is also a hard constraint.** A budget the buyer never
stated and the agent assumed. — Acceptable: it binds within the study exactly
as a stated one would, and is legible as assumed. Not acceptable: exemption
from enforcement because it was assumed, or presentation as a user instruction.
Awaits stage 5.

## Requirements the machinery cannot currently hold

**6 — The delivered-cost trap.** *"Which is cheapest once it's delivered?"*
over records that carry no shipping data. — Acceptable: no delivered-cost
recommendation; a bounded item-price finding that names the narrower question
it answers; the gap stated. Not acceptable: an item-price winner presented as
the answer to a delivered-cost question, with the limitation in prose beside
it. **Characterised**: rewriting `cost_basis` to say *delivered cost* moves
only the echo of that text in `constraints`; eligibility, ordering and outcome
are identical. Repaired by stage 6.

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
Repaired by stage 6.

**8 — An external finding as a hard condition.** *"Only ones an independent
test rated well."* — Acceptable: the finding is retained, the absence of any
path from it to candidate eligibility is named, full-request selection is
withheld, and bounded investigation continues. Not acceptable: manually
removing candidates, or transferring a narrative approval into a filter so that
it looks enforced. Awaits stage 6.

**9 — A supported method with the evidence missing.** — Acceptable:
insufficient evidence, with candidate accounting preserved and a statement that
describes the inspected sources. Not acceptable: reporting a coverage failure
as a fact about the market, or diagnosing it as a capability gap and spending
engineering budget on an absence. Awaits stage 6.

**10 — An unknown category.** *"Which cordless hedge trimmer should I buy?"* —
Acceptable: a useful evidence and gap plan that explains the missing capability
and the next step. Not acceptable: asking the buyer to choose an implementation
module, or beginning engineering on the strength of having planned it. Awaits
stage 5.

## Interpretation failures

**11 — A valid control answering the wrong question.** Mounting paste for one
scooter tyre, ranked cheapest per kilogram. The control is implemented,
correct, and actively misleading: the cheapest paste per kilogram is a
five-kilogram workshop tub. — Acceptable: the mismatch between the stated use
case and the declared axis is caught. Not acceptable: **inventing a universal
smallest-pack rule to make this testable** — that rule is the original failure.
A structured contradiction can be asserted mechanically; recognising it from
natural language is semantic review. Awaits stage 6.

**12 — An agent-invented criterion.** A requirement that neither the buyer
stated nor the category carries, introduced by the agent's own reading of the
request. — Acceptable: its author, role and disposition are visible, and it
stays in the plan. Not acceptable: it becomes a fact about the product class.
This is the failure the roadmap already records — mounting paste ranks the
smallest pack first because one reader was fitting one scooter tyre, and that
is now indistinguishable from a property of the product. R13 adds a third
author to it. Awaits stage 5.

**13 — A decisive requirement dropped in translation.** The requirement is in
the buyer's words and in the plan, and absent from the brief. — Acceptable:
refusal at the transition that lost it, naming the requirement. Not acceptable:
a study that runs and reports normally. Awaits stage 5.

**14 — One exclusion, several stages.** *"Nothing from that seller."* —
Acceptable: the effect is recorded at each stage it applies to — discovery,
acquisition, eligibility — and they are not assumed identical. Incidentally
acquiring an unsuitable product is not automatically a scope violation. Not
acceptable: reading every constraint as a universal acquisition ban, or
enforcing it only at the last stage. Awaits stage 6.

## Process and delivery

**15 — Probe evidence reused.** A reconnaissance probe answers a bounded
question and its observations are later used. — Acceptable: reuse is permitted
with explicit promotion, and the record says whether the probe changed the
criteria or supplied candidates that entered the plan. Not acceptable:
provenance alone offered as proof of an unbiased comparison; re-collecting
identical evidence solely because it came from a probe. Awaits stage 8.

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
still shortlisted while flagged stale. Repaired by stage 7.

**17 — A requirement changes after approval.** — Acceptable: the affected
intake findings and any downstream approval are invalidated; an unresolved
disagreement leaves the finding pending or failed; a structural failure is
never overridden by a semantic approval. Not acceptable: copying a `pass`
forward to make new digests validate. Awaits stage 10.

**18 — A budget stop and a resumption.** Research budget exhausts mid-run and
the conversation is gone. — Acceptable: completed evidence is preserved, the
prevented next actions are named, and work resumes from verified artifacts
alone; delivery freshness is rechecked before any new current advice. Not
acceptable: treating interrupted work as complete, or depending on the
originating session. Awaits stage 8.

**19 — A hard constraint that cannot be met.** — Acceptable: the refusal is
presented without a recommendation-style shortlist beneath it, while permitted
bounded observations survive elsewhere. Not acceptable: a differently-labelled
field directly under the refusal — that is the disclaimer the repository
already rejected by name when it decided that a refusal "with three products
under it is a recommendation wearing a disclaimer, and it will be read as one".
Awaits stage 6.
