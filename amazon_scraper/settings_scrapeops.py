"""The optional ScrapeOps proxy and monitoring integration.

Kept from the upstream project this crawler started as, and no longer the
default (T1). It is selected explicitly::

    SCRAPY_PROJECT=scrapeops SCRAPEOPS_API_KEY=… uv run scrapy crawl amazon_product

and it needs the optional dependencies::

    uv sync --locked --extra scrapeops

Two things changed when it stopped being the default.

**The key comes from the environment.** It used to be a literal in the
settings module -- a placeholder, which is how a real one gets committed by
somebody filling in the blank. The manifest an acquisition run writes records
an allowlist of settings and never this one; see
:mod:`amazon_scraper.provenance`.

**The locale is the marketplace's, not Scrapy's.** This profile inherits the
German ``Accept-Language`` from the baseline. Previously it inherited Scrapy's
stock ``en``, which the spider's locale gate now rejects outright for
amazon.de rather than letting extraction quietly under-report.

This profile is **not validated**: every measurement in this repository was
taken without a proxy, so its pacing, challenge rate and the prices a proxied
IP is shown are unknown. Treat a study run through it as a different
acquisition path, and say so in the report.
"""

import os

from amazon_scraper.settings import *  # noqa: F401,F403

SETTINGS_PROFILE = 'scrapeops'

#: Read from the environment, never committed. An empty value is left empty
#: rather than defaulted to a placeholder: ScrapeOps then fails with its own
#: message instead of this project pretending to be configured.
SCRAPEOPS_API_KEY = os.environ.get('SCRAPEOPS_API_KEY', '')

SCRAPEOPS_PROXY_ENABLED = True
# SCRAPEOPS_PROXY_SETTINGS = {'country': 'us'}

EXTENSIONS = {
    'scrapeops_scrapy.extension.ScrapeOpsMonitor': 500,
}

DOWNLOADER_MIDDLEWARES = {
    # ScrapeOps' own retry middleware replaces Scrapy's, which the baseline
    # profile installs at 550.
    'scrapeops_scrapy.middleware.retry.RetryMiddleware': 550,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,
}

# Max concurrency on the ScrapeOps free plan is one thread, which is also what
# the baseline profile uses.
CONCURRENT_REQUESTS = 1
