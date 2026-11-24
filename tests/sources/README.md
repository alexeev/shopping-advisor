# Declared source ledger fixture

Synthetic data for [`tests/test_sources.py`](../test_sources.py) and the command
in [RESEARCH.md](../../RESEARCH.md#a-bounded-review-of-an-unsupported-category);
the contract is [CONTRACT §17](../../CONTRACT.md#17-declared-source-ledger-v1-bucket-f-2026-11-24).
Nothing here is a real product, document or finding.

- `records.jsonl` — four invented listings on `www.amazon.de`.
- `ledger.json` — three sources and three mappings chosen for what they prove:
  a datasheet whose model string is in the record (`checked`, the same string);
  a certificate for `PB763 v2` mapped to a record naming `PB763` (`checked`,
  *not* the same string — the counterexample automatic matching was rejected
  on); a mapping with no record field (`declared`, with its basis); one lookup
  that found nothing; and `B0SRC00004`, model `FX-200`, which has no mapping
  and must stay `not_looked_up` although `FX-100`'s datasheet is one character
  away.
