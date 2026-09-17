"""Built-in category analyzers.

Adding a category means adding one module here. It costs no change to the
crawler, the extractor or the validation layer -- which is the claim R2 was
built to test, and tyre mounting paste is the test: a non-food, classified
from its title rather than its breadcrumbs, sold in units dry pasta never
uses, and ranked on an axis dry pasta would consider backwards.

The third, basmati rice, tests something the first two did not: a category
whose decisive evidence is partly *not on the page at all*. It reads buyer
reviews as a separate evidence class, and it carries a small table of
published laboratory results, because "what is known about this product from
outside Amazon" is category knowledge and has nowhere else to live.

The fourth, school backpacks, is the first non-consumable and the first
written during an intake conversation. Its ranking axis is the bag's own
weight, which the generic layer already read as a pack quantity; what the
category had to add was a positional title classifier and four vendor
statements, and what the generic layer had to learn was that Amazon.de appends
an item's weight to its dimensions row and that A+ copy may confirm one.
"""

from . import basmati_rice, dry_pasta, mounting_paste, school_backpack  # noqa: F401  (registration side effect)
from ..category import get, known, REGISTRY

__all__ = ['REGISTRY', 'basmati_rice', 'dry_pasta', 'get', 'known',
           'mounting_paste', 'school_backpack']
