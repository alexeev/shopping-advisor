"""Reading a JSON-lines feed, gzipped or not.

One function, and a module of its own on purpose. Until the second
architectural review (R16, 2026-09-19) it lived in :mod:`shopping_advisor.run`,
the acquisition module, and three downstream layers -- analysis, study and
delivery -- imported the acquisition module to read a file. Nothing in reading
a line of JSON is about crawling; the import edge said otherwise. The first
review scheduled the move for the next change to ``run.py``; that change
(``89c854b``) happened without it, and the second review carried it out as its
own commit, with no semantic diff: every caller reads the same bytes into the
same records.
"""

import gzip
import json


def read_jsonl(path):
    """Every record of a feed, gzipped or not."""
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]
