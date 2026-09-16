"""The brief: what was asked, under which constraints, with which defaults.

Before T2 the brief was a note somebody wrote under ``reports/`` if they
remembered to, and the constraints that actually decided the answer were
typed on a command line and then lost. The two failures that cost this
repository real work are both failures of *that*, not of the analysis:

* **A user's constraint became a fact about a product class.** Tyre mounting
  paste ranks the smallest pack first because one reader was fitting one
  scooter tyre. It is now in the category module, where no later reader can
  tell a constraint from a property of the shelf. A brief is the place that
  distinction survives: :mod:`amazon_scraper.study.analysis` records, for
  every constraint, whether the study stated it or fell back to the
  category's default.
* **A requirement moved mid-study and nothing recorded it.** An unrecorded
  requirement change is indistinguishable from a result. A brief has an id
  and a digest, and the study bundle names both.

The brief is **data, and only data**. It names a category by its registry
key, never by an import path; it carries no expression, no command and no
callable; and nothing in it is imported, evaluated or interpolated into a
shell. A brief naming ``amazon_scraper.analysis.categories.dry_pasta`` as its
category is refused with the list of keys that exist, which is the same
refusal a typo gets. That is deliberate: a brief may be written by an agent
reading an untrusted page, and the only power it has is to select among
things the repository already reviewed.

TOML and JSON are both read, by file extension. TOML is what the committed
examples use, because ``*.json`` is gitignored at the repository root and a
brief that cannot be committed is a brief that will be lost.
"""

import datetime as _dt
import json
import pathlib
import re
import tomllib
from dataclasses import dataclass, field

from ..analysis.category import get, known
from ..provenance import sha256_text

#: The brief shape this build reads. A brief declaring anything else is
#: refused rather than read partially: the fields a newer version adds are
#: exactly the constraints an older reader would silently ignore.
BRIEF_VERSION = 1

#: The id is used as a directory name and as the stem of the study id, so it
#: is a slug and nothing else -- not a path, not a shell word.
ID_RE = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')

TOP_LEVEL = {
    'brief_version', 'id', 'question', 'use_case', 'category', 'marketplace',
    'delivery_region', 'inputs', 'constraints', 'freshness', 'assumptions',
    'questions', 'sources', 'limits', 'unacceptable',
}
REQUIRED = ('brief_version', 'id', 'question', 'category', 'marketplace',
            'inputs')

CONSTRAINT_KEYS = {'axis', 'unit', 'require_claims', 'max_axis_value',
                   'shortlist', 'minimum_candidates', 'decisive_margin',
                   'cost_basis'}
FRESHNESS_KEYS = {'as_of', 'price_max_age_days', 'note'}
ASSUMPTION_KEYS = {'statement', 'default', 'if_wrong'}
QUESTION_KEYS = {'question', 'answer', 'default_used', 'blocking'}
SOURCE_KEYS = {'url', 'title', 'publisher', 'published', 'accessed', 'why'}


class BriefError(ValueError):
    """The brief cannot be used as written, and the message says what to fix.

    Raised rather than returned because every caller's next step is the same:
    stop, and tell the operator which line to change. A brief that is wrong
    in a way the tooling can see must never become a study that is wrong in a
    way only a reader can see.
    """


def _fail(source, message):
    raise BriefError(f'{source}: {message}' if source else message)


def _table(source, data, name, allowed):
    """One sub-table, checked for keys nobody will read."""
    value = data.get(name) or {}
    if not isinstance(value, dict):
        _fail(source, f'[{name}] must be a table')
    unknown = sorted(set(value) - allowed)
    if unknown:
        _fail(source, f'[{name}] has no key {", ".join(unknown)}. '
                      f'Known: {", ".join(sorted(allowed))}')
    return value


def _number(source, table, name, value, *, minimum=None, integer=False):
    if value is None:
        return None
    # ``bool`` is an ``int`` in Python and never what a constraint meant.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or \
            (integer and not isinstance(value, int)):
        _fail(source, f'{table}.{name} must be a '
                      f'{"whole number" if integer else "number"}, '
                      f'not {value!r}')
    if minimum is not None and value < minimum:
        _fail(source, f'{table}.{name} must be at least {minimum}, not {value}')
    return value


def _entries(source, data, name, allowed, required):
    """A list of small tables -- assumptions, questions, sources."""
    rows = data.get(name) or []
    if not isinstance(rows, list):
        _fail(source, f'[[{name}]] must be a list of tables')
    out = []
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            _fail(source, f'{name}[{position}] must be a table')
        unknown = sorted(set(row) - allowed)
        if unknown:
            _fail(source, f'{name}[{position}] has no key '
                          f'{", ".join(unknown)}. '
                          f'Known: {", ".join(sorted(allowed))}')
        for key in required:
            if not row.get(key):
                _fail(source, f'{name}[{position}] needs {key}')
        out.append({key: row[key] for key in sorted(row)})
    return out


def _strings(source, data, name):
    rows = data.get(name) or []
    if not isinstance(rows, list) or any(not isinstance(row, str)
                                         for row in rows):
        _fail(source, f'{name} must be a list of strings')
    return list(rows)


@dataclass(frozen=True)
class Brief:
    """One research question, written down before anything was collected."""

    id: str
    question: str
    category: str
    marketplace: str
    inputs: tuple
    #: ``inputs`` resolved against the brief's own directory, so that moving
    #: the brief and its feeds together keeps working and an absolute path
    #: never leaks into the committed file.
    resolved_inputs: tuple
    use_case: str = ''
    delivery_region: str = ''
    axis: str = ''
    unit: str = ''
    cost_basis: str = ''
    require_claims: tuple = ()
    max_axis_value: float = None
    shortlist: int = 3
    minimum_candidates: int = 1
    decisive_margin: float = None
    as_of: str = ''
    price_max_age_days: int = None
    freshness_note: str = ''
    assumptions: tuple = ()
    questions: tuple = ()
    sources: tuple = ()
    limits: tuple = ()
    unacceptable: tuple = ()
    #: Where it was read from and the digest of those exact bytes. The digest
    #: is what a later reader checks a brief against; the path is a
    #: convenience and may be gone by then.
    source_path: str = ''
    source_format: str = ''
    source_sha256: str = ''
    brief_version: int = BRIEF_VERSION

    @property
    def source_name(self):
        return pathlib.Path(self.source_path).name if self.source_path else ''

    def as_dict(self):
        """The normalised brief, which is what the bundle persists.

        Normalised rather than verbatim: the defaults a study ran under are
        part of what it decided, and a bundle that stored only what the
        operator typed would not say which of them applied.
        """
        return {
            'brief_version': self.brief_version,
            'id': self.id, 'question': self.question,
            'use_case': self.use_case, 'category': self.category,
            'marketplace': self.marketplace,
            'delivery_region': self.delivery_region,
            'inputs': list(self.inputs),
            'constraints': {
                'axis': self.axis, 'unit': self.unit,
                'cost_basis': self.cost_basis,
                'require_claims': list(self.require_claims),
                'max_axis_value': self.max_axis_value,
                'shortlist': self.shortlist,
                'minimum_candidates': self.minimum_candidates,
                'decisive_margin': self.decisive_margin,
            },
            'freshness': {'as_of': self.as_of,
                          'price_max_age_days': self.price_max_age_days,
                          'note': self.freshness_note},
            'assumptions': [dict(row) for row in self.assumptions],
            'questions': [dict(row) for row in self.questions],
            'sources': [dict(row) for row in self.sources],
            'limits': list(self.limits),
            'unacceptable': list(self.unacceptable),
            # The file's name, not the path somebody happened to invoke it
            # by: an absolute path is a fact about one machine, and a bundle
            # that carries one is no longer byte-identical to the same study
            # computed anywhere else. The full path is in the manifest,
            # which is where the machine-local record belongs.
            'source': {'path': self.source_name,
                       'format': self.source_format,
                       'sha256': self.source_sha256},
        }


def parse(text, source='', fmt='toml', directory='.'):
    """A validated :class:`Brief` from the text of one, or :class:`BriefError`.

    ``directory`` is what relative ``inputs`` resolve against -- the brief's
    own directory, not the working directory, so that a brief and the feeds
    it names travel together.
    """
    if fmt == 'toml':
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            _fail(source, f'not readable as TOML: {exc}')
    elif fmt == 'json':
        try:
            data = json.loads(text)
        except ValueError as exc:
            _fail(source, f'not readable as JSON: {exc}')
    else:
        _fail(source, f'{fmt}: a brief is .toml or .json')
    if not isinstance(data, dict):
        _fail(source, 'a brief is a table of fields, not a list or a scalar')

    unknown = sorted(set(data) - TOP_LEVEL)
    if unknown:
        _fail(source, f'has no field {", ".join(unknown)}. '
                      f'Known: {", ".join(sorted(TOP_LEVEL))}')
    missing = [key for key in REQUIRED if not data.get(key)]
    if missing:
        _fail(source, f'needs {", ".join(missing)}')

    version = data['brief_version']
    if version != BRIEF_VERSION:
        _fail(source, f'brief_version {version!r} is not supported; this '
                      f'build reads version {BRIEF_VERSION}')

    identifier = data['id']
    if not isinstance(identifier, str) or not ID_RE.fullmatch(identifier):
        _fail(source, f'id {identifier!r} must be a slug of lower-case '
                      f'letters, digits and hyphens: it names a directory')

    try:
        category = get(data['category'])
    except KeyError:
        _fail(source, f'{data["category"]!r}: unknown category. '
                      f'Known: {", ".join(known())}. A category is named by '
                      f'its key, never by an import path')

    for name in ('question', 'use_case', 'marketplace', 'delivery_region'):
        if name in data and not isinstance(data[name], str):
            _fail(source, f'{name} must be text')

    inputs = data['inputs']
    if not isinstance(inputs, list) or not inputs or \
            any(not isinstance(item, str) or not item.strip()
                for item in inputs):
        _fail(source, 'inputs must be a non-empty list of feed paths')
    base = pathlib.Path(directory)
    resolved = []
    for item in inputs:
        path = pathlib.Path(item)
        path = path if path.is_absolute() else base / path
        if not path.is_file():
            _fail(source, f'input {item!r} is not a readable file '
                          f'(looked in {base}). Feed paths are relative to '
                          f'the brief, not to the working directory')
        resolved.append(str(path))

    constraints = _table(source, data, 'constraints', CONSTRAINT_KEYS)
    axis = constraints.get('axis') or ''
    if axis and category.axis(axis) is None:
        _fail(source, f'constraints.axis {axis!r} is not an axis of '
                      f'{category.label}. Known: '
                      f'{", ".join(category.axis_keys)}')
    require = constraints.get('require_claims') or []
    if not isinstance(require, list):
        _fail(source, 'constraints.require_claims must be a list')
    for key in require:
        if key not in category.claim_keys:
            _fail(source, f'constraints.require_claims names {key!r}, which '
                          f'is not a claim of {category.label}. Known: '
                          f'{", ".join(category.claim_keys)}')

    freshness = _table(source, data, 'freshness', FRESHNESS_KEYS)
    as_of = freshness.get('as_of') or ''
    if as_of:
        if isinstance(as_of, _dt.date):
            as_of = as_of.isoformat()
        try:
            _dt.date.fromisoformat(str(as_of))
        except ValueError:
            _fail(source, f'freshness.as_of {as_of!r} is not an ISO date')
    max_age = _number(source, 'freshness', 'price_max_age_days',
                      freshness.get('price_max_age_days'), minimum=0,
                      integer=True)
    if max_age is not None and not as_of:
        _fail(source, 'freshness.price_max_age_days needs freshness.as_of: '
                      'an age measured against "today" would make the same '
                      'study decide differently tomorrow')

    return Brief(
        id=identifier, question=data['question'], category=category.key,
        marketplace=data['marketplace'], inputs=tuple(inputs),
        resolved_inputs=tuple(resolved),
        use_case=data.get('use_case', ''),
        delivery_region=data.get('delivery_region', ''),
        axis=axis, unit=constraints.get('unit') or '',
        cost_basis=constraints.get('cost_basis') or '',
        require_claims=tuple(require),
        max_axis_value=_number(source, 'constraints', 'max_axis_value',
                               constraints.get('max_axis_value'), minimum=0),
        shortlist=_number(source, 'constraints', 'shortlist',
                          constraints.get('shortlist', 3), minimum=1,
                          integer=True),
        minimum_candidates=_number(source, 'constraints',
                                   'minimum_candidates',
                                   constraints.get('minimum_candidates', 1),
                                   minimum=1, integer=True),
        decisive_margin=_number(source, 'constraints', 'decisive_margin',
                                constraints.get('decisive_margin'),
                                minimum=0),
        as_of=str(as_of), price_max_age_days=max_age,
        freshness_note=freshness.get('note') or '',
        assumptions=tuple(_entries(source, data, 'assumptions',
                                   ASSUMPTION_KEYS, ('statement',))),
        questions=tuple(_entries(source, data, 'questions',
                                 QUESTION_KEYS, ('question',))),
        sources=tuple(_entries(source, data, 'sources', SOURCE_KEYS,
                               ('url', 'why'))),
        limits=tuple(_strings(source, data, 'limits')),
        unacceptable=tuple(_strings(source, data, 'unacceptable')),
        source_path=source, source_format=fmt, source_sha256=sha256_text(text),
        brief_version=version,
    )


def load(path):
    """Read and validate the brief at ``path``."""
    path = pathlib.Path(path)
    fmt = {'.toml': 'toml', '.json': 'json'}.get(path.suffix.lower())
    if fmt is None:
        _fail(str(path), f'{path.suffix or "no extension"}: a brief is .toml '
                         f'or .json')
    if not path.is_file():
        _fail(str(path), 'no such brief')
    return parse(path.read_text(encoding='utf-8'), source=str(path), fmt=fmt,
                 directory=path.parent)


def rehydrate(data, resolved_inputs):
    """A :class:`Brief` from the normalised copy a bundle persisted.

    Not a second parser: this is data this repository wrote itself, and the
    bundle's own digest is what says it has not been edited. What is still
    checked is the pair that decides whether it can be read at all -- the
    version, and whether the category it names still exists. A bundle whose
    category was renamed out of the repository is not recomputable, and
    saying so is more useful than a partial answer.
    """
    version = data.get('brief_version')
    if version != BRIEF_VERSION:
        _fail('brief', f'brief_version {version!r} is not supported; this '
                       f'build reads version {BRIEF_VERSION}')
    try:
        get(data['category'])
    except KeyError:
        _fail('brief', f'{data["category"]!r}: this build has no such '
                       f'category. Known: {", ".join(known())}')
    constraints = data.get('constraints') or {}
    freshness = data.get('freshness') or {}
    source = data.get('source') or {}
    return Brief(
        id=data['id'], question=data['question'], category=data['category'],
        marketplace=data['marketplace'], inputs=tuple(data['inputs']),
        resolved_inputs=tuple(resolved_inputs),
        use_case=data.get('use_case', ''),
        delivery_region=data.get('delivery_region', ''),
        axis=constraints.get('axis') or '',
        unit=constraints.get('unit') or '',
        cost_basis=constraints.get('cost_basis') or '',
        require_claims=tuple(constraints.get('require_claims') or ()),
        max_axis_value=constraints.get('max_axis_value'),
        shortlist=constraints.get('shortlist', 3),
        minimum_candidates=constraints.get('minimum_candidates', 1),
        decisive_margin=constraints.get('decisive_margin'),
        as_of=freshness.get('as_of') or '',
        price_max_age_days=freshness.get('price_max_age_days'),
        freshness_note=freshness.get('note') or '',
        assumptions=tuple(data.get('assumptions') or ()),
        questions=tuple(data.get('questions') or ()),
        sources=tuple(data.get('sources') or ()),
        limits=tuple(data.get('limits') or ()),
        unacceptable=tuple(data.get('unacceptable') or ()),
        source_path=source.get('path', ''),
        source_format=source.get('format', ''),
        source_sha256=source.get('sha256', ''),
        brief_version=version,
    )
