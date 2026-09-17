# Auditable basmati examples

These are **synthetic software fixtures**, not acquired marketplace records or
real laboratory findings. The three record identities resemble the brands in
the legacy ledger solely to exercise its migration. No personal information or
source document is copied. `evidence.json` retains one invented laboratory
paragraph at `example.org`, labelled synthetic. Its `verified` status is test
data, not an assertion that a real source was verified.

The runtime adds three real legacy citation records with **unavailable** source
snapshots and **unverified** findings. Their original URLs/documents were never
retained; this example does not repair that historical access limit.

From the repository root:

```text
uv run --offline --locked python -m shopping_advisor.study run tests/studies/t3/positive.toml --evidence tests/studies/t3/evidence.json -o data/studies/t3-positive
uv run --offline --locked python -m shopping_advisor.study validate-report data/studies/t3-positive
uv run --offline --locked python -m shopping_advisor.study review data/studies/t3-positive tests/studies/t3/positive-review.json
uv run --offline --locked python -m shopping_advisor.study validate-report data/studies/t3-positive --require-review
uv run --offline --locked python -m shopping_advisor.study run tests/studies/t3/insufficient.toml --evidence tests/studies/t3/evidence.json -o data/studies/t3-insufficient
uv run --offline --locked python -m shopping_advisor.study review data/studies/t3-insufficient tests/studies/t3/insufficient-review.json
uv run --offline --locked python -m shopping_advisor.study validate-report data/studies/t3-insufficient --require-review
```

Use a new output directory for another run. The positive example ranks three
fixture prices at 3, 4 and 5 EUR/kg, choosing the first with a 33.3% margin.
The insufficient example requires four eligible candidates and puts none forward.
Both retain the same source/claim audit. The score is completely serialized and
replayed but never sorts this shortlist. Changing the price inputs reranks via
the existing analysis, not a second formula in the audit layer.

`test_audit.py` exercises wrong identity and variants, unknown/historical batches,
conflicts and supersession, missing and fabricated support, future source dates,
stale prices, vendor assertions, review-sample misuse, digest tampering,
rehashed score/rank/claim tampering and semantic-review binding. A source's
embedded instructions remain inert text. These tests do not establish that an
LLM will always resist prompt injection; provider trials are
[deferred to R17](../../../ROADMAP.md#r17--portability-evidence).

Both examples are replayed by the
[maintenance gate](../../../AGENTS.md#environment-and-checks) through exactly
the commands above, and their study IDs, outcomes and counts are recorded in
its baseline. A change that moves them fails the gate by name.

The JSON schema is enforced by `study/audit.py` and described in
[CONTRACT.md](../../../CONTRACT.md#8-study-audit-contracts-t3). For a new real
study, collect permitted excerpts with actual provenance, record scope and
identity without guessing, and fill the generated semantic-review checklist
in a separate pass. Both committed reviews are **review v2** (R13 stage 10,
[CONTRACT §14](../../../CONTRACT.md#14-manifest-v3-review-v2-and-the-delivery-review-r13-stage-10)):
they name their phase, bind every `semantic` artifact of the inventory, record
the intake findings they rest on — none, since neither brief has a plan — and
carry the conclusion-presentation check. They were reissued on 2026-09-17 after
manifest v3 moved the report bytes, with the six basis digests unchanged and the
findings re-read rather than copied. Never reuse these fixture approvals for
another report.
