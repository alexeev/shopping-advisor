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
import pathlib
import sys
import unittest

from scrapy.settings import Settings

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from amazon_scraper import settings as default_profile  # noqa: E402
from amazon_scraper import settings_baseline  # noqa: E402
from amazon_scraper.extraction import for_domain  # noqa: E402
from amazon_scraper.provenance import acquisition_settings  # noqa: E402
from amazon_scraper.run import acquisition_locale  # noqa: E402

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
        self.assertEqual(profiles()['default'], 'amazon_scraper.settings')
        self.assertEqual(default_profile.SETTINGS_PROFILE, 'baseline')

    def test_the_name_every_existing_command_uses_still_resolves_here(self):
        """``SCRAPY_PROJECT=baseline`` is written down in this repository's
        reports, runbook and roadmap, and in shells outside it."""
        self.assertEqual(profiles()['baseline'],
                         'amazon_scraper.settings_baseline')
        for name in SETTING_NAMES:
            with self.subTest(setting=name):
                self.assertEqual(getattr(settings_baseline, name),
                                 getattr(default_profile, name))

    def test_the_scrapeops_integration_is_opt_in_and_named(self):
        self.assertEqual(profiles()['scrapeops'],
                         'amazon_scraper.settings_scrapeops')


class NoCredentials(unittest.TestCase):

    def test_every_component_this_profile_names_can_be_loaded(self):
        """A component path is a string until something instantiates it, so
        the old default listed happily and failed when a crawl built its
        middleware managers. Loading each one here is the check that matters,
        and it is the one `scrapy list` does not perform."""
        from scrapy.utils.misc import load_object
        named = (list(default_profile.DOWNLOADER_MIDDLEWARES)
                 + list(default_profile.EXTENSIONS))
        self.assertTrue(named, 'the stock retry middleware should be restored')
        for component in named:
            with self.subTest(component=component):
                self.assertNotIn('scrapeops', component.lower())
                load_object(component)

    def test_no_api_key_is_carried_in_the_default_profile(self):
        self.assertFalse(hasattr(default_profile, 'SCRAPEOPS_API_KEY'))
        source = (ROOT / 'amazon_scraper' / 'settings.py').read_text(
            encoding='utf-8')
        self.assertNotIn('API-KEY', source)

    def test_the_optional_profile_reads_its_key_from_the_environment(self):
        """A literal placeholder in a settings module is how a real key gets
        committed by somebody filling in the blank."""
        module = importlib.import_module('amazon_scraper.settings_scrapeops')
        source = (ROOT / 'amazon_scraper' / 'settings_scrapeops.py').read_text(
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


if __name__ == '__main__':
    unittest.main()
