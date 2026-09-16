"""Command line for adding a page to the committed corpus.

The rules themselves are runtime code -- :mod:`shopping_advisor.redaction` --
because the crawler's page store depends on them and a crawl's privacy
handling must not depend on a test directory being importable. This file is
the corpus-side entry point and nothing else.

Every page in this corpus is run through ``redact`` before it is committed.
The pages are fetched without signing in -- ``customerId`` is empty and
``isCustomerLoggedIn`` is ``false`` on all of them -- so there is no account
data to remove. What is left are the anonymous identifiers Amazon mints per
session and per request, which have no place in a git history.

Usage, when adding a page to the corpus::

    python tests/corpus/redact.py raw.html tests/corpus/amazon_de/B0XXXXXXXX.html.gz
"""

import gzip
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from shopping_advisor.redaction import (CORRELATION_ID, REQUEST_ID,  # noqa: E402
                                      SESSION_ID, redact)

__all__ = ['CORRELATION_ID', 'REQUEST_ID', 'SESSION_ID', 'redact']


def main(src, dest):
    opener = gzip.open if src.endswith('.gz') else open
    with opener(src, 'rt', encoding='utf-8') as fh:
        html = fh.read()
    with gzip.open(dest, 'wt', encoding='utf-8', compresslevel=9) as fh:
        fh.write(redact(html))
    print(f'{src} -> {dest}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1].strip())
    main(sys.argv[1], sys.argv[2])
