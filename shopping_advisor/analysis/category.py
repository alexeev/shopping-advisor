"""What a category analyzer is, and the little it has to declare.

A category is the only place in the platform that is allowed to know what the
product is. It declares four things and implements one:

``profile``
    The plausibility data the generic layer needs -- nutrition bands, a price
    band -- and nothing procedural. See
    :class:`~shopping_advisor.validation.CategoryProfile`.

``axes``
    What it is worth comparing two of these products on, in order, and which
    direction is better. This is a *product* decision and it is not the same
    for every category: cheaper per kilogram is the point of dry pasta, and
    actively misleading for tyre mounting paste, where a five-kilogram tub is
    the worst buy on the page for somebody with one scooter tyre to fit.

``claims``
    The statements worth hunting for in the vendor's own text, each with the
    reason it matters. A claim may be *adverse* -- finding it is bad news.

``evaluate``
    ``record -> card``. Classification, the axes filled in, and the claims
    searched for. Everything it needs about trust it gets from
    :func:`shopping_advisor.validation.validate`; it must not re-derive any of
    it, and there is a test that asserts exactly that.

Since R16 a category also declares a fifth thing, and cannot register without
it:

``lifecycle``
    What the capability has *earned* -- a :class:`Lifecycle`: its maturity
    state, the last keep/promote/reject/retire decision and who is responsible
    for it, where it applies and what it declines, the committed evidence and
    the roadmap entries behind it, and when it was last reviewed. This is data
    beside the code that is the capability, so that the capability index
    (``study capabilities``) cannot drift from the registry the way a separate
    list would, and the maintenance gate pins the state: moving a category
    from one state to another is a recorded decision, never a side effect.
    Maturity is not trust. A value's status is decided by validation and says
    nothing about how many studies the category has served; the lifecycle
    says how much reuse the category has demonstrated and nothing about any
    value.
"""

from dataclasses import dataclass

REGISTRY = {}

# ---------------------------------------------------------------------------
# Lifecycle: R16's record of what a capability has earned
# ---------------------------------------------------------------------------

#: A named gap, a bounded change and its tests, one study behind it. Usable
#: within its validated scope; one success remains provisional. Retained for
#: audit, withdrawn, or nominated for reuse at study close.
EXPERIMENT = 'experiment'
#: Demonstrated value in a distinct subsequent use, applicability and
#: counterexamples on record, regression protection, a recorded review and a
#: maintenance responsibility.
MAINTAINED = 'maintained'
#: Several real consumers demonstrably share the same semantics. Not a state
#: a category reaches on its own; it is where a shared abstraction lands after
#: local duplication was compared with the coupling and measured.
FOUNDATION = 'foundation'
#: Superseded or withdrawn, with the reason, the replacement and the replay
#: implications recorded. Historical artifacts and method identity stay.
RETIRED = 'retired'
#: In the order a capability normally moves through them.
STATES = (EXPERIMENT, MAINTAINED, FOUNDATION, RETIRED)

#: The decision a capability last received. ``retained`` keeps its state,
#: ``promoted`` moved it up, ``rejected`` withdrew an experiment and
#: ``retired`` closed a maintained one.
DECISIONS = ('retained', 'promoted', 'rejected', 'retired')


@dataclass(frozen=True)
class Decline:
    """A product class the classifier files as ``other``, and the proof.

    The ASINs are committed case records the category's own test asserts on;
    an applicability claim with no record behind it is a hope, and the
    capability test checks that every one of these still classifies as
    ``other``.
    """

    label: str
    asins: tuple = ()


@dataclass(frozen=True)
class Applicability:
    """Where a capability was built and measured, and what it is not for."""

    #: Marketplace hosts the classifier, claims and axes were built and
    #: measured against, as the records name them: ``'www.amazon.de'``.
    marketplaces: tuple
    #: What the classifier accepts, in one sentence.
    accepts: str
    #: Product classes it files as ``other``, each proven by case records.
    declines: tuple = ()
    #: What no evidence in the repository establishes. Read before reusing
    #: the capability for a question its studies never asked.
    not_established: tuple = ()


@dataclass(frozen=True)
class Lifecycle:
    """What a capability has earned, declared beside the code that is it."""

    #: One of :data:`STATES`.
    state: str
    #: One of :data:`DECISIONS`: the last keep/promote/reject/retire decision.
    decision: str
    #: ISO date of that decision.
    decided: str
    #: The role responsible for maintaining it -- a role, never a person.
    maintainer: str
    applicability: Applicability
    #: Repository-relative paths: the case feeds, the test module, committed
    #: briefs and plans, dated investigations. Every one must exist.
    evidence: tuple
    #: ROADMAP.md heading anchors recording the capability's history.
    milestones: tuple
    #: ISO date of the last architectural review that looked at it.
    reviewed: str
    #: ROADMAP.md heading anchor of that review's record.
    review: str
    #: The category method's own version. It moves when a change moves a
    #: decision on the category's committed cases -- a classifier boundary,
    #: an axis direction, what a claim means -- and stays when a pattern
    #: merely reaches more phrasings of the same statement. The bundle does
    #: not record it yet; binding it into a study's manifest is R15's.
    method_version: int = 1


@dataclass(frozen=True)
class Axis:
    """One thing two products of this category can be compared on."""

    key: str
    label: str
    #: ``'lower'``, ``'higher'``, or ``''`` for an axis that can differ
    #: without one side being better -- raw material, for instance.
    better: str = ''
    #: Sentence fragment appended when this axis decides a comparison, e.g.
    #: "which for durum pasta tracks semolina quality".
    why: str = ''
    #: How to name the winner in a comparison: "A is 1.6x <comparative>".
    comparative: str = ''
    #: Renders the value for display. Defaults to "%g unit".
    render: object = None
    #: Smallest difference worth reporting. Below it the two are the same.
    tolerance: float = 0.0
    #: Shown on the card under the value, when there is something the number
    #: alone would mislead about.
    caveat: str = ''


@dataclass(frozen=True)
class Claim:
    """A statement to look for in the vendor's own words."""

    key: str
    label: str
    pattern: str
    #: Why a buyer should care. Printed on the card beside the quote.
    why: str = ''
    #: True when finding this counts against the product.
    adverse: bool = False
    #: Restrict the search to these record fields, when a claim is only
    #: meaningful in one of them.
    fields: tuple = None


@dataclass(frozen=True)
class Category:
    """A registered category analyzer."""

    key: str
    label: str
    profile: object
    axes: tuple
    claims: tuple
    evaluate: object
    #: Which axis ``rank`` uses when the user names none.
    default_axis: str = ''
    #: One or two sentences the reports open with, stating what this category
    #: can and cannot be judged on from an Amazon product page.
    blurb: str = ''
    #: ``card -> [line]``, for a section only this category has. Optional.
    render_extra: object = None
    #: The card keys this category adds beyond the shape :func:`card` returns.
    #: Declared rather than discovered because the JSON view has to serialise
    #: them, and until T2 it named two of them in ``report.py`` by hand -- so
    #: basmati's grain, cultivar, external test, review signals and score,
    #: which are the whole of what that category knows, were rendered on the
    #: text card and silently absent from the JSON one. A category that adds
    #: a key and does not list it here is not published.
    extras: tuple = ()
    #: What this capability has earned (R16). :func:`register` refuses a
    #: category that declares none; the gate checks what it declares.
    lifecycle: object = None

    def axis(self, key):
        for axis in self.axes:
            if axis.key == key:
                return axis
        return None

    @property
    def axis_keys(self):
        return tuple(axis.key for axis in self.axes)

    @property
    def claim_keys(self):
        return tuple(claim.key for claim in self.claims)

    def claim(self, key):
        for claim in self.claims:
            if claim.key == key:
                return claim
        return None


def register(category):
    if not isinstance(category.lifecycle, Lifecycle):
        raise TypeError(
            f'{category.key}: a category registers with its Lifecycle -- the '
            f'state it has earned, the decision behind it, where it applies '
            f'and the evidence -- and this one declares none. See R16.')
    REGISTRY[category.key] = category
    return category


def get(key):
    if key not in REGISTRY:
        raise KeyError(f'{key}: unknown category. Known: {", ".join(sorted(REGISTRY))}')
    return REGISTRY[key]


def known():
    return sorted(REGISTRY)


def card(record, validated, category, classification, axes, claims):
    """The shape every category's ``evaluate`` returns, and the report reads."""
    return {
        'category_key': category.key,
        'asin': validated.asin,
        # Carried on the card because grouping and ranking are
        # marketplace-scoped: an ASIN alone does not identify a listing, and
        # the card is what those layers are handed.
        'marketplace': validated.marketplace,
        'title': validated.title,
        'brand': validated.brand,
        'url': validated.url,
        'query': validated.query,
        'category': classification,
        'axes': axes,
        'claims': claims,
        'validated': validated,
        # Lifted out of the validated record because grouping and rendering
        # read them on every card, including ones this category rejected.
        'offer': validated.offer,
        'size_label': validated.size_label,
        'siblings': validated.siblings,
        'variation': validated.variation,
    }


def is_match(card):
    """True when the card's category accepted the record as one of its own."""
    return card['category'].value == card['category_key']
