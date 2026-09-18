# The extraction and validation contract

What downstream code may rely on, what it may not, and what has to change
before either of those changes. Two artefacts are published here:

| Artefact | Version | Produced by | Answers |
|---|---|---|---|
| **Product record** | `SCHEMA_VERSION = 6` | `shopping_advisor.extraction` | what the page says |
| **Validated record** | `CONTRACT_VERSION = 2` | `shopping_advisor.validation` | how much of that holds up |

They are versioned separately because they change for different reasons and
have different consumers. An extractor learning to read a new Amazon
structure moves the first; a rule learning that a value cannot be confirmed
moves the second.

```text
extraction  ──►  validation  ──►  category analysis  ──►  report
schema v6        contract v2      analysis/categories/    analysis/report.py
```

---

## 1. Why there are two layers and not one

A populated field is not a fact. Amazon's *structured* nutrition card states
87.7 kcal per 100 g for dry pasta on one record and 7 g of carbohydrate on
another; a sixteen-pack of Garofalo reports €62.56/kg because the vendor filed
`Anzahl der Einheiten: 500 gramm`, and Amazon's own price per kilogram agrees
with it because it is computed from the same wrong row.

The extractor's job is to be faithful to the page, including when the page is
wrong. Deciding what to believe is a separate job, with separate evidence, and
it is done once — not per category.

### The mistake this replaces

Schema v3 published `food.nutrition.confidence` (`high` / `medium` / `low`),
set from *which structure* the numbers came from. Measured over the
195-record Amazon.de validation set, `high`-confidence records failed
plausibility checks **more** often than `medium` ones — 5 of 45 against 2 of
40. A well-rendered table is evidence about the care a vendor took filling in
a form. It is not evidence about the number.

So v4 removes `confidence` and the contract splits it in two:

- **`source`** — how the value was obtained. Extraction may state this,
  because it knows it and it is a fact about the page.
- **`status`** — whether the value survived checking. Only the validation
  layer may state this, and never from the source alone.

---

## 2. The product record (schema v6)

One JSON object per line. Every group degrades to `{}` / `[]` rather than
disappearing, so consumers can index without guards.

| Group | Keys |
|---|---|
| envelope | `schema_version`, `fetched_at` |
| lineage | `marketplace`, `asin`, `product_url`, `canonical_url`, `search_query`, `search_page`, `search_position`, `run_id`, `locale`, `accept_language` |
| core | `title`, `brand`, `byline_text`, `brand_url`, `price{amount,currency,text,range?}`, `unit_price{amount,unit,text}`, `rating{value,count,text,count_text}`, `availability`, `seller`, `breadcrumbs[]` |
| package | `item_weight_*`, `package_weight_*`, `unit_count_*`, `volume_*`, `item_count`, `size_name`, `dimensions`, `total_quantity_base`, `total_quantity_unit`, `total_quantity_source`; `item_weight_origin` = `dimensions` when no Artikelgewicht row exists and the weight was read from the tail of the dimensions row ("22 x 30 x 45 cm; 1,1 Kilogramm"), absent otherwise |
| content | `feature_bullets[]`, `description`, `important_information[{heading,text}]`, `aplus{module_types,headings,text,text_length,prose,images,tables,comparison}`; `prose` is the A+ copy without table cells, and `comparison[]` each A+ comparison table as `{columns[{label,asin}], rows[[label,cell…]], self_column}` — `asin` the product a column's header links, `self_column` the index of the column that links this page's own ASIN or `null` (the page's product is not always a column, nor the first one), never inferred from position |
| food | `ingredients{text,source}`, `allergens[]`, `nutrition{source,basis_text,per_100g,rows,derived}` |
| attributes | `attributes{}` (canonical), `raw_tables{}` (verbatim), `attribute_sources{}` |
| media | `images[{url,variant,alt,thumb}]`, `primary_image`, `image_count`, `image_source` |
| variation | `dimensions[]`, `display_labels{}`, `variation_values{}`, `values_by_asin{asin:[…]}`, `current_asin`, `parent_asin`, `total_variations` — decoded verbatim, never interpreted |
| reviews | `histogram_percent{five_star…one_star}`, `sample[]`, `sample_size`, `sample_home`, `rating_count`, `sample_source` |
| diagnostics | `extraction{blocks_present[],blocks_absent[],errors[]}` |

`nutrition.per_100g` uses canonical keys: `energy_kj`, `energy_kcal`,
`protein_g`, `fat_g`, `saturated_fat_g`, `carbohydrates_g`, `sugars_g`,
`fiber_g`, `salt_g`, `sodium_mg`.

`nutrition.source` is one of `nutrition_card`, `attributes`, or `text:<field>`
— **which structure the numbers came from, and nothing more**.

In schema v6, `price.range` retains the bounds when the page presents a price
range. `price.amount` is then absent: one end of a range is not the price of a
selected offer. See §7 for the migration history.

### `reviews` — one complete structure and one sample, never confused

Added in v5. The two halves of this block have very different evidential
weight and the names say so.

`histogram_percent` is **complete**: five whole-percent shares covering every
rating the listing ever received. Measured over the 38 corpus pages that carry
one, it sums to exactly 100 on **every** record and reconstructs Amazon's
published average to within **0.08 stars**. It is therefore an independent
statement of the same fact the average asserts, and the validation layer uses
it to promote the average under the ordinary corroboration rule.

`sample` is **8–13 review cards Amazon chose**, out of a `rating_count` often
in the thousands. Each card carries `rating`, `title`, `text`, `date`,
`country`, `home_marketplace`, `variant`, `verified` and `helpful_votes`. Three
of those exist because the page merges things a reader should not:

* `home_marketplace: false` marks the "reviews from other countries" section —
  a different marketplace's listing, machine-translated. **82 of 277 corpus
  cards (30%)** are foreign.
* `variant` is Amazon's format strip ("Größe: 5 kg (1er Pack)"). Reviews are
  pooled across every pack size of a parent ASIN, and sometimes across
  different products.
* `verified` is Amazon's purchase badge. 271 of 277 corpus cards carry it, so
  a listing where most do not is an outlier worth noticing.

`sample_source` is `'pdp_widget'` and is named rather than implied: this is the
only review data reachable without an account, because `/product-reviews/<ASIN>`
redirects to sign-in. **No rate may be computed from `sample`.**

`package.total_quantity_base` is grams or millilitres, and
`total_quantity_unit` says which. The unit follows the attribute row the total
was read from — not a volume mentioned elsewhere on the page. Before v4 it was
inferred from any volume field present, which reported a 50 ml sponge tin as
50 g and then priced it per kilogram.

---

## 3. The validated record (contract v2)

`shopping_advisor.validation.validate(record, profile) -> Validated`

The Python API defaults to a neutral profile when called as `validate(record)`;
the saved-page corpus pins this neutral output. The `analysis validated` CLI
instead supplies the selected category's profile (default `dry_pasta`), applying
its plausibility bands without running its classifier or claim evaluator. It
has no neutral-profile switch. See [RESEARCH.md](RESEARCH.md#offline-walkthrough)
for an executable example.

```python
from shopping_advisor.validation import validate, CategoryProfile

validated = validate(record, CategoryProfile(key='paint', label='wall paint'))
validated.quantity.status        # 'trusted'
validated.quantity.source        # 'attributes'
validated.price_per_base.unit    # 'EUR/l'
validated.as_dict()              # JSON-serialisable, snapshot-tested
```

| Field | Type | Meaning |
|---|---|---|
| `contract_version`, `schema_version` | int | this shape, and the record's |
| `category_profile` | str | the profile's `key`, or `'product'` for none |
| `asin`, `title`, `brand`, `url`, `marketplace`, `query`, `run_id`, `locale` | str | lineage, copied |
| `offer` | `(family, signature)` or `None` | identity of "this product, in whatever pack size", **scoped by marketplace** since v2 |
| `size_label`, `siblings`, `variation` | str / list / dict | Amazon's own pack label and family |
| `quantity` | `Value` | total pack content, in `g` or `ml` |
| `price` | `Value` | what the listing costs |
| `price_per_base` | `Value` | price per kilogram or per litre, following the pack's unit |
| `nutrition` | `{key: Value}` | per 100 g; `{}` for anything that is not food |
| `review_rating` | `Value` | average stars; `trusted` only when the histogram corroborates it and the rating count is not trivially small |
| `review_negative_share` | `Value` | share of all ratings at 1–2★, from the complete histogram — the only review figure entitled to be read as a rate |
| `review_count` | `Value` | how many ratings the average rests on, in `ratings`; `trusted` when the rating block's histogram accounts for every rating, `unverified` on Amazon's word alone. Added 2026-09-18 for a buyer's rating threshold; available to categories as an axis and **not yet in `as_dict()`**, because adding a key moves every committed card digest the two T3 reviews bind — it enters the serialised view with the next contract migration |
| `review_sample` | `Value` | the rendered cards; **never better than `unverified`**, carrying every caveat that limits reading them |
| `record` | dict | the raw record used for category text search; not included by `as_dict()` |

`as_dict()` also omits the raw `variation` matrix and serializes `review_sample`
as its count plus status/evidence, rather than duplicating all review text.

### Listing identity is a marketplace and an ASIN

An ASIN is minted per Amazon site. The same ten characters name different
products on different marketplaces, and where they name the same product it is
a different offer, in another currency, with another delivery region. So the
identity of a listing is the **normalised host plus the ASIN** — `www.` is
stripped, case is folded — and `offer[0]` carries that host: `'amazon.de:B0PARENT01'`.

An empty prefix (`':B0PARENT01'`) means the record did not record a
marketplace. That is its own scope, not membership of any other: the saved-page
corpus extracts with no marketplace in its lineage, so its snapshot shows the
empty form. A record written by the spider always names one.

Two consumers depend on this and both were wrong before v2: feed merging keyed
by ASIN alone discarded a `.de` observation in favour of a `.com` one, and
variation grouping pooled a family across marketplaces. Comparison across
marketplaces remains unsupported regardless — the analysis CLI stops rather
than ranking two currencies together.

`Validated` also exposes `search_reviews(pattern, …)` and
`review_signal(pattern, label, …)`, kept deliberately separate from `search()`,
which walks the *vendor's* words. A producer's claim and a reader's experience
of it are different kinds of evidence, and a hunter that merged them would let
marketing copy corroborate itself.

For vendor claims, `not_claimed` means no accepted match in the selected search
scope, not that the property is false or that every possible source was checked.
Amazon selects which buyer cards to render, so a complaint absent from that
sample is `unknown`.

### `Value`

```python
Value(value, status, unit, evidence=[Evidence(field, quote)], notes=[], source='')
```

`.usable` is true only for `trusted` values with a value. Nothing else may be
ranked on or asserted from.

The status applies to the proposition being checked. A category can mark a
vendor declaration `trusted` because it found attributable text; this does not
independently verify the claimed performance. Likewise, histogram agreement
checks rating consistency, not review authenticity or product quality. Reports
must preserve this distinction and the source attribution. Basmati's optional
composite is a separate category method, not a generic trusted numeric axis;
its ingredients and unknowns must remain visible, and the CLI `rank` does not
sort by that score.

### Attributed text search

Both `search(record, pattern, limit=3, fields=None, *, scope='page',
affirmative=False, exclude=None)` and `Validated.search(pattern, …)` return
`Evidence` quotes in source order, with at most one accepted match per field.
String patterns are case-insensitive; compiled regexes retain their flags.

- `scope='page'` preserves the original discovery search: ingredients, title,
  feature bullets, description, raw attribute rows, important information and
  A+ text. Reviews have their own API. This is the extracted vendor text, not
  every string in the JSON record or original HTML.
- `scope='self'` restricts to `food.ingredients`, `title`, and `raw_tables`.
  These are the conservative sources for what a listing contains. This field
  policy does **not** guarantee that a title or attribute row is accurate or
  mentions only the product being sold.
- `fields` intersects the selected scope. Paths select themselves and their
  descendants (`content.feature_bullets` includes indexed bullets); an empty
  collection selects nothing. An unknown scope raises `ValueError`; a
  nonpositive limit returns no hits.
- `affirmative=True` filters adjacent German/English negating prefixes
  (`nicht`, `non-`, `ohne`, `without`, `free of`, etc.) and `frei`/`free`
  suffixes. It checks the context **outside the matched phrase**, so matching
  `mineralöl` in `mineralölfrei` is rejected, while matching `mineralölfrei`
  or `ohne Mineralöl` affirms the absence claim. Internal negation belongs to
  the meaning of the caller's pattern; arbitrary grammar, double negations,
  comparisons and cross-sell attribution are not resolved.
- `exclude` supplies an optional category-specific regex, such as a drying
  denial containing `trocknet nicht ein`. A candidate is rejected only when
  its span overlaps an exclusion match, not because an unrelated negation
  occurs elsewhere in the quote. Filtering runs against the full source text
  before quote cropping or result limits, and continues to later matches in
  the same field. Rejected matches remain discoverable with default search.

Search returns evidence, never a trust status. Basmati uses `self` and
affirmative matching for milling; mounting paste retains `page` search for
claims in prose, with category exclusions and kit caveats. A page match alone
does not resolve which product a claim concerns.

External laboratory attribution stays in the basmati category. The known
product-line match must also have a literal whole-brand match in the brand
or manufacturer field to receive its existing `trusted` status. Those fields
are included as evidence. A title-only match stays `unverified`; even matching
metadata does not prove that the listing's batch or pack was the tested one.

R7 adds these opt-in search controls within contract v1; the serialized
validated record and extraction schema are unchanged.

### Status vocabulary

| Status | Meaning |
|---|---|
| `trusted` | survived every check that applies to it |
| `disputed` | sources on the page contradict each other, or a check failed — shown with the contradiction, never ranked |
| `unverified` | nothing contradicts it, nothing independent confirms it |
| `unknown` | we do not know; distinct from "the page does not say" |
| `not_claimed` | no accepted claim in the caller's search scope — which is not the same as it being untrue |

### Source vocabulary

| Source | Meaning |
|---|---|
| `structured` | a structure Amazon renders as data: the nutrition card, the twister matrix |
| `attributes` | a row of a product-detail key/value table, filed by the vendor |
| `text` | prose: the title, a bullet, the description, A+ copy |
| `published` | a figure Amazon computed and published, e.g. its own price per unit |
| `derived` | computed here, from other values on the same record |

**A source never implies a status.** The nearest thing to an exception is
`derived`, and it is not one: a derived value is exactly as good as its
inputs, so whether it can be trusted depends on whether *they* were
validated. `price_per_base` is derived from price and pack size, and is
trusted when the pack size was confirmed by an independent statement on the
page. A derived *nutrient* — kcal computed from kJ — is a unit conversion of a
single unchecked number, adds no evidence about it, and is never promoted.

`Evidence.field` carries the precise origin; `source` is the coarse kind.

---

## 4. What the generic rules check

Each fires only where its evidence exists. A record with no food block pays
nothing for the nutrition rules.

**Pack quantity** — the attribute total against every *independent* statement
of it on the page: the variation matrix's size dimension, the title, the
pack-size name. A count is only ever combined with a weight stated in the
same string; multiplying a title's pack count by the attribute table's item
weight is circular, because whether that weight is per item or per pack is the
question under dispute. A bare, uncounted weight in the listing's own text may
**confirm** a total and may never contradict one.

**Price per base unit** — derived from price and pack size, cross-checked
against Amazon's own published per-unit figure. The published figure is
converted onto the pack's own dimension (`kg`, `100 g`, `l`, `ml`, `100 ml`)
and **refused** when it counts pieces rather than content, or when converting
it would need a density nobody published.

**Nutrition** — a unit that cannot measure the field it populated; a number
lifted out of the "per 100 g" phrase that describes the basis; macronutrients
summing to more than the food they sit in; energy disagreeing with the
macronutrients it is computed from (Atwater, 35% tolerance); and a declaration
carrying a single nutrient, which has nothing on the page to confirm it.

**Variation** — family identity and the pack-size dimension, looked up by
Amazon's own dimension names, never inferred.

---

**Added 2026-09-17, within the version.** Two more places a single-unit
weight may be *confirmed* from, both asymmetric like the bullet rule above:
the extractor reads the weight Amazon.de appends to the dimensions row when the
page has no Artikelgewicht row at all (`package.item_weight_origin =
"dimensions"`; a present but unparsed Artikelgewicht row keeps its own text),
and A+ copy joins the bullets and the description as text whose bare weight may
confirm an attribute total and never contradict or supply one. Measured: zero
change on the 39 corpus pages; on 43 school-backpack records, usable weights
went from 3 to 10.

## 5. What a category supplies, and what it may not

A category hands the generic layer a `CategoryProfile`, which is **data only**:

```python
CategoryProfile(
    key='dry_pasta',
    label='dry pasta',
    nutrition_bands={'protein_g': (4.0, 30.0), ...},   # per 100 g
    price_band=(0.80, 40.00),                          # per kg or per litre
)
```

A profile cannot add a rule, reorder the pipeline, or set a status. That is
deliberate, and it is the part of R2 that took the longest to get right,
because the ordering is not obvious:

```text
detect  →  category bands  →  resolve contradictions  →  promote
```

A generic check can prove that an energy figure and its own macronutrients
contradict each other, but not which side is wrong; a plausibility band can
say which value is impossible, but only for a named category. So the bands run
in the middle, and **nothing is promoted to `trusted` until both have
spoken**. While this sequence lived inside the pasta module, the pasta module
*was* the specification, and a second category would have had to copy four
lines of ordering it had no way to know were load-bearing.

`price_band=None` is a legitimate answer, not a gap. Tyre mounting paste
spans 50 ml tubes and 5 kg workshop tubs priced two orders of magnitude apart
per kilogram; inventing a band to have one would reject real listings.

A category analyzer then adds what only it can know — what the product *is*,
which of the vendor's statements matter, and which direction is better — and
returns a card. `tests/test_mounting_paste.py` asserts mechanically that it
imports no rule and settles no numeric value of its own.

A card key a category adds beyond the common shape — basmati's cultivar,
grain type, external test, review signals and score — is **declared** in
`Category.extras`, and that declaration is what publishes it in
`card --json`. It is a rendering statement rather than a contract change: the
values themselves are `Value`s that serialise as they always did, and until
T2 the JSON view named two such keys by hand and silently dropped basmati's
six. A key a category adds and does not declare is not published.

Since R16 a category also declares a **`Lifecycle`**, and cannot register
without one. Like the profile it is data and never procedure: the state the
capability has earned (`experiment`, `maintained`, `foundation`, `retired`),
the last keep/promote/reject/retire decision with its date and responsible
role, an `Applicability` — the marketplaces it was measured on, what the
classifier accepts, and what it declines with the committed case ASINs that
prove it — the evidence paths and roadmap anchors behind it, the last review,
and a **method version**. The declaration changes no value, no status and no
decision; `study capabilities` publishes it and the maintenance gate pins the
state, decision and method version in its baseline, so a change to any of
them is a reviewed diff whose reason is a dated ROADMAP entry. The method
version follows the spirit of §6: it moves when a change moves a decision on
the category's committed cases — a classifier boundary, an axis direction,
what a claim means — and stays when a pattern merely reaches more phrasings
of the same statement. No study manifest records it yet; binding the method
that produced a study into its bundle is R15's.

---

## 6. Compatibility policy

### Within a version

May change without a bump, because no correct consumer can depend on it:

- adding a key to the record or to `Validated`;
- adding a `status`- or `source`-bearing value to a group that already exists;
- the **wording** of a `note`, and the span of an evidence `quote`;
- which `Evidence` entries accompany a value, and their order;
- a value moving to a *more* conservative status (`trusted` → `unverified` →
  `disputed`/`unknown`) because a new rule found something.

### Requires a version bump

- removing or renaming a key, a `status` value or a `source` value;
- changing the unit or scale of a published number;
- changing what a `status` *means*;
- a value moving to a *less* conservative status by default — that is a claim
  about trustworthiness, and it has to be argued for and measured.

### How a bump is done

1. Change the code and bump `SCHEMA_VERSION` (`extraction/pdp.py`) or
   `CONTRACT_VERSION` (`validation/contract.py`).
2. Add a line to §7 saying what moved and why.
3. Regenerate the corpus snapshots and **read the diff**:
   ```bash
   uv run python tests/test_corpus.py --update
   ```
   `tests/corpus/` pins both artefacts over 39 saved real pages —
   `expected.jsonl.gz` for extraction and `validated.jsonl.gz` for the
   contract, the latter deliberately produced with *no* category profile, so
   what is pinned is the layer that belongs to nobody.
4. Records already on disk keep their own `schema_version`. The validation
   layer reads v2 and v3 records unchanged; older records simply carry fields
   it ignores.
5. Re-record the [maintenance gate](AGENTS.md#environment-and-checks) baseline
   in the same change: it pins every published version listed in §7 and the
   T3 audit contracts below, and it fails on a number that moved without this
   procedure. That is the point of it — a bump is a statement about meaning,
   and an unremarked one is the failure this section exists to prevent.

---

## 7. Version history

| Version | Change |
|---|---|
| schema v1 | the original rich PDP record |
| schema v2 | crawl provenance: `run_id`, `locale`, `accept_language` (R1) |
| schema v3 | `variation`: the twister matrix, decoded verbatim (R1) |
| **schema v4** | removed `food.nutrition.confidence`; `package.total_quantity_unit` now follows the row the total came from (R2) |
| **schema v5** | added `reviews`: the complete ratings histogram and the sample of cards the PDP renders (R5). **Purely additive** — every schema-4 field keeps its name and meaning, and the corpus regression diff touched only `reviews.*` and `extraction.blocks_present` |
| **schema v6** | `price.range`, and `price.amount` is no longer filled from one end of a price range. A variation parent with no size selected renders "5,63€ - 26,15€" in its own price container; the extractor published 5,63 EUR as the price of a listing that cost 9,98. Additive for every record that has a price; the 7 records in the mounting-paste sets that had a *fabricated* one now correctly have none |
| schema v6, additive (2026-09-18, R15's third adaptation) | `content.aplus.prose` and `content.aplus.comparison`. An A+ comparison table compares this product with others, and its cells were flattened into `content.aplus.text`, which the vendor-text search reads as this product's statement: on a retained Instinct 3 50 mm page the card showed a 40 h GPS runtime belonging to the 45 mm in a table that does not contain the 50 mm at all. `text` is unchanged; the search now reads `prose` where a record has it and the own column's rows, labelled, where the header links the page's ASIN. Records without the keys read exactly as before, so the six committed studies and the 39-page corpus values are untouched |
| **contract v1** | first published validated record (R2); extended in R5 with `review_rating`, `review_negative_share` and `review_sample`, which add fields without changing any existing one. A `price.range` reads as `unknown` with the range as its evidence — it adds no field to the validated record, because "we do not know" was already expressible |
| **contract v2** | `offer` is scoped by marketplace (T1). The field keeps its shape — a family identity and a variant signature — but the identity is no longer a bare parent ASIN, which is only unique within one Amazon site. That is a change in what a published value *means*, so it is a bump rather than an addition. The corpus regression diff touched exactly two fields on the 39 saved pages: `contract_version` on all of them, and `offer[0]` on the 27 that carry a family, which gain the (empty, because the corpus records no marketplace) host prefix. No status, value, source or note moved |

---

## 8. What the second category changed

R2's premise was that a rule earns promotion once a *second* consumer has
exercised it. The second consumer is tyre mounting paste: a non-food, with no
nutrition, sold in tubs, tubes, bottles and aerosols, classified from its
title because Amazon files it under four unrelated departments, and ranked on
*smallest pack first* — the opposite of what dry pasta wants. 90 records,
three Amazon.de queries, 93 requests, 93 × HTTP 200, 0 retries, 0 challenges.

**Every trust rule transferred unchanged.** Nothing in the quantity, price or
variation logic needed to know what the product was. What did change:

1. **Price per unit was hard-wired to kilograms.** Every pack in the dry-pasta
   set is a mass, so nothing had ever asked. A third of the paste listings are
   priced per litre by Amazon, and the layer ignored those figures entirely
   rather than converting them. Now the base unit follows the pack, Amazon's
   published unit price is converted onto it, and a per-*piece* figure is
   refused rather than misread — which is the error that once showed a Barilla
   listing at €38.56/kg.

2. **An extraction bug surfaced.** `total_quantity_unit` was inferred from any
   volume field on the page rather than from the row the total came from, so a
   50 ml tin filed as `Anzahl der Einheiten: 50.0 milliliter` was reported as
   50 g. 16 of 90 paste records are affected; 1 of 39 corpus pages changed,
   and that one — a 5 L olive-oil canister filed as 5 kg — loses a per-litre
   figure that had been `trusted` on the strength of the old guess. It is now
   an unverified price per kilogram with a note saying the two cannot be
   reconciled without a density. That is the honest reading.

3. **A confidently wrong nutrition value was one step away.** German *Fett*
   means grease as well as fat, so four listings here state a pack size beside
   the word and the food parser reads a nutrition declaration: `Fett wird in
   einer 100 g Tube geliefert` → 100 g of fat per 100 g. Two of the four state
   "100 g" close enough to satisfy the per-100 g basis test, so nothing in the
   generic layer stopped them — dry pasta was protected only by having a
   plausibility band. The rule that was missing is category-neutral: **a
   declaration carrying one nutrient has nothing on the page to confirm it, so
   it can be shown but never trusted.** Thirteen lone-nutrient blocks exist
   across the two validation sets and all thirteen are artefacts of matching a
   word — nine in dry pasta, six of those reporting 100 g of protein per 100 g
   and one reporting 534.

4. **Pack quantity could barely be confirmed at all.** The hint parser only
   understood multipack phrasing — "6 × 500 g", "500 g (5er Pack)" — which
   this category does not use. It writes "Reifenmontagepaste 5 kg" and means
   it. 2 of 43 pastes had a confirmable pack size. The rule added is narrow
   and asymmetric: when nothing anywhere on the page claims more than one
   unit, a bare weight in the listing's own text is an independent statement
   of the same quantity and may **confirm** the attribute total — never
   contradict it, because the weight may still be per unit or a kit's shipping
   weight. On dry pasta it moves 23 records from `unverified` to `trusted` and
   leaves every `disputed` and every `unknown` exactly as it was.

### Measured, both categories, after R2

| | dry pasta (195 records) | tyre mounting paste (90 records) |
|---|---|---|
| Classified | 165 / 30 other / 0 unclassified | 43 / 47 other / 0 unclassified |
| Pack quantity | 131 trusted · 13 disputed · 14 unverified · 7 unknown | 25 trusted · 1 disputed · 6 unverified · 11 unknown |
| Price per base unit | 100 trusted · 9 disputed · 2 unverified · 54 unknown | 13 trusted · 1 disputed · 1 unverified · 28 unknown |
| At least one trusted axis | 117 of 165 | 32 of 43 |

Effect of R2 on dry pasta, same records, same code path:

| | before | after |
|---|---:|---:|
| Pack quantity trusted | 108 | **131** |
| Pack quantity unverified | 37 | **14** |
| Pack quantity disputed / unknown | 13 / 7 | 13 / 7 *(identical)* |
| Price per base unit | 100 trusted | 100 trusted *(identical)* |
| Protein trusted | 61 | 60 |

The one lost protein figure is `B0D4R3N142`, a lupin-flour pasta whose only
nutrition value is `"Protein und 9g"` scraped out of marketing copy — a
figure that is implausibly *low* for the product it describes.

## 8. Study audit contracts (T3)

R13 stage 3 separates the three version constants in `study/audit.py`:
`LEDGER_VERSION` governs `ledger_version`, `AUDIT_VERSION` governs
`audit_version` in the claim index and validation result, and `REVIEW_VERSION`
governs `review_version`. All remain **1**. The maintenance gate tracks them
independently as `evidence_ledger`, `study_audit` and `semantic_review`.
This separation changes no artifact bytes, study identity or review binding.

Study manifests write **v3** since R13 stage 10 (§14); v2 was T3's, adding
`ledger.json`, `claim-index.json`, `validation.json`, and `semantic-review.json`,
and v3 records each artifact's review binding beside its digest. V1 and v2
bundles remain historical artifacts; this build refuses to verify them. Re-run
their original brief and pinned feeds into a new directory. Brief v1, extraction
schema v6 and generic validation contract v2 are unchanged.

The external ledger is **v1**. Its executable schema is
`shopping_advisor/study/audit.py:check_ledger`; a complete JSON example is
`tests/studies/t3/evidence.json`. Each observation has a unique ID, source ID,
class, publisher, title, URL, publication/retrieval dates, locator, claim,
excerpt, original units, quotation/interpretation distinction, verification,
product identity, matching status, applicability limits, conflicts and
supersession links. Unknown legacy dates/identity/URLs remain empty, not inferred.
Verified sources require ISO dates and a URL/locator. A snapshot either embeds
permitted UTF-8 text and its SHA-256 or declares unavailability and a reason.
The digest covers the retained text, not an unavailable original document.

Indexed external claims reference an observation and declare their scope:
`historical`, `current_batch`, `vendor_declaration`, `review_sample`, or
`access_limit`. Their statement must equal the recorded source claim (or access
limit). A listing reference is `marketplace:ASIN`; identity matches use JSON
Pointers into the selected feed record. Brand, model, variant and geography
must match exactly and be known; current-batch claims additionally require the
batch, a reference date at or after publication, independent evidence, and no
conflicts or supersession. This conservative matching may refuse usable evidence
that requires interpretation; a semantic reviewer cannot override a failed
check by approving prose. Record uncertainty or historical scope instead.

Source verification is an operator assertion, distinct from generic `trusted`.
Digest and matching checks cannot prove semantic truth. Vendor text supports
an attributed declaration; buyer samples support sampled experiences, never
population rates. Secondary reports cannot be promoted to primary tests.
Unverified or unavailable sources support access-limit claims only. Historical
findings without listing claims need no guessed listing match.

The claim index records the adopted single-axis method, decision/card references,
computation names and pinned feed references. Full replay checks ranking,
eligibility, grouping, numeric claims, every serialized card/score and exact
report rendering. No arbitrary hand-written additions are validated. Freshness
violations or unknown age explicitly label the report historical/incomplete.
Basmati's score is published for inspection; **it does not order the shortlist**,
and external claims do not silently change the adopted price ranking.

The semantic review is **v2** since R13 stage 10 (§14) and separately binds the
report and the evidence/decision artifact digests the inventory marks `semantic`.
Ledger content also participates in the study ID. It records reviewer, citation
support, variant applicability, user priorities, coverage/limits, conclusion
presentation, findings for each check and unresolved limits. `pending` is not
approval. `validate-report --require-review` requires a complete passing review;
plain `verify` checks replay without claiming semantic approval.

**Basmati method v2:** three former executable test constants move to
`shopping_advisor/evidence/basmati-legacy.json` as `legacy_unverified`, with
explicit missing citations/snapshot and unresolved applicability. `external:`
evidence fields resolve to these ledger observation IDs. None earns laboratory
score credit. The health component starts neutral (0.5), without unsupported
milling/origin/vendor-safety bonuses; existing adverse review adjustments remain
category heuristics. Missing verified external evidence remains a reported score
gap. This is a conservative trust correction and versioned category method,
not a change to generic status meanings. See the measured T3 result in ROADMAP.

## 9. Intake plan and brief preservation (R13 stage 5)

**Plan v1** is defined by `study/intake.py:check` and tracked as `intake_plan`
by the maintenance gate. It is JSON data with closed fields and no executable
expressions, imports or provider-specific state. A plan may name an unregistered
category key and may exist before feeds. A brief still requires a registered
category and readable inputs. Complete sanitized examples are
[supported-plan.json](tests/intake/supported-plan.json) and
[unsupported-plan.json](tests/intake/unsupported-plan.json).

| Plan part | Contract |
|---|---|
| Identity and scope | Slug `id`, positive integer `revision`, `supersedes` canonical digest for later revisions; question, use case, category key, marketplace and delivery region. Unresolved geography may be empty in a plan. |
| `user_evidence` | Conversation locator and start boundary, missing context, `selection = all_user_messages`, and user-authored messages with unique IDs. Capture the whole stated user exchange, including corrections and messages not mapped to a requirement. Tool/source text is not user authority. |
| Redactions | Each message records removed content by description/reason and a `limits_review` flag. Removed wording cannot be presented as retained supporting wording. |
| `sources` | Distinct IDs, locators and retained text for cited-source provenance; these are untrusted data, not verified external findings. |
| Requirements | Unique ID, statement, role (`hard_constraint`, `preference`, `objective`, `context`), operative/decisive flags and independent settlement (`stated`, `delegated`, `assumed`, `unresolved`). Hard constraints remain decisive when assumed; only context may be non-operative. |
| Provenance | Author (`user`, `cited_source`, `agent`), wording and references, basis (`user_statement`, `source`, `hypothesis`, `reasonableness`), applicability, rationale and if-wrong consequence. User/source quotations must occur in referenced retained text. Resolved delegation requires a user reference. |
| Assessment | Path (`control`, `evidence_review`, `unsupported`, `revised`, `withdrawn`, or `not_applicable` for non-operative context); state (`not_assessed`, `supported`, `failed`, `unknown`); resolved controls, evidence/review digest references, gap or authorized change. Resolving a control does not make evidence assessed. |
| Controls | Full resolver results, rechecked against the live category interface. Changed metadata refuses and requires reassessment. No narrative field is a control. |
| Gaps and changes | Unsupported paths require a kind, reason and next step. Revision/withdrawal requires retained user authority and a reason; revisions name a retained replacement and cannot form cycles. Gap kinds are open text, not a capability index. |
| Priorities and effects | Preferences/objectives have positive priorities (lower first); ties require a stated tradeoff. Operative requirements name affected stages and consequences. This records intent; it does not implement tradeoffs or acquisition rules. |
| Questions | Uncertainty, expected effect, affected requirement IDs and retained answer-message IDs. These are prospective records, not an automatic questionnaire. |
| Read-back | Exact deterministic rendering of the plan revision, kept separately from response status: `not_presented`, `no_response`, `confirmed`, `delegated`, `corrected`. Answered statuses require retained message references and scope. Rendering from an unregistered-category plan is supported. |

The brief's optional **`intake` binding** contains plan version/ID/revision,
canonical content SHA-256 and a lossless copy of the requirements. It is additive
within brief v1 and absent from legacy serialization; older source-brief parsers
reject the new field. Pre-stage-5 verifiers read manifest v2 and are not
intake-aware; since stage 10 a bundle is v3 and such a verifier refuses it rather
than passing a plan-backed study it cannot gate.
At the transition, every requirement's
meaning, role, settlement, provenance, assessment and effects must match exactly,
including withdrawals. Scope fields must also match. The executable brief must
implement all active mapped claim filters, selected axis, unit, cap and axis
bounds, and cannot introduce an unrecorded claim filter, cap or bound. Explicit axis selection cannot
silently become category-default attribution.

`analyse(brief, plan=...)`, `run(..., plan=...)` and `study check --plan` consume
this boundary. A bound brief without its plan refuses, as does a plan supplied
without a brief binding. Refusal precedes analysis and, in `run`, input digest
reads and replacement of an existing output. No confirmation ritual is required:
settled instructions and assumptions may proceed without a read-back response.
Unreconciled corrections and unresolved decisive requirements refuse. A settled
decisive requirement without an executable control crosses this bridge into
**bounded execution** under [§10](#10-stage-gates-r13-stage-6): the analysis
runs, the recommendation is withheld, and the brief still may not carry a filter,
cap or ordering that no active requirement maps to.

**Retention decision:** private working plans live under `data/plans/` or an
explicit private location, with revisions and dependencies durably archived even
when no study results. Gitignored storage is not a backup. A plan-backed study
must carry `intake-plan.json` internally, digest-listed in its manifest, checked
against `brief.intake` and consumed during replay. The original working plan is
not needed to verify the study. Sanitized committed examples have a separate
allowlist under `tests/intake/`.

The snapshot entered as an optional addition to manifest v2 and is a
`semantic`-bound artifact under v3 (§14). The brief binding pins the plan's
canonical digest into the study id, and that binding is the identity projection
INTAKE §8 asked for — decided in stage 10, with the reason in §14 — but it **does
not constitute intake semantic approval**; that is §13's artifact. New bound
briefs naturally have new source digests; the study-ID algorithm is unchanged in
shape.

Structural preservation is not faithful language interpretation or semantic
adequacy. Completeness of capture, whether wording authorizes a change, the truth
and applicability of evidence/review references, and whether a control answers a
requirement still need review. Stage 5 does not enforce assessment outcomes or
acquisition effects; stage 6 consumes them at the conclusion (§10). Delivery
freshness, session budgets and review invalidation are later stages in
[INTAKE §16](INTAKE.md#16-implementation-sequence).

## 10. Stage gates (R13 stage 6)

**Stage gates v1** are `study/gates.py`, tracked as `stage_gates` by the
maintenance gate. They run inside `analyse(brief, plan=...)` for a plan-backed
study only and read the plan's recorded semantics — role, decisiveness,
settlement, assessment path and state, stage effects — and the brief's declared
axis. They read no narrative field and no marketplace content. Without a plan
they do not run: `gates` is `null`, `stop` is empty, and every legacy artifact is
byte-identical. Two committed plan-backed examples,
[delivered-cost](tests/intake/delivered-cost-plan.json) and
[purchase budget](tests/intake/budget-plan.json), are replayed by the gate.

| Gate | Decides | Output |
|---|---|---|
| **Intake** | Whether dependent work may proceed and which next action is justified. Reads the plan alone, before a category module or feed exists. | `readiness`: `blocked` (a decisive requirement is unresolved, or a correction is unreconciled), `bounded` (a decisive requirement restricts the conclusion) or `full_request`; `next_action` text; one row per requirement with its disposition, routing and per-stage effect status. |
| **Comparison support** | Whether the declared axis answers every decisive preference and objective. | The axis with its source; `answers`; `unanswered` with reasons; `refused = substitution` when any decisive preference or objective is not enforced; the `bounded_question` the axis does answer. |
| **Conclusion** | Whether the full request supports a recommendation, a tie, a bounded finding or a refusal. | `stop`, `statement`, `permits`, `withheld` ids, the `analytical_outcome` kept separately, and a `diagnosis` for an insufficient-evidence outcome under a fully enforced plan. |

**Dispositions**, one per active requirement, derived from the assessment path:
`enforced` (`control`), `assessed` (`evidence_review` with an outcome state),
`awaiting_evidence` (`evidence_review`, `not_assessed`), `unsupported`
(`unsupported`), `non_operative` (`not_applicable`) and `inactive` (`withdrawn`,
`revised`). **Routing** follows INTAKE §3: `execute`, `collect_or_stop` for an
awaiting assessment, `gap_plan` for an unsupported one. A decisive requirement
**restricts the conclusion** unless it is enforced, or it is an enforced or
assessed hard constraint whose state is `failed`. A non-decisive requirement
restricts nothing, whatever its disposition. **Stage effects** are reported per
declared stage: `enforced` where the resolved control takes effect
(`candidate_filter` and `ranked_row_filter` at candidate assessment, `ranking` at
comparison), the requirement's disposition at the other stages this offline
study performs (candidate assessment, comparison, conclusion), and `recorded`
with a note at every stage it does not perform (intake, probe, discovery,
collection, delivery, revision). Recorded is not executed and is not claimed.

**Stops** are a vocabulary separate from the three analytical outcomes and do
not map onto them:

| `stop` | Condition | Headline | Presentation |
|---|---|---|---|
| `requirement_failed` | A decisive hard constraint's bound assessment state is `failed` | **Requirement cannot be met.** | No candidate put forward; bounded observations under their own heading |
| `requirement_unsupported` | A decisive requirement is `unsupported` or `assessed` (a reviewed finding supports a scoped explanation, not selection) | **Recommendation withheld.** | As above; the statement names each requirement, its reason and its next step, and says "a gap plan, not an evidence finding" |
| `requirement_unassessed` | A decisive requirement is `awaiting_evidence` | **Recommendation withheld.** | As above; the statement says the method exists and this is not a capability gap |
| empty | Every decisive requirement is enforced | The analytical outcome's headline | Unchanged from a plan-less study |

Precedence is failed, then unsupported, then unassessed; `withheld` lists every
restricting requirement. Under any stop `shortlist` is empty, no candidate is
`shortlisted`, ranked rows stay `ranked`, and `permits` is `bounded_finding`. The
analytical `outcome` is computed and persisted unchanged, and the report renders
it under `## Bounded finding: <axis label> only`, which states the narrower
question it answers, names the requirements it leaves unenforced and unanswered,
and says it is not a recommendation. The `## Result` slot reads "No candidate is
put forward." followed by the withheld requirements. An insufficient-evidence
outcome under a stop renders no table. Placement and wording are tested, not only
the fields.

**Report inputs.** A plan-backed report gains `## Requirements and their
dispositions`: plan id, revision and digest; the read-back **attribution
sentence**, a function of the retained response status alone (`not_presented`
and `no_response` state that nothing is described as user-confirmed; `confirmed`
and `delegated` name the scope and message ids and say what they do not waive);
readiness and next action; the requirement table with role, settlement, author,
disposition and whether it restricts the conclusion; stage effects; and the
comparison-support sentence. The reproduction block adds `--plan`.

**Persistence.** `ranking.json` gains `stop` and `gates` for a plan-backed study
only, `manifest.json` gains `stop` and `permits`, and `verify` recomputes and
compares both; a plan-backed bundle without a `gates` block predates this stage
and is reported as `stage_gates_missing`. The study-id algorithm is unchanged;
`gates` is a function of the plan digest and brief already pinned. `stage_gates`
follows the version rules in §6: a change to what a disposition, routing or stop
means is a bump; a rendering change alone is not.

**Limits.** The gates enforce what the plan recorded. They cannot detect a
requirement the plan never captured, a decisive requirement recorded as
non-decisive, or a control that runs correctly and answers the wrong question —
a purchase budget mapped onto the per-kilogram cap passes as `enforced`, and the
report says beside the table that enforced does not mean adequate. Those are
the intake review (§13) and the semantic-execution question of INTAKE
§12. The gates do not apply discovery or acquisition effects, account for
session resources (§12) or invalidate reviews (§14 binds those). Delivery
freshness is §11.

## 11. Declared scope and the delivery record (R13 stage 7)

**Two references, two questions.** `analyse()` measures every observation
against the brief's `as_of` and answers the historical question: how old was
the evidence relative to the date the study is about. That block is computed on
an author-chosen date and blocks nothing, by design — INTAKE §1 measured it. The
**delivery record** answers the other question, whether the observations are
recent enough for advice issued *now*, against a reference the brief's author
does not supply. Nothing in the analysis, `ranking.json`, the report bytes or
`study_id` changes when a study is delivered; the record is integrity-bound, not
identity-bearing (INTAKE §8).

**Declared scope.** `freshness.scope` in the brief is `historical` or
`current_advice`. **Absent means historical**: nobody claimed the study was
current, and fresh dates do not turn a regression fixture into buying evidence.
The four legacy examples are historical on that reading with their bytes and ids
unchanged; the key is additive within brief v1 and persisted in `brief.json` only
when declared, so review-bound bytes do not move. `current_advice` requires
`as_of`, `price_max_age_days` and a non-empty `note` stating why that age bound
is adequate; the brief refuses otherwise. The manifest records `scope` and
`scope_source` (`brief` or `undeclared`). A declared scope adds a `Scope` header
row and a scope paragraph in the report's freshness section; a current-advice
report says of itself that without a passing delivery record it is a historical
comparison as of `as_of`.

**The delivery event.** `study deliver BUNDLE [--reference ISO]` verifies the
bundle, reads the execution clock in UTC — or a declared instant, which it
records as declared — and appends one event to `delivery.json`, digest-listed in
the manifest. **Delivery record v1** is `study/delivery.py`, tracked as
`delivery_record`:

| Field | Meaning |
|---|---|
| `reference`, `reference_source`, `reference_as_supplied`, `time_zone` | The frozen instant, normalised to UTC seconds; `execution_clock` or `declared`; a reference without an explicit offset is refused |
| `study_id`, `report_sha256` | What was delivered; the record belongs to exactly those report bytes |
| `scope`, `scope_source`, `as_of`, `price_max_age_days`, `rationale` | The declaration and policy the event was assessed under |
| `analytical_outcome`, `stop` | Copied from the analysis, never re-decided |
| `governed` | The `shortlisted` and `ranked` candidates — decisive comparison inputs, including a bounded finding's rows — each with its age in whole UTC days at the reference and a `stale` flag. Excluded, folded, over-budget and off-category records are not governed |
| `counts`, `blockers`, `current_advice`, `statement`, `limits` | `permitted`, `blocked` or `not_in_scope`, with every reason |

Under `current_advice` scope the event is **blocked** by any of: no age policy; a
reference that precedes `as_of`; a governed observation older than the policy at
the reference; a governed observation undated or dated after the reference
(unknown is not current); a withheld recommendation (stage 6 stop). Otherwise it
is **permitted for that event** — a later delivery is a new assessment. Under
`historical` scope every event is `not_in_scope`: staleness at the reference is
recorded, nothing is blocked, and the statement names the reference date it was
delivered as history at.

**Structural, not waivable.** `validate-report` reports the latest event and,
for a current-advice study, fails with `delivery_missing` when no record exists
and `current_advice_blocked` when the latest event is not permitted — whether or
not `--require-review` is passed and whatever a completed semantic review says.
`verify` recomputes every event from its own frozen reference and this bundle's
persisted data and reports `delivery_invalid` when an event does not re-derive or
belongs to different report bytes. Replay never reads the clock, so the
maintenance gate replays every example with a fixed `deliver_at` and fails with a
change, not with the passage of time.

**Limits.** The execution clock is not a trusted time service: the record
prevents silent backdating inside the declared workflow and does not prove a
supplied reference true; every event says where its reference came from. Session
consumption and interruption facts travel beside it in the bundle's session
snapshot (§12) rather than inside the event; both are bound, per event, into the
delivery review of §14, and the declared scope is a declaration — a brief that
calls frozen fixture evidence current advice has made a false declaration the
software cannot detect, and the delivery review can only record who vouched for it.

## 12. Session resource ledger and resumption (R13 stage 8)

**Session ledger v1** is `study/session.py`, tracked as `session_ledger`. It is
JSON data with closed fields: `session_version`, slug `id`, `revision` with the
previous ledger's canonical `supersedes` digest for a later revision (an
extension is an explicit budget revision), an optional `plan` binding (`id`,
`revision`, canonical `sha256`), `limits` and `actions`. It is a record and a
check, not a scheduler or a command runner: nothing in it runs, and `resume`
writes nothing. A private working ledger lives under `data/sessions/` or an
explicit private path; a study run with `--session` snapshots it as
`session.json`, digest-listed in the manifest with `manifest.session` naming its
id, revision and digest. The sanitized example is
[session-ledger.json](tests/intake/session-ledger.json).

| Limit field | Contract |
|---|---|
| `kind` | `research` or `engineering`. A research allowance does not fund engineering and an engineering allowance does not fund research; an action may reference limits of its own kind only. A purchase budget is a different quantity and is not a limit |
| `unit`, `measurement` | An **observed** unit the run manifest reports — `requests` (`downloader/request_count`), `responses` (`downloader/response_count`), `items` (`item_scraped_count`), `seconds` (`elapsed_time_seconds`, or the manifest's own `finished_at` − `started_at` when a closed manifest lacks the stat), `pages_retained` (`counts.pages_saved`), `runs` (one per manifest) — or an **estimate** (`eur`, `tokens`) whose `note` says how it is estimated. Acquisition units are whole numbers |
| `amount`, `mode` | Finite, non-negative. `stops_new_work` refuses the next action once the remainder is short; `strict_ceiling` is permitted only for `responses`, `items` and `seconds`, which `CLOSESPIDER_PAGECOUNT`, `CLOSESPIDER_ITEMCOUNT` and `CLOSESPIDER_TIMEOUT` can close on, and its `note` must state the known overshoot. Reconciliation names the overshoot beside the limit: a page-count closure does not cancel requests in flight, an item cap is not a request cap, a timeout may leave requests in flight. No mechanism enforces a ceiling on requests, runs, retained pages or an estimate, and none is promised |
| `scope`, `authorization`, `deadline` | What the limit covers; `source` (`user_message` with a retained message `ref`, `existing_authorization`, `operator`) and text; an optional ISO instant with offset. A deadline is wall-clock: time elapsed during an interruption counts |

| Action field | Contract |
|---|---|
| `kind`, `purpose`, `question` | `inspection`, `probe`, `collection`, `analysis` or `engineering`. A probe states its question. Inspection and analysis touch nothing live: they may not allocate acquisition units or link a run. A probe or collection allocates a finite, positive amount in an acquisition unit. Collection requires the ledger to name its plan: it is only what a brief declares |
| `limit_ids`, `allocation` | Every allocated unit names a declared limit of the action's kind in that unit |
| `state`, `authorisation` | `planned`, `authorised`, `running`, `completed`, `interrupted`, `abandoned`. Beyond `planned` an action says whether the check ran (`checked`) or not (`unchecked`); a run that happened without the check is recorded honestly as unchecked, never refused |
| `consumption`, `consumption_source` | Recorded only when completed or interrupted, for every allocated unit, `null` where unknown; from `run_manifest`, `declared`, `assumed_allocation` (the whole allocation counted as spent — the conservative record for a run that left no readable count) or `unknown` |
| `run_id`, `run_manifest`, timestamps | The crawl the action was, linked by manifest path and digest; a finished action records when it started |
| `resumes`, `replay_of`, `depends_on` | A resumption is a new record continuing an `interrupted` action of the same kind; the predecessor's consumption is counted once, on the predecessor. A replay recomputes retained bytes and is analysis or inspection, never acquisition. Dependencies name retained actions |
| `result`, `promotion` | A completed probe records the result that determines the next action, and whether its evidence was **promoted** into the declared inputs (`into = plan_inputs`, explicit), whether seeing it **changed the criteria** or **supplied candidates**, and — when any of those is true — an assessment of whether broader discovery or renewed comparison is needed. Provenance alone does not establish an unbiased comparison |
| Engineering | Retained as a proposal against the engineering allowance: state `planned` or `abandoned` only, never authorised, recorded or executed here. Controlled execution is R15 |

**Reconciliation** (`session-check`, `reconcile()`) computes per limit the
consumed total over finished actions, the reserved total over authorised and
running allocations, and the remainder; a finished action with unknown
consumption in that unit leaves the limit **unreconciled** with the action named,
and unknown is never read as zero. It lists interrupted actions as interrupted,
never complete; the planned actions the remainder **prevents**, each with its
reasons; and the engineering proposals. It writes nothing: an exhaustion stop
deletes no record and completed evidence stands.

**The next-action check** (`session-authorise`, `authorise()`) permits a
`planned` action only when it is not engineering, every dependency is
`completed`, no referenced limit is unreconciled or past its deadline at the
given reference, and every allocated unit fits the remainder. Every refusal names
its reason with the arithmetic. `--record` marks a fitting action `authorised`
and `checked`; it runs nothing. `session-record` writes what an action did: from
a run directory it reads the manifest's `run_id`, timestamps, `stats` and
`counts`, links the manifest by digest, and sets `completed` or `interrupted`
from the manifest's own state; without a run the operator declares consumption or
assumes the allocation. A finished action is never recorded twice. `seconds` is
read from `stats.elapsed_time_seconds` and, when a closed manifest lacks it, from
the difference of the manifest's own `finished_at` and `started_at`, with
`consumption_source` still `run_manifest`: the run stamped both instants itself.
The spider writes the manifest on `engine_stopped`, after CoreStats has written
the closing stats; a manifest written before 2026-09-17 was snapshotted on
`spider_closed` ahead of CoreStats and lacks `elapsed_time_seconds`, which is
what the fallback reads. Neither moved a key, a unit or a status, so the ledger
and the run manifest keep their versions; an open manifest still reads as unknown.

**Resumption** (`resume BUNDLE [--session LEDGER] [--reference ISO]`,
`resume()`) reads the bundle and the ledger — the bundle's own snapshot when no
working ledger is given — and writes nothing. It verifies the retained artifacts
with `verify`, compares the active plan revision in the bundle with the one the
ledger names, reconciles consumed and reserved resources, checks that every
linked run manifest is present and unaltered, reads the pending review state,
and rechecks delivery freshness at the reference by assessing the bundle as a
delivery would without recording an event. The study is **resumable** when
nothing is missing; otherwise the precise missing dependency is named
(`artifacts_not_verified`, `session_missing`, `session_invalid`,
`plan_revision_mismatch`, `unreconciled_consumption`, `run_manifest_missing`,
`run_manifest_altered`, `plan_snapshot_invalid`). The report lists the
interrupted actions, the authorisable and prevented next actions with reasons,
and the proposals. A prevented next action is a fact about the budget, not a
failed check: the command exits 0 on a resumable study. `verify` reports
`session_invalid` when the snapshot is malformed, names another digest than the
manifest, or binds another plan revision than the bundle holds; `run --session`
refuses a ledger whose plan is not the study's.

**Identity and bytes.** The ledger and its snapshot enter neither `study_id` nor
the report; they are integrity-bound artifacts (INTAKE §8), and a study run with
or without `--session` has the same id, decisions and report bytes. The
maintenance gate replays the delivered-cost example with the committed ledger and
resumes it from the bundle's snapshot at a fixed reference; `resumable` is a
recorded decision beside `stop` and `current_advice`.

**Limits.** The ledger records what was declared and recorded. It cannot recover
an action nobody recorded, cannot measure monetary or model usage — those stay
estimates that stop new work and enforce no ceiling — and does not prove that a
declared consumption is true. A strict ceiling is only as strict as the closure
setting the crawl actually ran under, which `enforced_caps()` reads from the
manifest and the record names. Resumption does not reconstruct the conversation;
what it verifies is what the files hold. The attestation, and the binding of
session facts per delivery event, are the delivery review of §14.

## 13. Intake review (R13 stage 9)

**Intake review v1** is `study/intake_review.py`, tracked as `intake_review`. It
is the semantic pass over a plan revision that the plan contract (§9) and the
stage gates (§10) cannot perform: whether the plan reads the retained request
faithfully and completely, whether each resolved control answers the requirement
it is mapped to, whether each assumed default was defensible, and whether the
recorded stage effects are the ones a requirement's meaning implies. It is a
separate artifact under the same workflow and deliberately not the final
semantic review of §8, which stage 10 then moved to v2 (§14) so that it rests on
this one. The sanitized completed example is
[delivered-cost-intake-review.json](tests/intake/delivered-cost-intake-review.json).

| Part | Contract |
|---|---|
| `plan` | The plan's `id`, `revision` and canonical `sha256`. A review whose digest is not the plan's is **superseded**: its findings are not this revision's and are never carried forward |
| `basis` | Digests of the retained `user_evidence` and of the `requirements` with their resolved control metadata, the read-back `readback_response` status, and `catalogue_sha256`, the digest of the category's live control catalogue (empty for an unregistered category). Every one is recomputed from the plan and the registry at each check; a changed catalogue refuses, because adequacy was judged against other controls |
| `review_limits` | Recomputed from the plan, never authored: every redaction the plan marked `limits_review` and any non-empty `missing_context`. A review that omits one refuses. While a redaction limit stands, `omissions` and `faithfulness` cannot be `pass`; while context is missing, `omissions` cannot |
| `checks` | Exactly `omissions`, `faithfulness`, `adequacy`, `assumptions` and `stage_effects`, each with `status` (`pending`, `pass`, `fail`, `limited`), `findings`, and `requirement_ids` and `message_ids` that resolve in the plan. `limited` means not established from the retained evidence and is not a pass. A non-pending check needs a `reviewer` and non-empty findings, never a bare approval; a pending one records nothing. A failed `omissions` names the user messages that carry the missing instruction; a failed check of the other four names the requirements it concerns |
| `reviewer`, `unresolved_limits` | Text, and the limits the review leaves open |

**Status** is `fail` if any check failed, else `pending` if any is pending, else
`limited` if any is limited, else `pass`.

**Consumers.** `study plan-review-template PLAN -o OUT` writes the pending
template and prints the five questions; `study plan-review PLAN REVIEW` checks a
review against its plan and exits 1 when it records a failure. `study run --plan
PLAN --intake-review REVIEW` snapshots the review as `intake-review.json`,
digest-listed in the manifest with `manifest.intake_review` naming its status and
digest, and **refuses to run** a study on a plan revision whose review records a
failure: a recorded blocker at intake is a planning outcome, not authorisation to
proceed through it. `study review-intake BUNDLE REVIEW` attaches or replaces the
review on an existing plan-backed bundle after `verify`; a recorded failure is
attached and recorded as one. `verify` reports `intake_review_invalid` when the
snapshot binds another plan revision or catalogue, accompanies no plan snapshot,
or the manifest names another digest or status than it holds. `validate-report`
reports the status as `intake_review` (`absent` when there is none), fails with
`intake_review_failed` when it records a failure whether or not `--require-review`
is passed, and under `--require-review` requires a plan-backed bundle to carry a
passing one (`intake_review_missing`, `intake_review_incomplete`). `resume`
reports the state beside the final review's. A legacy study without a plan is
asked for nothing.

**Identity and bytes.** The review enters neither `study_id` nor the report: a
study run with or without it has the same id, decisions and report bytes.
Approval travels in review artifacts and is checked before delivery, never
rendered into the report it approves (INTAKE §11). The maintenance gate replays
the delivered-cost example with its committed review and pins `intake_review`
beside `stop`, `current_advice` and `resumable`.

**Limits.** The review is a reviewer's record; the checks keep it bound and
honest, and nothing here judges. It cannot detect an instruction absent from both
the plan and the retained evidence, and a reviewer can pass an inadequate mapping.
A passing review says the plan reads the retained request faithfully and its
controls answer it, not that the buyer confirmed it: the read-back response
status is bound, not waived, and the review authorises no engineering. Findings
are not reused across plan revisions: the plan digest refuses a review of another
revision, and a revision is re-reviewed. The final review that requires these
findings, and what a changed intake review does to it, are §14.

## 14. Manifest v3, review v2 and the delivery review (R13 stage 10)

Stage 10 is the one migration INTAKE §16 priced: the change that moves every
committed study id and both committed final reviews at once, so everything that
could be inert landed first and this landed last. It changes no eligibility,
ordering or outcome — the measurement below is that it did not — and it closes
the gap INTAKE §6 measured: artifacts the manifest digested and no review bound.

### The artifact inventory

`study/inventory.py` names every file a bundle may hold and how the workflow
binds it. A file without a row is refused by `artifact_digests` and reported by
`verify` as `artifact_undeclared`; the manifest records each present artifact's
`binding` beside its digest, and a manifest recording another binding than this
build's is `artifact_binding_changed`. A new artifact enters the bundle only
through a row here, which is a contract change reviewed like any other.

| Artifact | Present | Binding | Meaning |
|---|---|---|---|
| `brief.json`, `candidates.jsonl`, `cards.jsonl`, `ranking.json`, `ledger.json`, `claim-index.json` | always | `semantic` | in the final review's `basis` |
| `intake-plan.json`, `intake-review.json` | with a plan | `semantic` | in the final review's `basis`: approval rests on the intake findings it was given |
| `report.md` | always | `report` | the final review's `report_sha256` target |
| `delivery.json`, `session.json` | when delivered; with a session | `delivery` | bound per event into the delivery review, never into the semantic basis |
| `semantic-review.json`, `validation.json`, `delivery-review.json` | always; always; when reviewed | `review` | a review record or its derivative: binds others, never itself |

**Manifest v3** writes this. A v2 bundle is refused with
`unsupported_manifest_version`; regenerate it from its brief and pinned inputs.
The `study_id` material is unchanged in shape and includes the manifest version,
so the bump alone moved every id once.

### Final review v2

| Field | Contract |
|---|---|
| `review_version`, `phase` | `2` and `final`. A v1 review is refused outright: a review of other report bytes is reissued with reconsideration, never carried forward |
| `report_sha256` | the report |
| `basis` | digests of every present `semantic` artifact, from the inventory: six for a legacy study, plus the plan snapshot and the intake review for a plan-backed one |
| `intake_review` | `null` for a study without a plan; otherwise the intake review's `status` and canonical digest, or `absent` |
| `checks` | exactly `citation_support`, `variant_applicability`, `user_priorities`, `coverage_and_limits` and **`conclusion_presentation`**: do the headline, the result slot and any bounded finding claim no more than the outcome, the stop and the declared scope permit, with nothing beneath a refusal that reads as a recommendation. A completed check names a reviewer and findings |
| `reviewer`, `unresolved_limits` | text, and a list of text |

A completed review must match the live basis and the live intake findings.
**Final approval requires valid intake findings:** a review whose every check
passes is refused on a plan-backed bundle whose intake review is absent, pending,
limited or failed; a review recording a failure may be attached regardless, since
it is not approval. The order is therefore intake review, then final review.
`study review-intake` refreshes the pending final-review template to name the
intake review it attached, and **refuses** when the final review is already
completed, because attaching another intake review would supersede it — re-run
the study with `--intake-review` instead. A changed intake review behind the
CLI's back leaves a completed final review that no longer binds, which `verify`
reports as `report_invalid`.

### The identity decision

No operative-requirement projection enters `study_id` as separate material.
Since stage 5 the brief's `intake` binding carries the plan's canonical digest
and a lossless copy of its requirements, and the brief digest is in the id, so
every fact INTAKE §8 lists — the operative requirements and assumptions, the
conclusion scope, the response status the attribution renders from — is in the
id already, and the assessment results and stop are deterministic functions of
it that `verify` replays, as every other decision is. Hashing computed gate
results into the id would move it with the gate code, which INTAKE §8 itself
forbids. The transitive binding is broader than the projection would have been:
retained wording, redactions and the read-back response status move the id too.
The intake review, the session snapshot and a delivery move nothing.

### The delivery review

**Delivery review v1** is `study/delivery_review.py`, tracked as
`delivery_review`; the bundle holds `delivery-review.json` with one review per
reviewed event. It is the scoped re-check INTAKE §8 describes: at a later
delivery event the semantic findings are not rewritten, the new event is. A review whose bindings no longer hold is a `delivery_review_invalid` finding; because the record keeps one review per event and a new review replaces the old one, `delivery-review-template` and `review-delivery` for that same event proceed past that one finding and restore a verified bundle, while a stale review of any other event, or any other finding, still blocks them (added 2026-09-17, found in use).

| Part | Contract |
|---|---|
| `event`, `reference`, `current_advice`, `event_sha256` | the event's position in `delivery.json`, its reference and status for legibility, and its canonical digest. A review of another event's bytes is superseded and names every field that moved |
| `report_sha256`, `semantic_review` | the report, and the semantic review's `status` and file digest at review time |
| `session_sha256`, `intake_review_sha256` | the snapshots' digests, or empty when the bundle holds none |
| `checks` | exactly `freshness` (is the declared age bound adequate for advice issued at this reference, and are the right observations governed), `applicability` (do the governed observations and scope still fit this buyer's marketplace, region and variant) and `conclusion_presentation` (does the delivered statement claim no more than the event permits). A completed check names a reviewer and findings |
| `attestation` | `by`, `reference_read_honestly`, `declaration_true`, `statement`. A completed review answers both questions; **a passing review needs both true** — a delivery nobody will vouch for is not approved. A statement signed by name, not a proof |
| `unresolved_limits`, `limits` | the reviewer's open limits, and this contract's |

**Consumers.** `study delivery-review-template BUNDLE -o OUT [--event N]` writes a
pending review bound to one event, the latest by default; `study review-delivery
BUNDLE REVIEW` checks its bindings and attaches it, replacing an earlier review of
the same event. `verify` reports `delivery_review_invalid` when any review no
longer binds its event or when one event has two. `validate-report` reports the
latest event's review as `delivery.review`, fails a recorded failure whatever the
flags (`delivery_review_failed`), and under `--require-review` requires a passing
review of a **permitted current-advice** event (`delivery_review_missing`,
`delivery_review_incomplete`); a historical study is asked for nothing. `resume`
reports the state. A later event is a new event: the earlier review stays bound
to its own event, the semantic review is untouched, and the new event owes its
own review.

### The dirty-tree caveat

`code_identity()` records `git_dirty`; until now nothing read it. `verify` and
`validate-report` say, as a caveat and not a finding, that a bundle produced from
a working tree with uncommitted changes carries a non-identifying revision, and
that an unknown answer from git is not a clean one. The replay still decides
whether the study holds; exact patch provenance stays R15's.

### The migration, measured

Six study ids moved once, by the manifest version alone; every decision artifact
of every example is byte-identical before and after, and each report differs in
one line, its id. Both T3 final reviews were reissued under v2 against the new
bytes with the same six basis digests and re-read findings. The intake review
fixture and the session ledger bind the plan digest and did not move. The
baseline records `study_manifest` 3, `semantic_review` 2 and `delivery_review`
1; the test floor rose from 676 to 712.

**Limits.** An attestation is a statement; a reviewer's pass is a judgement; the
inventory decides what a review covers, not whether the reviewer looked. Nothing
here detects a requirement the plan never captured or a declaration that is
false.

---

## 15. Adaptation record v1 and session ledger v2 (R15, phase 0)

R15 makes a bounded engineering operation part of a study. Phase 0 is the
procedure without a real category yet: the record that binds a gap to a patch,
its checks, its review and its adoption; the ledger revision that lets
engineering run against its own allowance; the runner that executes checks
inside a declared boundary; and the binding that puts the method into the
study's identity. It changes no eligibility, ordering or outcome — the six
committed studies replay with their ids unchanged, which the gate measures —
and it adds one committed example whose id differs *because* its method does.

### The adaptation record

**Adaptation record v2** is `study/adaptation.py`, tracked as
`adaptation_record` (v1 lived for an hour on 2026-09-18; the first real
category moved it, see `baseline_moves` below). It is JSON data with closed fields; a private working
record lives under `data/adaptations/` or an explicit private path; `study run
--adaptation` snapshots it into the bundle as `adaptation.json`. It runs
nothing: `study/trial.py` is the controlling procedure that fills it in, on the
trusted side, and `verify` checks it.

| Part | Contract |
|---|---|
| `adaptation_version`, `id`, `layer`, `hypothesis` | `2`; a slug; one of `category`, `extraction`, `validation`, `analysis`, `acquisition`, `evidence`, `method`; what the patch is expected to change and why |
| `origin`, `predecessor` | the intake plan id, revision and canonical digest the gap was found in (or empty, `0`, empty when there was no plan), and the session ledger id and **engineering action** id the work accounts against. The predecessor is `plan_session` (this case's first link: the trial produced no bundle) or a prior `adaptation`, with a reference and a digest, or `null` |
| `budget`, `attempts`, `consumption` | seconds of runner time and checks run, both positive; recorded attempts never exceed the budget — exhaustion stops new work, it does not extend the envelope. `consumption.seconds` is a number or `null` (unknown is not zero); `consumption.attempts` equals the attempts recorded |
| `base`, `patch`, `result_tree_sha256`, `lock_sha256`, `method_versions` | the base git revision (empty where git could not answer) and the digest of the base tree; **the patch as a complete archive** — every added or modified file with its full content, as text or base64, and its digest, every deleted file named, and one digest over the sorted path/status/digest rows; the digest of the resulting tree; the lock digest; and the capability key → method version table the patch declares. A commit in a disposable worktree reconstructs nothing once the worktree is gone; the archive does |
| `descriptor_sha256` | the **method identity**: a canonical digest over base revision, base tree, patch digest, result tree, lock digest and method versions. It **enters `study_id`** when the record is bound, and only then. It excludes the review and the adoption on purpose: approval cannot be part of what it approves |
| `evaluator` | the **evaluator set** — `shopping_advisor/maintenance/`, `tests/test_maintenance.py`, `pyproject.toml`, `uv.lock` — as the files present at the base, their digest, and `frozen`: whether the trial tree's copies are byte-identical. A patch that touches the set is captured, flagged, and **not executed as an adaptation**: a gate a patch may rewrite judges nothing, so that change goes through ordinary maintenance |
| `inspection` | computed **before any import**: every path with its status; flags `import_side_effects`, `network`, `subprocess`, `file_writes`, `evaluator`, `contracts` (a `*_VERSION = n` line that moved), `dependencies`, each a list of `path:line: what`; and findings in sentences |
| `runner` | the boundary the checks ran under — `kernel` (a `sandbox-exec` profile, digest recorded) or `harness-only`, which is an **exception the maintainer recorded** and must name it — the interpreter, the temporary directory and the timeout |
| `checks[]` | one entry per attempt: the command, both instants, seconds, `exit` (**`null` when killed**), `timed_out`, the output's digest and path, a summary, the boundary. A timed-out check has no exit status and no pass |
| `review` | reviewer, verdict `pending`/`pass`/`fail`/`limited`, findings (never empty when completed), and the `patch_sha256` and `checks_sha256` the reviewer read. A completed review must equal the record's current patch and checks digests: **a patch edited or a check run after the review supersedes it**, and the record refuses to load until the review is reissued |
| `adoption` | decision `pending`/`accepted`/`rejected`/`withdrawn`/`interrupted`/`budget_exhausted`, the instant, the deciding role, the reason; recorded once. **`accepted` needs a passing review, a frozen evaluator, a non-empty patch and a last check that finished** — and that passed, unless `baseline_moves` declares why the frozen evaluator had to fail it. No decision turns a killed check into success |
| `baseline_moves` | **v2.** The baseline changes the patch needs at adoption, in sentences: a new capability the baseline must record, a new test module, a moved floor. The evaluator set is frozen inside a trial and its own tests pin the tree to the committed baseline, so a patch that *adds* a capability necessarily fails `capability_untracked` and the baseline-pinning tests until adoption records it — R15's scope asks that such a patch "says so in the same diff", and this is where. With moves declared, a failing last check is accepted only on a passing review whose reviewer read the check's output; with none declared, it is not accepted at all |
| `rollback` | instructions, and whether the base was demonstrated to stand (tree digest, evaluator digest and the gate at the base) with the instant |

### The binding

| Artifact | Present | Binding | Meaning |
|---|---|---|---|
| `adaptation.json` | with `run --adaptation` | `semantic` | the method that produced the decisions is part of what a final review approves; a replaced record supersedes the review |

The manifest records `adaptation` — `id`, `layer`, `descriptor_sha256`, the
record's canonical `sha256`, the `adoption` decision and the `boundary`. `run
--adaptation` refuses a record that is not `accepted` unless `--trial` is
given; a trial run measures a patch, its manifest says `adoption: pending`, and
it delivers nothing. `verify` loads the record, requires the manifest's entry
to name exactly it, and **re-derives the study id with the descriptor in it**:
a mismatch, a missing record behind a manifest that names one, or a tampered
record is `adaptation_invalid` (or `artifact_altered`, when the bytes moved).
A build without the inventory row reports the file as `artifact_undeclared`
and the bundle does not verify: an older reader refuses rather than reading an
adaptation-backed bundle as an ordinary v3 one. `code_caveats` names the record
instead of the dirty flag: the tree was patched on purpose, and the patch is
on record.

**The identity decision.** The study id material gains one term,
`adaptation`, present only when a record is bound. Measured: the six committed
ids are unchanged, and the same brief over the same bytes under the committed
fixture adaptation is `pasta-bronze-die-306e33f25417` where the unadapted study
is `pasta-bronze-die-bde2b027b117`, with the same decisions — the method moved
the id, nothing else did. Manifest v3 is unchanged in version: the key is
additive, and the id rule is conditional on it.

### Session ledger v2

| Change | Contract |
|---|---|
| `session_version` | `2`. This build reads `1` and `2`; a v1 file keeps v1's rules — engineering is `planned` or `abandoned`, never authorised — because the file says what its author was entitled to, and a newer reader grants nothing more |
| Engineering under v2 | an engineering action may be `authorised`, `running`, `completed` or `interrupted` like any other, against an `engineering` limit in `seconds`. Attempts are the adaptation record's own budget; acquisition units stay research's. A research allowance still never funds engineering |
| `consumption_source: adaptation_record` | engineering only, and engineering never records from `run_manifest`. `run_id` is the record's id, `run_manifest` the record's path and digest, linked only when the attempt finished; `seconds` come from the record's checks, `null` when unknown |
| `session-record LEDGER ACTION --adaptation RECORD` | records what the attempt did from the record; the record must account against this ledger's id and this action. A record whose last check timed out and whose adoption is still pending records the action as `interrupted` |

Why a version and not an allowance: v1's text says engineering is never
executed, and a reader of a v2 file that let it run under v1's rules would be
reading a state the contract had refused. That is a change of meaning
(§6), and it moved the version.

### The execution boundary

The runner is one measured profile, wrapping the locked virtual environment's
interpreter directly (never `uv run`) in a `sandbox-exec` profile that denies
by default and allows: reads of `/`, `/usr`, `/System`, `/Library`,
`/private/etc`, `/private/var/db`, `/dev`, the worktree, the interpreter's
distribution and the virtual environment; writes under one scratch directory
inside the worktree, `/dev`, and `tests/studies/.tmp-*` (six test modules write
temporary briefs beside the committed fixtures, because a brief's inputs are
relative to the brief file — a measured exception, stated); no network; and a
watchdog that kills the whole process group at the timeout. `TMPDIR` points
inside the scratch directory. Measured on 2026-09-18 on the development
machine: the full offline suite and the full gate pass inside the profile
(814 and 815 tests, about 22 s); a read outside, a write outside, a write to
the tree, a socket connection and a read of the home directory are refused
with `EPERM`; the write to the scratch directory succeeds; a check that
spawned a child and hung was killed with its child at the timeout.

What the boundary does not do, and says so: `git` does not run inside it (its
shim writes a cache under `TMPDIR` and reads the user's configuration), so tree
and patch identity are computed by the controlling procedure outside, never by
code inside; Apple marks `sandbox-exec` deprecated, and nothing here claims
portability beyond the machine it was measured on (R17). Where the profile
cannot be demonstrated the default is to stop and record the blocker; the
maintainer may record an exception, and then the checks are labelled
`harness-only`, count toward none of R15's Done-when, and are never presented
as the demonstrated boundary.

**Limits.** A digest proves that bytes did not change, not that they are
safe; the static inspection reads names, not intent, and a patch can reach the
network through a name it does not list — which is what the boundary is for.
The review is a reviewer's judgement, the adoption a role's decision; the
contract checks that both bind the bytes they read, not that they were right.
