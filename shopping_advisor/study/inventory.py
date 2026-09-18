"""The bundle's artifact inventory: every file a study may hold, and how it binds.

R13 stage 10. INTAKE §6 measured the gap this closes: the manifest digested
nine artifacts and the semantic review bound six of them, so an artifact added
to the bundle acquired an integrity digest and **no review binding** -- its
decision-relevant content could change while the report bytes, the study id
and the completed review all stayed fixed. Stages 5 to 9 then added four more
optional artifacts, each with its binding decided in CONTRACT prose and
nowhere a test could see it. This module is that decision as data.

Every artifact a bundle may contain has exactly one row in :data:`BINDINGS`,
and the row says how the study workflow binds it:

``semantic``
    Its digest enters the final semantic review's ``basis``. Change it and a
    completed final review is no longer this bundle's. The intake plan and
    the intake review are bound this way: final approval rests on the intake
    findings it was given (INTAKE §11), so replacing them supersedes it.
``report``
    The final review's ``report_sha256`` target -- the report itself.
``delivery``
    Bound per delivery event into the delivery review: the delivery record
    and the session snapshot. Neither enters the final review's basis, which
    is what keeps re-delivery of an unchanged analysis affordable (INTAKE §8):
    a new event costs a new delivery review, not a rewritten semantic one.
``review``
    A review record, or a file derived from one. It binds other artifacts and
    is never bound into itself; a digest cycle would make approval
    unfalsifiable.

:func:`bundle.artifact_digests` refuses a file this table does not name, and
``verify`` reports one. That is the test INTAKE §6 asked for -- a new artifact
cannot enter the bundle without a deliberate binding decision -- because the
only way in is a row here, and a row is a contract change reviewed like any
other. The manifest records each present artifact's binding beside its digest,
so a reader of the bundle sees the decision without opening the code.
"""

from . import adaptation, delivery, delivery_review, intake, intake_review, session

MANIFEST = 'manifest.json'
BRIEF = 'brief.json'
CANDIDATES = 'candidates.jsonl'
CARDS = 'cards.jsonl'
RANKING = 'ranking.json'
REPORT = 'report.md'
LEDGER = 'ledger.json'
CLAIM_INDEX = 'claim-index.json'
VALIDATION = 'validation.json'
REVIEW = 'semantic-review.json'

SEMANTIC = 'semantic'
REPORT_TARGET = 'report'
DELIVERY = 'delivery'
REVIEW_RECORD = 'review'
KINDS = (SEMANTIC, REPORT_TARGET, DELIVERY, REVIEW_RECORD)

#: Every artifact a bundle may hold. ``required`` ones are written by every
#: run; the others accompany a plan, a review, a delivery or a session. Order
#: is the order the manifest lists them in and the order a basis is built in.
BINDINGS = {
    BRIEF: {'required': True, 'binding': SEMANTIC},
    CANDIDATES: {'required': True, 'binding': SEMANTIC},
    CARDS: {'required': True, 'binding': SEMANTIC},
    RANKING: {'required': True, 'binding': SEMANTIC},
    REPORT: {'required': True, 'binding': REPORT_TARGET},
    LEDGER: {'required': True, 'binding': SEMANTIC},
    CLAIM_INDEX: {'required': True, 'binding': SEMANTIC},
    VALIDATION: {'required': True, 'binding': REVIEW_RECORD},
    REVIEW: {'required': True, 'binding': REVIEW_RECORD},
    intake.SNAPSHOT: {'required': False, 'binding': SEMANTIC},
    intake_review.SNAPSHOT: {'required': False, 'binding': SEMANTIC},
    delivery.RECORD: {'required': False, 'binding': DELIVERY},
    session.SNAPSHOT: {'required': False, 'binding': DELIVERY},
    delivery_review.RECORD: {'required': False, 'binding': REVIEW_RECORD},
    # R15: the adaptation record a study rests on. Semantic, because the
    # method that produced the decisions is part of what a final review
    # approves; a replaced record supersedes the review, and a build without
    # this row refuses the bundle as ``artifact_undeclared`` rather than
    # reading it as an ordinary study.
    adaptation.RECORD: {'required': False, 'binding': SEMANTIC},
}

#: The nine artifacts every bundle holds, in manifest order.
ARTIFACTS = tuple(name for name, row in BINDINGS.items() if row['required'])
#: The ones that accompany a plan, a review, a delivery or a session.
OPTIONAL = tuple(name for name, row in BINDINGS.items() if not row['required'])


def bound(kind):
    """The artifact names with this binding, in table order."""
    return tuple(name for name, row in BINDINGS.items() if row['binding'] == kind)


def present(directory, kind):
    """The artifacts with this binding that this bundle actually holds."""
    from pathlib import Path
    directory = Path(directory)
    return tuple(name for name in bound(kind) if (directory / name).is_file())
