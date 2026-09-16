"""Versioned external observations; content is data, never executable policy."""
import json
from pathlib import Path


def legacy_basmati():
    return json.loads(Path(__file__).with_name('basmati-legacy.json').read_text())
