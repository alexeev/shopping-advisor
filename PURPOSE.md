# What Shopping Advisor is for

This document owns one thing: the purpose. It says whom the product serves,
what problem it takes off their hands, whose side the agent is on and where
that role ends, and what a finished piece of work owes the buyer. It is the
first thing a buyer, a stakeholder, an operating agent or a maintainer should
read, and it is meant to stay short. Everything it names is enforced somewhere
else: [CONTRACT.md](CONTRACT.md) owns the data semantics,
[RESEARCH.md](RESEARCH.md) the procedure, [ROADMAP.md](ROADMAP.md) the
priorities and the decisions, and [AGENTS.md](AGENTS.md) the operating rules.
This file links to those homes rather than repeating them, and it carries no
numbers that go stale.

## The buyer's problem

Somebody needs to buy something — pasta for the week, a paste to seat one
scooter tyre, rice for a family, a school backpack for a child — and wants to
get it right without making it a project. The marketplace answers with
hundreds of listings in several pack sizes and colours, each described in the
vendor's own words. Five things go wrong between that shelf and a good
decision, and the product exists for all five.

- **The shelf is too wide to read.** Nobody compares two hundred listings;
  people compare the six the search put first. The agent collects the
  listings, folds pack-size variants into one offer, brings every price to one
  unit and sets aside the values whose arithmetic does not hold — the part of
  the work a person cannot do carefully at that scale.
- **The requirements arrive incomplete.** "I need a new vacuum cleaner" is how
  a real request begins. The buyer knows the purpose and forgets the
  constraint that will matter on the first dark morning. The agent looks at
  what is already known, asks the few questions that change the answer,
  proposes the criteria the buyer did not think of — from the category's
  experience or from a professional test's own checklist — and records every
  requirement with its author, so that nothing agreed in the conversation is
  lost by the time the result arrives.
- **The decisive fact is not on the page.** Whether a rice carries
  contaminants, whether a satchel is visible in traffic, is settled by a
  laboratory or a test institute, not by a product description. The agent
  reads independent tests and manufacturer specifications when the question
  needs them, records each with its date, its publisher and what exactly it
  applies to, and says when no applicable test exists instead of lending an
  adjacent product class's verdict to this one.
- **The numbers on the page are wrong.** Vendors fill in the forms, and a
  sixteen-pack filed as one pack gives the marketplace's own price per
  kilogram a straight face. Every value here carries where it came from and
  which checks it survived; a contradiction is shown, not averaged away; and a
  ranking is refused rather than built on a disputed number.
- **The work evaporates.** A shop assistant's advice is gone when the
  conversation ends. Here the question, the evidence, the decisions and the
  lessons stay in files: the next question begins from what the last one
  learned, and a result can be checked without the conversation that produced
  it.

The product does not promise the best product. It promises a comparison the
buyer can defend, or a precise account of why the evidence does not support
one — and the second is a result, not a failure.

## Whose side the agent is on

The agent is an independent researcher working for the buyer. It has no
seller's interest and takes no seller's word for a fact: a vendor's statement
is recorded as the vendor's statement, quoted from the page, and never promoted
to a verified property of the goods. The buyer's constraints live in the brief
and the plan, not in the code, so that a later reader can always tell what
this buyer wanted from what is true of the product class.

It is not a shop assistant who knows the range, and the difference matters in
five ways.

1. **It does not know the shelf until it looks.** There is no product
   database. Every study collects afresh, or reads evidence retained from an
   earlier crawl and labelled as historical. Search does not enumerate a
   shelf; the agent states what it searched, how deep, and what it did not
   see.
2. **It judges claims, not goods.** Nothing here handles the product. What can
   be established is what the page says, whether the page contradicts itself,
   and what an independent source measured — each attributed.
3. **It ranks on one axis.** A study orders candidates on one declared axis in
   one unit, under the hard requirements the brief states. Several soft
   preferences at once are the buyer's call over the shortlist, not the
   agent's weighting.
4. **It has no delivered-cost budget yet.** The brief can cap the ranked
   unit price and, since 2026-09-18, bound the listed price or any other
   number a category publishes on the card; it cannot enforce a total spend
   that includes delivery, because delivery is on no card. Prices are shown
   and the gap is said out loud. [INTAKE.md](INTAKE.md#4-current-capability-boundaries) records the
   boundary and the work on it.
5. **It sees one shop at a time.** Amazon.de is the validated marketplace; a
   study covers one marketplace, and the report says which.

Where a category is not yet known to the repository, the agent says what it
can still establish — price, quantity, contradictions — and what it cannot,
which is what makes one such product good. The procedure for that moment is in
[RESEARCH.md](RESEARCH.md#say-so-when-the-category-is-not-supported). When the
repository lacks what a question needs, the agent may extend it — a category,
a parser, a method — as reviewed, tested maintenance, and the buyer hears of it
only when it changes cost, time, confidence or the decision. Making that
routine is the [product vision](ROADMAP.md#product-vision--the-shopping-conversation),
and it is planned, not shipped.

## Who operates it

The buyer and the operator are the same person, and today every one of them
is an IT professional working through an agentic coding harness. The goal is
the purchase decision; the means is driving the agent's tools, reading its
diffs and judging its changes. Nobody without that expertise operates the
product, and the documents do not pretend otherwise. Two things follow. A
change the agent makes is reviewed at once by an experienced engineer, and the
harness's own permission system stands in front of anything unsafe, so the
repository's guards exist to make that review mechanical and replayable, not
to replace the engineer or defend against them. And an expert buyer is still a
buyer: the questions, the coverage statement and the honesty rules above are
owed to them exactly as they would be to anyone else.

## What a finished outcome owes the buyer

A study is done when the buyer holds all of the following. Each item names the
place that enforces it, so this list is an index and not a second contract.

| The buyer receives | Where it is enforced |
|---|---|
| The question as it was understood, and the use case behind it | The brief — [RESEARCH.md](RESEARCH.md#the-brief-itself) |
| Every requirement with its role (hard, preference or context), its author (the buyer, a cited source or the agent), and whether the brief stated it or the category supplied the default | Plan v1 — [CONTRACT.md §9](CONTRACT.md#9-intake-plan-and-brief-preservation-r13-stage-5); the semantics in [INTAKE.md §3](INTAKE.md#3-requirement-semantics) |
| What was searched and what was not: queries, pages, caps, and the plain statement that search does not enumerate a shelf | The run manifest — [README.md](README.md#collecting-and-retaining-evidence); the research rules in [AGENTS.md](AGENTS.md#research-rules) |
| Every candidate considered and its fate, with the reason | The study bundle and `rank --json` — [README.md](README.md#commands) |
| A recommendation, a tie, or the exact reason there is none, judged by stopping criteria written before the data was seen | Stage gates — [CONTRACT.md §10](CONTRACT.md#10-stage-gates-r13-stage-6); the brief's `minimum_candidates` and `decisive_margin` |
| Every decisive number with its source and its status, contradictions shown | The status and source vocabularies — [CONTRACT.md](CONTRACT.md#status-vocabulary) |
| External facts with their date, publisher and applicability, and what no source covered | The evidence ledger — [CONTRACT.md §8](CONTRACT.md#8-study-audit-contracts-t3); [RESEARCH.md](RESEARCH.md#check-external-evidence-and-write-the-report) |
| What the study is — a historical comparison or current advice — and when it goes stale | The delivery record — [CONTRACT.md §11](CONTRACT.md#11-declared-scope-and-the-delivery-record-r13-stage-7); [RESEARCH.md](RESEARCH.md#deliver-the-study-and-say-what-it-is) |
| What to verify by hand before buying | The semantic review — [CONTRACT.md](CONTRACT.md#final-review-v2) |
| A result that replays without the conversation | `study verify` — [RESEARCH.md](RESEARCH.md#a-saved-study-end-to-end) |

Nothing on this list is established by an automated check alone. The checks
establish that the artifacts are complete, consistent and replayable; a
reviewer establishes that they mean what they say.

## What the product is not

- A fixed shopping application awaiting its own chat or web frontend. The
  coding interface is the lasting interface; CLI commands are tools used by
  the agent.
- A scraper with advice appended, or a programme to prebuild every category.
  Acquisition and maintained categories serve decisions, not coverage targets.
- An unrestricted self-modifying agent. A task cannot silently rewrite its own
  trust policy, permissions or acceptance criteria to manufacture success.
- A universal product ontology, scoring engine or agent framework. Shared
  abstractions earn their place through demonstrated use.
- A product expert who knows the range. The agent's expertise is method — how
  to compare defensibly, and how not to be fooled by a page — and its product
  knowledge is whatever a maintained category has earned against real
  listings.

## Three readers

| Reader | What this file settles | Where to go next |
|---|---|---|
| A buyer or a stakeholder | What the product does for a purchase, what it refuses to pretend, and what a finished result looks like | [tests/studies](tests/studies/README.md): two committed studies, one that recommends and one that refuses and says why |
| An operating agent | Whom it works for, and what a good outcome is when two rules pull apart | [AGENTS.md](AGENTS.md), then [RESEARCH.md](RESEARCH.md) |
| A maintainer | Which trade-offs the product exists to make, so that a change can be judged against them | The [decision principles](ROADMAP.md#decision-principles), and [CONTRACT.md](CONTRACT.md) before changing a meaning |

## Glossary

One line per term, and a link to the document that owns it. The definition
lives there; this is the index.

| Term | Meaning | Owner |
|---|---|---|
| Brief | The written question, use case, constraints, assumptions and limits a study runs under; data, never code | [RESEARCH.md](RESEARCH.md#the-brief-itself) |
| Intake plan | The structured record of the conversation — requirements with their roles, authors and settlements — read back to the buyer | [CONTRACT.md §9](CONTRACT.md#9-intake-plan-and-brief-preservation-r13-stage-5) |
| Intake review | A separate check that the plan did not misread the request | [CONTRACT.md §13](CONTRACT.md#13-intake-review-r13-stage-9) |
| Study, bundle | The brief plus every candidate, its fate, the decisions and a generated report, saved under an id derived from its inputs | [RESEARCH.md](RESEARCH.md#a-saved-study-end-to-end) |
| Stage gates, stops, bounded finding | Where a study withholds its recommendation because a decisive requirement has no executable control, and reports what it can under its own heading | [CONTRACT.md §10](CONTRACT.md#10-stage-gates-r13-stage-6) |
| Freshness scope, delivery record | Whether a study is a historical comparison or current advice, and the frozen instant at which that was decided | [CONTRACT.md §11](CONTRACT.md#11-declared-scope-and-the-delivery-record-r13-stage-7) |
| Delivery review | The named attestation that a permitted current-advice delivery was reviewed | [CONTRACT.md](CONTRACT.md#the-delivery-review) |
| Semantic review | The pass over meaning that automated validation cannot make, signed by its reviewer | [CONTRACT.md](CONTRACT.md#final-review-v2) |
| Session ledger | The declared budget of requests and time, what each probe and collection consumed, and what remains | [CONTRACT.md §12](CONTRACT.md#12-session-resource-ledger-and-resumption-r13-stage-8) |
| Evidence ledger | External sources with their retained text, dates and applicability; declared until checked | [CONTRACT.md §8](CONTRACT.md#8-study-audit-contracts-t3) |
| Record | What the extractor read from one product page, faithful to the page even where the page is wrong | [CONTRACT.md §2](CONTRACT.md#2-the-product-record-schema-v6) |
| Validated record, Value | The record after the generic checks: every value with its source, its status and its evidence | [CONTRACT.md §3](CONTRACT.md#3-the-validated-record-contract-v2) |
| Source | How a value was obtained: structured, attributes, text, published, derived | [CONTRACT.md](CONTRACT.md#source-vocabulary) |
| Status | What a value survived: trusted, disputed, unverified, unknown, not_claimed | [CONTRACT.md](CONTRACT.md#status-vocabulary) |
| Category, profile, axis, claim | What a product is, which plausibility bands apply, which axes rank and in which direction, and which vendor statements matter | [CONTRACT.md §5](CONTRACT.md#5-what-a-category-supplies-and-what-it-may-not) |
| Card | One product's evidence, quoted and attributed, in text or JSON | [RESEARCH.md](RESEARCH.md#3-inspect-a-card-and-its-evidence) |
| ASIN, offer, family | Amazon's identifier for one listing; pack-size variants folded into one offer; non-size variants kept apart | [CONTRACT.md](CONTRACT.md#listing-identity-is-a-marketplace-and-an-asin) |
| Controls | The executable filters and limits a category actually offers a brief | [RESEARCH.md](RESEARCH.md#inspect-executable-controls-before-mapping-requirements) |
| Capability index, lifecycle | What each registered capability has earned — a task experiment, a maintained capability, a shared foundation or a retired one — where it was measured and what it declines; inspection, and never a statement about a value's trust | [RESEARCH.md](RESEARCH.md#inspect-executable-controls-before-mapping-requirements), [ROADMAP.md, R16](ROADMAP.md#r16--capability-lifecycle-and-architectural-review) |
| Feed, run, manifest | The JSONL a crawl wrote; the directory that records what the crawl did, with which code, and what it retained | [README.md](README.md#collecting-and-retaining-evidence) |
| Coverage | What a collection searched and how deep; never a claim to have seen the shelf | [ROADMAP.md, R12](ROADMAP.md#r12--discovery-that-states-its-own-coverage) |
| Corpus, cases | Saved pages that pin extraction; selected records that pin a category's verdicts, counterexamples included | [tests/corpus](tests/corpus/README.md), [tests/cases](tests/cases/README.md) |
| Maintenance gate, baseline | The one local command that verifies the repository, and the tracked record of what it is entitled to find | [AGENTS.md](AGENTS.md#environment-and-checks) |
| Decision principles | The tie-breakers a maintainer applies when a proposal could go either way | [ROADMAP.md](ROADMAP.md#decision-principles) |
