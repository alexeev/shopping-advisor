"""School backpack: the fourth category, and the first that is not a consumable.

The use case is a parent buying a school backpack for a child moving from the
last primary year into secondary school, on Amazon.de. Four things decide
whether a listing is worth looking at, and only one of them is a number the
page states in a structured row:

1. **It has to be a school backpack**, not a primary-school satchel
   (Schulranzen with a rigid frame, sold in sets with a pencil case and a gym
   bag for the first day of school), not a trekking, hiking or laptop pack
   that happens to mention school, and not an adult's daypack. Amazon.de
   files all of these in the same two nodes and vendors stuff both
   "Schulrucksack" and "Schulranzen" into one title, so the title decides,
   read positionally the way tyre mounting paste is: the head noun comes
   first in a German title, and a disqualifying word *before* the school
   word names the thing the listing actually is.
2. **Weight.** A school bag is carried every day by a growing child, so the
   ranking axis is the bag's own weight, lighter first. The generic layer
   already reads it -- Artikelgewicht, or the weight Amazon.de appends to the
   dimensions row -- and reconciles it against the vendor's own text; this
   module takes that value and its status as they are and adds nothing to
   either. Measured on the 43 records of 2026-09-17 this was built against:
   3 bags had a usable weight before the dimensions row and the A+ copy were
   read, 10 after.
3. **What the vendor states about safety and fit.** Reflective elements,
   a manufacturer warranty, a height-adjustable back and a hip or chest
   strap are the four statements worth hunting for; the first two were
   named by the buyer this category was written for, the last two are the
   criteria the Stiftung Warentest and ÖKO-TEST satchel tests grade. Every
   one is a vendor's sentence quoted from the page, never a verified property.
4. **Whether it fits one particular child** is a question about that child,
   so the body-height range a vendor states is shown on the card and ranked
   on by nobody.
5. **What buyers said, as a threshold the buyer sets.** The second buyer of
   this category (2026-09-18) asked for at least four stars from at least
   fifty ratings. The average and the count are the validation layer's
   values, taken as they are; they exist here as axes so that a stated
   threshold can be executed through an `axis_bound`, and they rank nothing
   by default -- a rating measures satisfaction among the buyers who chose
   to rate, not durability.

Durability is not on the page. A warranty statement is the nearest thing to
a vendor commitment about it, and a review sample is a sample; no rule here
turns either into a failure rate.
"""

import re

from shopping_advisor.validation import (CategoryProfile, NOT_CLAIMED, TEXT,
                                       TRUSTED, UNVERIFIED, Evidence, Value,
                                       validate)

from .. import category as cat

KEY = 'school_backpack'

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

# The words that say a listing is sold for school. "Schulranzen" is here on
# purpose: on Amazon.de it names the node that holds Satch, Coocazoo and Deuter
# as well as the first-graders' satchels, and vendors write it into teenagers'
# titles for the search traffic. What separates the two classes is PRIMARY_RE.
SCHOOL_RE = re.compile(
    r'schul[\s-]?rucksack|schul[\s-]?ranzen|schul[\s-]?tasche|schulranze\b'
    r'|school[\s-]?(?:bag|backpack|rucksack)'
    r'|schul-?\s*(?:&|und|/)\s*\w*rucksack'       # "Schul- & Arbeitsrucksack"
    r'|rucksack\s+(?:f[üu]r\s+(?:die\s+)?)?schule\b'
    r'|f[üu]r\s+(?:die\s+)?schule\b', re.I)

# The primary-school satchel and its sets: a different product class with a
# rigid frame, a lid and a first-day-of-school market. Anywhere in the title.
PRIMARY_RE = re.compile(
    r'einschulung|schulanf[äa]nger|erstkl[äa]ssler|schult[üu]te'
    r'|\b1\.\s*klasse\b|\bklasse\s*1\b|\berste[nr]?\s+klasse'
    r'|grundschul\w*|vorschul\w*'
    r'|schulranzen[\s-]?set|ranzen[\s-]?set|schultaschen[\s-]?sets?'
    r'|\b\d+[\s-]?(?:tlg\.?|teilig)\b', re.I)

# Other backpack classes. Positional: a hit *before* the first school word
# heads the title and names what the listing is; after it, it is a feature
# ("... Schulrucksack mit Laptopfach") or a stuffed keyword.
OTHER_CLASS_RE = re.compile(
    r'trekking|wander(?:rucksack)?|touren|tages?rucksack|daypack'
    r'|laptop[\s-]?(?:rucksack|tasche)|notebook[\s-]?(?:rucksack|tasche)'
    r'|business|reise(?:rucksack|tasche)|wickel(?:rucksack|tasche)'
    r'|fahrrad|\bbike\b|sport(?:rucksack|tasche|beutel)|turnbeutel|\bgym\b'
    r'|kita|kindergarten|kinderwagen', re.I)

# An adult's backpack with a school word stuffed in after it. "Rucksack
# Herren, Schulrucksack Jungen Teenager, Laptop Rucksack" is a men's laptop
# pack; three of the 43 records read like this and none of them is a school
# backpack a ten-year-old would be sold in a shop.
WEARER_RE = re.compile(r'\bherren\b|\bdamen\b|erwachsene|\bfrauen\b|\bm[äa]nner\b',
                       re.I)

# Amazon's own node names. Only the school-bag node is allowed to speak for a
# title that names no school word; "Kinderrucksäcke" holds leisure daypacks.
SCHOOL_NODE = 'schulranzen'
PRIMARY_NODES = ('schultaschen-sets', 'schultaschen sets')


def classify(record):
    """Is this a school backpack? Decided on the title, with one node check."""
    title = record.get('title') or ''
    if not title:
        return Value.unknown('the listing has no title to classify')
    crumbs = [str(crumb).strip().lower() for crumb in record.get('breadcrumbs') or []]
    evidence = [Evidence('title', title[:160])]

    primary = PRIMARY_RE.search(title)
    if primary:
        return Value('other', TRUSTED, evidence=evidence,
                     notes=[f'a primary-school satchel or set, not a school '
                            f'backpack: the title says "{primary.group(0)}"'])
    if any(node in PRIMARY_NODES for node in crumbs):
        return Value('other', TRUSTED,
                     evidence=evidence + [Evidence('breadcrumbs', ' > '.join(crumbs))],
                     notes=['Amazon files it among the primary-school satchel '
                            'sets, and nothing in the title says otherwise'])

    head = SCHOOL_RE.search(title)
    if head:
        for pattern, why in ((OTHER_CLASS_RE, 'another class of backpack heads '
                                              'the title'),
                             (WEARER_RE, 'an adult\'s backpack heads the title')):
            match = pattern.search(title)
            if match and match.start() < head.start():
                return Value('other', TRUSTED, evidence=evidence,
                             notes=[f'{why}: "{match.group(0)}" comes before '
                                    f'"{head.group(0)}"'])
        return Value(KEY, TRUSTED, evidence=evidence)

    for pattern, what in ((OTHER_CLASS_RE, 'another class of backpack'),
                          (WEARER_RE, "an adult's backpack")):
        match = pattern.search(title)
        if match:
            return Value('other', TRUSTED, evidence=evidence,
                         notes=[f'the title names {what} and no school use: '
                                f'"{match.group(0)}"'])

    if any(node == SCHOOL_NODE for node in crumbs) and \
            re.search(r'rucksack|backpack', title, re.I):
        return Value(KEY, UNVERIFIED,
                     evidence=evidence + [Evidence('breadcrumbs', ' > '.join(crumbs))],
                     notes=['the title names no school at all; Amazon files the '
                            'listing in its school-bag node, which is weaker '
                            'evidence than the vendor saying so'])

    return Value('other', TRUSTED, evidence=evidence,
                 notes=['the title names neither a school backpack nor a '
                        'school use'])


# ---------------------------------------------------------------------------
# Claims: the vendor's own statements, quoted. Written against the text of the
# 43 records of 2026-09-17; the counts in the comments are what they found.
# ---------------------------------------------------------------------------

CLAIMS = (
    cat.Claim(
        'reflective_elements', 'Reflective elements',
        # 13 of the 23 school backpacks. Vendors write the noun ("Reflektoren"), the
        # adjective ("reflektierend"), a named part ("Leuchtstreifen") or
        # the effect ("Sichtbarkeit im Straßenverkehr"); DIN 58124 is the
        # satchel standard and appears on no secondary-school listing here.
        r'reflekt\w*|reflect\w*|fluoresz\w*|leuchtstreifen|leuchtfl[äa]che'
        r'|warnwirkung|din\s*58124'
        r'|sichtbar\w*\s+(?:im|bei)\s+(?:stra(?:ß|ss)enverkehr|dunkel\w*'
        r'|d[äa]mmerung|nacht)',
        why='a child on the way to school is seen by drivers or is not'),
    cat.Claim(
        'manufacturer_warranty', 'Manufacturer warranty',
        # 4 of the 23, always the technical table's "Garantie für das
        # Produkt" row: "4 Jahre", "20+ Jahre", "2 year manufacturer". A row
        # reading "Gesetzlich" states only the statutory right and is not a
        # manufacturer warranty; Amazon's own "Rückgabegarantie" is a return
        # policy; "garantieren" is a verb in marketing copy. None of those
        # match.
        r'garantie\s+f[üu]r\s+das\s+produkt\s*:\s*(?!gesetzlich)\d'
        r'|\d+\+?\s*(?:jahre?|years?|monate?|months?)\s*'
        r'(?:hersteller[\s-]?)?(?:garantie|warranty)\b'
        r'|\d+\+?\s*(?:jahre?|years?)\s+manufacturer'
        # Written out, or counted from the purchase: "ein Jahr Garantie",
        # "innerhalb von 12 Monaten nach dem Kauf ... deckt die Garantie". Found
        # on two of the 192 listings the widened collection returned; the first
        # version missed both.
        r'|(?:ein|zwei|drei|vier|f[üu]nf|zehn)\s+jahre?\s+(?:hersteller[\s-]?)?garantie\b'
        r'|\d+\s*(?:monaten|jahren)\s+nach\s+dem\s+kauf[^.]{0,60}\bgarantie\b'
        r'|hersteller[\s-]?garantie|lebenslange\s+garantie|lifetime\s+warranty',
        why='the nearest thing on the page to a durability commitment'),
    cat.Claim(
        'adjustable_back', 'Height-adjustable back',
        # 10 of the 23. "höhen- & größenverstellbar", "an die Rückenlänge
        # angepasst", "Körpergröße von 135 cm bis 180 cm", "EASY GROW".
        r'h[öo]hen\W{0,3}(?:&|und)?\s*(?:gr[öo](?:ß|ss)en)?verstellbar'
        r'|r[üu]ckenl[äa]nge\w*\s+(?:\w+\s+){0,4}(?:anpass|verstell|einstell)'
        r'|verstellbar\w*\s+r[üu]cken|r[üu]ckensystem\s+(?:\w+\s+){0,3}verstell'
        r'|k[öo]rpergr[öo](?:ß|ss)en?\s+von\s+\d|easy\s*grow|mitw[äa]chs',
        why='a back that adjusts to the child is what the satchel tests grade '
            'ergonomics on'),
    cat.Claim(
        'hip_or_chest_strap', 'Hip or chest strap',
        # 13 of the 23.
        r'h[üu]ftgurt|beckengurt|brustgurt|h[üu]ftflosse|bauchgurt',
        why='the tests\' other ergonomics criterion: a strap that moves load '
            'off the shoulders'),
)

PROFILE = CategoryProfile(key=KEY, label='school backpack',
                          nutrition_bands={}, price_band=None)


def _show_height(value):
    return value


def _show_years(value):
    return f'{value:g} years'


AXES = (
    cat.Axis('weight', 'Weight of the bag', better='lower', comparative='lighter',
             tolerance=10.0,
             why='a school bag is carried every day by a growing child'),
    cat.Axis('price', 'Price', better='lower', comparative='cheaper to buy',
             tolerance=0.01),
    cat.Axis('volume', 'Volume',
             caveat='shown, not ranked: the right volume depends on the school '
                    'day, not on more being better'),
    cat.Axis('body_height', 'Stated body-height range', render=_show_height,
             caveat='shown, not ranked: whether a range fits is a question '
                    'about one child'),
    cat.Axis('warranty_years', 'Warranty stated', better='higher',
             comparative='longer', tolerance=0.5, render=_show_years,
             why='the vendor\'s own commitment, read from its warranty row'),
    cat.Axis('review_rating', 'Average rating', better='higher',
             comparative='better rated', tolerance=0.1,
             caveat='Amazon\'s published average, trusted only where the '
                    'histogram agrees and at least twenty buyers rated; it '
                    'measures satisfaction among those who chose to rate, '
                    'not durability'),
    cat.Axis('review_count', 'Number of ratings',
             caveat='shown and boundable, not ranked: a count says how many '
                    'rated, not how good the bag is'),
)

# Weight statements in prose, read only when no structured row states one.
WEIGHT_TEXT_RE = re.compile(
    r'(?:gewicht|wiegt)\D{0,25}?(\d[\d.,]*)\s*(kg|kilogramm|g|gramm)\b'
    r'|(\d[\d.,]*)\s*(kg|kilogramm|g|gramm)\s+(?:leicht|schwer)\b', re.I)
VOLUME_RE = re.compile(r'(\d{2}(?:[.,]\d)?)\s*(?:l\b|liter\b|litern\b)', re.I)
HEIGHT_RANGE_RE = re.compile(
    r'k[öo]rpergr[öo](?:ß|ss)en?\s+von\s+(\d{3})\s*cm\s+bis\s+(\d{3})\s*cm'
    r'|(\d{3})\s*(?:cm)?\s*(?:bis|-|–)\s*(\d{3})\s*cm\s+k[öo]rpergr[öo](?:ß|ss)e'
    r'|k[öo]rpergr[öo](?:ß|ss)en?\s+von\s+(\d,\d\d)\s*(?:m)?\s*(?:bis|-|–)\s*(\d,\d\d)\s*m'
    r'|(\d,\d\d)\s*(?:m)?\s*(?:bis|-|–)\s*(\d,\d\d)\s*m', re.I)
HEIGHT_FROM_RE = re.compile(
    r'\bab\s+(?:einer\s+)?(?:k[öo]rpergr[öo](?:ß|ss)e\s+von\s+)?(\d{3})\s*cm'
    r'|\bab\s+(\d,\d\d)\s*m\b', re.I)


def _number(text):
    """A German-format number from vendor text: "1.250" is 1250, "1,1" is 1.1."""
    text = text.strip()
    if ',' in text:
        text = text.replace('.', '').replace(',', '.')
    elif text.count('.') == 1 and len(text.split('.')[1]) == 3:
        text = text.replace('.', '')
    try:
        return float(text)
    except ValueError:
        return None


def _grams(amount, unit):
    return amount * (1000.0 if unit.lower().startswith('k') else 1.0)


def weight(validated):
    """The bag's own weight, as the generic layer settled it.

    Identity, not a copy: the value and its status are the validation layer's
    and this module changes neither. A backpack is a single unit, so the
    Artikelgewicht row -- or the weight Amazon.de appends to the dimensions
    row -- *is* the bag's weight, and the generic reconciliation against the
    vendor's own text is exactly the check it needs. When no structured row
    states one, a weight in the prose is quoted as unverified so the card can
    say what the vendor wrote; it is never promoted here.
    """
    package = validated.record.get('package') or {}
    source = package.get('total_quantity_source') or ''
    count = package.get('item_count') or 1
    if source in ('item_weight', 'item_weight_x_count') and count == 1 \
            and validated.quantity.value is not None:
        return validated.quantity
    if source == 'item_weight_x_count':
        return Value.unknown('the page files more than one item, so its weight '
                             'row is not the weight of one bag')
    if source == 'package_weight':
        return Value.unknown('only a package weight is stated, which includes '
                             'the packaging')
    for hit in validated.search(WEIGHT_TEXT_RE, limit=1):
        match = WEIGHT_TEXT_RE.search(hit.quote)
        if match:
            amount = _number(match.group(1) or match.group(3))
            unit = match.group(2) or match.group(4)
            if amount:
                return Value(_grams(amount, unit), UNVERIFIED, 'g', [hit],
                             notes=['stated only in the vendor\'s prose, never '
                                    'in a structured row, so nothing confirms it'],
                             source=TEXT)
    return Value.unknown('the vendor states no weight for the bag')


def volume(validated):
    for hit in validated.search(VOLUME_RE, limit=1,
                                fields=('title', 'raw_tables',
                                        'content.feature_bullets',
                                        'content.description', 'content.aplus')):
        match = VOLUME_RE.search(hit.quote)
        if match:
            amount = _number(match.group(1))
            if amount and 5 <= amount <= 60:
                return Value(amount, UNVERIFIED, 'l', [hit], source=TEXT)
    return Value.unknown('no volume stated')


def body_height(validated):
    """The body-height range the vendor states, as text like "135–180 cm"."""
    for hit in validated.search(HEIGHT_RANGE_RE, limit=1):
        match = HEIGHT_RANGE_RE.search(hit.quote)
        if match:
            low, high = [g for g in match.groups() if g][:2]
            low, high = _number(low), _number(high)
            if low and high:
                if low < 3:      # metres
                    low, high = low * 100, high * 100
                return Value(f'{low:g}–{high:g} cm', UNVERIFIED, '', [hit],
                             source=TEXT)
    for hit in validated.search(HEIGHT_FROM_RE, limit=1):
        match = HEIGHT_FROM_RE.search(hit.quote)
        if match:
            low = _number(match.group(1) or match.group(2))
            if low:
                if low < 3:
                    low *= 100
                return Value(f'from {low:g} cm', UNVERIFIED, '', [hit],
                             source=TEXT)
    return Value.unknown('no body-height range stated')


YEARS_RE = re.compile(r'(\d+)\s*\+?\s*(?:jahre?n?|years?)\b|(\d+)\s*(?:monate?n?|months?)\b'
                      r'|(lebenslang|lifetime)|(?:\b(ein)\s+jahr\b)', re.I)


def warranty_years(found):
    """The years a stated manufacturer warranty names, from the claim's quote."""
    claim = found.get('manufacturer_warranty')
    if claim is None or claim.status != TRUSTED or not claim.evidence:
        return Value.unknown('no manufacturer warranty stated')
    quote = claim.evidence[0].quote
    match = YEARS_RE.search(quote)
    if not match:
        return Value.unknown('a warranty is stated without a duration')
    if match.group(3):
        return Value(99.0, UNVERIFIED, 'years', [claim.evidence[0]],
                     notes=['stated as lifetime; shown as 99 years so it sorts last'],
                     source=TEXT)
    if match.group(2):
        return Value(int(match.group(2)) / 12.0, UNVERIFIED, 'years',
                     [claim.evidence[0]], source=TEXT)
    if match.group(4):
        return Value(1.0, UNVERIFIED, 'years', [claim.evidence[0]], source=TEXT)
    return Value(float(match.group(1)), UNVERIFIED, 'years', [claim.evidence[0]],
                 source=TEXT)


def stated(validated, claim):
    return validated.search(claim.pattern, limit=2, fields=claim.fields,
                            scope='page', affirmative=True)


def claims(validated):
    """Every criterion, each with the vendor's own sentence or an explicit gap."""
    result = {}
    for claim in CLAIMS:
        hits = stated(validated, claim)
        if hits:
            result[claim.key] = Value(True, TRUSTED, evidence=hits, source=TEXT)
        else:
            result[claim.key] = Value(
                False, NOT_CLAIMED,
                notes=[f'{claim.label}: not stated anywhere on the page. That '
                       f'is not the same as it being untrue.'])
    return result


def evaluate(record):
    """One school-backpack evidence card, or a classification-only card."""
    classification = classify(record)
    validated = validate(record, PROFILE)
    if classification.value != KEY:
        return cat.card(record, validated, CATEGORY, classification,
                        axes={}, claims={})
    found = claims(validated)
    axes = {'weight': weight(validated),
            'price': validated.price,
            'volume': volume(validated),
            'body_height': body_height(validated),
            'warranty_years': warranty_years(found),
            'review_rating': validated.review_rating,
            'review_count': validated.review_count}
    return cat.card(record, validated, CATEGORY, classification, axes, found)


# What this capability has earned (R16): one study, one buyer, one shelf. It
# was built as reviewed maintenance during the 2026-09-17 intake conversation,
# with no R15 gate to pass through, and retained at study close nominated for
# reuse. That is a task experiment, whatever the registry calls it: promotion
# to maintained needs a distinct subsequent use, and this declaration is where
# that decision will be recorded when it happens.
LIFECYCLE = cat.Lifecycle(
    state=cat.EXPERIMENT,
    decision='retained',
    decided='2026-09-18',
    maintainer='repository maintainer',
    applicability=cat.Applicability(
        marketplaces=('www.amazon.de',),
        accepts='Secondary-school backpacks sold as such on Amazon.de: the title '
                'names a school bag and no other backpack class, adult wearer or '
                'primary-school marker comes before it. A title naming no '
                'school use is accepted only from the school-bag node, as '
                'unverified.',
        declines=(
            cat.Decline("adults' laptop and men's packs with a school word "
                        'stuffed into the title',
                        ('B0BRKHTWB1', 'B07RW36W3K', 'B0CYBW4V5H', 'B0DSPQ96PH',
                         'B0B2RC7F6M')),
            cat.Decline("first-graders' satchel sets, and a satchel Amazon "
                        'files in the satchel-set node',
                        ('B0GYS582DH', 'B0CYZKT2V5')),
            cat.Decline('trekking, hiking, leisure and adult daypacks the brand '
                        'queries return',
                        ('B0D5R73HZ2', 'B0FHKWFVDR', 'B0FHL3BH68', 'B0F8W25VDC',
                         'B000RE5A4U', 'B07DNZCRVX', 'B07P6M89HV', 'B0DCH9D4H9',
                         'B0B1VXPQF9', 'B0CKTHQVXF', 'B0B6H24C3H', 'B0GPNQ54YZ',
                         'B0HCPS1THW')),
        ),
        not_established=(
            'a distinct subsequent use: one study, one buyer, one shelf of 43 '
            'records on 2026-09-17',
            'classifier accuracy beyond those 43 titles',
            'durability, or fit for a given child: the body-height range a '
            'vendor states is shown and ranked on by nobody',
            'weights stated in pounds, which the extractor keeps as text',
            'that a rating threshold separates good bags from bad: the two '
            'review axes exist so a buyer\'s stated threshold can be executed, '
            'and they rank nothing by default',
        )),
    evidence=('tests/cases/school_backpack_v1.jsonl.gz',
              'tests/test_school_backpack.py'),
    milestones=('r11--category-synthesis-as-a-default-step',
                'r13--the-conversation-as-the-entry-point'),
    reviewed='2026-09-18',
    review='architectural-review-1--2026-09-18',
    method_version=1,
)


CATEGORY = cat.register(cat.Category(
    key=KEY,
    label='school backpack',
    profile=PROFILE,
    axes=AXES,
    claims=CLAIMS,
    evaluate=evaluate,
    default_axis='weight',
    lifecycle=LIFECYCLE,
    blurb='Ranked by the bag\'s own stated weight, lighter first, among '
          'listings the vendor sells as school backpacks and not as '
          'primary-school satchels. Reflective elements, a manufacturer '
          'warranty, an adjustable back and a hip or chest strap are the '
          'vendor\'s statements quoted from the page; whether a stated '
          'body-height range fits is a question about one child.',
))
