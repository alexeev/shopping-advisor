"""Exercise product entry points in fresh processes, as an operator runs them."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent


class ProductCLI(unittest.TestCase):
    def command(self, *arguments):
        return subprocess.run(
            [sys.executable, '-m', 'shopping_advisor', *arguments],
            cwd=ROOT, capture_output=True, text=True, timeout=30)

    def test_layer_help_is_forwarded(self):
        for layer in ('study', 'analysis', 'run'):
            with self.subTest(layer=layer):
                result = self.command(layer, '--help')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('shopping_advisor.' + layer, result.stdout)

    def test_study_check_and_failure_status(self):
        result = self.command('study', 'check',
                              'tests/studies/pasta-bronze-die.toml')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('valid brief', result.stdout)
        result = self.command('study', 'check', 'missing-brief.toml')
        self.assertEqual(result.returncode, 2)

    def test_analysis_preserves_fixture_result(self):
        result = self.command('analysis', 'summary',
                              'tests/cases/pasta_v1.jsonl.gz',
                              '--category', 'dry_pasta')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('22', result.stdout)
        self.assertIn('25', result.stdout)

    def test_unknown_command_is_rejected(self):
        self.assertEqual(self.command('unknown').returncode, 2)

    def test_scrapy_discovers_only_the_source_spider(self):
        env = {key: value for key, value in os.environ.items()
               if key not in ('SCRAPY_PROJECT', 'SCRAPY_SETTINGS_MODULE')}
        result = subprocess.run(
            [sys.executable, '-m', 'scrapy', 'list'], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'amazon_product')
