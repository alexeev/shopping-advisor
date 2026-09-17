# Analysis cases

Product records taken verbatim from real validation crawls, one JSON object
per line, as written by the `amazon_product` spider. Each file is the evidence
one category's rules were built against, and `../test_analysis.py`,
`../test_mounting_paste.py` and `../test_school_backpack.py` assert the verdict
on every record in it.

They are here because `data/` is gitignored, so the evidence every validation
rule was written against would otherwise live on one machine.

```
pasta_v1.jsonl.gz           25 records · dry pasta
mounting_paste_v1.jsonl.gz  34 records · tyre mounting paste
school_backpack_v1.jsonl.gz 43 records · school backpack
```

## `pasta_v1.jsonl.gz`

| Group | ASINs | Why |
|---|---|---|
| Disputed pack quantity | `B08JLSVW3J` `B08HQSZR3D` `B0173KFFIG` `B0BG28G6SZ` `B0C3WCFKHT` `B0C5XK2QFR` `B0BTPZ7TXJ` `B0GQ5BKHPT` | Amazon's attribute table contradicts the title or the pack-size name. Left unchecked these report €62.56/kg for a €3.91/kg pasta, and €0.32/kg for a €6.47/kg one. |
| Corroborated quantity | `B0CH3MHVF8` `B08BNQ2D54` `B0D4R7K82Q` `B0C2VN9NCD` `B00XUMS46W` | False-positive guards. Every one of these was disputed by an earlier version of the reconciler and is in fact correct. |
| Amazon's own figure is wrong | `B0G6D354JV` | Pack size confirmed by the title (20×500 g); Amazon's published price per kilo is the value that does not fit. |
| Implausible nutrition | `B089HJPK5T` `B0FWXQ6NWM` `B0FWXCDCYV` `B07NZ1K8L3` `B086K1MFSL` `B0BP2QDLPQ` | 534 g of protein per 100 g, a mistyped kJ column, a table header parsed as its own value, 7 g of carbohydrate in dry pasta. Five of the six come from Amazon's *structured* nutrition card. |
| Clean pasta | `B08WJGD5Z5` `B0DQ2N5HRW` `B0CT3Q17FP` | The comparison path, and proof the rules do not fire on ordinary records. |
| Not pasta | `B0CZ473RQT` `3969301173` | A cleaning brush and a cookbook, both returned by pasta searches. Classification is not optional. |

## `mounting_paste_v1.jsonl.gz`

The second category, added in R2. Its job is partly to guard the category's
own rules and partly to keep the *contract* honest: this is the set that made
three latent defects in the generic layer visible.

| Group | ASINs | Why |
|---|---|---|
| Mounting paste | `B01M25SBQ5` `B000RW5FVA` `B00295ER76` `B0GNMRKPGQ` `B0GNMSWB7D` `B0DHS9JHLJ` `B01LB62GQ2` `B01LB4QIEU` `B071JNV24H` `B001NYY87I` `B0FSRM9TBK` `B0055Y6M7Q` `B076HTCT4J` | Tubs, tubes, a sponge tin, an aerosol and three kits. `B0GNMRKPGQ` states the drying criterion the whole category turns on in the one phrasing the original pattern recognised. |
| Near-miss product classes | `B097C8JJY4` `B0D1RJ1HLC` `B00CSRY8OC` `B0FJG6YJ2X` `B08VNDJJS6` | All five have "Montagepaste" in the title and none is one. Carbon paste is a *friction* paste — the opposite function; anti-seize and ceramic paste are designed never to dry; the last is a lubricant for repair plugs, caught by the `für` rule. |
| Accessories | `B01MXXA922` `B01M6WXE0X` | A brush named before the paste it is for. The positional rule that excludes them must not also exclude "5 kg paste **with** a brush". |
| Other products entirely | `B07V48PZY5` `B0CRTZ5ZJN` `B0C1GHMX8V` | Tubeless sealant, wheel weights, a pressure gauge — all returned by the same searches. |
| "Fett" is grease *and* fat | `B0068ICY70` `B07J2W1S6Q` `B0DGPV9TWZ` `B0F4PQ7NMM` | The food parser reads a pack size as a nutrition declaration: `"Fett wird in einer 100 g Tube geliefert"` → 100 g of fat per 100 g. Two of the four satisfy the per-100 g basis test, so only the single-nutrient corroboration rule stops them. |
| Volume pricing | `B0D6N5HYKB` `B007MFMN9W` | Priced per litre by Amazon. The first also states `2 x 75ml` against a 75 ml attribute total, which is a disputed pack quantity. |
| How vendors actually write "dries" | `B000RW5FVA` `B0GXK9CM2D` `B0H94J1QZW` | Added when the drying pattern was widened. None of the three says "trocknet ab": they say "Schnelltrocknend", "schnell trocknend" and "vollständig lufttrocknet", and the first files it as an attribute row as well. The original pattern matched none of them, which cost the smallest pack on the shelf its decisive claim. |
| A title that names nothing | `B086BX8M3C` | "Rema Tip Top 501004 - Schwammdose, Transparent, 50 ml" — container, colour, volume, and never the product class. Thirteen queries across five crawls never surfaced it, and the title-based classifier filed it as "other" when it finally arrived. It is a bicycle tyre mounting gel, and its description says so. The only record in the corpus classified on body text rather than on its title. |
| The pack size a ranking dropped | `B087WQJQDS` | A 5 g tube — the smallest pack in a 127-record corpus, and the only listing that states both "trocknend" and freedom from mineral oil. Its title ends "Schwarz Einheitsgröße" and its size field says "Einheitsgröße", so the 5 g exist only in a feature bullet; until bullets were read for corroboration, the quantity stayed unverified and unverified values are not ranked. The product the ranking exists to surface was the one it hid. |
| A drying claim and its own negation | `B0BJRG3K8Y` | "TROCKNET NICHT EIN IM EIMER UND AM PINSEL" and "Abtrocknungsverhalten: schnell trocknend", on one page, with the negated bullet printed first. Both are true of the product; only the second answers this category's question. |

## `school_backpack_v1.jsonl.gz`

The fourth category, and the first non-consumable, written on 2026-09-17
during an intake conversation under the unsupported-category rule. The 43
unique records are what two bounded Amazon.de probes returned for
"Schulrucksack Mädchen", "Schulrucksack Jugendliche" and eight brand queries
(Satch, Coocazoo, Deuter, Dakine, Eastpak, Jack Wolfskin, 4YOU, Beckmann),
re-extracted from their retained pages after the extractor learned to read the
weight Amazon.de appends to the dimensions row. Titles here stuff
"Schulrucksack" and "Schulranzen" into one line, and Amazon files Satch and a
first-grader's set under the same node, so the classifier is positional on the
title the way mounting paste is.

| Group | ASINs | Why |
|---|---|---|
| School backpacks | `B0GM19PXKV` `B0DXJJ861V` `B0DXJLY2L2` `B0DWXLM44P` `B0DXJDZDB9` `B09MCRN848` `B09MCT66NR` `B0GGJHD7M6` `B0GGV5ZNFC` `B09MCSCQGD` `B0F8NJ5TGL` `B0DVTDG2G2` `B07V3FR8V3` `B003OSUDOS` `B00JPZ0B2S` `B0DY8BN2BJ` `B08Y5WHP98` `B0DNZBZSR6` `B099PLV2F4` `B0C1BVTCR1` `B0DTD4KXGD` `B0G6KJYRSB` `B0GCHZ4RYR` | Five colour variants of one Satch Pack, three Coocazoo listings, a Deuter "ab der 5. Klasse", two Beckmann, three daypacks sold as school bags, and the low-price shelf the generic queries returned. |
| An adult's pack with a school word stuffed in | `B0BRKHTWB1` `B07RW36W3K` `B0CYBW4V5H` `B0DSPQ96PH` `B0B2RC7F6M` | "Rucksack Herren, Schulrucksack Jungen Teenager, Laptop Rucksack": the head noun comes first in a German title, and it is a men's laptop pack. |
| First-grader's set, and the satchel-set node | `B0GYS582DH` `B0CYZKT2V5` | A "Schulranzen Set 5-TLG. ... 1. Klasse", and a satchel whose title says nothing and whose node says primary school. |
| Other backpack classes | `B0D5R73HZ2` `B0FHKWFVDR` `B0FHL3BH68` `B0F8W25VDC` `B000RE5A4U` `B07DNZCRVX` `B07P6M89HV` `B0DCH9D4H9` `B0B1VXPQF9` `B0CKTHQVXF` `B0B6H24C3H` `B0GPNQ54YZ` `B0HCPS1THW` | Trekking, hiking, leisure and adults' daypacks the brand queries returned. None names a school use in its title. |
| Weight only in the dimensions row | `B0GM19PXKV` `B0DXJJ861V` `B0DXJLY2L2` `B0DWXLM44P` `B0DXJDZDB9` `B09MCSCQGD` `B07V3FR8V3` `B099PLV2F4` | "Produktabmessungen: 22 x 30 x 45 cm; 1,1 Kilogramm" and no Artikelgewicht row. The A+ copy confirms the Satch and Porter weights; the other two stay unverified. |
| Weight only in prose | `B09MCRN848` | "Mit einem Gewicht von 1.250 Gramm" in the A+ copy and no structured row anywhere: unverified, never promoted. |
| The warranty row | `B0GGV5ZNFC` `B0GGJHD7M6` `B00JPZ0B2S` `B003OSUDOS` `B0CKTHQVXF` | "Garantie für das Produkt: 4 Jahre" / "20+ Jahre" state a manufacturer warranty; "Gesetzlich" on the Puma states only the statutory right and is not one. |
| Body-height ranges | `B0GM19PXKV` `B09MCRN848` `B09MCSCQGD` | "1,40 - 1,80 m" and "von 135 cm bis 180 cm": shown on the card, ranked on by nobody. |
| A weight in pounds | `B00JPZ0B2S` `B0B6H24C3H` | "1,32 Pfund" and "1,5 Pfund" in the Artikelgewicht row, which the extractor keeps as text and does not yet convert. |

## Privacy

These are product records, not page captures: they contain published product
data and the product URL, and no session identifiers, customer data or account
state. Unlike `../corpus/`, no redaction step is needed — the spider never
wrote anything per-session into a record.

## Updating

Add a record when a new rule needs evidence, or when a rule fires where it
should not. Take it verbatim from a crawl; do not hand-edit, or the case stops
being evidence of what Amazon actually publishes. A record may legitimately be
*re-extracted* from a retained page when the schema moves — that is not an
edit, it is the same bytes read by newer code, and it is what the page store
exists for.
