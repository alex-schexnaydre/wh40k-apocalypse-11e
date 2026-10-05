# Apocalypse profile inference

11th edition datasheets are not copied into Apocalypse. Apocalypse keeps its own characteristic lines. 11th edition supplies the unit list, keywords, weapon identity, and points. The 2019 Apocalypse datasheet PDFs in `sources/pdfs/datasheets/` and the field manual in `sources/pdfs/field-manual.pdf` are the rules and the calibration set. 8th edition BSData in `sources/wh40k-8th-edition/` is the 40k stat key those printed sheets were written from.

Games Workshop PDFs are local reference only. They are gitignored and are not part of the data files.

## How an attack works

From the field manual (Making Attacks, Damage phase, datasheet glossary):

- Hit roll: one D6 per attack, against the unit's Ballistic Skill when shooting or Weapon Skill when fighting. An unmodified 1 fails. An unmodified 6 succeeds.
- Wound roll: one D12. Use the weapon's Strength Against Personnel (SAP) when the target is Light. Use Strength Against Tanks (SAT) when the target is Heavy or Super-heavy. An unmodified 1 fails. An unmodified 12 succeeds.
- Each successful wound places a blast marker. In the Damage phase the target rolls a save against each marker (D12 for a small marker, D6 for a large one) and must meet or beat its Save. Failed saves place damage markers. The unit is destroyed when damage markers equal its Wounds.
- Morale is a D6 plus the number of blast markers, and must be less than or equal to Leadership.
- Weapon Attacks of `User` copy the unit's Attacks. `x2` or `+1` modifies that number.
- Weapon types used on datasheets are Melee, Small Arms, and Heavy.

Light, Heavy, and Super-heavy are Apocalypse target classes. They are assigned from 11th edition keywords:

- Super-heavy: Titanic or Towering
- Heavy: Vehicle or Monster, when not Super-heavy
- Light: Infantry, Beast, Swarm, Mounted, and other personnel

## Points to Power Level

Power Level is `max(1, round(points / 20))`.

The divisor is the fork's current Intercessor Squad, checked against 11th edition points: 80 points for 5 models is PL 4, and 150 points for 10 models is PL 8. The printed 2019 Power Ratings are higher (a 5-model Intercessor Squad was Power Rating 6). This update follows the catalogue's points-per-PL scale, not the 2019 printed ratings.

When a datasheet has a minimum and a maximum size, the minimum size uses the base points cost and the maximum size uses the higher points modifier. Units whose 11th edition cost is not a single base cost are left unchanged and listed in the gap report.

## Unit characteristics

Existing datasheets keep their Attacks and Wounds. Those values were already compressed for Apocalypse. New datasheets use the rules below. Movement, Weapon Skill, Ballistic Skill, and Leadership on a new sheet come from the 11th edition model and its default weapons.

| Field | Rule |
| --- | --- |
| M | Copy the model's Move. |
| WS | Weapon Skill of the default melee weapon. |
| BS | Ballistic Skill of the default ranged weapon. |
| Ld | The number in the 11th edition Leadership value. `6+` is stored as `6`, which is the morale target already used for Intercessors in this catalogue. |
| A, squad | `max(1, round(models x melee attacks / 3.5))`. Five Intercessors with 2 melee attacks become A3. Ten become A6. |
| A, one model on foot | 1. |
| A, single vehicle or monster | `max(1, round(wounds / 8))`. A 10-wound Rhino is A1. A 16-wound Land Raider is A2. |
| W | `max(1, round(models x wounds / 5))`. Five Intercessors (2 wounds each) are W2. A 16-wound Land Raider is W3. A squad of multi-wound models is at least W2. |

Save is the Apocalypse save (higher is harder to damage), fitted to printed sheets:

| 11th edition armour | Apocalypse Save |
| --- | --- |
| 2+ | 4+ |
| 3+ | 6+ |
| 4+ | 8+ |
| 5+ | 9+ |
| 6+ | 10+ |
| 7+ | 11+ |

Toughness 5 or 6 improves a 3+ or worse save by one step, which is why Aggressors are Save 5+. A 4+ invulnerable save improves a 3+ or worse save by one more step, which is why a Captain is Save 5+. A 2+ save stays at 4+, which is the printed Terminator and Land Raider save.

## Weapons

New datasheets carry the default ranged weapon and the default melee weapon on the unit. Pistols are omitted when the model also has a primary gun, matching the field manual note that sidearms are already accounted for. Optional wargear is not expanded into separate entries.

Attacks on a Heavy weapon are compressed: 1 for 1-3 attacks, 2 for 4-6, 3 for 7-12, and 4 above that. A Heavy Bolter (3 attacks) stays Attacks 1. Squad Small Arms and Melee weapons use `User` when the 11th edition weapon has 2 attacks or fewer, and `xN` when it has more.

SAP and SAT are estimated. Lower is stronger. Dedicated anti-tank guns (high Strength, high AP, high Damage) get a poor SAP and a strong SAT, which is how the printed Lascannon (SAP 10+, SAT 5+) and Multi-melta (SAP 10+, SAT 4+) behave. A boltgun-class weapon lands near SAP 7+ and SAT 9+ or 10+. Shared weapons that already exist keep their printed SAP and SAT. Range and ability names on those shared weapons are refreshed when every 11th edition profile of that name agrees.

Ability text on a new sheet is the 11th edition ability name, not the paragraph from the datasheet.

## Keywords

11th edition keywords are category links. Battlefield role is the primary category, using the slots the detachment already offers: Epic Hero, Character, Battleline, Infantry, Mounted, Beast, Swarm, Vehicle, Monster, Dedicated Transport, Fortification, Flyer. Battleline units also keep the Troops category. The Light, Heavy, and Super-heavy target classes are added as well.

Walker, Towering, Grenades, Tacticus, Phobos, Gravis, and Terminator are game-system categories. They are linked when the 11th edition unit has that keyword. Force-organisation categories already on a datasheet are not removed.

## What is created, and what is left alone

Matched-play units with no catalogue entry get a new datasheet. Units tagged `[Legends]` are a second pass: they use the same profile rules and stay hidden until Show Legends is selected. Datasheets already in the catalogues stay, including units that 11th edition no longer prints. Their Power Level is updated when the 11th edition points cost is known, and missing keywords are added. Their Attacks and Wounds are not rewritten.

Genestealer Cults, Agents of the Imperium, Deathwatch, and Unaligned Forces did not have catalogues. They are added as faction files.
