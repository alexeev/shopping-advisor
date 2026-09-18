"""The capability index: what the repository can do, and what each capability has earned.

R16. Before this module the registry could answer one question about a
capability -- is a category with this key registered -- and the intake step
that has to decide whether an existing capability fits a new request read the
rest from module docstrings and roadmap prose. This is the small discoverable
index the roadmap asked for, and it is built the way the controls catalogue
is: from the live registry on every call, with nothing to keep in step by
hand. Each row is the category's own :class:`~..analysis.category.Lifecycle`
declaration plus what can be derived from the code and the committed
evidence beside it::

    uv run --offline --locked python -m shopping_advisor.study capabilities
    uv run --offline --locked python -m shopping_advisor.study capabilities --category school_backpack
    uv run --offline --locked python -m shopping_advisor.study capabilities --marketplace www.amazon.com

What a row answers, for the inspection step of an intake: what the
capability is for and what it declines, with the case records that prove
each decline; which marketplaces it was measured on; what it has earned -- a
task experiment, a maintained capability, a shared foundation or a retired
one -- and the last decision, its date and the responsible role; which
committed cases, tests, briefs and studies stand behind it; which roadmap
entries record its history; and what nothing in the repository establishes.

What it does not do: it is inspection, not authorisation, and not a judgement
of fit. It compares marketplace hosts when asked to; whether a product class
matches a buyer's question is read from ``accepts``, ``declines`` and
``not_established``, and stays a judgement the agent makes and the plan
records. Nothing here enters study identity or report bytes, and nothing here
loads code from anywhere: the index describes registered modules, it does not
find or import them. The maintenance gate pins each row's ``state``,
``decision`` and ``method_version`` in its baseline, so a promotion is a
reviewable diff and never a side effect (``maintenance.check_capabilities``).

Categories are the one capability kind the registry can enumerate today, and
the one kind that has been built on demand. Sources, extraction techniques,
evidence classes and comparison methods enter the index with the first
task-born one, under R15, with the row shape decided against that case rather
than in advance of it.
"""

import datetime as _dt
import pathlib
import re

from ..analysis import categories as _categories  # noqa: F401  (registration side effect)
from ..analysis.category import (DECISIONS, STATES, Applicability, Decline,
                                 Lifecycle, get, known)
from ..extraction.marketplaces import domain_key
from . import brief as _brief

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

#: The capability kinds the index enumerates. One, today, on purpose.
KINDS = ('category',)

LIMITS = (
    'The index describes what the repository has built, measured and decided '
    'to keep. It does not establish that a category suits a new question, '
    'that a listing belongs to it, or that any value on a card is true.',
    'Categories are the one capability kind the registry enumerates. Sources, '
    'extraction techniques, evidence classes and comparison methods enter the '
    'index with the first task-born one (R15), not before.',
    'A marketplace check compares hosts. Product-class fit is read from '
    'accepts, declines and not_established, and remains a judgement recorded '
    'in the intake plan.',
    'Maturity is not trust: a value\'s status comes from validation and says '
    'nothing about how many studies the category has served.',
)

_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_ANCHOR = re.compile(r'^[a-z0-9][a-z0-9-]*$')


class CapabilityError(ValueError):
    """The index was asked about a capability it does not have."""


def index(category_key=None, marketplace='', examples=(), root=ROOT):
    """JSON-ready rows for every registered capability, or for one.

    ``examples`` are the maintenance gate's committed study examples; the
    ones whose brief names a category are listed on its row, with the study
    id and outcome the gate replays. ``marketplace`` adds a host comparison
    to every row.
    """
    keys = [category_key] if category_key else known()
    rows = []
    for key in keys:
        try:
            category = get(key)
        except KeyError as exc:
            raise CapabilityError(str(exc)) from exc
        rows.append(row(category, marketplace=marketplace, examples=examples,
                        root=root))
    return {'kinds': list(KINDS), 'states': list(STATES),
            'decisions': list(DECISIONS), 'capabilities': rows,
            'limits': list(LIMITS)}


def row(category, marketplace='', examples=(), root=ROOT):
    """One capability, as the index publishes it."""
    root = pathlib.Path(root)
    lifecycle = category.lifecycle
    applicability = lifecycle.applicability
    data = {
        'kind': 'category',
        'key': category.key,
        'label': category.label,
        'module': getattr(category.evaluate, '__module__', ''),
        'state': lifecycle.state,
        'decision': lifecycle.decision,
        'decided': lifecycle.decided,
        'maintainer': lifecycle.maintainer,
        'method_version': lifecycle.method_version,
        'default_axis': category.default_axis,
        'axes': list(category.axis_keys),
        'claims': list(category.claim_keys),
        'applicability': {
            'marketplaces': list(applicability.marketplaces),
            'accepts': applicability.accepts,
            'declines': [{'label': decline.label, 'asins': list(decline.asins)}
                         for decline in applicability.declines],
            'not_established': list(applicability.not_established)},
        'evidence': [{'path': path, 'present': (root / path).exists()}
                     for path in lifecycle.evidence],
        'studies': studies(category.key, examples, root),
        'milestones': list(lifecycle.milestones),
        'reviewed': lifecycle.reviewed,
        'review': lifecycle.review,
        'controls': f'study controls --category {category.key}',
    }
    if marketplace:
        fits = applies(lifecycle, marketplace)
        data['marketplace'] = {
            'host': marketplace, 'applies': fits,
            'reason': ('built and measured on this marketplace' if fits else
                       'built and measured on ' + ', '.join(applicability.marketplaces)
                       + ' only; nothing here was validated on this host')}
    return data


def applies(lifecycle, marketplace):
    """Whether the capability was measured on this marketplace host.

    Hosts are compared through the same normalisation listing identity
    uses, so ``amazon.de`` and ``www.amazon.de`` are one marketplace. This is
    the only applicability question the index answers by itself.
    """
    wanted = domain_key(marketplace)
    return bool(wanted) and wanted in {
        domain_key(host) for host in lifecycle.applicability.marketplaces}


def studies(category_key, examples, root=ROOT):
    """The committed, gate-replayed studies whose brief names this category."""
    root = pathlib.Path(root)
    found = []
    for example in examples or ():
        path = example.get('brief')
        if not path or not (root / path).is_file():
            continue
        try:
            named = _brief.load(root / path).category
        except _brief.BriefError:
            continue
        if named != category_key:
            continue
        expect = example.get('expect') or {}
        found.append({'name': example.get('name', ''), 'brief': path,
                      'study_id': expect.get('study_id', ''),
                      'outcome': expect.get('outcome', ''),
                      'stop': expect.get('stop', '')})
    return found


def problems(category, root=ROOT):
    """What is wrong with a capability's declaration, as ``(field, message)``.

    The gate turns each one into a finding; the tests assert there are none.
    Roadmap anchors are checked for shape here and for existence by the gate,
    which owns the documentation index.
    """
    root = pathlib.Path(root)
    lifecycle = category.lifecycle
    if not isinstance(lifecycle, Lifecycle):
        return [('lifecycle', 'no Lifecycle is declared')]
    found = []
    if lifecycle.state not in STATES:
        found.append(('state', f'{lifecycle.state!r} is not one of '
                               f'{", ".join(STATES)}'))
    if lifecycle.decision not in DECISIONS:
        found.append(('decision', f'{lifecycle.decision!r} is not one of '
                                  f'{", ".join(DECISIONS)}'))
    for field in ('decided', 'reviewed'):
        if not _iso_date(getattr(lifecycle, field)):
            found.append((field, f'{getattr(lifecycle, field)!r} is not an '
                                 f'ISO date (YYYY-MM-DD)'))
    if not _text(lifecycle.maintainer):
        found.append(('maintainer', 'names no responsible role'))
    if type(lifecycle.method_version) is not int or lifecycle.method_version < 1:
        found.append(('method_version', f'{lifecycle.method_version!r} is not '
                                        f'a positive integer'))
    applicability = lifecycle.applicability
    if not isinstance(applicability, Applicability):
        found.append(('applicability', 'is not an Applicability'))
    else:
        hosts = applicability.marketplaces
        if not hosts or not all(_text(host) for host in hosts):
            found.append(('applicability.marketplaces',
                          'names no marketplace host'))
        if not _text(applicability.accepts):
            found.append(('applicability.accepts',
                          'says nothing about what the classifier accepts'))
        for decline in applicability.declines:
            if not isinstance(decline, Decline) or not _text(decline.label):
                found.append(('applicability.declines',
                              f'{decline!r} is not a labelled Decline'))
            elif not all(_text(asin) for asin in decline.asins):
                found.append(('applicability.declines',
                              f'{decline.label}: an ASIN is not text'))
        if not all(_text(item) for item in applicability.not_established):
            found.append(('applicability.not_established',
                          'carries an empty entry'))
    if not lifecycle.evidence:
        found.append(('evidence', 'names no committed evidence'))
    for path in lifecycle.evidence:
        if not _text(path):
            found.append(('evidence', f'{path!r} is not a path'))
        elif pathlib.PurePosixPath(path).is_absolute() or \
                pathlib.PureWindowsPath(path).is_absolute() or \
                path.startswith(('/', '\\')):
            found.append(('evidence', f'{path}: an absolute path never enters '
                                      f'a committed declaration'))
        elif not (root / path).exists():
            found.append(('evidence', f'{path}: not in the tree'))
    if not lifecycle.milestones:
        found.append(('milestones', 'names no roadmap record'))
    for anchor in lifecycle.milestones:
        if not (_text(anchor) and _ANCHOR.match(anchor)):
            found.append(('milestones', f'{anchor!r} is not a heading anchor'))
    if not (_text(lifecycle.review) and _ANCHOR.match(lifecycle.review)):
        found.append(('review', f'{lifecycle.review!r} is not a heading anchor'))
    return found


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _iso_date(value):
    if not (isinstance(value, str) and _DATE.match(value)):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True
