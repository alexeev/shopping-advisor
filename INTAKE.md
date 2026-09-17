# Intake — what the conversation has to preserve

A design assessment for [R13](ROADMAP.md#r13--the-conversation-as-the-entry-point),
written before implementation. It states the constraints an intake design has to
satisfy, the places the current code would not satisfy them, and the cases that
would demonstrate either. It is not an adopted contract and changes no runtime
authority: every change it implies is separate work under the
[maintenance workflow](AGENTS.md#maintenance-workflow).

R13 makes prospective reasoning explicit, persistent and checked across
transitions. The brief is already prospective judgement — the runbook requires
the question, the requirements, the collection limits and both stopping criteria
before collection, and says why: written afterwards they rationalise whatever the
evidence happened to support. A brief *file* can be written before its feeds
exist. What cannot exist yet is a **validated** intake representation that
survives, covers requests that cannot become executable briefs, and is checked at
each transition it passes through.

Repair that connection to execution. Do not build a parallel planning system.
[R16](ROADMAP.md#r16--capability-lifecycle-and-architectural-review) prohibits a
*free-form* memory store and a dynamic loader, which does not prejudge the
architecture of a structured, contract-bound intake artifact — but an artifact the
execution boundary never consumes and the gate never protects is the thing that
prohibition is aimed at. Every structure proposed below is tested against that:
what reads it, and what fails when it is wrong.

---

## 1. Three failure patterns this repository has already paid for

Every safeguard proposed here is checked against these before it is written down.

**A buyer's constraint becoming a fact about the product class.** Recorded in the
roadmap: tyre mounting paste ranks the smallest pack first because one reader was
fitting one scooter tyre, and that is now indistinguishable from a property of the
product. [AGENTS.md](AGENTS.md#research-rules) states the rule — "A user's
constraint is not a fact about the product class; once both are in a category
module nobody can tell them apart" — and R11 keeps buyers' constraints in the
brief. R13 introduces a **third author** to this failure: the agent's own
operationalisation of natural language, which is neither the user's constraint nor
the category's property.

**Declared read as obtained.** A brief's `[[sources]]` were declared and
unverified until T3's ledger made acquisition checkable. R13 adds two more of the
same shape: planned evidence read as collected evidence, and questions asked read
as questions that mattered.

**A qualification that is computed, rendered, and consumed by nothing.**
`cost_basis` is the known case. `stale_ranked` is the measured one, and it is the
stronger demonstration because the presentation is already correct. Under the
committed bronze-die study with its seven-day policy unchanged, moving the
reference date to 2026-10-16:

| `as_of` | `stale_ranked` | oldest ranked | shortlist | outcome |
|---|---|---|---|---|
| 2026-09-16 | 0 | 2 days | B0DQ2N5HRW, B08WJGD5Z5, B08BNQ2D54 | `recommendation` |
| 2026-10-16 | **5** | **32 days** | identical | **identical** |

Five decisive observations breach the declared policy and nothing moves, because
`analyse()` computes the freshness block and `_decide` never reads it. The
renderer does warn, and warns well: the banner is inserted *above* the headline
and reads "Historical / incomplete comparison. Prices are stale or freshness is
not fully established; **this is not current buying advice**" — and the
recommendation stands underneath it anyway. Placement was never the gap. Labelling
being the whole mechanism is the gap.

---

## 2. What must survive intake

1. **Interpretation is faithful.** The requirements the conversation produces are
   the ones the user's words support.
2. **Requirements survive translation.** An explicitly stated requirement reaches
   the execution boundary with the same meaning and role, or the transition
   refuses.
3. **Every decisive requirement has an accountable disposition** at every stage it
   affects — enforced, assessed through identified evidence and review, or
   unsupported and stated as such.
4. **Authorship, role and settlement are legible** (§3).
5. **The answer claims no more than its method supports.** A bounded analytical
   finding is permitted; a recommendation that a missing requirement could
   overturn is not.

Property 5 has a committed illustration. The pasta brief declares "Delivery is not
included: these records carry no shipping data." `cost_basis`, `unacceptable` and
`limits` are parsed, persisted and rendered, and nothing evaluates any of them.
Precisely: changing one of them changes the brief bytes, the study id and the
report text, and leaves **eligibility, ordering and outcome identical**. A brief
that said *delivered cost* would produce a different-looking study that decided
exactly the same way.

---

## 3. Requirement semantics

Provenance records who said a thing and why; it does not say what to do with it.
"Under €100", "prefer quiet" and "quiet enough for this room" can carry identical
authorship records and require different handling. These are independent
dimensions, and collapsing them into one taxonomy makes all of them unreadable.

| Dimension | Meaning |
|---|---|
| **Decision role** | Hard constraint, preference or objective, or context. Context may be operative or explicitly non-operative. |
| **Settlement** | Stated by the user, resolved through delegation, assumed without being raised, or unresolved. Delegation does not mean a choice has already been made. |
| **Provenance** | Who introduced it — **user, cited source, or agent** — the supporting wording, the factual basis (a source, a labelled hypothesis, or reasonableness alone), applicability, and what changes if it is wrong. |
| **Assessment path** | An existing executable control; an evidence-and-review finding; an unsupported method; or revised/withdrawn with authority and reason. |
| **Assessment state** | Not yet assessed, supported within scope, failed, or unknown, with the evidence and review bindings that justify the state. |
| **Stage effects** | Which next actions, candidate decisions or permissible claims depend on it. |

An assumed budget is a hard constraint that happens to have been assumed. It binds
within the declared study; assumption status neither exempts it from enforcement
nor makes it a user instruction. Prefer no cap when no budget is stated, as the
runbook already does — do not invent an exclusion to fill a field.

Hard constraints all bind; conflicts need a stated precedence. Preferences need an
ordering or a declared tradeoff, and the brief expresses exactly one, which is
where a multi-preference request first breaks.

A non-blocking assumption may enter executable research on that record with its
limitations preserved; stricter evidence is required for assertions presented as
**established fact**. That line is not the one `trusted` draws. `trusted` is
proposition-specific: a category may mark a vendor declaration `trusted` because
it found attributable text, and [CONTRACT.md](CONTRACT.md#status-vocabulary)
states that this "does not independently verify the claimed performance";
histogram agreement checks rating consistency, not review authenticity. `trusted`
separates a checked proposition from an unchecked one, which is narrower than
separating an assumption from a fact. A source cannot establish a preference
either: a publication using 60 dB does not make 60 dB right for this buyer.

What must never happen is narrow: a buyer's constraint must not become a fact
about the product class. R11 permits a category to carry scoped domain knowledge
and explicit method defaults, each with a source *or a labelled hypothesis* and
applicability limits, so a demonstrated scoped default may still enter later
through reviewed adoption under R11 and R16.

### What execution refuses — per action, per requirement

Refusal is a matrix, not a switch. A single global gate would contradict the same
document's permission for bounded investigation.

| Requirement, by role and disposition | Refuses | Still permits |
|---|---|---|
| Hard constraint with no enforceable control | The full-request recommendation, and collection *framed* as a study that answers the question | A bounded probe, and collection that could resolve the gap, both scoped and labelled |
| **Decisive preference the declared axis does not answer** | The substitution, at comparison support | Ranking on the available axis as an explicitly bounded finding |
| Unresolved context needed to interpret a decisive requirement | Dependent work | Asking, or stopping with the choice recorded |
| Context informing nothing decisive | Nothing | Retained, marked non-operative |

The second row matters more than it looks. "Choose the cheapest delivered option"
is an **optimization objective**, not an eligibility condition; a refusal rule
naming only hard constraints would let the delivered-cost failure — the case this
document is built around — escape it.

The last row exists because requiring every contextual statement to become a
criterion would manufacture invented requirements, which is the failure this
document exists to prevent.

### Three settlement outcomes that look alike and route differently

| Situation | Next step |
|---|---|
| An assessment method exists and the evidence is present | Execute it |
| An assessment method exists and the evidence is missing | Collect, probe, or stop on coverage — not a capability gap |
| No adequate assessment method exists | Gap plan; hand off to [R15](ROADMAP.md#r15--controlled-task-driven-capability-adaptation). Not an evidence problem |

Misreading the second as the third spends R15 budget on an absence, which this
repository has already measured once (§7).

The open decision is not where any of this is stored. It is what minimum semantics
the execution boundary consumes and refuses on. A plan recording role and
settlement that execution never reads is `cost_basis` with more fields.

---

## 4. Current capability boundaries

Today the brief carries two controls that move the candidate set, and they are not
the only mechanisms that do:

| Mechanism | Where | What it actually does |
|---|---|---|
| `require_claims` | `report.ranking()` in [ranking](shopping_advisor/analysis/report.py) | Filters on claim keys the **category evaluation derived from the record**, requiring `trusted` status — the presence of a vendor statement, not its truth |
| `max_axis_value` | `analyse()` in [study analysis](shopping_advisor/study/analysis.py) | Caps the ranking row's **selected-axis** value |
| Category classification | `is_match()` | Removes records the classifier does not place in the category |
| Value usability | `ranked_value()` | Removes values that are absent, not usable, or measured in a non-comparable unit |
| Offer grouping | `variation.group_offers()` | Folds pack-size variants into one ranked row |

`cost_basis`, `unacceptable` and `limits` are retained narrative fields. They do
not implement their prose as predicates. Document that where a brief author will
read it, beside the brief-authoring guidance.

Reviewed external evidence is **not** an eligibility path. T3 checks evidence
scope and declared listing matches and supports separately reviewed claims; it
does not pass those findings into `analyse()` as candidate filters. The ledger is
an *input* — read before `analyse()` and included in `study_id` — but
`audit.check_claims` validates statements against observations without touching a
candidate, and the claim index is built after every candidate decision exists. So
"rated well by an independent test" as a hard eligibility condition is **net-new
machinery**: candidate and variant identifiers, retained assessment outcomes,
missing and conflicting evidence rules, effects on grouping and eligibility,
deterministic replay, and regression tests. It must not be priced as a schema
addition or a disposition field.

For minimum R13, a reviewed finding can support a scoped explanation. Where a hard
eligibility condition depends on one and no supported application path exists,
that condition stays unsupported for automated selection: block the full-request
recommendation, allow bounded investigation and a gap plan. Do not manually remove
candidates or transfer a narrative approval into a filter to disguise the missing
control.

### Two mandatory boundary examples

**Delivered cost.** Shipping is absent from the committed pasta evidence. Changing
the cost-basis prose cannot make item-price ranking answer delivered cost.

**"Under €100 total, then cheapest per kilogram."** The strongest case available,
because it is unremarkable. It is not a multi-preference problem: it is
**eligibility on one dimension and ordering on another**. `max_axis_value` caps
the *selected-axis* value, so `100` against a EUR/kg axis caps unit price, not
purchase price; dry pasta and basmati publish no total-price ranking axis to
switch to. The available workaround is the first trap — adding the budget to
`unacceptable` leaves `outcome`, `shortlist`, `candidates`, `ranking`, `freshness`
and `constraints` byte-identical. This must resolve to a supported independent
constraint, an explicit gap plan, or a comparison whose limits are stated. It must
never pass by substituting units or by treating a narrative exclusion as enforced.

---

## 5. Enforcement across stages

Boundaries are not interchangeable places to put a requirement cheaply. Specify
each requirement's consequence at every stage it affects, then avoid duplicated
implementation where one check serves two.

| Stage | What it decides | Delivered cost, traced |
|---|---|---|
| Intake | Whether dependent work may proceed, and which next action is justified | Requirement recorded; no supported control found; proceed to a bounded probe or stop — not to collection framed as a price study |
| Probe | The named uncertainty, the finite allocation, and the result that determines the next step | A bounded search for shipping evidence is permitted; it is not authorisation for full collection |
| Discovery and collection | What is looked for and where; what was planned, attempted and not attempted | Shipping data is not on these records; the scope says so before collection |
| Candidate assessment | Which candidates qualify; failed and unknown assessments are retained, not silently dropped | Unchanged: no delivered-cost predicate exists, and none is proposed |
| Comparison | Whether the declared axes, units, objective, cost basis and evidence support the declared comparison | Price per kg does not answer delivered cost; the substitution is refused here |
| Conclusion and rendering | Whether the full request supports a recommendation, a tie, a bounded finding or a refusal | A bounded item-price finding is allowed; the recommendation is withheld |
| Delivery | Current-advice freshness, and the final review against frozen conclusion inputs | Re-checked at each delivery event, not once at analysis |
| Revision and resumption | Retained state, reconciled consumption, and which collection, analysis or review findings are invalidated | Interrupted work is never assumed complete |

Not every hard constraint excludes every discovery observation. "Do not buy X" and
"do not access seller X" have different stage effects; incidentally acquiring an
unsuitable product is not automatically a scope violation. Record the effects
rather than reading every constraint as a universal acquisition ban.

**Readiness is staged and names its next action.** Ready for a probe is not ready
for collection; ready for collection is not ready for a recommendation. A recorded
blocker is a planning outcome, not authorisation to proceed through it.

**Enforcement and attestation coexist.** Software can refuse an explicitly
unresolved requirement, as the brief already refuses an unknown category key. It
cannot detect a requirement the plan never recorded, a false capability claim, or
a semantically irrelevant mapping.

**Cost, stated accurately.** The intake gate and the comparison-support check cost
nothing in *candidate-ranking semantics* — no eligibility predicate, no corpus
movement. They are not free: they decide whether research or a recommendation may
proceed, which is consequential behaviour needing tests, replayable inputs and
rendering.

---

## 6. One authoritative conclusion, with explicit rendering rules

The primary portable study report carries the request-level purchasing conclusion,
**every qualification that restricts it**, and the completion state. Non-restricting
process history may live in a separate manifest-bound artifact. The test for which
is which is not document length; it is whether the fact changes the conclusion or
its permissible scope.

A separate research-context report, bound by a stable name and a manifest digest,
fails on two checkable grounds. **Presentation:** the analytical report opens with
the outcome headline, and the headline for a recommendation is the word
"Recommendation" — a document that begins with that word circulates as one, and a
pointer to the file that withdraws it is the same construction as a leader
rendered beneath a refusal. **Binding:** semantic review binds the report digest
plus a `basis` of exactly six hard-coded filenames, while the manifest digests
nine artifacts. A context artifact added to the manifest therefore acquires an
integrity digest and **no review binding**: its decision-relevant content could
change while the report bytes and study id stay fixed, and an invalidation rule
keyed on report bytes or study ids would not fire. The integrity mechanism is real
and guards the wrong boundary.

The price is real and is paid in §8: conclusion-restricting facts become declared,
pinned report inputs, so the identity contract grows to cover them, and
`review_basis` stops being a literal tuple and becomes a **contract** covering
every decision-relevant artifact — with a test that a new artifact cannot enter the
bundle without a deliberate decision about whether it binds.

| Outcome or stop | Presentation |
|---|---|
| Supported recommendation | Recommendation and shortlist may appear together, with their scope and evidence |
| Supported comparison, no decisive winner | Preserve today's behaviour: the shortlist **is** the answer, and no winner is selected |
| Insufficient decisive evidence | Preserve today's behaviour: no shortlist beneath the refusal. Candidate accounting stays available |
| Unsupported decisive requirement or method | State the unsupported requirement and withhold the purchasing recommendation. No winner card or recommendation-style shortlist beneath it. Bounded observations belong in a separately titled section that names the narrower question they answer |
| Research-budget or access stop | State what remains unexamined and its effect. A stop is neither automatically failure nor automatically permission to recommend; the same decisive-requirement checks apply |
| Current-advice freshness failure | No current purchasing recommendation. A separately scoped historical comparison may be delivered with its reference date |

**An analytical leader is not a recommendation.** "Product A has the lowest
observed item price; delivered-cost ordering is unknown" is an accurate finding. It
becomes misleading when it occupies the place a recommendation occupies. Two of
these placements are already decided and the reasoning is in the code:
`no_decisive_winner` keeps its shortlist because the shortlist is the answer, while
`insufficient_evidence` puts nobody forward because — in the repository's own words
— a refusal "with three products under it is a recommendation wearing a disclaimer,
and it will be read as one". A new requirement-unsupported stop needs that judgment
made explicitly rather than inherited by default, and **distinct field names are
not that judgment**. Tests must cover placement and wording, not only outcome
fields. Record stop reasons separately from analytical outcomes; they need not map
one-to-one.

---

## 7. Stopping, budgets, and not overclaiming

Bounded research cannot establish that evidence does not exist. Calling a stop "the
evidence does not exist" turns a local search failure into a universal claim — the
overclaim [R12](ROADMAP.md#r12--discovery-that-states-its-own-coverage) exists to
prevent, whose rule is that counts describe the inspected sources and never the
entire market.

| Observation | Implication |
|---|---|
| Not found within the inspected scope | A coverage statement; says nothing about the market |
| Located but inaccessible | An access limit — the ledger already has a scope for it |
| Available but stale, mismatched or insufficient | An applicability failure, not an absence |
| Collection interrupted, or budget exhausted | A fact about this session, not about the shelf |
| A source states a measurement was not performed | The nearest thing to a real negative, still bounded by that source |

A **software gap** and an **unresolved user preference** are stops of different
kinds again, implying different next steps. Three outcome codes exist today; the
stop vocabulary must not collapse into them by default, and each kind needs its own
stopping rule.

**Gap diagnosis is provisional too.** A missing value may be an extraction defect,
an inaccessible source, a variant mismatch, or something nobody publishes. The
repository has the measurement: **73 of 239 basmati (31%) had no purchasable offer
at crawl time**, and [R9](ROADMAP.md#r9--a-second-pass-for-missing-prices) still
sits behind a decision test because the explanation was never resolved.

### The session resource ledger

Per-crawl provenance is a foundation, not session accounting: the run manifest
retains `arguments` and allowlisted `settings` for one crawl. Three things are
missing at session scope.

- **Declared aggregate limits** — research and engineering kept apart, with
  explicit units, scope and authorisation. Willingness to investigate products
  does not imply willingness to fund development. A purchase budget is a different
  quantity again.
- **Action records** — unique action and run identifiers, purpose, allocation,
  timestamps, observed consumption and completion or interruption state, linked to
  crawl manifests where they exist.
- **Reconciliation and next-action checks** — include probes, retries and
  interrupted runs; never count a replay as new acquisition or a resumed action
  twice. Unknown consumption stays unknown, not zero. Authorise only an action
  whose bounded allocation fits the remaining applicable limit. An exhaustion stop
  preserves completed evidence and records which next actions it prevents.

Choose units the environment can actually observe. The run manifest already
carries `counts` and the filtered Scrapy `stats`, and
[provenance](shopping_advisor/provenance.py) allowlists `CLOSESPIDER_TIMEOUT`,
`CLOSESPIDER_ITEMCOUNT` and `CLOSESPIDER_PAGECOUNT` into the record. Their limits
are part of the design: **a product cap is not a request cap**, and timeout closure
may leave requests in flight. A deadline includes time elapsed during interruption,
and any extension is an explicit budget revision. Monetary or model usage that
cannot be measured reliably stays an estimate, not an enforced ceiling. State
whether a limit stops new work or enforces a strict consumption ceiling, including
known overshoot; do not promise a hard cap without a mechanism that can enforce it.

Minimum R13 implements the records and the check before a supported research
action, with conservative allocations or a stop when consumption cannot be
reconciled. It is not a scheduler or an unrestricted command runner. R15 supplies
controlled engineering execution; R13 may retain an engineering allowance or
proposal without enabling autonomous adaptation.

On resumption, verify retained artifacts, the active plan revision, consumed and
reserved resources, missing predecessors and pending review state. Recheck delivery
freshness before issuing new current advice. Resume from the verified state or name
the precise missing dependency; do not depend on the original conversation still
being open.

---

## 8. Identity: two questions, not one choice

Identity of the **analysis** and identity of the **complete research record** are
different questions. Two conversations can produce the same executable analysis
while differing in unsupported requirements, process history and permitted
conclusions. Decide both before choosing what to hash: collapsing them into one
identity is what makes re-delivery expensive and reproduction impossible.

### The analysis identity stays a function of declared content

`study_id` today pins the ledger, the manifest and brief versions, the brief
digest, the input digests and two schema versions. Its guarantee is stated in the
runbook: the id is derived "**not from the clock** — so the id above is what a
clean checkout produces, and running it again in another directory writes
byte-identical artefacts." Three things rest on that:

- The documented offline walkthrough names the id a clean checkout must produce.
- `study_id` is a **content address**: a repeated run over the same bytes is
  refused with "this is the same study over the same bytes — read it", which is the
  deduplication affordance.
- The manifest's `VOLATILE` list already declares `started_at` and `finished_at` to
  be "what two runs of the same brief over the same inputs may legitimately
  disagree about. Everything not on this list is a finding."

Therefore: **the delivery clock reference must not enter `study_id`.** Folding an
execution-environment timestamp into the identity material would mint a new id on
every run, break the documented reproduction, and invert the `VOLATILE` contract
without saying so. The clock read the design needs already exists — the study CLI
reads UTC at start and finish and records both in the manifest.

What *does* extend the analysis identity is a frozen **operative-requirement
projection**: the operative requirements and assumptions, their assessment results,
the conclusion scope, rendered confirmation attribution, and decisive stop facts.
Any change to those can change report bytes or permissible conclusions, so they
must move the id. Use canonical serialisation with its own version, check the
projection for omissions, and avoid digest cycles — neither the projection nor a
review basis includes the enclosing manifest or its own approval bytes.

### The delivery record is integrity-bound, not identity-bearing

The delivery reference, session consumption, interruption and resumption facts, and
attestation status are retained, digested as manifest artifacts, and bound into the
**delivery review**. They do not enter `study_id`.

This is what keeps re-delivery affordable. A previously issued report does not
remain current forever: reusing it for a later purchase creates a new delivery
assessment against a newly recorded reference. If the policy fails, recollect or
deliver a historical comparison. If it passes, produce and review the new
**delivery** binding — a scoped re-check of freshness, applicability and conclusion
presentation. It must not require re-writing the four semantic findings for an
analysis whose inputs, decisions and report bytes have not moved. Without that
scoping rule, every re-delivery of an unchanged study costs a full human review,
since a completed review needs a reviewer and non-empty findings per check and
cannot be copied forward.

### Migration

Extending report inputs and review binding is a coordinated migration: new intake
and projection contracts, a review version bump, an artifact inventory, and a
manifest version bump. Under it every regenerated maintained example gets a new id.
Keep the original bundles intact and regenerate into new directories; do not
relabel old bundles. Update documented ids and example expectations deliberately.
**Ids move; decisions must not** — preserve eligibility and ordering on unchanged
supported historical cases, and explain every change to conclusion semantics with
an explicit regression expectation. Previously misleading cases are expected to
change. A version bump is not permission to overwrite history or to approve new
output automatically.

### What identity does not establish

A registry key proves availability, not unchanged behaviour, and the repository
cannot currently tell the difference. `study_id` excludes the analysis code;
`verify` compares `git_revision` and two schema versions and then re-derives the
outputs. A change to what a control *means* that leaves these particular examples'
outputs unchanged is invisible to all three. Two consequences: retain the
applicable contract and method metadata alongside each resolved control, and give
each control's meaning **regression cases chosen to be sensitive to it**, because
output comparison over existing examples is not that protection.

One narrower hole is worth closing while this is open. `code_identity()` records
`git_dirty`; `verify` never compares it. This does not mean a dirty tree passes
silently — `verify` replays the outputs, so a dirty change that moves a checked
decision is caught. It means a recorded `git_dirty` of `true` makes the revision
**non-identifying**, and nothing says so. The useful action needs no comparison:
report a production-time dirty tree as a finding. Comparing two dirty flags would
not establish equal patches and is not the fix. Exact patch and method provenance
stays R15's promise; R13 records what metadata is available and states the limit
rather than implying the stronger guarantee has shipped.

---

## 9. Freshness at analysis and at delivery

Two different questions need two references:

1. **Historical analysis** — how old was the observation relative to the declared
   `as_of` date?
2. **Current delivery** — is the observation recent enough for advice being issued
   at this delivery event?

`_age_days` measures every observation against `brief.as_of`, a date the brief's
author supplies; the pasta fixture sets it to the build date under a seven-day
policy, with a note conceding the prices are frozen regression bytes. **A block
computed on an author-chosen reference date is self-certifying and will block
nothing, forever.** Preserve the declared date for historical analysis, and capture
a separate delivery reference from the execution environment when the final answer
is prepared, with its provenance and time zone. Freeze that reference in the
delivery record so replay never reads today's clock, and normalise age comparisons
explicitly.

Issuing *current buying advice* then becomes a **structural condition**, not a
stated consequence: a disclosure satisfies a stated consequence, and the
measurement in §1 shows exactly what that buys. Name which observations the policy
governs — decisive comparison inputs and shortlisted products, not an irrelevant
excluded candidate — block the current-advice conclusion when those breach it, and
do not let semantic approval waive the block. Unknown or inconsistent observation
dates block current-advice scope where they are decisive. An undated irrelevant
candidate does not invalidate a study. Age bounds need an explicit rationale; a
conveniently huge bound does not establish adequacy.

Fresh dates do not turn a regression fixture set into live buying evidence. Retain
study purpose and evidence origin and check applicability separately: the committed
pasta example describes frozen regression evidence and stays historical in scope
even when its timestamps satisfy an age calculation. The repository already states
the principle for output — reports are gitignored because "a stale recommendation
that still looks authoritative is worse than none."

The execution clock is not a cryptographic trusted-time service. These checks
prevent accidental or silent backdating inside the declared workflow; they do not
prove that an operator who fabricates timestamps supplied true observations. Record
that limit rather than claiming self-certification has been eliminated.

---

## 10. Questions, defaults, probes and confirmation

**Defaults, stated once.**

- **Several defensible defaults exist** — choose one, record the rationale and the
  if-wrong consequence, and proceed. "You decide" is an answer of this kind.
- **No defensible default exists** — ask before dependent work, or stop with the
  choice recorded as unresolved. Disclosure does not make an indefensible default
  acceptable, whoever or whatever is running the conversation.

**The blocking rule was falsified by its own first example.** Blocking had been
defined as wrong or useless under *every* plausible answer, while the marketplace
question the same passage listed as blocking is wrong under *some* answers and
right under others — which is exactly why it blocks. The replacement, now in
force, is in §13.

**Question review, made falsifiable.** Expected value is the right test when
deciding whether to ask, and is not observable afterwards — retrospectively almost
any question can be justified. Apply the discipline the brief already uses for
stopping criteria, which exist precisely because criteria written afterwards
rationalise the result: record the expected consequence **when asking**, then
review observables against it — what action depended on the answer, whether it
resolved a recorded uncertainty, the burden imposed, and repeated experience across
studies. A question need not change the winner to be useful, but "confirmed
robustness" requires an explanation naming what it confirmed; it is not an
automatic exemption from pruning.

**Three activities, one restriction, two records.**

| Activity | May decide | Constraint |
|---|---|---|
| Inspection | Capabilities, retained evidence, prior studies | Touches nothing live |
| Reconnaissance probe | Feasibility, whether evidence plausibly exists, **and prospective candidates** | A crawl: run identity, provenance, pacing, a specific question, a finite budget, and a result that determines the next action |
| Collection | The study's evidence set under the agreed brief | Only what the brief declares |

The restriction is **no silent promotion**, not no reuse: re-collecting evidence
solely because it came from a probe spends budget without improving trust. Probe
evidence may be promoted into the declared inputs explicitly, subject to
applicability and freshness checks.

**The second record is selection bias.** A declared input establishes where an
observation came from. It does not establish whether *seeing* it moved the
criteria, the stopping threshold or the search scope. A favoured product found
during reconnaissance can shape the plan that follows while every retained
observation stays authentic, fresh and honestly attributed. The repository already
applies this discipline one level down: `minimum_candidates` and `decisive_margin`
are "the part worth writing before looking at the data" because "written
afterwards, they are a rationalisation of whatever the evidence happened to
support". Reconnaissance is looking at the data. So record whether it changed
criteria or supplied candidates that entered the plan; a material change triggers an
explicit assessment of whether broader discovery or renewed comparison is needed.
Traceability alone does not establish an unbiased comparison.

**Confirmation.** The read-back cannot render from the parsed `Brief`, which
requires a registered category and readable feeds. Render it from the authoritative
plan revision and verify the plan-to-brief translation separately once inputs
exist. Deterministic rendering reduces omission risk; it does not prove the user
understood every encoded implication. Retain the read-back as presented, its
revision, and its response status, separately:

| Evidence | Consequence |
|---|---|
| Explicit confirmation | Supports a claim that the user agreed to this revision's scope. Does not waive failed structural checks or authorise unrelated engineering |
| Explicit delegation | Permits a choice within the delegated domain, with rationale and if-wrong consequence retained |
| No response | Is not agreement. Research may proceed under defensible non-blocking assumptions and existing authorisation; **the report may not describe those choices as user-confirmed** |
| Correction or contradiction | Invalidates the affected interpretation and every downstream conclusion until reconciled |
| Material ambiguity with no defensible default | Blocks dependent work, whether or not a read-back was presented |

Confirmation is therefore neither mandatory nor irrelevant: its absence changes the
permissible attribution, and where a material choice stays unresolved it changes
permission to proceed. An explicit request needs no extra confirmation to be usable.

The third row is a rule and therefore needs a mechanism, or it is another label.
Attribution rendered in the report is a **declared report input** under §8: what the
report may say about user agreement is a function of the retained response status,
and a report claiming confirmation the record does not support is a structural
failure, not a review finding.

---

## 11. Two review phases within one workflow

The existing four-check review cannot validate a prospective plan. Its checks are a
closed tuple and are rejected if the key set differs; its `basis` is six fixed
filenames, and it binds the report digest. An intake-phase review runs before an
executable brief exists and carries different checks, so it has no binding target
and no valid key set. Extending the existing study workflow is the right direction,
but it is **a new binding contract and a review version bump with example
migration**, not a free reuse.

- **Intake review** binds the retained user-evidence snapshot, the plan revision,
  the resolved mappings and the applicable control and method metadata. It checks
  omissions, faithfulness, adequacy, assumptions and stage effects. These targets
  exist before feeds or an executable brief.
- **Final review** binds the primary report, the intake snapshot and its review,
  requirement assessments, decisions, cards, ledger and decision-relevant delivery
  facts. It checks evidence meaning, applicability, coverage, priorities and
  conclusion presentation.

Use a versioned, phase-aware contract with exact phase-specific target and check
sets. It may consist of separate artifacts under one workflow. Do not force an
intake review into the final-review shape or claim the existing validator already
accepts it.

**Invalidation is recorded per revision, not inferred.** Structural failures cannot
be overridden by review. Final approval requires the applicable intake findings to
remain valid. A material request revision invalidates affected intake findings and
downstream approval; changed evidence or decisions invalidate affected final
findings; changed context that affects the conclusion invalidates final review even
where an old analytical report would render identically. An unresolved disagreement
leaves the affected finding pending or failed.

**Avoid a self-referential approval cycle.** The report records research completion
and limitations; the review records approval of those exact report bytes. Approval
travels in the bundle's review and validation artifacts and is checked before
delivery. Do not insert an approval badge into the report after reviewing it
without generating and reviewing a new binding. Reuse an unchanged finding only
with identical bound inputs and unchanged scope; migration or a new report digest
requires substantive reconsideration, never copied `pass` values.

---

## 12. Controls, gaps, retention and evaluation

**A closed catalogue of executable controls**, with parameter semantics, **resolved
against the live category interface rather than maintained beside it**. It is
partly implicit today: `axis` is validated against `category.axis_keys` and
`require_claims` against `category.claim_keys`. A separately maintained list drifts
from the code, and a catalogue that has drifted is worse than none. It must cover
every mechanism in §4 that moves the candidate set, not only the two brief fields —
the pasta fixture's own second assumption is a pack-size constraint, which lands on
grouping and classification, and a catalogue that cannot express it will either
report "no control" wrongly or map it to an axis wrongly.

**An extensible vocabulary for diagnosing gaps**, derived from gaps this repository
has actually hit rather than an unvalidated list: basmati needed an external source
class *and* evidence handling; mounting paste needed an axis direction; the Rema
Tip Top miss was a discovery-strategy gap. Neither this nor the control catalogue
is R16's capability index, and building that index inside R13 would invert the
sequence.

**Retention needs a capture rule independent of the interpreted requirements.** A
review of the plan alone cannot detect an instruction missing from it. If the
interpreter selects the retained excerpts using the requirements it already
recognised, an omitted requirement vanishes from the plan *and* from the evidence
that would expose the omission, and the audit certifies its own blind spot. So
capture by **provenance, not relevance**: user-authored messages in this
conversation, plus the user's subsequent corrections. Tool output and marketplace
content are not user instructions and are not captured as such — quoted marketplace
text cannot authorise engineering, change access permissions or become a buyer
requirement. For a resumed or wider conversation, record where the retained
exchange begins and what context is missing. A complete transcript is unnecessary;
what must survive is the evidence needed to challenge the interpretation.

**Storage is a decision, not a default.** Under current ignore rules `data/*` and
root `*.json` are untracked. Untracked does not mean unreplayable, but it does mean
not reviewed in a diff, not distributed and not protected from loss — a poor fit for
an artifact that owns intent, supports resumption and holds the reviewer's referent.
Once a study exists, its required intake snapshot travels **inside the bundle**, and
the answer must not depend on a private external file. Sanitised committed examples,
private working records and durable archives have different retention policies, and
every required dependency accompanies an archive.

**Redaction must not silently remove the reviewer's basis.** Purchasing
conversations carry personal information; the repository already has a redaction
path and quarantines pages whose redaction failed. What is removed is recorded as
removed, together with whether the omission limits semantic review. If decisive
wording is unavailable, intake review must identify that limitation and cannot
claim to have established faithfulness on that point.

**Evaluation is four questions, not one.**

| Evaluation | Question | How |
|---|---|---|
| **Interpretation** | Did the conversation produce the right requirements? | Independently specified expectations per case, plus review. Not machine-decidable |
| **Preservation** | Did structured requirements survive translation? | Deterministic, once a plan-to-brief boundary exists |
| **Mechanical execution** | Did the declared controls run and affect the right stages? | Deterministic, against §5 |
| **Semantic execution** | Do those controls adequately represent the requirements? | Review. An agent can declare a control that runs correctly and answers the wrong question |

The last row is the one that constrains reporting: an agent can mark every
requirement supported while choosing irrelevant mappings, so passing the mechanical
check is not evidence that the purchase requirements were enforced and must never
be reported as if it were. Nothing here is deterministically assertable today: no
plan-to-brief boundary is implemented, and asserting that an already-structured
budget survives a transformation says nothing about whether the agent read that
budget correctly out of the user's language.

**One session is an observation.** Repeat trials and independently stated
expectations matter within a single provider and need nothing from
[R17](ROADMAP.md#r17--portability-evidence), which gates only the claim that
*another* provider reaches equivalent outcomes. Harmless wording differences are
acceptable; a different choice among several defensible defaults is acceptable when
recorded with its rationale; proceeding on an indefensible default instead of
asking is a failure whoever does it; loss or alteration of an explicit user
instruction is never acceptable and is testable.

---

## 13. Replacement operating text

These replacements are in force. They are recorded here with where each landed,
so the wording and the reason for it stay together: the runbook and AGENTS state
the rule, and this says what was wrong with the rule they replaced.

**Blocking rule** — replaced the blocking test and action in the RESEARCH table
and the corresponding AGENTS bullet:

> Ask before dependent work when unresolved information could invalidate the
> purchase decision or cause substantial avoidable work, and existing context
> provides no defensible default. Weigh the magnitude and likelihood of the
> consequence, the available budget and the cost of asking. While waiting, continue
> the work that does not depend on the answer. If a defensible default exists,
> state it and what changes if it is wrong, then proceed within existing
> authorisation. "You decide" permits a reasoned choice within the delegated scope;
> silence is not explicit confirmation.

Revise the adjacent examples consistently. Marketplace, delivery region and cost
basis are common sources of material divergence, not an unconditional fixed
questionnaire; an absent budget may still default to no cap.

**Question review** — replaced the automatic answered-but-unused rule in the
RESEARCH close-out list, the hindsight-based promotion rule beside it, and the
matching clause in R13's Done-when, which had read "removes unused questionnaire
steps":

> When asking a question, record the uncertainty it is intended to resolve and the
> expected effect on the next action or decision. At close, review whether the
> answer established eligibility, changed scope or ordering, prevented avoidable
> work, or confirmed a named load-bearing assumption. Compare that value with the
> burden of asking. A question need not change the winner to be useful. Remove or
> simplify questions when repeated evidence shows they add no material value; do
> not infer necessity solely from an outcome observed afterwards, or explicit
> agreement from silence.

**Unsupported requests and authorisation** — aligned the AGENTS bullet, the
runbook's unsupported-category section and R13's Done-when:

> An unsupported request may produce an evidence and gap plan without asking the
> user to choose an implementation module. Explain missing capability when it
> affects cost, time, confidence or the answer. Planning does not authorise
> engineering. Before R15's gates ship, any implementation work remains scoped,
> authorised maintenance under the existing workflow, and existing authorisation
> need not be requested again.

Removing an implementation choice from the user's experience must not silently
remove the engineering boundary.

**Non-operative fields** — the retained-but-unenforced nature of `cost_basis`,
`unacceptable` and `limits` is now stated beside their brief-authoring guidance,
together with the fact that `max_axis_value` caps the ranked axis and is not a
purchase budget. The characterisation test holding that description is
`tests/test_intake.py`: it asserts that two briefs differing only in those fields
produce identical **eligibility, ordering and outcome**, and deliberately not
identical report bytes or study ids, which legitimately differ and would be the
wrong invariant to freeze. The negative test that keeps the conclusion gates
from mistaking those fields for enforcement is in `tests/test_gates.py`:
rewriting `cost_basis` on a fully supported plan causes no stop, rewriting it on
the delivered-cost plan lifts none, and a budget written into `unacceptable`
satisfies nothing.

---

## 14. Worked cases and acceptance gates

Write the expected user intent and the acceptable outcomes independently of the
interpreter's produced plan, and assess against behavioural boundaries rather than
identical wording.

1. A supported request with enough context to proceed without questions or extra
   confirmation.
2. A material ambiguity resolved by one consequential clarification — a specific
   fixture, not a target question count for conversations in general.
3. A delegated choice among defensible defaults, with rationale and sensitivity.
4. No defensible default: ask or stop dependent work; do not proceed on a disclosed
   guess.
5. A retained assumption that is also a hard constraint and still binds.
6. **The delivered-cost trap**: legacy narrative fields do not change ranking, and
   the full delivered-cost recommendation is refused.
7. **Purchase budget with unit-price ordering** — "under €100 total, then cheapest
   per kilogram": detect the unsupported combination without changing its units or
   meaning.
8. An external-evidence hard condition with no eligibility integration: retain the
   finding and the gap, withhold full-request selection.
9. A supported assessment method with missing decisive evidence: preserve candidate
   accounting and return insufficient evidence.
10. An unknown category: a useful plan with no module-selection ritual and no
    unauthorised engineering.
11. A valid control mapped to the wrong objective — the mounting-paste axis:
    cheapest-per-kilogram is implemented, correct, and actively misleading for
    somebody fitting one scooter tyre. A structured contradiction between a stated
    use case and a declared axis can be asserted mechanically; recognising the
    mismatch from natural language is semantic review. **Do not invent a universal
    smallest-pack rule to make this testable** — that rule is the original failure.
12. **An agent-invented criterion**: a requirement neither the user stated nor the
    category carries. Provenance, role and disposition are visible, and a buyer's
    constraint does not become a category fact.
13. A decisive requirement dropped between user evidence, plan and brief: refusal at
    the affected transition.
14. A hard exclusion with distinct intake, acquisition and candidate effects:
    verify each applicable stage.
15. Reused probe evidence, including a probe that changes criteria and requires
    reassessment of discovery scope.
16. Stale or undated decisive prices; a later delivery of an old study; and
    fresh-dated regression fixtures that still cannot support current buying advice.
17. A changed requirement, a conflicted review, a superseded binding, and an
    attempt to reuse approval after conclusion-relevant context changed.
18. An aggregate research-budget stop, an interrupted run, and resumption from
    retained artifacts without the originating conversation.
19. A hard constraint that cannot be met: present the refusal without an adjacent
    recommendation-style shortlist, while preserving permitted bounded observations.

**The offline maintenance gate** acquires the new artifact contracts and their
versions; requirement-to-control mapping checks; plan-to-brief transition fixtures
including a dropped requirement; stage-effect cases; conclusion and rendering cases
for each stop kind; delivery-freshness checks including a stale decisive input that
fails; resource reconciliation and a complete resumption example; review-binding
failures including a review bound to a superseded report; the budget-plus-unit-price
case; and the documentation index. It needs no model and no marketplace, and uses
fixed execution-time inputs so the tests stay deterministic.

Existing example decisions must not move without an explicit behavioural reason.
Run the full gate for implementation changes, inspect report and decision diffs,
and explain baseline updates as separate claims about what the repository now
guarantees. **A passing gate protects the tested machinery; it does not establish
general understanding of arbitrary purchase requests.** Separate conversational
trials assess interpretation and semantic adequacy against independently stated
expectations, repeated within one provider.

---

## 15. What stays owned elsewhere

Execution isolation and rollback are R15's. Coverage measurement is R12's.
Capability promotion and the index are R16's. Provider portability is R17's.

**Method maturity stays off R13's critical path.** A useful unsupported-request
plan explains the limitation and the next step; it does not execute a provisional
method, so it needs no report-level provisional status. That contract becomes
necessary when provisional methods are executed or delivered, under R11 and R15.
Newness is not a confidence level.

R13 does **not** include a universal constraint language, a general
external-evidence eligibility engine, automatic capability adaptation, or R16's
capability index. Unsupported assessment paths remain explicit gaps. Narrow
additional controls may be justified by the worked cases above; none is assumed to
exist merely because a schema can describe it.

**Declared versus obtained** applies throughout: declared sources against verified
evidence (done, T3); planned evidence against achieved coverage (R13 and R12);
questions asked against questions that mattered; and declared freshness against
enforced freshness. A plan is a request, never a promise — the AKASH and Rema Tip
Top measurements say the agent cannot know at intake what discovery will miss.

**Sequence.** Write the worked cases first: what must survive intake, what permits
each next action, what the final answer may claim. Then requirement semantics and
stage consequences. Then routing, identity, contracts and storage, derived from
those and priced against the layer that actually moved.

---

## 16. Implementation sequence

### Two migration costs, and they are coupled

The order of the work is dictated by what this repository charges for a change,
not by the order the sections above are written in.

**Report bytes move** and both committed semantic reviews die. `check_review`
compares `report_sha256`, and a completed review needs a reviewer and non-empty
findings rather than a bare approval, so each break costs two *human* review acts
and cannot be regenerated.

**`study_id` moves** and all four baseline examples' pinned ids change across six
files. Because the report renders `study_id` into its own header, this cost always
triggers the first one.

The surface is exact:

| File | What moves |
|---|---|
| `shopping_advisor/maintenance/baseline.json` | four pinned `study_id` values, `contracts`, `tests` |
| [RESEARCH.md](RESEARCH.md#offline-walkthrough) | three occurrences in the offline walkthrough |
| [tests/studies/README.md](tests/studies/README.md) | one occurrence |
| [ROADMAP.md](ROADMAP.md) | the current-identity list and the T3 correction; earlier ids are already marked historical and stay as written |
| `tests/studies/t3/positive-review.json`, `tests/studies/t3/insufficient-review.json` | `report_sha256`, `basis`, `review_version` — reissued by a reviewer |

Therefore everything that can be inert on the existing four examples lands first,
and **one** explicitly named migration commit pays both costs once. What makes that
possible is a single decision: **the plan is an optional input to `run()` and
`analyse()`, exactly as the evidence ledger is today.** Absent a plan, behaviour is
byte-identical, so stages 1–9 cannot move a committed example.

### The stages

| # | Stage | Moves ids | Moves report bytes | Weight |
|---|---|---|---|---|
| 1 | Worked cases and characterisation tests | no | no | M |
| 2 | Operating-text pass (§13) | no | no | S |
| 3 | Split `audit.VERSION` into three contracts | no | no | S |
| 4 | Controls catalogue from the live category interface | no | no | M |
| 5 | Intake plan contract and the plan-to-brief refusal | no | no | L |
| 6 | Stage gates: intake, comparison support, conclusion | no | new fixtures only | L |
| 7 | Declared study scope, delivery record, freshness block | no | new fixtures only | M |
| 8 | Session resource ledger and resumption | no | no | M |
| 9 | Intake review artifact | no | no | M |
| 10 | **Migration**: manifest v3, identity projection, review v2 | **once** | **once** | L |

**Implementation status (2026-09-17): stages 1–7 shipped.** Stage 3 uses
`LEDGER_VERSION`, `AUDIT_VERSION` and `REVIEW_VERSION`, each still 1 and tracked
independently by the gate. Stage 4 is
[study/controls.py](shopping_advisor/study/controls.py), exposed by
`study controls --category CATEGORY`; its resolver reads the live registry and
covers the five mechanisms in §4. The catalogue is inspection, not an intake
plan, execution authorisation or a semantic adequacy check. Stage 5 adds
[plan v1 and the preservation boundary](CONTRACT.md#9-intake-plan-and-brief-preservation-r13-stage-5),
retained user evidence, deterministic read-back and response status, explicit brief
bindings, and bundle-internal snapshots used in replay. Stage 6 is
[study/gates.py](shopping_advisor/study/gates.py) and
[CONTRACT §10](CONTRACT.md#10-stage-gates-r13-stage-6): the intake, comparison-
support and conclusion gates, three stop kinds kept apart from the analytical
outcomes, the bounded-finding rendering, the attribution sentence from the
response status, and two plan-backed examples replayed by the maintenance gate.
Stage 7 is [study/delivery.py](shopping_advisor/study/delivery.py) and
[CONTRACT §11](CONTRACT.md#11-declared-scope-and-the-delivery-record-r13-stage-7):
the declared scope with silence read as historical, `study deliver` freezing the
execution-clock reference in a bundle-internal record, current advice as a
structural condition `validate-report` enforces past any semantic review, and
replay that never reads the clock. Stages 8 onward remain planned; the four
pre-existing study identities, decisions and report bytes stay unchanged, and
both committed reviews stand.

**1 — Worked cases and characterisation tests.** The referent, written before any
field name. The cases in §14 become committed fixtures with their intent and
acceptable outcomes stated independently of any produced plan, together with tests
pinning the three failure patterns in §1 so none of them is repaired by accident:
two briefs differing only in `cost_basis`, `unacceptable` or `limits` decide
identically; a purchase budget routed through `max_axis_value` caps unit price and
routed through `unacceptable` changes nothing; and the bronze-die study at a
reference date thirty days on yields stale ranked candidates with an unchanged
shortlist and outcome. Assert eligibility, ordering and outcome — never report
bytes or ids, which legitimately differ. *Measured effect:* three known-inert
qualifications become regressions, and every case has a written expectation before
any code exists.

**2 — Operating-text pass.** The replacements in §13, with no code dependency.
*Measured effect:* the blocking quantifier falsified by its own first example is
gone.

**3 — Split `audit.VERSION`.** One constant currently serves three contracts —
`ledger_version`, `audit_version` and `review_version`. Review v2 cannot ship
without separating them, because the bump would invalidate every committed ledger
for no reason. Three constants, all at 1, each registered in the maintenance
gate's contract discovery and in `baseline.contracts`, since a published version
absent from the baseline is itself a finding. No artifact bytes change.
*Measured effect:* three independently movable contracts where there was one.

**4 — Controls catalogue.** A resolver over the live category interface rather
than a list maintained beside it, covering all five mechanisms in §4 and not only
the two brief fields, with regression cases chosen to be sensitive to each
control's meaning. *Measured effect:* a catalogue for three categories, and cases
that fail when a control's semantics change while these examples' outputs do not.

**5 — Intake plan contract and the plan-to-brief refusal.** The requirement model
of §3, user evidence captured by the provenance rule of §12, the read-back and its
response status, and resolved control mappings — landing together with the
transition check that refuses when a decisive requirement fails to reach the brief
with the same meaning and role. The refusal is what makes the artifact pass R16's
test on the day it arrives: a plan the boundary never reads is `cost_basis` with
more fields. *Measured effect:* the dropped-requirement case refuses at the
affected transition.

**6 — Stage gates.** The refusal matrix of §3 at the stages of §5, including the
decisive-preference row, without which the delivered-cost case escapes the rule
this document is built around. Inert without a plan. *Measured effect:* the
delivered-cost recommendation is withheld while the bounded item-price finding
survives.

**7 — Declared study scope, delivery record and the freshness block.** A delivery
check that compares against the execution clock would make the gate
**clock-dependent**: the committed examples would go stale the day after they were
recorded, and the gate would begin failing with the passage of time rather than
with a change. The check therefore keys off a declared study scope — current advice
or historical — which the committed examples already assert in prose and would now
assert as data. The delivery reference is frozen in the delivery record and does
not enter `study_id` (§8). *Measured effect:* a stale decisive input blocks current
advice, and the frozen regression fixtures remain deliverable as historical.

**8 — Session resource ledger and resumption.** Declared limits, action records,
reconciliation and the next-action check, in the units the environment observes.
*Measured effect:* a study resumes from retained artifacts without the originating
conversation.

**9 — Intake review artifact.** A new artifact with its own contract, binding the
plan snapshot, mappings and control metadata, deliberately not touching the final
review or its version so that no committed review is invalidated yet.

**10 — Migration.** One commit, argued as one claim: manifest v3 for the artifacts
the bundle gains, `review_basis` as a contract with a test that a new artifact
cannot enter the bundle without a deliberate binding decision, the phase-aware
final review at v2 requiring valid intake findings, and the frozen
operative-requirement projection entering `study_id`. Then four ids re-recorded,
two reviews reissued, ids updated in the files listed above, and the baseline
re-recorded as a separately explained part of the same change. **Ids move;
decisions must not** — eligibility, ordering and outcome on all four examples are
shown unchanged in the diff.

### Decided, and one that is not

Decided here: optional-plan inertness; one migration rather than three;
scope-declared rather than clock-driven freshness; the intake review as a separate
artifact.

**Decided in stage 5 (2026-09-17): where a plan lives before a study exists.**
Private working plans use `data/plans/` or an explicit private location; a
mandatory bundle-internal snapshot accompanies every plan-backed study. Sanitized
examples are tracked under `tests/intake/`. Plans that never become studies and
their revisions/dependencies must also be durably archived. Ignored working
storage is not a backup, and the CLI does not claim that it has archived anything.
This keeps private conversations out of the repository by default while retaining
the executable study's intent without an external-file dependency.

### On estimating this

No effort figure is offered, for the reason given in §8's closing: the components
have to be scoped against the cases first. Relative weight is stated per stage, and
the two carrying the most unknown are stage 5, where the requirement dimensions
meet real language, and stage 10, where three version bumps and a reissued review
land together. Stages 1 to 4 are the ones that no later design choice can
invalidate.

---

## Evidence checked

This assessment inspected AGENTS, README, RESEARCH, CONTRACT, the R9–R17 roadmap
sections, the study audit contracts, brief parsing, ranking, study analysis,
rendering, bundle identity and verification, semantic review bindings, crawl
manifests, code provenance, the ignore rules and the relevant study and audit
tests.

Offline characterisation through the existing analysis implementation confirmed
that changing `cost_basis`, `unacceptable` or `limits` leaves candidate decisions,
ranking, shortlist and outcome unchanged in the committed bronze-die case. Moving
its reference date to 2026-10-16 under the unchanged seven-day policy left five
ranked candidates stale and thirty-two days old while preserving the same shortlist
and the same `recommendation` outcome, with the renderer's historical/incomplete
banner placed above the headline. These observations establish current behaviour,
not completed work.

The original assessment changed no runtime implementation, canonical operating
instruction, contract or baseline. Subsequent implementation status and storage
decisions are recorded in §16, with adopted semantics in CONTRACT.md.
