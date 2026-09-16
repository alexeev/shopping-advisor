# Study briefs

Two complete worked studies over the committed [case feeds](../cases/README.md),
runnable offline from a fresh clone with no private files. They are the
examples [RESEARCH.md](../../RESEARCH.md#a-saved-study-end-to-end) walks
through, and `../test_study.py` asserts both down to their ASINs.

```
pasta-bronze-die.toml               reaches a recommendation
pasta-low-temperature-drying.toml   refuses, and says exactly why
```

Both read `../cases/pasta_v1.jsonl.gz`. **A brief's `inputs` are relative to
the brief file, not to the working directory**, so a brief and the feeds it
names travel together and no absolute path ever enters a committed file.

## Why there are two

A study that can only succeed is not a study. The second brief exists because
the refusal path is the one that gets quietly skipped: nothing fails when an
agent turns a thin result into a confident one, and the difference is visible
only to whoever buys the pasta.

**`pasta-bronze-die`** asks for the cheapest kilogram among the listings that
state bronze-die extrusion. Eight of the twenty-two classified records state
it; five have a price per kilogram that survived validation; three are
excluded because Amazon quotes a unit price *per piece*, which cannot confirm
a price per weight. The leader is 9.1% ahead of the runner-up, past the 5%
the brief declared decisive before the data was seen, so there is a winner.

**`pasta-low-temperature-drying`** asks the same question of the listings that
state low-temperature drying. Two state it — and *both* have a disputed price
per kilogram, for the same reason those three were excluded. The requirement
is met and the axis is not, so the study returns insufficient evidence and
names the two listings with their contradictions. Forcing a comparison here
would mean ignoring a contradiction the page itself contains.

## What they are not

- **Not buying advice.** The records are a selected regression set built to
  exercise particular validation rules, and their prices are fixed so the
  studies reproduce. The cheapest bronze-die pasta on Amazon.de is very
  probably not among twenty-five records chosen for their defects.
- **Not a survey.** Search does not enumerate a shelf.
- **Not a verified property of any pasta.** A `trusted` claim is one the page
  demonstrably makes, quoted on the evidence card.

## Running them

```text
uv run --offline --locked python -m amazon_scraper.study check tests/studies/pasta-bronze-die.toml
uv run --offline --locked python -m amazon_scraper.study run tests/studies/pasta-bronze-die.toml
uv run --offline --locked python -m amazon_scraper.study verify data/studies/pasta-bronze-die-501d864a1a0c
```

The study id is derived from the brief, the input digests and the published
schema/contract versions, so `run` lands in the same directory name on any
machine and the id above is the one a clean checkout produces. Bundles are
written under `data/studies/`, which is gitignored: the bundle is output, the
brief is source. Nothing here touches the network.

## Adding one

Keep the brief's question answerable from committed evidence, state the
stopping criteria (`minimum_candidates`, `decisive_margin`) *before* looking
at what the data supports, and add the assertions to `../test_study.py` in
the same change. A brief whose expected outcome is not asserted will drift
without anything failing, which is the failure mode these exist to prevent.

`amazon_scraper/study/brief.py` holds the schema and refuses unknown keys, so
a misspelt constraint is an error rather than a constraint that silently did
nothing. A brief names a category by its **registry key** and never by an
import path; nothing in it is imported, evaluated or interpolated into a
command.
