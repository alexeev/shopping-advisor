"""Tests for which crawl profile a plain command actually gets.

The default used to be the ScrapeOps profile, and it was the one
configuration that could not crawl: it names components from an optional
package that is not installed, so building the middleware and extension
managers raises ``ModuleNotFoundError``; it shipped a placeholder API key; and
it never overrode Scrapy's stock ``Accept-Language: en`` -- so a crawl of
amazon.de on the default profile asked for English and read the answer with
German label lists, which is precisely the silent under-extraction R1's locale
gate exists for.

These tests pin the swap: the validated, proxy-free, credential-free profile
is what a command with no environment variables gets, and the name every
existing command and report uses still resolves to it.
"""

import configparser
import importlib
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

import requests
import scrapy
from scrapy.crawler import Crawler
from scrapy.downloadermiddlewares import cookies
from scrapy.settings import Settings
from tldextract import TLDExtract
from tldextract.cache import DiskCache

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shopping_advisor import addons  # noqa: E402
from shopping_advisor import settings as default_profile  # noqa: E402
from shopping_advisor import settings_baseline  # noqa: E402
from shopping_advisor.extraction import for_domain  # noqa: E402
from shopping_advisor.provenance import acquisition_settings  # noqa: E402
from shopping_advisor.run import acquisition_locale  # noqa: E402

SETTING_NAMES = [name for name in dir(default_profile) if name.isupper()]


def profiles():
    parser = configparser.ConfigParser()
    parser.read(ROOT / 'scrapy.cfg')
    return dict(parser['settings'])


def as_settings(module):
    return Settings({name: getattr(module, name)
                     for name in dir(module) if name.isupper()})


class Profiles(unittest.TestCase):

    def test_a_command_with_no_environment_gets_the_validated_profile(self):
        self.assertEqual(profiles()['default'], 'shopping_advisor.settings')
        self.assertEqual(default_profile.SETTINGS_PROFILE, 'baseline')

    def test_the_name_every_existing_command_uses_still_resolves_here(self):
        """``SCRAPY_PROJECT=baseline`` is written down in this repository's
        reports, runbook and roadmap, and in shells outside it."""
        self.assertEqual(profiles()['baseline'],
                         'shopping_advisor.settings_baseline')
        for name in SETTING_NAMES:
            with self.subTest(setting=name):
                self.assertEqual(getattr(settings_baseline, name),
                                 getattr(default_profile, name))

    def test_the_scrapeops_integration_is_opt_in_and_named(self):
        self.assertEqual(profiles()['scrapeops'],
                         'shopping_advisor.settings_scrapeops')


class NoCredentials(unittest.TestCase):

    def test_every_component_this_profile_names_can_be_loaded(self):
        """A component path is a string until something instantiates it, so
        the old default listed happily and failed when a crawl built its
        middleware managers. Loading each one here is the check that matters,
        and it is the one `scrapy list` does not perform."""
        from scrapy.utils.misc import load_object
        named = (list(default_profile.DOWNLOADER_MIDDLEWARES)
                 + list(default_profile.EXTENSIONS)
                 + list(default_profile.ADDONS))
        self.assertTrue(named, 'the stock retry middleware should be restored')
        for component in named:
            with self.subTest(component=component):
                self.assertNotIn('scrapeops', component.lower())
                load_object(component)

    def test_no_api_key_is_carried_in_the_default_profile(self):
        self.assertFalse(hasattr(default_profile, 'SCRAPEOPS_API_KEY'))
        source = (ROOT / 'shopping_advisor' / 'settings.py').read_text(
            encoding='utf-8')
        self.assertNotIn('API-KEY', source)

    def test_the_optional_profile_reads_its_key_from_the_environment(self):
        """A literal placeholder in a settings module is how a real key gets
        committed by somebody filling in the blank."""
        module = importlib.import_module('shopping_advisor.settings_scrapeops')
        source = (ROOT / 'shopping_advisor' / 'settings_scrapeops.py').read_text(
            encoding='utf-8')
        self.assertIn("os.environ.get('SCRAPEOPS_API_KEY'", source)
        self.assertNotIn('API-KEY', source)
        self.assertEqual(module.SETTINGS_PROFILE, 'scrapeops')
        self.assertEqual(module.DEFAULT_REQUEST_HEADERS['Accept-Language'],
                         default_profile.DEFAULT_REQUEST_HEADERS['Accept-Language'],
                         'the optional profile inherits the German locale')


class LocaleAndPacing(unittest.TestCase):

    def test_the_default_profile_asks_amazon_de_for_german(self):
        locale = acquisition_locale(as_settings(default_profile),
                                    for_domain('www.amazon.de'))
        self.assertEqual(locale['status'], 'matches')

    def test_the_default_profile_keeps_the_measured_pacing(self):
        settings = as_settings(default_profile)
        self.assertEqual(settings.getint('CONCURRENT_REQUESTS'), 1)
        self.assertEqual(settings.getfloat('DOWNLOAD_DELAY'), 9.0)
        self.assertTrue(settings.getbool('AUTOTHROTTLE_ENABLED'))

    def test_a_manifest_records_this_profile_without_a_credential(self):
        recorded = acquisition_settings(as_settings(default_profile))
        self.assertEqual(recorded['SETTINGS_PROFILE'], 'baseline')
        self.assertFalse(recorded['proxy_middleware'])
        self.assertNotIn('SCRAPEOPS_API_KEY', recorded)
        self.assertEqual(sorted(recorded['DEFAULT_REQUEST_HEADERS']),
                         ['Accept', 'Accept-Language',
                          'Upgrade-Insecure-Requests'])
        self.assertEqual(recorded['ADDONS'],
                         ['shopping_advisor.addons.BundledPublicSuffixList'],
                         'a manifest says where the suffix list came from')


class NoThirdParty(unittest.TestCase):
    """The proxy-free profile talks to the marketplace, and to nothing else.

    Scrapy's cookies middleware asks tldextract whether a ``Set-Cookie`` domain
    is a public suffix, and tldextract's default extractor answers, the first
    time, by downloading the Public Suffix List. On the school-backpack probe
    of 2026-09-17 -- 15 requests, 15 HTTP 200, ``finished`` -- that was two
    connections to hosts that are not Amazon, both failing TLS verification,
    and twelve tracebacks in the log of a crawl that had no error of its own.
    :mod:`shopping_advisor.addons` puts the snapshot bundled with the locked
    tldextract in place of the download; these tests pin the add-on.
    """

    ADDON = 'shopping_advisor.addons.BundledPublicSuffixList'

    def setUp(self):
        self.original = getattr(cookies, addons.SCRAPY_EXTRACTOR_ATTRIBUTE)
        self.addCleanup(setattr, cookies, addons.SCRAPY_EXTRACTOR_ATTRIBUTE,
                        self.original)

    @staticmethod
    def blocked_network():
        """Every HTTP request tldextract could make fails at once, locally."""
        return mock.patch.object(
            requests.Session, 'request',
            side_effect=requests.ConnectionError('blocked by the test'))

    def test_both_profiles_enable_the_add_on(self):
        self.assertIn(self.ADDON, default_profile.ADDONS)
        scrapeops = importlib.import_module('shopping_advisor.settings_scrapeops')
        self.assertIn(self.ADDON, scrapeops.ADDONS,
                      'a proxied crawl has no more business fetching the '
                      'list than a direct one')

    def test_scrapy_still_holds_the_extractor_the_add_on_replaces(self):
        """Pinned so that a Scrapy release which moves the attribute fails
        here, in the suite, and not by quietly downloading again."""
        self.assertIsInstance(self.original, TLDExtract)
        self.assertTrue(self.original.include_psl_private_domains)

    def test_without_the_add_on_scrapy_would_download_the_list(self):
        """The counterexample: Scrapy's own construction of the extractor,
        with only its cache redirected to scratch so that this test touches
        nothing under ~/.cache."""
        with tempfile.TemporaryDirectory() as scratch:
            stock = TLDExtract(cache_dir=scratch,
                               include_psl_private_domains=True)
            with self.blocked_network() as request, \
                    self.assertLogs('tldextract', level='WARNING') as log:
                self.assertEqual(stock('www.amazon.de').domain, 'amazon',
                                 'the snapshot answers in the end')
            urls = [call.args[1] for call in request.call_args_list]
            self.assertEqual(urls, list(stock.suffix_list_urls))
            self.assertEqual(len(urls), 2)
            self.assertTrue(all(url.startswith('https://') for url in urls))
            self.assertEqual(len(log.records), 2)
            self.assertTrue(
                os.listdir(scratch),
                'and it caches the fallback under the same key, which is why '
                'the tracebacks appear once per cache identity, not per crawl')

    def test_the_installed_extractor_has_nowhere_to_fetch_from(self):
        extractor = addons.install()
        self.assertIs(getattr(cookies, addons.SCRAPY_EXTRACTOR_ATTRIBUTE),
                      extractor)
        self.assertEqual(extractor.suffix_list_urls, ())
        self.assertTrue(extractor.fallback_to_snapshot)
        self.assertTrue(extractor.include_psl_private_domains,
                        "Scrapy's cookie decision must not move with the "
                        "list's origin")
        self.assertIs(addons.install(), extractor,
                      'a second crawler in the process keeps the first one')

    def test_the_snapshot_answers_without_a_request_a_cache_or_a_warning(self):
        with self.blocked_network() as request, \
                mock.patch.object(DiskCache, 'set',
                                  side_effect=AssertionError('cache write')), \
                self.assertNoLogs('tldextract', level='WARNING'):
            split = addons.install()
            self.assertEqual(split('co.uk').domain, '',
                             'a public suffix: the cookie check says public')
            self.assertEqual(split('amazon.de').domain, 'amazon',
                             'a registrable domain: a cookie may be set on it')
            self.assertEqual(split('github.io').domain, '',
                             'a private-section suffix stays public for '
                             "cookies, as in Scrapy's own extractor")
        self.assertEqual(request.call_count, 0)

    def test_a_crawler_built_from_the_profile_installs_it_before_the_engine(self):
        """Through Scrapy's own add-on manager, which is how `scrapy crawl`
        gets there: `Crawler.crawl()` loads add-ons before it builds the
        engine and its middlewares."""
        crawler = Crawler(scrapy.Spider, as_settings(default_profile))
        with self.blocked_network() as request:
            crawler.addons.load_settings(crawler.settings)
        self.assertEqual([repr(addon) for addon in crawler.addons.addons],
                         [self.ADDON], 'and the crawl log names it')
        installed = getattr(cookies, addons.SCRAPY_EXTRACTOR_ATTRIBUTE)
        self.assertEqual(installed.suffix_list_urls, ())
        self.assertEqual(request.call_count, 0)

    def test_the_add_on_refuses_a_scrapy_that_moved_the_extractor(self):
        elsewhere = types.ModuleType('elsewhere')
        with self.assertRaises(RuntimeError) as raised:
            addons.install(module=elsewhere)
        self.assertIn('elsewhere._split_domain', str(raised.exception))
        self.assertIs(getattr(cookies, addons.SCRAPY_EXTRACTOR_ATTRIBUTE),
                      self.original, 'and it leaves Scrapy alone')


if __name__ == '__main__':
    unittest.main()
