"""A study: one written question, its evidence, its decisions and its report.

This package is the thin entry point a research agent uses, and it adds no
rule of its own. Acquisition belongs to the spider, provenance to
:mod:`amazon_scraper.run`, trust to :mod:`amazon_scraper.validation`, and what
"better" means to a category. What was missing until T2 was the envelope: the
question, the constraints somebody chose, every candidate that was considered,
and the reason each one is or is not in the answer -- persisted together, so
that the study outlives the terminal it was run in::

    uv run --offline --locked python -m amazon_scraper.study check  BRIEF
    uv run --offline --locked python -m amazon_scraper.study run    BRIEF
    uv run --offline --locked python -m amazon_scraper.study verify BUNDLE

``run`` reads feeds that are already on disk and touches no network. ``verify``
re-derives every decision from the same bytes and reports what moved -- which
is the only way to tell a study that still holds from one whose inputs, code
or brief have changed underneath it.

Three properties are worth stating because each replaces something that used
to be nowhere:

**A constraint is not a category default.** The report says, for every
decision it rests on, whether this study stated it or the category supplied
it. Tyre mounting paste ranks the smallest pack first because one reader was
fitting one scooter tyre, and that is now indistinguishable from a fact about
the product class. This is where that distinction survives.

**Every considered candidate is recorded, with its reason.** Not the first
twenty rows and ten exclusions a terminal shows.

**A refusal is a result.** The stopping criteria -- how many candidates are
enough, how far apart two of them have to be -- are declared in the brief
before the data is seen, so "there is not enough here to choose" is a
criterion that was met rather than a judgement improvised at the end.
"""

from .analysis import (INSUFFICIENT_EVIDENCE, NO_DECISIVE_WINNER,
                       RECOMMENDATION, StudyError, analyse)
from .brief import BRIEF_VERSION, Brief, BriefError, load, parse
from .bundle import (DEFAULT_STUDY_ROOT, STUDY_MANIFEST_VERSION, BundleError,
                     load_manifest, run, study_id, verify)

__all__ = ['BRIEF_VERSION', 'Brief', 'BriefError', 'BundleError',
           'DEFAULT_STUDY_ROOT', 'INSUFFICIENT_EVIDENCE',
           'NO_DECISIVE_WINNER', 'RECOMMENDATION', 'STUDY_MANIFEST_VERSION',
           'StudyError', 'analyse', 'load', 'load_manifest', 'parse', 'run',
           'study_id', 'verify']
