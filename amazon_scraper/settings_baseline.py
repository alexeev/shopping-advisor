"""Compatibility alias for the proxy-free local profile.

``SCRAPY_PROJECT=baseline`` is written down in this repository's reports, its
runbook and its roadmap, and in whatever shells and notes exist outside it.
Since T1 the profile it selects *is* the default, so this module is one line
of re-export rather than an overlay: both names resolve to exactly the same
settings, and no command that already worked has to change.

New commands need no profile selection at all. See
:mod:`amazon_scraper.settings` for the profile and
:mod:`amazon_scraper.settings_scrapeops` for the optional proxy integration.
"""

from amazon_scraper.settings import *  # noqa: F401,F403
