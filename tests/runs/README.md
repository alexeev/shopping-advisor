# Retained run fixtures

Run directories the tests read as evidence about the crawler's own records,
**without their pages**: each holds the `manifest.json` a real crawl wrote, its
`discovery.jsonl` and its `pages.jsonl` index. The pages themselves stay in
the operator's gitignored `data/runs/`; nothing here can be re-extracted, and
nothing here is a product record.

| Run | Why it is here |
|---|---|
| `20260919T111600Z-www.amazon.de-eb1e5c7f` | The targeted powerbank crawl of 2026-09-19 that the operator **stopped** after 16 responses. Its manifest is `state: closed` with `finish_reason: shutdown`, which `run_state` used to read as complete and `session-record` therefore wrote as `completed` ([HISTORY.md](../../HISTORY.md#postmortem-of-the-iphone-15-qi2-powerbank-review--2026-09-19), row 6). Its manifest predates the coverage counts, so `coverage()` recomputes them from the arguments, the discovery log and the page index: 5 of 7 seeds and 8 of 40 discovered listings fetched. `tests/test_run.py` pins the state and the counts; `tests/test_session.py` records a collection from it as `interrupted` and authorises a dependent that declares `builds_on_partial` |

The files are copied verbatim. A manifest carries an allowlist of acquisition
settings and never a credential ([provenance](../../shopping_advisor/provenance.py));
the discovery log holds search-result titles and price texts, which are
listing data, and the index holds paths, digests and fetch times.
