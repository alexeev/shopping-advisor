"""What produced an artefact: which code, which settings, which bytes.

A run manifest used to say what was asked for and what came back. It did not
say *which repository state answered the question*, which turns every finding
older than the last commit into a claim nobody can check: a record extracted
by schema 5 and one extracted by schema 6 are different readings of the same
shelf, and nothing on disk distinguished them.

Three kinds of identity are recorded, and they are deliberately separate:

**Code identity** -- the commit, whether the tree was dirty, the dependency
lock digest, the interpreter and Scrapy versions, and the two published
artefact versions. Enough to say "this is reproducible from that state", and
honest when it is not: a dirty tree is recorded as dirty rather than as its
last commit.

**Acquisition settings** -- an allowlist. Not the effective settings dump:
that is the whole of Scrapy's configuration including whatever a profile adds,
and serialising it into a file this project keeps beside its evidence is how a
proxy key ends up in an archive. Only names on the list are written, only
header names on a second list are written, and a guard drops anything that
looks like a credential even if somebody adds it to the list later.

**Artefact digests** -- SHA-256 over the bytes actually stored. For a retained
page that is the bytes *after* redaction, which is not a hash of Amazon's
response; :func:`shopping_advisor.redaction.redact_page` changed them on
purpose. The digest answers "is this the file the manifest describes", not
"is this what the server sent", and the manifest says so in the field name.
"""

import functools
import hashlib
import json
import pathlib
import platform
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Version of the manifest/page-index shape written by :mod:`shopping_advisor.run`.
#: A run store without it predates T1: its pages have no recorded fetch time,
#: no digests and no feed bindings, and a reader must treat their freshness as
#: unknown rather than inferring it from the filesystem.
RUN_MANIFEST_VERSION = 2

# The settings that describe *how the marketplace was asked*, and nothing
# else. Each one changes what a crawl observed or how hard it pushed; none of
# them is a credential. Anything not on this list is not written down.
ACQUISITION_SETTINGS = (
    'SETTINGS_PROFILE', 'BOT_NAME', 'USER_AGENT', 'ROBOTSTXT_OBEY',
    'CONCURRENT_REQUESTS', 'CONCURRENT_REQUESTS_PER_DOMAIN',
    'DOWNLOAD_DELAY', 'DOWNLOAD_DELAY_JITTER', 'RANDOMIZE_DOWNLOAD_DELAY',
    'DOWNLOAD_TIMEOUT', 'RETRY_ENABLED', 'RETRY_TIMES', 'COOKIES_ENABLED',
    'AUTOTHROTTLE_ENABLED', 'AUTOTHROTTLE_START_DELAY',
    'AUTOTHROTTLE_MAX_DELAY', 'AUTOTHROTTLE_TARGET_CONCURRENCY',
    'HTTPCACHE_ENABLED', 'DEPTH_LIMIT',
    'CLOSESPIDER_TIMEOUT', 'CLOSESPIDER_ITEMCOUNT', 'CLOSESPIDER_PAGECOUNT',
)

# Request headers worth recording: they describe the identity a crawl
# presented. A Cookie or an Authorization header describes an account, and
# there is no version of this file that should contain one.
HEADERS_RECORDED = ('accept', 'accept-language', 'upgrade-insecure-requests')

# Defence in depth for the two lists above. It has nothing to drop today; it
# exists so that adding a name to `ACQUISITION_SETTINGS` cannot quietly start
# writing a secret into every manifest.
SECRETISH = re.compile(r'key|token|secret|password|passwd|auth|credential|'
                       r'cookie|session', re.I)


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _git(*arguments):
    try:
        done = subprocess.run(('git',) + arguments, cwd=ROOT, timeout=10,
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _version(module_name, attribute='__version__'):
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return getattr(module, attribute, None)


@functools.lru_cache(maxsize=1)
def code_identity():
    """Which repository state produced this artefact.

    Cached: it shells out to git and reads the lock file, and every artefact
    of one process was produced by the same state. ``None`` is a real answer
    -- a checkout without git, or an export without ``uv.lock`` -- and is
    better than a value that implies a reproducibility this run cannot offer.
    """
    revision = _git('rev-parse', 'HEAD')
    status = _git('status', '--porcelain')
    lock = ROOT / 'uv.lock'
    from .extraction.pdp import SCHEMA_VERSION
    from .validation.contract import CONTRACT_VERSION
    return {
        'git_revision': revision,
        # None when git could not answer at all: "unknown" and "clean" are
        # not the same statement about a working tree.
        'git_dirty': None if status is None else bool(status),
        'lock_sha256': sha256_file(lock) if lock.is_file() else None,
        'python': platform.python_version(),
        'scrapy': _version('scrapy'),
        'extraction_schema_version': SCHEMA_VERSION,
        'validated_contract_version': CONTRACT_VERSION,
    }


def _scalar(value):
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


def _component_names(settings, name):
    """The component paths of a priority dictionary, without their order.

    Names, not priorities: what a later reader needs from this is whether a
    proxy or a monitor sat in the request path at all, and the names answer
    that without turning the manifest into a settings dump.
    """
    try:
        return sorted(str(key) for key in (settings.getdict(name) or {}))
    except Exception:
        return []


def acquisition_settings(settings):
    """The allowlisted description of how this crawl asked the marketplace."""
    recorded = {}
    for name in ACQUISITION_SETTINGS:
        if SECRETISH.search(name):
            continue
        value = settings.get(name)
        if value is not None:
            recorded[name] = _scalar(value)

    headers = settings.getdict('DEFAULT_REQUEST_HEADERS') or {}
    recorded['DEFAULT_REQUEST_HEADERS'] = {
        str(name): _scalar(value) for name, value in headers.items()
        if str(name).lower() in HEADERS_RECORDED}

    middlewares = _component_names(settings, 'DOWNLOADER_MIDDLEWARES')
    recorded['DOWNLOADER_MIDDLEWARES'] = middlewares
    recorded['EXTENSIONS'] = _component_names(settings, 'EXTENSIONS')
    # Add-ons configure the crawler before its middlewares exist. The one this
    # project ships decides where the public suffix list came from -- which is
    # whether the process contacted anything besides the marketplace -- so a
    # manifest without it in this list is a crawl that may have.
    recorded['ADDONS'] = _component_names(settings, 'ADDONS')
    # Stated rather than left to be inferred from a class path: whether the
    # requests went through a third party is the first thing that decides
    # what a challenge count or an IP-dependent price means.
    recorded['proxy_middleware'] = any(
        'proxy' in name.lower() for name in middlewares)
    return recorded


def write_json_atomically(path, payload):
    """Write JSON so a reader never sees a half-written file.

    A manifest is read by whoever is diagnosing the crawl that was writing it,
    which is exactly the moment a truncated file is most likely and least
    welcome. ``os.replace`` is atomic within a filesystem, so the previous
    manifest stands until the new one is complete.
    """
    path = pathlib.Path(path)
    temporary = path.with_name(path.name + '.tmp')
    text = json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + '\n'
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)
    return path
