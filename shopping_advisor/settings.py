"""The default crawl profile: local, proxy-free, paced for Amazon.de.

This module used to hold the upstream ScrapeOps configuration, and the
validated profile lived beside it in ``settings_baseline`` behind
``SCRAPY_PROJECT=baseline``. The default was therefore the one configuration
that could not crawl. Three faults, measured on a checkout without the
optional extra installed:

* it names ``scrapeops_scrapy`` and ``scrapeops_scrapy_proxy_sdk`` components,
  and none of the three can be loaded, so a crawl fails with
  ``ModuleNotFoundError`` when the middleware and extension managers build.
  (``scrapy list`` still works: component paths are strings until something
  instantiates them, which is exactly why the failure arrives at crawl time.)
* it ships a placeholder API key as a literal, which is how a real one gets
  committed by somebody filling in the blank;
* it never overrides Scrapy's stock ``Accept-Language: en``, so a crawl of
  amazon.de on that profile asked for English and read the answer with German
  label lists -- the silent under-extraction R1's locale gate exists for,
  present in the default configuration.

T1 swaps them. The profile that is validated, needs no credentials and no
third party is the default; the ScrapeOps integration is
:mod:`shopping_advisor.settings_scrapeops`, selected explicitly and reading its
key from the environment. ``SCRAPY_PROJECT=baseline`` still resolves here, so
every command already written down keeps working.
"""

#: Which profile answered. Recorded in every run manifest, because pacing and
#: request path change what a crawl observed.
SETTINGS_PROFILE = 'baseline'

BOT_NAME = 'shopping_advisor'

SPIDER_MODULES = ['shopping_advisor.spiders']
NEWSPIDER_MODULE = 'shopping_advisor.spiders'

ROBOTSTXT_OBEY = False

# Scrapy 2.19 enables the RemoteControl extension by default, which serves an
# HTTP endpoint that executes code inside the running crawl process. Nothing
# in this project uses it, and the validated baseline never had it, so it
# stays off rather than silently widening what a crawl exposes.
REMOTE_CONTROL_ENABLED = False

# Replacing the dictionaries rather than switching entries off inside them:
# a component this profile does not name is a component nothing will try to
# import. The ScrapeOps packages are an optional extra and are not installed
# by ``uv sync --locked``.
EXTENSIONS = {}

DOWNLOADER_MIDDLEWARES = {
    # Scrapy's stock retry middleware, at its default position.
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
}

# The cookies middleware decides whether a Set-Cookie domain is a public
# suffix with tldextract, whose default extractor *downloads* the Public
# Suffix List from publicsuffix.org and a GitHub mirror the first time it is
# asked. The school-backpack probe of 2026-09-17 -- 15 requests, all 200 --
# therefore opened connections to two hosts that are not the marketplace,
# both failed TLS verification on this machine, and its log carried twelve
# tracebacks from a failure that changed nothing; the manifest's request
# count never saw the two requests. This add-on has the middleware read the
# snapshot bundled with the *locked* tldextract instead: no download, no
# per-machine cache, and the list a crawl used is fixed by uv.lock. The
# optional ScrapeOps profile inherits it. See shopping_advisor/addons.py.
ADDONS = {
    'shopping_advisor.addons.BundledPublicSuffixList': 0,
}

# --- Conservative local crawl profile --------------------------------------
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# 9 seconds, not the 2 this profile was validated at. Measured on 2026-09-15,
# three crawls of the same shelf within one hour:
#
#   delay  requests  challenges  items
#   2.0    21        18          2       abandoned
#   9.0    51         0         48       finished
#   9.0    56         0         53       finished
#
# At 2 s Amazon answered almost every product page with a captcha, and the
# crawl produced two usable records before it was stopped. The same queries at
# 9 s ran to completion without a single challenge. A blocked crawl is not a
# slow crawl -- it is no crawl, and it costs Amazon the requests anyway.
#
# This is a floor rather than a tuned optimum: 9 s is the first value tried
# after 2 s failed, and nothing between them was measured. Lower it only with
# `amazon/challenge/*` in the run manifest in front of you.
DOWNLOAD_DELAY = 9.0
# Scrapy 2.19 replaced the RANDOMIZE_DOWNLOAD_DELAY toggle with an explicit
# magnitude. 0.5 is what the old toggle meant, so the delay still varies
# uniformly between 0.5x and 1.5x of DOWNLOAD_DELAY, as during validation.
DOWNLOAD_DELAY_JITTER = 0.5

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 9
AUTOTHROTTLE_MAX_DELAY = 30
# 0.3 rather than 0.5: autothrottle targets an *average* concurrency, and at
# 0.5 it shortens the delay again as soon as Amazon answers quickly -- which
# it does, right up until it answers with a captcha instead.
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.3

COOKIES_ENABLED = True

RETRY_TIMES = 2

DOWNLOAD_TIMEOUT = 30

# A single, ordinary desktop browser identity. This is not UA rotation: the
# stock "Scrapy/x.y" agent is rejected outright by Amazon, so one realistic
# static UA is the minimum needed to observe normal behaviour.
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
)

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
              'image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
}

LOG_LEVEL = 'INFO'

FEED_EXPORT_ENCODING = 'utf-8'
