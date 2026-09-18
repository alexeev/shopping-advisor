"""Smartwatch: the fifth category, and the first written through R15.

The use case is the third R13 conversational trial of 2026-09-18: a buyer on
Android wanted one watch for three sports, an annual two-week scuba trip to
30 m that the watch should cover instead of a separate dive computer, and NFC
payment, ordered by battery life and then by display. Three probes on Amazon.de
returned 57 records; a person read them by hand because no category existed.
This module is that reading turned into code, written inside the study through
the R15 procedure -- the record of that is the adaptation the study binds --
and it is honest about the same limits the hand reading had:

1. **It has to be a smartwatch**, not a strap, a case, a charger or a screen
   protector returned for a watch query, not a fitness band or a GPS tracker
   sold with "Smart Watch" stuffed into its title, and not a pure dive computer
   -- the Mares, Cressi and Suunto instruments the class queries surface beside
   the watches. The title decides, read positionally as for tyre mounting paste
   and school backpacks: a band or tracker word *before* the watch word heads
   the title and names what the listing is; an accessory noun anywhere names an
   accessory; a dive computer that names no smartwatch function is a dive
   computer. A title that names no class at all is accepted only from Amazon's
   Smartwatches node or from a body text that says so, as unverified.
2. **What the vendor states.** GPS, an optical heart-rate sensor, a barometric
   altimeter, a scuba dive mode, NFC payment and Android compatibility are the
   six statements the trial's engineering proposal named, and each is the
   vendor's sentence quoted from the page, never a verified property. Three of
   them are exactly where the hand reading went wrong twice under independent
   review, so the card says the narrow thing: a sensor present is not
   measurement quality, a dive mode is not a licence to dive without a
   computer, NFC present is not payment that works with this buyer's card in
   Germany. Payment usable in Germany is on no product page and is not a claim
   here.
3. **Price is the one ranked axis.** The buyer's first ordering criterion was
   battery life, and the vendors state it on incompatible scales -- days in
   "smartwatch mode", hours of GPS, hours in a dive mode, days of standby, each
   as a "bis zu" -- and the review of the trial's plan failed a ranking that
   put those in one order. So the stated runtimes are shown on the card with
   the mode the vendor named and ranked on by nobody, as is the stated depth
   rating in metres (never converted from ATM) and the display technology.
   Ranking runtimes needs a comparability control this category does not
   have, and this module does not pretend to.

What no page states, and this category does not invent: measurement quality,
whether a watch can replace a dive computer on a real dive, whether a payment
service works with a given bank, and battery life as a buyer will experience
it.
"""

import re

from shopping_advisor.validation import (CategoryProfile, NOT_CLAIMED, TEXT,
                                       TRUSTED, UNVERIFIED, Evidence, Value,
                                       validate)

from .. import category as cat

KEY = 'smartwatch'

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

# The words that say a listing is a smartwatch or a GPS sports watch. A bare
# "Uhr" or "Watch" is not one of them: "Tauchcomputer und Uhr" is a dive
# computer, "Garmin Watch Ladeadapter" is a charger, "Watch Style Computer" is
# a dive-computer interface. The brand-model forms are here for titles that
# name the product and not the class.
WATCH_RE = re.compile(
    r'smart[\s-]?watch(?:es)?|multisport[\s-]?(?:smartwatch|uhr)'
    r'|gps-?\s?(?:multisport-?)?(?:smartwatch|uhr|sportuhr)'
    r'|sport-?uhr|fitness-?uhr|puls-?uhr|outdoor-?uhr'
    r'|apple\s+watch|huawei\s+watch|galaxy\s+watch|pixel\s+watch', re.I)

# Fitness bands and GPS trackers: a different product class. Positional --
# "Xiaomi Smart Band 10, Smart Watch, Fitness-Tracker" is a band with the
# watch word stuffed in after; "Smartwatch ... Fitness Tracker" is a watch that
# also tracks. A tracker word with no watch word at all is a tracker.
TRACKER_RE = re.compile(
    r'smart[\s-]?band|fitness[\s-]?(?:tracker|armband)|aktivit[äa]ts-?tracker'
    r'|gps-?tracker|\btracker\b', re.I)

# Accessories. Positional like the rest: an accessory noun *before* the first
# watch word heads the title ("22mm Nylon Armband Kompatibel mit Garmin ..."),
# after it the noun is the watch's own strap ("Apple Watch Ultra 3 ... mit
# Ozean Armband"). A compatibility phrase anywhere -- "kompatibel mit", "für
# Garmin" -- names the watch an accessory fits and decides the rest.
# "Silikonband" and "Silicone Strap" are not matched on purpose.
ACCESSORY_RE = re.compile(
    r'\barmband\b|armb[äa]nder|ersatz-?armband|uhren-?armband|quickfit'
    r'|schutzh[üu]lle|\bh[üu]lle\b|\bcase\b|schutzglas|schutzfolie|panzerglas'
    r'|displayschutz|ladeger[äa]t|ladekabel|ladeadapter|ladestation|dockingstation'
    r'|\bcharger\b|\bzubeh[öo]r\b|halterung|schnittstelle|\binterface\b', re.I)

# A dive computer. Only decisive when nothing in the title names a smartwatch:
# "Descent G2, GPS-Tauchcomputer/Smartwatch" is a smartwatch that dives;
# "Cressi GOA Tauchcomputer und Uhr" is a dive computer that tells the time.
COMPATIBLE_RE = re.compile(r'kompatibel\s+mit|compatible\s+with|passend\s+f[üu]r'
                           r'|\b(?:f[üu]r|for|zu)\s+(?:garmin|apple|huawei|samsung|polar|suunto)\b', re.I)
DIVE_RE = re.compile(r'tauch-?computer|dive\s*computer|diving\s*computer', re.I)

# Amazon's own node. Weaker evidence than the vendor saying so.
SMARTWATCH_NODE = 'smartwatches'
BODY_FIELDS = ('content.feature_bullets', 'content.description')


def classify(record):
    """Is this a smartwatch? Decided on the title, with a node and a body fallback."""
    title = record.get('title') or ''
    if not title:
        return Value.unknown('the listing has no title to classify')
    crumbs = [str(crumb).strip().lower() for crumb in record.get('breadcrumbs') or []]
    evidence = [Evidence('title', title[:160])]

    head = WATCH_RE.search(title)
    accessory = ACCESSORY_RE.search(title)
    if accessory and (head is None or accessory.start() < head.start()
                      or COMPATIBLE_RE.search(title)):
        return Value('other', TRUSTED, evidence=evidence,
                     notes=[f'an accessory for a watch, not a watch: the title says '
                            f'"{accessory.group(0)}"'
                            + (f' before "{head.group(0)}"' if head and accessory.start() < head.start()
                               else ' and names the watch it fits' if head else '')])
    tracker = TRACKER_RE.search(title)
    if tracker and (head is None or tracker.start() < head.start()):
        return Value('other', TRUSTED, evidence=evidence,
                     notes=[f'a fitness band or tracker heads the title: '
                            f'"{tracker.group(0)}"'
                            + (f' comes before "{head.group(0)}"' if head else '')])
    dive = DIVE_RE.search(title)
    if dive and head is None:
        return Value('other', TRUSTED, evidence=evidence,
                     notes=[f'a dive computer, not a smartwatch: the title says '
                            f'"{dive.group(0)}" and names no smartwatch function'])
    if head:
        return Value(KEY, TRUSTED, evidence=evidence)

    if any(node == SMARTWATCH_NODE for node in crumbs):
        return Value(KEY, UNVERIFIED,
                     evidence=evidence + [Evidence('breadcrumbs', ' > '.join(crumbs))],
                     notes=['the title names no product class; Amazon files the '
                            'listing in its Smartwatches node, which is weaker '
                            'evidence than the vendor saying so'])
    from shopping_advisor.validation.evidence import search
    body = search(record, WATCH_RE, limit=1, fields=BODY_FIELDS)
    if body:
        return Value(KEY, UNVERIFIED, evidence=evidence + body,
                     notes=['the title names no product class; the vendor\'s own '
                            'text calls it a smartwatch, which is read as unverified'])
    return Value('other', TRUSTED, evidence=evidence,
                 notes=['the title names neither a smartwatch nor a class this '
                        'category declines, and neither the node nor the body '
                        'text says what it is'])


# ---------------------------------------------------------------------------
# Claims: the vendor's own statements, quoted. Written against the text of the
# 55 unique records of 2026-09-18; the counts in the comments are lexical hits
# over that set before the classifier, not verified properties.
# ---------------------------------------------------------------------------

NOT_FOR_DIVING = (r'nicht\s+(?:zum|f[üu]r(?:s)?|beim)\s+tauch\w*|kein\w*\s+tauch\w*'
                  r'|not\s+(?:for|suitable\s+for)\s+(?:scuba\s+)?div\w*')
NOT_ANDROID = (r'nicht\s+(?:mit\s+|f[üu]r\s+)?android|kein\w*\s+android'
               r'|nur\s+(?:mit\s+|f[üu]r\s+)?(?:iphone|ios)|iphone\s+erforderlich'
               r'|requires\s+an?\s+iphone')

CLAIMS = (
    cat.Claim(
        'gps', 'GPS',
        # 41 of 55 records mention a satellite system somewhere on the page.
        r'\bgps\b|\bgnss\b|multi-?band|\bglonass\b|\bgalileo\b',
        why='the buyer\'s sports are outdoors; a stated satellite receiver is '
            'the vendor\'s word, not a measured track'),
    cat.Claim(
        'heart_rate_sensor', 'Heart-rate sensor',
        # 33 of 55. A sensor's presence, never its accuracy.
        r'herzfrequenz\w*|pulsmess\w*|puls-?(?:uhr|sensor|messung)'
        r'|heart[\s-]?rate|\bhf-?sensor|optische[rn]?\s+(?:herz|puls|sensor)\w*',
        why='the buyer asked for measurement quality; the page can only say '
            'that a sensor is there'),
    cat.Claim(
        'barometric_altimeter', 'Barometric altimeter',
        # 6 of 55: "barometrischer Höhenmesser", "Höhenmesser: Ja".
        r'barometr\w*|h[öo]henmesser|altimeter|luftdruck\w*',
        why='the outdoor sensor the trial\'s buyer listed; presence, not '
            'accuracy'),
    cat.Claim(
        'scuba_dive_mode', 'Dive mode stated',
        # 32 of 55 mention diving; the pure dive computers among them are
        # declined by the classifier before this claim is read.
        # "Tauchen" alone is an activity in a list ("Surfen oder Tauchen: über
        # 80 Sport-Apps") and is not matched: the claim is a stated *scuba*
        # function -- a dive mode, function or technology, a dive computer,
        # nitrox or a decompression model. Method version 2 (R15, the second
        # adaptation) stopped reading "tauchfähig bis 40m" (dive-capable: a
        # water-resistance sentence, which the trial's plan says never
        # satisfies a dive-computer condition), "Tauchgänge" (dives as an
        # activity), and "Freitauchen" and "Apnoe" (freediving is not scuba):
        # version 1 credited the fenix 8, the fenix 8 Pro and a 178 EUR KOSPET
        # with a dive function on those words.
        r'tauch(?:modus|modi|funktion\w*|technologie|computer)'
        r'|scuba|dive\s*mode|nitrox|dekompression\w*',
        why='the vendor says the watch has a scuba function: a dive mode, a '
            'dive computer or a decompression model. A water-resistance or '
            'freediving sentence is not one, and whether the watch may replace '
            'a dive computer on a real dive is not on the page'),
    cat.Claim(
        'nfc_payment', 'NFC payment',
        # Method version 3 (R15's fourth adaptation, 2026-09-18): a payment
        # service or a contactless-payment phrase, not the word NFC. Version 2
        # also matched a bare "NFC" and a bare "Wallet", so a connectivity row
        # "Bluetooth, GPS, NFC" was credited as a payment statement: of the 20
        # positives on the 39 committed cards, 5 rested on that word alone
        # (both Huawei Watch Ultimate 2 listings, two GT 7 Pro, the Watch D3).
        # An NFC chip is not a payment function; the independent review of
        # plan revision 8 found the mismatch (A8.1).
        r'kontaktlos\w*\s+(?:bezahl|zahl)\w*|nfc[\s-]*(?:zahl|bezahl|payment)\w*'
        r'|garmin\s+pay|huawei\s+pay|apple\s+pay|samsung\s+pay|google\s+(?:pay|wallet)'
        r'|(?:huawei|garmin|google|samsung)\s+wallet',
        why='the vendor names a payment service or contactless payment on the '
            'page; a bare "NFC" is connectivity, not payment, and whether the '
            'service works with the buyer\'s card in Germany is not there'),
    cat.Claim(
        'android_compatible', 'Android compatibility stated',
        # 16 of 55 name Android; Apple's pages name the iPhone and no Android,
        # and read as not claimed rather than as incompatible.
        r'\bandroid\b',
        why='the buyer\'s phone; an unstated compatibility is a gap, not a no'),
)

PROFILE = CategoryProfile(key=KEY, label='smartwatch', nutrition_bands={},
                          price_band=None)


def _show_metres(value):
    return f'{value:g} m'


def _show_atm(value):
    return f'{value:g} ATM'


def _show_hours(value):
    return f'up to {value:g} h'


def _show_days(value):
    return f'up to {value:g} days'


def _show_text(value):
    return value


AXES = (
    cat.Axis('price', 'Price', better='lower', comparative='cheaper to buy',
             tolerance=0.01),
    cat.Axis('depth_rating_m', 'Stated depth rating', render=_show_metres,
             caveat='shown, not ranked: a rating in metres is the vendor\'s '
                    'statement about the case, never converted from ATM, and '
                    'not a licence to dive to it'),
    cat.Axis('water_resistance_atm', 'Stated water resistance', render=_show_atm,
             caveat='shown, not ranked, and not converted to metres: an ATM '
                    'rating is a pressure test, not a diving depth'),
    cat.Axis('gps_runtime_hours', 'Stated GPS runtime', render=_show_hours,
             caveat='shown, not ranked: a "bis zu" hours figure in the '
                    'vendor\'s GPS mode, measured by nobody here and on no '
                    'scale another vendor shares'),
    cat.Axis('smartwatch_runtime_days', 'Stated runtime in watch mode',
             render=_show_days,
             caveat='shown, not ranked: a "bis zu" days figure in the mode '
                    'the vendor named; standby time is not this'),
    cat.Axis('display_type', 'Display technology', render=_show_text,
             caveat='shown, not ranked: the buyer\'s second criterion, and a '
                    'name is not a readability measurement'),
)

DEPTH_RE = re.compile(
    r'(?:wasserdicht\w*|wassergesch[üu]tzt|wasserfest|water[\s-]?resistan\w*'
    r'|water-?proof|tauch\w*|tief\w*)\W{0,3}(?:bis\s+(?:zu\s+)?)?(?:in\s+)?(\d{2,3})\s*(?:m\b|meter)'
    r'|(\d{2,3})\s*(?:-\s*)?meter\W{0,3}(?:tauch|wasser)'
    r'|(\d{2,3})\s*m\s+wasserdicht', re.I)
ATM_RE = re.compile(r'\b(\d{1,2})\s*atm\b', re.I)
GPS_HOURS_RE = re.compile(
    r'(?:bis\s+zu\s+)?(\d{1,3})\s*(?:stunden|std\.?|h)\b[^.;]{0,40}?\bgps'
    r'|\bgps[^.;]{0,40}?(?:bis\s+zu\s+)?(\d{1,3})\s*(?:stunden|std\.?|h)\b', re.I)
DAYS_RE = re.compile(
    r'(?:bis\s+zu\s+)?(\d{1,2})\s*tage\w*[^.;]{0,30}?(?:smartwatch|uhren)-?modus'
    r'|(?:smartwatch|uhren)-?modus[^.;]{0,25}?(?:bis\s+zu\s+)?(\d{1,2})\s*tage'
    r'|akku(?:laufzeit)?\W{0,3}(?:bis\s+zu\s+)?(\d{1,2})\s*tage'
    r'|(?:bis\s+zu\s+)?(\d{1,2})\s*tage\w*\s+akku(?:laufzeit)?', re.I)
STANDBY_RE = r'standby[^.;]{0,40}|[^.;]{0,40}standby'
DISPLAY_RE = re.compile(r'\bamoled\b|\bmip\b|memory[\s-]in[\s-]pixel|\blcd\b|\boled\b'
                        r'|transflekt\w*|e-?ink|retina', re.I)
DISPLAY_NAMES = {'memory in pixel': 'MIP', 'memory-in-pixel': 'MIP', 'e ink': 'E-ink',
                 'eink': 'E-ink', 'e-ink': 'E-ink', 'retina': 'Retina'}

TEXT_FIELDS = ('title', 'content.feature_bullets', 'content.description',
               'content.aplus', 'raw_tables')


def _first_number(match):
    return next((float(group) for group in match.groups() if group), None)


def _stated(validated, regex, unit, note, fields=TEXT_FIELDS, exclude=None,
            accept=lambda amount: amount > 0):
    for hit in validated.search(regex, limit=1, fields=fields, exclude=exclude):
        match = regex.search(hit.quote)
        if match:
            amount = _first_number(match)
            if amount is not None and accept(amount):
                return Value(amount, UNVERIFIED, unit, [hit], notes=[note], source=TEXT)
    return None


def depth_rating(validated):
    """A depth the vendor states in metres. Never converted from ATM."""
    found = _stated(validated, DEPTH_RE, 'm',
                    'the vendor\'s stated rating, quoted; not a depth anyone dived to',
                    accept=lambda amount: 10 <= amount <= 500)
    return found or Value.unknown('no depth rating in metres stated')


def water_resistance(validated):
    found = _stated(validated, ATM_RE, 'atm',
                    'an ATM rating is a pressure test, not a diving depth',
                    accept=lambda amount: 1 <= amount <= 30)
    return found or Value.unknown('no ATM rating stated')


def gps_runtime(validated):
    found = _stated(validated, GPS_HOURS_RE, 'h',
                    'stated "bis zu" in the vendor\'s GPS mode, on no shared scale',
                    accept=lambda amount: 1 <= amount <= 500)
    return found or Value.unknown('no GPS runtime stated with its mode')


def smartwatch_runtime(validated):
    found = _stated(validated, DAYS_RE, 'days',
                    'stated "bis zu" in the mode the vendor named; standby excluded',
                    exclude=STANDBY_RE, accept=lambda amount: 1 <= amount <= 120)
    return found or Value.unknown('no runtime in days stated for a watch mode')


def display_type(validated):
    for hit in validated.search(DISPLAY_RE, limit=1, fields=TEXT_FIELDS):
        match = DISPLAY_RE.search(hit.quote)
        if match:
            word = match.group(0).lower()
            name = 'MIP' if word.startswith('transflekt') else DISPLAY_NAMES.get(word, word.upper())
            return Value(name, UNVERIFIED, '', [hit], source=TEXT)
    return Value.unknown('no display technology stated')


def stated(validated, claim, exclude=None):
    return validated.search(claim.pattern, limit=2, fields=claim.fields,
                            scope='page', affirmative=True, exclude=exclude)


EXCLUSIONS = {'scuba_dive_mode': NOT_FOR_DIVING, 'android_compatible': NOT_ANDROID}


def claims(validated):
    """Every criterion, each with the vendor's own sentence or an explicit gap."""
    result = {}
    for claim in CLAIMS:
        hits = stated(validated, claim, EXCLUSIONS.get(claim.key))
        if hits:
            result[claim.key] = Value(True, TRUSTED, evidence=hits, source=TEXT)
        else:
            result[claim.key] = Value(
                False, NOT_CLAIMED,
                notes=[f'{claim.label}: not stated anywhere on the page. That '
                       f'is not the same as it being untrue.'])
    return result


def evaluate(record):
    """One smartwatch evidence card, or a classification-only card."""
    classification = classify(record)
    validated = validate(record, PROFILE)
    if classification.value != KEY:
        return cat.card(record, validated, CATEGORY, classification,
                        axes={}, claims={})
    found = claims(validated)
    axes = {'price': validated.price,
            'depth_rating_m': depth_rating(validated),
            'water_resistance_atm': water_resistance(validated),
            'gps_runtime_hours': gps_runtime(validated),
            'smartwatch_runtime_days': smartwatch_runtime(validated),
            'display_type': display_type(validated)}
    return cat.card(record, validated, CATEGORY, classification, axes, found)


# What this capability has earned (R16): one study, one buyer, one shelf of 55
# unique records -- and, unlike school_backpack, a passage through R15: the
# adaptation record the study binds holds the patch, its checks inside the
# execution boundary, its review and its adoption. It is a task experiment;
# promotion needs a distinct subsequent use, recorded here when it happens.
LIFECYCLE = cat.Lifecycle(
    state=cat.EXPERIMENT,
    decision='retained',
    decided='2026-09-18',
    maintainer='repository maintainer',
    applicability=cat.Applicability(
        marketplaces=('www.amazon.de',),
        accepts='Smartwatches and GPS sports watches sold as such on Amazon.de: '
                'the title names one and no band, tracker or accessory noun '
                'heads it. A title naming no class is accepted only from the '
                'Smartwatches node or from a body text that says so, as unverified.',
        declines=(
            cat.Decline('straps, cases, screen protectors, chargers and adapters '
                        'returned for watch queries',
                        ('B0F9WXLL2X', 'B0H8P8FT5Q', 'B0D4F71WQC', 'B07D6HM812',
                         'B09V7CJZWQ', 'B07DJ92CFR')),
            cat.Decline('fitness bands and GPS trackers with a watch word stuffed '
                        'in after the head noun',
                        ('B0DYF82545', 'B0GNNFBJ3H')),
            cat.Decline('dive computers that name no smartwatch function, '
                        'including one whose bullets list GPS and maps',
                        ('B0CRDZ35S8', 'B082B8WMBD', 'B0DQ2MHKHW', 'B0719H6GGH',
                         'B07P1WV8VP', 'B0G1S9FV62')),
            cat.Decline('a dive-computer interface sold in watch form',
                        ('B09TRS84XP',)),
        ),
        not_established=(
            'a distinct subsequent use: one study, one buyer, one shelf of 55 '
            'unique records on 2026-09-18, most of the named-model ones '
            'supplied by the agent rather than discovered (selection bias)',
            'classifier accuracy beyond those 55 titles; a fenix 8 listing '
            'whose title, node and bullets never name a class is filed as '
            'other',
            'measurement quality, suitability as a sole dive computer, or '
            'payment that works with a given card in Germany: the decisive '
            'conditions of the trial are on no product page and stay withheld',
            'any ordering of battery life: runtimes are stated per vendor mode '
            'on no shared scale and are shown, not ranked',
            'that the Suunto Nautic S is not a smartwatch: its title names only '
            'a dive computer and the classifier reads the title',
        )),
    evidence=('tests/cases/smartwatch_v1.jsonl.gz',
              'tests/test_smartwatch.py',
              'tests/intake/smartwatch-brief.json',
              'tests/intake/smartwatch-plan.json',
              'tests/intake/smartwatch-adaptation.json',
              'data/evidence/probe-amazon-de-smartwatch-2026-09-18-class.jsonl.gz',
              'data/evidence/probe-amazon-de-smartwatch-2026-09-18-named.jsonl.gz',
              'data/evidence/probe-amazon-de-smartwatch-2026-09-18-asin.jsonl.gz'),
    milestones=('r15--controlled-task-driven-capability-adaptation',
                'r11--category-synthesis-as-a-default-step',
                'r13--the-conversation-as-the-entry-point'),
    reviewed='2026-09-18',
    review='architectural-review-1--2026-09-18',
    # 2 since the second R15 adaptation (2026-09-18): the dive claim's meaning
    # moved on five committed records. 3 since the fourth (2026-09-18): the
    # payment claim stopped reading a bare "NFC", and moved on five.
    method_version=3,
)


CATEGORY = cat.register(cat.Category(
    key=KEY,
    label='smartwatch',
    profile=PROFILE,
    axes=AXES,
    claims=CLAIMS,
    evaluate=evaluate,
    default_axis='price',
    lifecycle=LIFECYCLE,
    blurb='Ranked by listed price, cheaper first, among listings the vendor '
          'sells as smartwatches or GPS sports watches and not as bands, '
          'trackers, accessories or dive computers. GPS, a heart-rate sensor, '
          'a barometric altimeter, a dive mode, NFC payment and Android '
          'compatibility are the vendor\'s statements quoted from the page; '
          'stated depth ratings, runtimes and display technology are shown '
          'with the mode the vendor named and ranked on by nobody.',
))
