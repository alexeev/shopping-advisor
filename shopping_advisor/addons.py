"""One Scrapy add-on: the public suffix list comes from the locked snapshot.

Scrapy's cookies middleware decides whether a ``Set-Cookie`` domain is a
public suffix -- ``co.uk`` and ``github.io`` are, ``amazon.de`` is not -- with
a module-level :class:`tldextract.TLDExtract` built with the library's
defaults. The first time it is consulted, which is the first response that
carries a cookie, that default extractor tries to *download* the Public
Suffix List from publicsuffix.org and then from a GitHub mirror, caches
whatever it ends up with under ``~/.cache/python-tldextract/<python>__<venv>__
<version>/``, and only after both downloads fail falls back to the snapshot
shipped inside the tldextract wheel.

Measured on the school-backpack probe of 2026-09-17 (15 requests, 15 HTTP
200, ``finish_reason: finished``, no ``log_count/ERROR``): the crawl process
opened TLS connections to two hosts that are not the marketplace, both were
refused by this machine's certificate verification, and the log carried two
``[tldextract] WARNING`` entries with twelve chained Python tracebacks between
them, for a failure that changed nothing about the crawl. Those requests are
not Scrapy requests: ``downloader/request_count`` in the run manifest does not
count them, and the manifest's claim that the proxy-free profile asked the
marketplace and nobody else was not true of the process. The TLS failure is
local and incidental -- with a working trust store the same two requests
would simply have succeeded, silently, and the list a crawl used would have
depended on the day and on a per-machine cache.

The add-on replaces that extractor with one that has no URLs, no disk cache
and the bundled snapshot only. Two consequences:

* **The proxy-free profile talks to the marketplace and nothing else.** Which
  suffix list a crawl used is fixed by the tldextract version in ``uv.lock``,
  whose digest the manifest already records, instead of by publicsuffix.org's
  state on the day or by what an earlier run left in ``~/.cache``.
* **A crawl log's tracebacks are the crawl's.** Nothing is fetched, so
  nothing fails, and ``log_count/WARNING`` counts what the crawl did.

Why an add-on and not a setting: Scrapy 2.19 exposes no setting for this. The
extractor is a private module attribute of
``scrapy.downloadermiddlewares.cookies``, and the function that consults it
reads the attribute at call time, so replacing it before the engine exists is
enough. An add-on is Scrapy's documented hook for exactly that moment -- it
runs from ``Crawler.crawl()`` before the middleware managers are built -- it
is enabled from the settings profile like any other component, and the crawl
log names it under ``Enabled addons``. The swap reaches into a private name
on purpose and **fails loudly** when that name is gone: a Scrapy release that
moves it is the kind of change the pinned runtime exists to make deliberate,
and a crawl that quietly resumed downloading the list would be worse than one
that refuses to start.

``cache_dir=None`` is deliberate too: with no URLs there is nothing a cache
could save, the snapshot parses once per process in well under a second, and
a crawl then writes nothing outside its own run directory.
"""

from scrapy.downloadermiddlewares import cookies as _cookies
from tldextract import TLDExtract

#: The private attribute Scrapy's cookies middleware consults. Named once, so
#: that the add-on and its tests cannot disagree about what is being replaced.
SCRAPY_EXTRACTOR_ATTRIBUTE = '_split_domain'


def bundled_extractor():
    """A ``TLDExtract`` that never fetches: no URLs, no disk cache, snapshot only.

    ``include_psl_private_domains=True`` is what Scrapy's own extractor uses
    and it has to stay: a private-section suffix such as ``github.io`` counts
    as public for cookie purposes, and the middleware's decision must not
    move because of where the list came from.
    """
    return TLDExtract(cache_dir=None, suffix_list_urls=(),
                      fallback_to_snapshot=True,
                      include_psl_private_domains=True)


def install(module=_cookies):
    """Put :func:`bundled_extractor` where ``module`` keeps its extractor.

    Returns the extractor in place afterwards. A second call finds the first
    one and keeps it. Raises rather than returning if ``module`` holds no
    ``TLDExtract`` under the expected name: the alternative is leaving the
    default, and its downloads, in place without a word.
    """
    current = getattr(module, SCRAPY_EXTRACTOR_ATTRIBUTE, None)
    if not isinstance(current, TLDExtract):
        raise RuntimeError(
            f'{module.__name__}.{SCRAPY_EXTRACTOR_ATTRIBUTE} is not a '
            f'tldextract.TLDExtract: Scrapy has moved the public suffix lookup '
            f'this add-on configures. Find it again before crawling, or the '
            f'cookies middleware will download the Public Suffix List.')
    if not current.suffix_list_urls:
        return current
    extractor = bundled_extractor()
    setattr(module, SCRAPY_EXTRACTOR_ATTRIBUTE, extractor)
    return extractor


class BundledPublicSuffixList:
    """Scrapy add-on: cookie-domain checks use the locked snapshot, never a download."""

    def update_settings(self, settings):
        install()

    def __repr__(self):
        # Scrapy logs the add-on *instances* under "Enabled addons"; the class
        # path is what a reader of the crawl log can look up.
        return f'{type(self).__module__}.{type(self).__name__}'
