"""Build the 11th-edition gap report and update Apocalypse catalogues.

Reads sources/wh40k-11e, writes reports/, and edits the .cat and .gst files
using the rules in docs/INFERENCE.md. Running the script again does not
duplicate units or keyword links.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC_11E = ROOT / "sources" / "wh40k-11e"
REPORTS = ROOT / "reports"
GST_NAME = "Warhammer_40k_Apocalypse_11th_Edition.gst"
OLD_GST_NAME = "Warhammer_40k_Apocalypse_10th_Edition.gst"
PTS_FIELD = "51b2-306e-1021-d207"
PL_COST = '<cost name=" PL" typeId="1466-da3f-0d27-dace" value="{value}"/>'
NS_CAT = "http://www.battlescribe.net/schema/catalogueSchema"
GAME_SYSTEM_ID = "440c-9567-ca71-f95b"
SHOW_LEGENDS_ID = "c13b-ab88-b33f-dcd5"

# 11th edition catalogue -> Apocalypse file that should receive its units.
TARGETS = {
    "Aeldari - Aeldari Library.json": "Aeldari_Craftworlds.cat",
    "Aeldari - Craftworlds.json": "Aeldari_Craftworlds.cat",
    "Aeldari - Drukhari.json": "Aeldari_Drukhari.cat",
    "Chaos - Chaos Daemons Library.json": "Chaos_Chaos_Daemons.cat",
    "Chaos - Chaos Daemons.json": "Chaos_Chaos_Daemons.cat",
    "Chaos - Chaos Knights Library.json": "Chaos_Chaos_Knights.cat",
    "Chaos - Chaos Knights.json": "Chaos_Chaos_Knights.cat",
    "Chaos - Chaos Space Marines.json": "Chaos_Chaos_Space_Marines.cat",
    "Chaos - Death Guard.json": "Chaos_Death_Guard.cat",
    "Chaos - Emperor's Children.json": "Chaos_Emperors_Children.cat",
    "Chaos - Thousand Sons.json": "Chaos_Thousand_Sons.cat",
    "Chaos - Titanicus Traitoris.json": "Adeptus_Titanicus.cat",
    "Chaos - World Eaters.json": "Chaos_World_Eaters.cat",
    "Genestealer Cults.json": "Tyranids_Genestealer_Cults.cat",
    "Imperium - Adepta Sororitas.json": "Imperium_Adepta_Sororitas.cat",
    "Imperium - Adeptus Custodes.json": "Imperium_Adeptus_Custodes.cat",
    "Imperium - Adeptus Mechanicus.json": "Imperium - Adeptus Mechanicus.cat",
    "Imperium - Adeptus Titanicus.json": "Adeptus_Titanicus.cat",
    "Imperium - Agents of the Imperium.json": "Imperium_Agents_of_the_Imperium.cat",
    "Imperium - Astra Militarum - Library.json": "Imperium_Astra_Militarum.cat",
    "Imperium - Astra Militarum.json": "Imperium_Astra_Militarum.cat",
    "Imperium - Black Templars.json": "Imperium_Black_Templars.cat",
    "Imperium - Blood Angels.json": "Imperium_Blood_Angels.cat",
    "Imperium - Dark Angels.json": "Imperium_Dark_Angels.cat",
    "Imperium - Deathwatch.json": "Imperium_Deathwatch.cat",
    "Imperium - Grey Knights.json": "Imperium_Grey_Knights.cat",
    "Imperium - Imperial Fists.json": "Imperium_Adeptus_Astartes.cat",
    "Imperium - Imperial Knights - Library.json": "Imperium_Imperial_Knights.cat",
    "Imperium - Imperial Knights.json": "Imperium_Imperial_Knights.cat",
    "Imperium - Iron Hands.json": "Imperium_Adeptus_Astartes.cat",
    "Imperium - Raven Guard.json": "Imperium_Adeptus_Astartes.cat",
    "Imperium - Salamanders.json": "Imperium_Adeptus_Astartes.cat",
    "Imperium - Space Marines.json": "Library_Space_Marines.cat",
    "Imperium - Space Wolves.json": "Imperium_Space_Wolves.cat",
    "Imperium - Ultramarines.json": "Imperium_Adeptus_Astartes.cat",
    "Imperium - White Scars.json": "Imperium_Adeptus_Astartes.cat",
    "Leagues of Votann.json": "Leagues_of_Votann.cat",
    "Library - Titans.json": "Adeptus_Titanicus.cat",
    "Library - Tyranids.json": "Tyranids.cat",
    "Necrons.json": "Necrons.cat",
    "Orks.json": "Orks.cat",
    "T'au Empire.json": "Tau_Empire.cat",
    "Tyranids.json": "Tyranids.cat",
    "Unaligned Forces.json": "Unaligned_Forces.cat",
}

NEW_CATALOGUES = {
    "Tyranids_Genestealer_Cults.cat": "Genestealer Cults",
    "Imperium_Agents_of_the_Imperium.cat": "Agents of the Imperium",
    "Imperium_Deathwatch.cat": "Deathwatch",
    "Unaligned_Forces.cat": "Unaligned Forces",
}

# Keywords that get a game-system category if the 11e unit has them.
EXTRA_KEYWORDS = [
    "Walker",
    "Towering",
    "Grenades",
    "Tacticus",
    "Phobos",
    "Gravis",
    "Terminator",
]

ABILITY_KEEP = (
    "Sustained Hits",
    "Lethal Hits",
    "Devastating Wounds",
    "Rapid Fire",
    "Melta",
    "Blast",
    "Twin-linked",
    "Ignores Cover",
    "Hazardous",
    "Torrent",
    "Indirect Fire",
    "Precision",
    "Conversion",
    "Anti-",
    "Pistol",
    "Assault",
    "One Shot",
    "Extra Attacks",
)

# Printed 2019 sheets used to show how far the SAP/SAT estimate sits.
OFFICIAL_WEAPONS = [
    ("Boltgun", 4, 0, 1, 7, 9),
    ("Bolt rifle", 4, 1, 1, 5, 8),
    ("Heavy bolter", 5, 1, 1, 7, 9),
    ("Lascannon", 9, 3, 6, 10, 5),
    ("Multi-melta", 8, 4, 6, 10, 4),
    ("Plasma cannon", 7, 3, 1, 7, 7),
    ("Assault cannon", 6, 1, 1, 6, 8),
    ("Storm bolter", 4, 0, 1, 9, 10),
]


def bid() -> str:
    token = uuid.uuid4().hex[:16]
    return f"{token[0:4]}-{token[4:8]}-{token[8:12]}-{token[12:16]}"


def norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("[legends]", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def first_int(value) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else None


def parse_damage(value) -> float:
    text = str(value or "1").upper().replace(" ", "")
    table = {
        "D6": 3.5,
        "1D6": 3.5,
        "D3": 2.0,
        "1D3": 2.0,
        "D6+1": 4.5,
        "D6+2": 5.5,
        "2D6": 7.0,
        "D6+3": 6.5,
    }
    if text in table:
        return table[text]
    match = re.search(r"\d+", text)
    return float(match.group(0)) if match else 1.0


def sap_sat(strength: int, ap: int, damage: float) -> tuple[int, int]:
    """Estimate SAP and SAT. Lower is stronger. See docs/INFERENCE.md."""
    ap = abs(ap)
    sat = 11 - max(0, strength - 5) - max(0, ap - 1)
    if damage >= 3:
        sat -= 1
    if strength <= 5 and ap <= 1 and damage <= 2:
        sat = max(sat, 9)
    if strength <= 4 and ap == 0:
        sat = 10
    sat = clamp(sat, 3, 12)

    if strength >= 8 and ap >= 3 and damage >= 3:
        sap = 10
    elif strength >= 9 and damage >= 3:
        sap = 10
    else:
        sap = 8
        if strength >= 4:
            sap = 7
        if strength >= 6:
            sap = 6
        if strength >= 8:
            sap = 5
        sap -= min(ap, 2)
        if damage >= 2 and 5 <= strength <= 6:
            sap -= 1
    sap = clamp(sap, 4, 12)
    return sap, sat


def apoc_save(toughness: int, save: int, invuln: int | None) -> int:
    table = {2: 4, 3: 6, 4: 8, 5: 9, 6: 10, 7: 11}
    base = table.get(save, 10)
    if save >= 3 and 4 < toughness < 7:
        base -= 1
    if save >= 3 and invuln is not None and invuln <= 4:
        base -= 1
    return clamp(base, 3, 12)


def plus(value: int) -> str:
    return f"{value}+"


def heavy_attacks(attacks: int) -> int:
    if attacks <= 3:
        return 1
    if attacks <= 6:
        return 2
    if attacks <= 12:
        return 3
    return 4


def ability_text(keywords: str) -> str:
    if not keywords:
        return "-"
    kept = []
    for part in re.split(r",\s*", keywords):
        part = part.strip()
        if not part or part in {"Heavy", "Assault"}:
            continue
        if any(part.startswith(token) or token in part for token in ABILITY_KEEP):
            if part not in kept:
                kept.append(part)
    return ", ".join(kept) if kept else "-"


def weapon_type(profile: dict, keywords: str) -> str:
    if profile.get("typeName") == "Melee Weapons" or str(profile.get("Range")) == "Melee":
        return "Melee"
    keys = keywords or ""
    strength = first_int(profile.get("S")) or 0
    if "Heavy" in keys or "Blast" in keys or strength >= 8:
        return "Heavy"
    return "Small Arms"


def chars_of(profile: dict) -> dict:
    out = {}
    for item in profile.get("characteristics") or []:
        out[item.get("name")] = item.get("$text")
    return out


class IdGen:
    def __init__(self) -> None:
        self._used = set()

    def get(self) -> str:
        while True:
            value = bid()
            if value not in self._used:
                self._used.add(value)
                return value


IDS = IdGen()


def index_nodes(node, by_id: dict) -> None:
    if isinstance(node, dict):
        if node.get("id"):
            by_id[node["id"]] = node
        for value in node.values():
            index_nodes(value, by_id)
    elif isinstance(node, list):
        for value in node:
            index_nodes(value, by_id)


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def weapon_from_profile(profile: dict) -> dict:
    raw = chars_of(profile)
    keywords = raw.get("Keywords") or ""
    strength = first_int(raw.get("S")) or 4
    ap = abs(first_int(raw.get("AP")) or 0)
    damage = parse_damage(raw.get("D"))
    attacks = first_int(raw.get("A")) or 1
    sap, sat = sap_sat(strength, ap, damage)
    kind = weapon_type({**raw, "typeName": profile.get("typeName")}, keywords)
    if kind == "Heavy":
        attack_text = str(heavy_attacks(attacks))
    elif attacks <= 2:
        attack_text = "User"
    else:
        attack_text = f"x{max(2, round(attacks / 2))}"
    ranged = raw.get("Range") or ("Melee" if kind == "Melee" else '24"')
    return {
        "name": profile.get("name") or "Weapon",
        "type": kind,
        "range": ranged,
        "attacks": attack_text,
        "sap": plus(sap),
        "sat": plus(sat),
        "abilities": ability_text(keywords),
        "bs": raw.get("BS") or raw.get("WS"),
        "ws": raw.get("WS"),
        "raw_a": attacks,
        "keywords": keywords,
    }


def collect_weapons(entry: dict, by_id: dict, depth: int = 0) -> list[dict]:
    if depth > 4 or not isinstance(entry, dict):
        return []
    found = []
    for profile in entry.get("profiles") or []:
        if profile.get("typeName") in ("Ranged Weapons", "Melee Weapons"):
            found.append(weapon_from_profile(profile))
    for link in entry.get("entryLinks") or []:
        target = by_id.get(link.get("targetId"))
        if target:
            found.extend(collect_weapons(target, by_id, depth + 1))
    for group in entry.get("selectionEntryGroups") or []:
        found.extend(collect_weapons(group, by_id, depth + 1))
    for child in entry.get("selectionEntries") or []:
        found.extend(collect_weapons(child, by_id, depth + 1))
    return found


def representative_model(unit: dict) -> dict | None:
    models = [node for node in walk(unit) if node.get("type") == "model"]
    if not models:
        return None

    def min_count(model: dict) -> int:
        values = [
            int(item.get("value"))
            for item in model.get("constraints") or []
            if item.get("type") == "min" and str(item.get("value", "")).isdigit()
        ]
        return max(values) if values else 0

    ranked = sorted(models, key=lambda model: (min_count(model), "sergeant" not in (model.get("name") or "").lower()), reverse=True)
    return ranked[0]


def model_stats(model: dict | None, unit: dict) -> dict | None:
    profiles = []
    source = model or unit
    for node in walk(source):
        if node.get("typeName") == "Unit":
            stats = chars_of(node)
            if stats.get("M"):
                profiles.append(stats)
    if not profiles:
        for node in walk(unit):
            if node.get("typeName") == "Unit":
                stats = chars_of(node)
                if stats.get("M"):
                    profiles.append(stats)
    return profiles[0] if profiles else None


def size_bounds(unit: dict) -> tuple[int, int]:
    mins, maxs = [], []
    for node in walk(unit):
        children = node.get("selectionEntries") or []
        if not any(isinstance(child, dict) and child.get("type") == "model" for child in children):
            continue
        for item in node.get("constraints") or []:
            if item.get("field") != "selections":
                continue
            if not str(item.get("value", "")).lstrip("-").isdigit():
                continue
            if item.get("type") == "min":
                mins.append(int(item["value"]))
            elif item.get("type") == "max":
                maxs.append(int(item["value"]))
    if not mins and not maxs:
        return 1, 1
    low = min(mins) if mins else 1
    high = max(maxs) if maxs else low
    if high < low:
        high = low
    return low, high


def points_of(unit: dict) -> tuple[float | None, float | None]:
    base = None
    for cost in unit.get("costs") or []:
        if cost.get("name") == "pts":
            try:
                base = float(cost.get("value"))
            except (TypeError, ValueError):
                base = None
    alts = []
    for node in walk(unit):
        for modifier in node.get("modifiers") or []:
            if modifier.get("type") == "set" and modifier.get("field") == PTS_FIELD:
                try:
                    alts.append(float(modifier.get("value")))
                except (TypeError, ValueError):
                    continue
    higher = [value for value in alts if base is not None and value > base]
    return base, (max(higher) if higher else None)


def keywords_of(unit: dict) -> list[str]:
    names = []
    for link in unit.get("categoryLinks") or []:
        name = link.get("name")
        if name and name not in names:
            names.append(name)
    return names


def choose_weapons(weapons: list[dict]) -> list[dict]:
    ranged = [item for item in weapons if item["type"] != "Melee"]
    melee = [item for item in weapons if item["type"] == "Melee"]
    primary = [item for item in ranged if "Pistol" not in item["keywords"]] or ranged[:1]
    # One gun and one melee weapon. Prefer the gun with the most attacks.
    chosen = []
    if primary:
        chosen.append(sorted(primary, key=lambda item: item["raw_a"], reverse=True)[0])
    if melee:
        chosen.append(sorted(melee, key=lambda item: item["raw_a"], reverse=True)[0])
    return chosen


SKIP_LINKS = {
    "detachment",
    "show/hide options",
    "order of battle",
    "warlord",
    "configuration",
}


def link_belongs(source_file: str, target_file: str) -> bool:
    """Faction files may link a companion library. They may not pull in allied codexes."""
    if target_file == source_file:
        return True
    source = source_file.replace(".json", "")
    target = target_file.replace(".json", "")
    if target.startswith(source):
        return True
    companions = {
        "Imperium - Adeptus Titanicus": "Library - Titans",
        "Chaos - Titanicus Traitoris": "Library - Titans",
        "Tyranids": "Library - Tyranids",
        "Aeldari - Craftworlds": "Aeldari - Aeldari Library",
        "Aeldari - Drukhari": "Aeldari - Aeldari Library",
    }
    return companions.get(source) == target


def load_11e_units() -> list[dict]:
    catalogues = {}
    owners: dict[str, str] = {}
    by_id: dict = {}
    for path in sorted(SRC_11E.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        catalogue = data.get("catalogue")
        if not catalogue:
            continue
        catalogues[path.name] = catalogue

        def index(node, filename=path.name):
            if isinstance(node, dict):
                if node.get("id"):
                    by_id[node["id"]] = node
                    owners.setdefault(node["id"], filename)
                for value in node.values():
                    index(value)
            elif isinstance(node, list):
                for value in node:
                    index(value)

        index(catalogue)

    units = []
    seen = set()
    for filename, target in TARGETS.items():
        if "Library" in filename:
            continue
        catalogue = catalogues.get(filename)
        if not catalogue:
            continue
        links = catalogue.get("entryLinks") or []
        nodes = []
        if links:
            for link in links:
                label = (link.get("name") or "").strip().lower()
                if label in SKIP_LINKS:
                    continue
                node = by_id.get(link.get("targetId"))
                if not node:
                    continue
                if not link_belongs(filename, owners.get(link.get("targetId"), "")):
                    continue
                nodes.append(node)
        else:
            nodes = [
                entry
                for entry in catalogue.get("sharedSelectionEntries") or []
                if entry.get("type") in {"unit", "model"}
            ]
        for entry in nodes:
            if entry.get("type") not in {"unit", "model"}:
                continue
            name = entry.get("name") or ""
            if not name or name.lower() in SKIP_LINKS:
                continue
            key = (target, norm(name))
            if key in seen:
                continue
            model = entry if entry.get("type") == "model" else representative_model(entry)
            stats = model_stats(model, entry)
            if not stats:
                continue
            seen.add(key)
            low, high = size_bounds(entry)
            base_pts, alt_pts = points_of(entry)
            weapons = choose_weapons(collect_weapons(model or entry, by_id))
            ability_names = []
            for node in walk(entry):
                if node.get("typeName") == "Abilities" and node.get("name"):
                    if node["name"] not in ability_names and node["name"] != name:
                        ability_names.append(node["name"])
            units.append(
                {
                    "source": filename,
                    "target": target,
                    "name": name,
                    "legends": "[Legends]" in name,
                    "stats": stats,
                    "min_models": low,
                    "max_models": high,
                    "base_pts": base_pts,
                    "alt_pts": alt_pts,
                    "keywords": keywords_of(entry),
                    "weapons": weapons,
                    "abilities": ability_names[:6],
                }
            )
    return units


def strip_inferred(text: str) -> str:
    """Remove datasheets generated by an earlier run so they can be placed again."""
    marker = "Inferred from the 11th edition datasheet"
    if marker not in text:
        return text
    entries = scan_entries(text)
    roots = [
        item["id"]
        for item in entries.values()
        if not item.get("parent") and marker in item.get("head", "")
    ]
    for entry_id in sorted(roots, key=lambda value: text.find(f'id="{value}"'), reverse=True):
        span = find_entry_span(text, entry_id)
        if span:
            text = text[: span[0]] + text[span[1] :]
    return text


def propose_profile(unit: dict, models: int, points: float | None) -> dict:
    stats = unit["stats"]
    toughness = first_int(stats.get("T")) or 4
    save = first_int(stats.get("Sv")) or 4
    invuln = first_int(stats.get("InSv"))
    wounds = first_int(stats.get("W")) or 1
    leadership = first_int(stats.get("LD") or stats.get("Ld")) or 6
    melee = next((item for item in unit["weapons"] if item["type"] == "Melee"), None)
    ranged = next((item for item in unit["weapons"] if item["type"] != "Melee"), None)
    ws = (melee or {}).get("ws") or "4+"
    bs = (ranged or {}).get("bs") or "4+"
    keywords = set(unit["keywords"])
    vehicle_like = bool(keywords & {"Vehicle", "Monster", "Titanic", "Towering"})
    if models == 1 and not vehicle_like:
        attacks = 1
    elif models == 1 and vehicle_like:
        attacks = max(1, round(wounds / 8))
    else:
        melee_attacks = (melee or {}).get("raw_a") or 2
        attacks = max(1, round(models * melee_attacks / 3.5))
    unit_wounds = max(1, round(models * wounds / 5))
    if models > 1 and wounds >= 2 and unit_wounds < 2:
        unit_wounds = 2
    return {
        "models": models,
        "M": stats.get("M") or '6"',
        "WS": ws,
        "BS": bs,
        "A": attacks,
        "W": unit_wounds,
        "Ld": leadership,
        "Sv": plus(apoc_save(toughness, save, invuln)),
        "PL": max(1, round(points / 20)) if points else None,
    }


def target_class(keywords: list[str]) -> str:
    keys = set(keywords)
    if keys & {"Titanic", "Towering"}:
        return "Super-heavy"
    if keys & {"Vehicle", "Monster"}:
        return "Heavy"
    return "Light"


def primary_role(keywords: list[str]) -> str:
    keys = set(keywords)
    if "Epic Hero" in keys:
        return "Epic Hero"
    if "Character" in keys:
        return "Character"
    if "Battleline" in keys:
        return "Battleline"
    if "Dedicated Transport" in keys:
        return "Dedicated Transport"
    if "Fortification" in keys:
        return "Fortification"
    if "Aircraft" in keys or "Flyer" in keys:
        return "Flyer"
    if "Monster" in keys:
        return "Monster"
    if "Vehicle" in keys:
        return "Vehicle"
    if "Mounted" in keys:
        return "Mounted"
    if "Beast" in keys:
        return "Beast"
    if "Swarm" in keys:
        return "Swarm"
    return "Infantry"


def desired_keywords(unit: dict) -> list[tuple[str, bool]]:
    """Return (category name, primary) pairs that should be linked."""
    keys = list(unit["keywords"])
    role = primary_role(keys)
    ordered = [role, target_class(keys)]
    if role == "Battleline":
        ordered.append("Troops")
    if "Epic Hero" in keys and role != "Epic Hero":
        ordered.append("Epic Hero")
    for name in (
        "Character",
        "Infantry",
        "Monster",
        "Vehicle",
        "Mounted",
        "Beast",
        "Swarm",
        "Fly",
        "Aircraft",
        "Fortification",
        "Transport",
        "Psyker",
        "Dedicated Transport",
        "Battleline",
    ):
        if name in keys and name not in ordered:
            ordered.append(name)
    for name in EXTRA_KEYWORDS:
        if name in keys and name not in ordered:
            ordered.append(name)
    result = []
    seen = set()
    for name in ordered:
        if name in seen:
            continue
        seen.add(name)
        result.append((name, name == role))
    return result


def scan_entries(text: str) -> dict[str, dict]:
    """One pass over selection entries. Root datasheets are entries with no selectionEntry parent."""
    entries: dict[str, dict] = {}
    token_re = re.compile(r"<selectionEntry\b([^>]*)>|</selectionEntry>")
    stack: list[dict] = []
    for match in token_re.finditer(text):
        if match.group(0).startswith("</"):
            if not stack:
                continue
            item = stack.pop()
            head = text[item["start"] : item["nested"] or match.start()]
            item["head"] = head
            item["has_unit"] = 'typeName="Unit"' in head
            if (item["has_unit"] or item["child_unit"]) and stack:
                stack[-1]["child_unit"] = True
            entries[item["id"]] = item
            continue
        attrs = match.group(1) or ""
        if attrs.rstrip().endswith("/"):
            continue

        def attr(key: str, attrs: str = attrs) -> str:
            found = re.search(rf'\b{key}="([^"]*)"', attrs)
            return found.group(1) if found else ""

        if stack and stack[-1]["nested"] is None:
            stack[-1]["nested"] = match.start()
        stack.append(
            {
                "id": attr("id"),
                "name": unescape(attr("name")),
                "type": attr("type"),
                "start": match.start(),
                "nested": None,
                "parent": stack[-1]["id"] if stack else None,
                "child_unit": False,
                "has_unit": False,
                "head": "",
            }
        )
    # Parents closed before their flag could propagate need a second walk.
    changed = True
    while changed:
        changed = False
        for item in entries.values():
            parent = entries.get(item["parent"] or "")
            if item["has_unit"] and parent and not parent["child_unit"]:
                parent["child_unit"] = True
                changed = True
    return entries


def load_apocalypse_index() -> dict[str, list[dict]]:
    """Map a normalised datasheet name to root selection entries that contain a unit profile."""
    index: dict[str, list[dict]] = {}
    for path in sorted(ROOT.glob("*.cat")):
        entries = scan_entries(path.read_text(encoding="utf-8"))
        for item in entries.values():
            if item["parent"]:
                continue
            datasheet = item["type"] == "unit" or (
                item["type"] == "upgrade" and "<categoryLink" in item["head"]
            )
            if not datasheet:
                continue
            name = item["name"]
            if re.search(r"\(\d+\s+models\)", name, re.I) or re.fullmatch(r"0?\d+\s+models", name, re.I):
                continue
            index.setdefault(norm(name), []).append(
                {
                    "file": path.name,
                    "id": item["id"],
                    "name": name,
                    "type": item["type"],
                }
            )
    return index


def unescape(text: str) -> str:
    return (
        text.replace("&apos;", "'")
        .replace("&quot;", '"')
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def find_entry_span(text: str, entry_id: str) -> tuple[int, int] | None:
    token = f'id="{entry_id}"'
    idx = text.find(token)
    if idx < 0:
        return None
    start = text.rfind("<selectionEntry", 0, idx)
    if start < 0 or text.startswith("<selectionEntryGroup", start):
        return None
    open_re = re.compile(r"<selectionEntry(?!Group)\b")
    pos = start
    depth = 0
    while pos < len(text):
        nxt_open = open_re.search(text, pos if depth == 0 else pos + 1)
        nxt_close = text.find("</selectionEntry>", pos if depth == 0 else pos + 1)
        if nxt_close < 0:
            return None
        open_at = nxt_open.start() if nxt_open else -1
        if open_at != -1 and open_at < nxt_close:
            depth += 1
            pos = open_at + 1
        else:
            depth -= 1
            pos = nxt_close + len("</selectionEntry>")
            if depth == 0:
                return start, pos
    return None


def direct_head(block: str) -> str:
    nested = re.search(r"\n[ \t]*<selectionEntry[ >]", block[1:])
    if not nested:
        return block
    return block[: nested.start() + 1]


def pl_targets(entries: dict[str, dict], entry_id: str) -> list[tuple[str, int, int | None]]:
    """Return (entry id, current PL, model count) for this datasheet and its size options."""
    results = []
    for item in entries.values():
        node_id = item["id"]
        belongs = node_id == entry_id
        parent = item.get("parent")
        while parent and not belongs:
            if parent == entry_id:
                belongs = True
                break
            parent = (entries.get(parent) or {}).get("parent")
        if not belongs or not item["has_unit"]:
            continue
        cost = re.search(
            r'<cost name=" PL" typeId="1466-da3f-0d27-dace" value="(-?\d+)"',
            item["head"],
        )
        if not cost:
            continue
        current = int(cost.group(1))
        if current == 0 and node_id == entry_id:
            continue
        count_match = re.search(r"(\d+)\s+models", item["name"], re.I)
        if not count_match:
            profile_name = re.search(r'<profile[^>]*name="([^"]+)"[^>]*typeName="Unit"', item["head"])
            if profile_name:
                count_match = re.search(r"(\d+)\s+models", unescape(profile_name.group(1)), re.I)
        models = int(count_match.group(1)) if count_match else None
        results.append((node_id, current, models))
    return results


def category_ids(text: str) -> dict[str, str]:
    found = {}
    for match in re.finditer(r'<categoryEntry id="([^"]+)" name="([^"]+)"', text):
        found[unescape(match.group(2))] = match.group(1)
    return found


def existing_links(head: str) -> set[str]:
    return set(re.findall(r'<categoryLink[^>]*name="([^"]+)"', head))


def newline_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def replace_pl(text: str, entry_id: str, new_value: int) -> tuple[str, bool]:
    span = find_entry_span(text, entry_id)
    if not span:
        return text, False
    block = text[span[0] : span[1]]
    head = direct_head(block)
    match = re.search(
        r'(<cost name=" PL" typeId="1466-da3f-0d27-dace" value=")(-?\d+)(")',
        head,
    )
    if not match or int(match.group(2)) == new_value:
        return text, False
    new_head = head[: match.start(2)] + str(new_value) + head[match.end(2) :]
    new_block = new_head + block[len(head) :]
    return text[: span[0]] + new_block + text[span[1] :], True


def insert_links(text: str, entry_id: str, links: list[str], categories: dict[str, str]) -> tuple[str, int]:
    span = find_entry_span(text, entry_id)
    if not span:
        return text, 0
    block = text[span[0] : span[1]]
    head = direct_head(block)
    present = {unescape(name) for name in existing_links(head)}
    nl = newline_of(text)
    fresh = []
    for name, primary in links:
        if name in present or name not in categories:
            continue
        fresh.append(
            f'        <categoryLink id="{IDS.get()}" name="{esc(name)}" hidden="false" '
            f'targetId="{categories[name]}" primary="{"true" if primary else "false"}"/>'
        )
        present.add(name)
    if not fresh:
        return text, 0
    has_primary = 'primary="true"' in head
    if has_primary:
        fresh = [line.replace('primary="true"', 'primary="false"') for line in fresh]
    payload = nl.join(fresh)
    if "<categoryLinks>" in head:
        close = head.find("</categoryLinks>")
        if close < 0:
            return text, 0
        new_head = head[:close] + payload + nl + "        " + head[close:]
    else:
        # Place the block immediately after the opening tag.
        end_of_open = head.find(">")
        if end_of_open < 0:
            return text, 0
        snippet = (
            f"{nl}      <categoryLinks>{nl}{payload}{nl}      </categoryLinks>"
        )
        new_head = head[: end_of_open + 1] + snippet + head[end_of_open + 1 :]
    new_block = new_head + block[len(head) :]
    return text[: span[0]] + new_block + text[span[1] :], len(fresh)


def unit_xml(unit: dict, categories: dict[str, str], faction_category: str | None) -> str:
    low = unit["min_models"]
    high = unit["max_models"]
    sizes = [low] if low == high else [low, high]
    profiles = []
    for models in sizes:
        points = unit["base_pts"] if models == low or not unit["alt_pts"] else unit["alt_pts"]
        if models != low and unit["alt_pts"] is None and unit["base_pts"]:
            points = unit["base_pts"] * models / low
        profiles.append(propose_profile(unit, models, points))
    links = desired_keywords(unit)
    link_xml = []
    for name, primary in links:
        if name not in categories:
            continue
        link_xml.append(
            f'        <categoryLink id="{IDS.get()}" name="{esc(name)}" hidden="false" '
            f'targetId="{categories[name]}" primary="{"true" if primary else "false"}"/>'
        )
    if faction_category and faction_category in categories:
        link_xml.append(
            f'        <categoryLink id="{IDS.get()}" name="{esc(faction_category)}" hidden="false" '
            f'targetId="{categories[faction_category]}" primary="false"/>'
        )
    unit_category = unit["name"].replace("[Legends]", "").strip()
    if unit_category in categories:
        link_xml.append(
            f'        <categoryLink id="{IDS.get()}" name="{esc(unit_category)}" hidden="false" '
            f'targetId="{categories[unit_category]}" primary="false"/>'
        )
    ability = "; ".join(unit["abilities"]) if unit["abilities"] else "No additional abilities."
    weapons_xml = []
    for weapon in unit["weapons"]:
        weapons_xml.append(
            f"""        <profile id="{IDS.get()}" name="{esc(weapon['name'])}" hidden="false" typeId="c9f1-094d-9681-28f3" typeName="Weapons">
          <characteristics>
            <characteristic name="Type" typeId="359f-19b3-6670-21f5">{esc(weapon['type'])}</characteristic>
            <characteristic name="Range" typeId="bea7-7040-8485-6f0f">{esc(weapon['range']).replace('"', '&quot;')}</characteristic>
            <characteristic name="A" typeId="2883-af07-d4e8-d8d0">{esc(weapon['attacks'])}</characteristic>
            <characteristic name="SAP" typeId="74b1-f85d-ede5-c758">{esc(weapon['sap'])}</characteristic>
            <characteristic name="SAT" typeId="4b6c-996a-d317-affb">{esc(weapon['sat'])}</characteristic>
            <characteristic name="Abilities" typeId="61ff-d2ec-f13b-06fa">{esc(weapon['abilities'])}</characteristic>
          </characteristics>
        </profile>"""
        )
    size_ids = [IDS.get() for _ in profiles]
    size_xml = []
    for profile, size_id in zip(profiles, size_ids):
        label = f"{profile['models']:02d} models" if profile["models"] < 10 else f"{profile['models']} models"
        move = esc(profile["M"]).replace('"', "&quot;")
        pl = profile["PL"] if profile["PL"] is not None else 1
        size_xml.append(
            f"""            <selectionEntry id="{size_id}" name="{label}" hidden="false" collective="false" import="true" type="upgrade">
              <profiles>
                <profile id="{IDS.get()}" name="{esc(unit['name'])} ({profile['models']} models)" hidden="false" typeId="758b-2459-9a46-721a" typeName="Unit">
                  <characteristics>
                    <characteristic name="M" typeId="606d-344a-bc3d-9dce">{move}</characteristic>
                    <characteristic name="WS" typeId="e2a3-fade-c12d-860b">{esc(profile['WS'])}</characteristic>
                    <characteristic name="BS" typeId="bcfe-d5af-2691-5c77">{esc(profile['BS'])}</characteristic>
                    <characteristic name="A" typeId="ddfe-6a9e-32c1-a51c">{profile['A']}</characteristic>
                    <characteristic name="W" typeId="7c7f-f763-1f39-410c">{profile['W']}</characteristic>
                    <characteristic name="Ld" typeId="91b0-3d37-1843-1290">{profile['Ld']}</characteristic>
                    <characteristic name="Sv" typeId="a56f-38ae-3917-aadc">{esc(profile['Sv'])}</characteristic>
                  </characteristics>
                </profile>
              </profiles>
              <costs>
                {PL_COST.format(value=pl)}
              </costs>
            </selectionEntry>"""
        )
    group = ""
    if len(size_xml) > 1:
        group = f"""
      <selectionEntryGroups>
        <selectionEntryGroup id="{IDS.get()}" name="{sizes[0]} - {sizes[-1]} models" hidden="false" collective="false" import="true" defaultSelectionEntryId="{size_ids[0]}">
          <constraints>
            <constraint field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" id="{IDS.get()}" type="min"/>
            <constraint field="selections" scope="parent" value="1" percentValue="false" shared="true" includeChildSelections="false" includeChildForces="false" id="{IDS.get()}" type="max"/>
          </constraints>
          <selectionEntries>
{chr(10).join(size_xml)}
          </selectionEntries>
        </selectionEntryGroup>
      </selectionEntryGroups>"""
        body_profiles = weapons_xml
        costs = f"""      <costs>
        {PL_COST.format(value=0)}
      </costs>"""
    else:
        group = ""
        only = size_xml[0]
        # Pull the single profile up onto the unit entry.
        profile_match = re.search(r"<profiles>\s*(<profile id=.*?</profile>)\s*</profiles>", only, re.S)
        cost_match = re.search(r"(<cost name=\" PL\".*?/>)", only)
        body_profiles = []
        if profile_match:
            body_profiles.append("        " + profile_match.group(1).replace("\n", "\n        "))
        body_profiles.extend(weapons_xml)
        pl_xml = cost_match.group(1) if cost_match else PL_COST.format(value=1)
        costs = f"""      <costs>
        {pl_xml}
      </costs>"""
    profiles_block = "\n".join(body_profiles)
    link_block = "\n".join(link_xml)
    legends_block = ""
    if unit.get("legends"):
        legends_block = f"""
      <modifiers>
        <modifier type="set" field="hidden" value="true">
          <conditions>
            <condition field="selections" scope="force" value="1" percentValue="false" shared="true" includeChildSelections="true" includeChildForces="false" childId="{SHOW_LEGENDS_ID}" type="lessThan"/>
          </conditions>
        </modifier>
      </modifiers>"""
    return f"""    <selectionEntry id="{IDS.get()}" name="{esc(unit['name'])}" hidden="false" collective="false" import="true" type="unit">
      <comment>Inferred from the 11th edition datasheet. SAP and SAT are calibrated estimates.</comment>{legends_block}
      <profiles>
        <profile id="{IDS.get()}" name="Abilities" hidden="false" typeId="f075-616f-79da-32a6" typeName="Abilities">
          <characteristics>
            <characteristic name="Description" typeId="4493-9fa3-8c30-866f">{esc(ability)}</characteristic>
          </characteristics>
        </profile>
{profiles_block}
      </profiles>
      <categoryLinks>
{link_block}
      </categoryLinks>{group}
      <entryLinks>
        <entryLink id="{IDS.get()}" name="Commander" hidden="false" collective="false" import="true" targetId="7347-5716-355f-9165" type="selectionEntry"/>
      </entryLinks>
{costs}
    </selectionEntry>"""


def insert_before(text: str, pattern: str, payload: str) -> str:
    match = re.search(pattern, text, re.M)
    if not match:
        raise RuntimeError(f"Could not find insertion point {pattern!r}")
    return text[: match.start()] + payload + text[match.start() :]


def ensure_catalogue(filename: str, title: str) -> None:
    path = ROOT / filename
    if path.exists():
        return
    faction = f"Faction: {title}"
    content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<catalogue id="{IDS.get()}" name="{esc(title)}" revision="1" battleScribeVersion="2.03" authorName="Community Apocalypse" library="false" gameSystemId="{GAME_SYSTEM_ID}" gameSystemRevision="21" xmlns="{NS_CAT}" type="catalogue">
  <categoryEntries>
    <categoryEntry id="{IDS.get()}" name="{esc(faction)}" hidden="false"/>
  </categoryEntries>
  <selectionEntries>
  </selectionEntries>
</catalogue>
"""
    path.write_text(content, encoding="utf-8")


def root_insert_pattern(text: str, filename: str) -> str:
    if filename == "Library_Space_Marines.cat" or "\n  <sharedSelectionEntries>" in text and "\n  <selectionEntries>" not in text:
        return r"^  </sharedSelectionEntries>$"
    return r"^  </selectionEntries>$"


def faction_category_name(catalogue_name: str) -> str:
    return f"Faction: {catalogue_name}"


def catalogue_title(text: str) -> str:
    match = re.search(r'<catalogue[^>]*name="([^"]+)"', text)
    return unescape(match.group(1)) if match else ""


def bump_revision(text: str) -> str:
    match = re.search(r'(<catalogue[^>]*revision=")(\d+)(")', text)
    if not match:
        return text
    return text[: match.start(2)] + str(int(match.group(2)) + 1) + text[match.end(2) :]


def write_reports(units: list[dict], apoc_index: dict[str, list[dict]]) -> dict:
    REPORTS.mkdir(exist_ok=True)
    by_source: dict[str, list[dict]] = {}
    for unit in units:
        by_source.setdefault(unit["source"], []).append(unit)
    summary = ["# 11th edition gap report", "", "Power Level uses round(points / 20), minimum 1.", ""]
    created = []
    matched = []
    for source, group in sorted(by_source.items()):
        target = group[0]["target"]
        lines = [f"# {source}", "", f"Catalogue: `{target}`", ""]
        new_lines = []
        match_lines = []
        only_apoc_note = ""
        for unit in group:
            key = norm(unit["name"])
            hits = apoc_index.get(key) or []
            if hits:
                matched.append(unit)
                points = unit["base_pts"]
                alt = unit["alt_pts"]
                proposal = propose_profile(unit, unit["min_models"], points)
                match_lines.append(
                    f"- {unit['name']}: matched {len(hits)} existing entr{'y' if len(hits)==1 else 'ies'}; "
                    f"11e points {points if points is not None else 'unknown'}"
                    f"{'' if alt is None else f' / {alt}'}; "
                    f"proposed minimum PL {proposal['PL'] if proposal['PL'] is not None else 'unchanged'}."
                )
            elif unit["legends"]:
                match_lines.append(f"- {unit['name']}: Legends, not created on this pass.")
            else:
                created.append(unit)
                low = propose_profile(unit, unit["min_models"], unit["base_pts"])
                high = None
                if unit["max_models"] != unit["min_models"]:
                    points = unit["alt_pts"] or (
                        unit["base_pts"] * unit["max_models"] / unit["min_models"] if unit["base_pts"] else None
                    )
                    high = propose_profile(unit, unit["max_models"], points)
                weapon_bits = ", ".join(
                    f"{item['name']} {item['type']} {item['range']} A{item['attacks']} SAP {item['sap']} SAT {item['sat']}"
                    for item in unit["weapons"]
                ) or "no default weapon"
                new_lines.append(
                    f"- **{unit['name']}** ({unit['min_models']}"
                    f"{'' if high is None else f'-{unit['max_models']}'} models). "
                    f"M {low['M']}, WS {low['WS']}, BS {low['BS']}, A {low['A']}, W {low['W']}, "
                    f"Ld {low['Ld']}, Sv {low['Sv']}, PL {low['PL']}."
                    + (
                        f" Maximum size A {high['A']}, W {high['W']}, PL {high['PL']}."
                        if high
                        else ""
                    )
                    + f" Keywords: {', '.join(unit['keywords']) or 'none'}. Weapons: {weapon_bits}."
                )
        lines.append(f"Matched or already present: {len(match_lines) - sum(1 for u in group if u['legends'] and not apoc_index.get(norm(u['name'])))}.")
        lines.append(f"New matched-play datasheets: {len(new_lines)}.")
        lines.append("")
        lines.append("## New datasheets")
        lines.append("")
        lines.extend(new_lines or ["None."])
        lines.append("")
        lines.append("## Already in the catalogues")
        lines.append("")
        lines.extend(match_lines or ["None."])
        lines.append("")
        lines.append(only_apoc_note)
        (REPORTS / f"{Path(source).stem}.md").write_text("\n".join(lines), encoding="utf-8")
        summary.append(
            f"- {source} -> `{target}`: {len(new_lines)} new matched-play datasheets, "
            f"{sum(1 for u in group if apoc_index.get(norm(u['name'])))} already present."
        )
    missing_cats = sorted({name for name in NEW_CATALOGUES if not (ROOT / name).exists()})
    summary.extend(["", "## Factions without a catalogue before this update", ""])
    summary.extend(f"- `{name}`" for name in missing_cats)
    summary.append("")
    (REPORTS / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    return {"created": created, "matched": matched}


def calibration_report() -> None:
    lines = ["# SAP / SAT calibration check", "", "Printed 2019 value, then the estimate used for new weapons.", ""]
    for name, strength, ap, damage, sap, sat in OFFICIAL_WEAPONS:
        guess_sap, guess_sat = sap_sat(strength, ap, float(damage if damage < 6 else 3.5 if damage == 6 else damage))
        # The tuples store D6 as 6 to mean a high damage roll. Pass the real scale.
        lines.append(
            f"- {name}: printed SAP {sap}+ SAT {sat}+; estimate SAP {guess_sap}+ SAT {guess_sat}+ "
            f"(S{strength} AP-{ap} D{damage})."
        )
    # Recompute lascannon and multi-melta with D6-scale damage explicitly.
    lines.append("")
    lines.append("High-damage guns use a D6-scale damage of 3.5 when the printed Damage is D6:")
    for name, strength, ap, sap, sat in (
        ("Lascannon", 9, 3, 10, 5),
        ("Multi-melta", 8, 4, 10, 4),
    ):
        guess_sap, guess_sat = sap_sat(strength, ap, 3.5)
        lines.append(f"- {name}: printed {sap}+/{sat}+; estimate {guess_sap}+/{guess_sat}+.")
    lines.append("")
    lines.append("Save checks against printed sheets: Intercessor T4 Sv3+ -> "
                 f"{plus(apoc_save(4, 3, None))}; Captain T4 Sv3+ 4++ -> {plus(apoc_save(4, 3, 4))}; "
                 f"Terminator T4 Sv2+ -> {plus(apoc_save(4, 2, 5))}; Scout T4 Sv4+ -> {plus(apoc_save(4, 4, None))}; "
                 f"Aggressor T5 Sv3+ -> {plus(apoc_save(5, 3, None))}; Rhino T7 Sv3+ -> {plus(apoc_save(7, 3, None))}; "
                 f"Land Raider T8 Sv2+ -> {plus(apoc_save(8, 2, None))}.")
    (REPORTS / "calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_11e_weapons() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for path in SRC_11E.glob("*.json"):
        if path.name == "Warhammer 40,000.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        catalogue = data.get("catalogue") or {}
        for node in walk(catalogue):
            if node.get("typeName") not in ("Ranged Weapons", "Melee Weapons"):
                continue
            raw = chars_of(node)
            name = node.get("name")
            if not name:
                continue
            grouped.setdefault(norm(name), []).append(
                {
                    "range": raw.get("Range"),
                    "abilities": ability_text(raw.get("Keywords") or ""),
                }
            )
    return grouped


def sync_shared_weapons(path: Path, weapon_index: dict[str, list[dict]]) -> int:
    text = path.read_text(encoding="utf-8")
    updated = 0
    matches = list(re.finditer(r'<profile id="[^"]+" name="([^"]+)"[^>]*typeName="Weapons">', text))
    for match in reversed(matches):
        name = unescape(match.group(1))
        variants = weapon_index.get(norm(name))
        if not variants:
            continue
        ranges = {item["range"] for item in variants if item["range"]}
        abilities = {item["abilities"] for item in variants}
        start = match.start()
        end = text.find("</profile>", start)
        if end < 0:
            continue
        end += len("</profile>")
        block = text[start:end]
        new_block = block
        if len(ranges) == 1:
            new_range = esc(next(iter(ranges))).replace('"', "&quot;")
            range_match = re.search(
                r'(<characteristic name="Range"[^>]*>)(.*?)(</characteristic>)',
                new_block,
            )
            if range_match and unescape(range_match.group(2)).replace("&quot;", '"') != next(iter(ranges)):
                new_block = (
                    new_block[: range_match.start(2)]
                    + new_range
                    + new_block[range_match.end(2) :]
                )
        if len(abilities) == 1:
            ability = next(iter(abilities))
            if ability != "-":
                ability_match = re.search(
                    r'(<characteristic name="Abilities"[^>]*>)(.*?)(</characteristic>)',
                    new_block,
                )
                if ability_match:
                    current = unescape(ability_match.group(2))
                    if current in {"", "-"}:
                        merged = ability
                    elif ability not in current:
                        merged = current + ", " + ability
                    else:
                        merged = current
                    if merged != current:
                        new_block = (
                            new_block[: ability_match.start(2)]
                            + esc(merged)
                            + new_block[ability_match.end(2) :]
                        )
        if new_block != block:
            text = text[:start] + new_block + text[end:]
            updated += 1
    if updated:
        path.write_text(bump_revision(text), encoding="utf-8")
    return updated


def apply(rebuild: bool = False) -> None:
    REPORTS.mkdir(exist_ok=True)
    if rebuild:
        for path in sorted(ROOT.glob("*.cat")):
            original = path.read_text(encoding="utf-8")
            stripped = strip_inferred(original)
            if stripped != original:
                ET.fromstring(stripped)
                path.write_text(stripped, encoding="utf-8")
                print(f"Cleared earlier inferred datasheets from {path.name}")
    print("Loading 11th edition units...")
    units = load_11e_units()
    print(f"  {len(units)} units")
    print("Indexing Apocalypse catalogues...")
    apoc_index = load_apocalypse_index()
    print(f"  {sum(len(v) for v in apoc_index.values())} datasheets")
    calibration_report()
    plan = write_reports(units, apoc_index)
    print(f"  {len(plan['created'])} new matched-play datasheets")

    for filename, title in NEW_CATALOGUES.items():
        ensure_catalogue(filename, title)

    # Group work by target file.
    by_file: dict[str, list[dict]] = {}
    for unit in units:
        by_file.setdefault(unit["target"], []).append(unit)

    gst_path = ROOT / GST_NAME if (ROOT / GST_NAME).exists() else ROOT / OLD_GST_NAME
    gst_text = gst_path.read_text(encoding="utf-8")
    gst_categories = category_ids(gst_text)

    for filename, group in sorted(by_file.items()):
        path = ROOT / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        entries = scan_entries(text)
        file_categories = category_ids(text)
        categories = {**gst_categories, **file_categories}
        title = catalogue_title(text)
        faction = faction_category_name(title) if f"Faction: {title}" in categories or True else None
        # Local faction category may use a shorter name. Prefer one that already exists.
        faction_link = None
        for existing in categories:
            if existing.startswith("Faction:") and norm(existing).endswith(norm(title)):
                faction_link = existing
                break
        changed = False
        # Power Level and keywords on matched entries in this file only.
        matched_here = []
        for unit in group:
            for hit in apoc_index.get(norm(unit["name"]), []):
                if hit["file"] == filename:
                    matched_here.append((unit, hit))
        # Apply from the end of the file so earlier spans stay valid.
        edits = []
        for unit, hit in matched_here:
            for child_id, current, models in pl_targets(entries, hit["id"]):
                if unit["base_pts"] is None:
                    continue
                if models is None or models <= unit["min_models"] or unit["max_models"] == unit["min_models"]:
                    points = unit["base_pts"]
                elif unit["alt_pts"] is not None and models >= unit["max_models"]:
                    points = unit["alt_pts"]
                elif unit["alt_pts"] is not None and unit["max_models"] != unit["min_models"]:
                    span = (models - unit["min_models"]) / (unit["max_models"] - unit["min_models"])
                    points = unit["base_pts"] + (unit["alt_pts"] - unit["base_pts"]) * span
                else:
                    points = unit["base_pts"] * models / max(1, unit["min_models"])
                new_pl = max(1, round(points / 20))
                if new_pl != current:
                    edits.append((child_id, new_pl))
        for child_id, new_pl in sorted(edits, key=lambda item: text.find(f'id="{item[0]}"'), reverse=True):
            text, did = replace_pl(text, child_id, new_pl)
            changed = changed or did
        for unit, hit in matched_here:
            links = desired_keywords(unit)
            text, count = insert_links(text, hit["id"], links, categories)
            if count:
                changed = True
        # New units.
        fresh = [
            unit
            for unit in group
            if not unit["legends"] and not apoc_index.get(norm(unit["name"]))
        ]
        # A unit can be listed twice if two json files share a target. Create it once.
        seen = set()
        unique = []
        for unit in fresh:
            key = norm(unit["name"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(unit)
        if unique:
            new_categories = []
            for unit in unique:
                label = unit["name"].replace("[Legends]", "").strip()
                if label not in categories:
                    new_categories.append(
                        f'    <categoryEntry id="{IDS.get()}" name="{esc(label)}" hidden="false"/>'
                    )
                    categories[label] = new_categories[-1].split('id="')[1].split('"')[0]
            if new_categories and re.search(r"^  </categoryEntries>$", text, re.M):
                text = insert_before(text, r"^  </categoryEntries>$", "\n".join(new_categories) + "\n")
                changed = True
            blocks = [unit_xml(unit, categories, faction_link) for unit in unique]
            pattern = root_insert_pattern(text, filename)
            text = insert_before(text, pattern, "\n".join(blocks) + "\n")
            changed = True
            for unit in unique:
                apoc_index.setdefault(norm(unit["name"]), []).append(
                    {"file": filename, "id": "", "name": unit["name"], "type": "unit"}
                )
        if changed:
            text = bump_revision(text)
            ET.fromstring(text)
            path.write_text(text, encoding="utf-8")
            print(f"Updated {filename}: {len(edits)} power changes considered, {len(unique)} new units")

    # Shared weapon range and ability refresh.
    weapon_index = collect_11e_weapons()
    for filename in ("Library_Weapons.cat", "Library_Space_Marines.cat"):
        count = sync_shared_weapons(ROOT / filename, weapon_index)
        print(f"Weapon profiles refreshed in {filename}: {count}")

    update_game_system(gst_path)


def legend_line(unit: dict) -> str:
    low = propose_profile(unit, unit["min_models"], unit["base_pts"])
    high = None
    if unit["max_models"] != unit["min_models"]:
        points = unit["alt_pts"] or (
            unit["base_pts"] * unit["max_models"] / unit["min_models"] if unit["base_pts"] else None
        )
        high = propose_profile(unit, unit["max_models"], points)
    weapon_bits = ", ".join(
        f"{item['name']} {item['type']} {item['range']} A{item['attacks']} SAP {item['sap']} SAT {item['sat']}"
        for item in unit["weapons"]
    ) or "no default weapon"
    return (
        f"- **{unit['name']}** ({unit['min_models']}"
        f"{'' if high is None else f'-{unit['max_models']}'} models). "
        f"M {low['M']}, WS {low['WS']}, BS {low['BS']}, A {low['A']}, W {low['W']}, "
        f"Ld {low['Ld']}, Sv {low['Sv']}, PL {low['PL']}."
        + (f" Maximum size A {high['A']}, W {high['W']}, PL {high['PL']}." if high else "")
        + f" Keywords: {', '.join(unit['keywords']) or 'none'}. Weapons: {weapon_bits}."
    )


def apply_legends() -> None:
    """Add 11th edition Legends datasheets that are not already in the catalogues."""
    REPORTS.mkdir(exist_ok=True)
    print("Loading 11th edition Legends units...")
    units = [unit for unit in load_11e_units() if unit["legends"]]
    print(f"  {len(units)} Legends units")
    apoc_index = load_apocalypse_index()
    by_file: dict[str, list[dict]] = {}
    for unit in units:
        by_file.setdefault(unit["target"], []).append(unit)

    summary = [
        "# 11th edition Legends",
        "",
        "These datasheets are hidden until Show Legends is selected.",
        "Power Level uses round(points / 20), minimum 1.",
        "",
    ]
    gst_path = ROOT / GST_NAME if (ROOT / GST_NAME).exists() else ROOT / OLD_GST_NAME
    gst_categories = category_ids(gst_path.read_text(encoding="utf-8"))
    created_total = 0

    for filename, group in sorted(by_file.items()):
        path = ROOT / filename
        if not path.exists():
            summary.append(f"- `{filename}` is missing; skipped {len(group)} Legends units.")
            continue
        text = path.read_text(encoding="utf-8")
        entries = scan_entries(text)
        categories = {**gst_categories, **category_ids(text)}
        title = catalogue_title(text)
        faction_link = None
        for existing in categories:
            if existing.startswith("Faction:") and norm(existing).endswith(norm(title)):
                faction_link = existing
                break
        fresh = []
        already = []
        seen = set()
        for unit in group:
            key = norm(unit["name"])
            if key in seen:
                continue
            seen.add(key)
            if apoc_index.get(key):
                already.append(unit)
            else:
                fresh.append(unit)
        changed = False
        edits = []
        for unit in already:
            for hit in apoc_index.get(norm(unit["name"]), []):
                if hit["file"] != filename:
                    continue
                for child_id, current, models in pl_targets(entries, hit["id"]):
                    if unit["base_pts"] is None:
                        continue
                    if models is None or models <= unit["min_models"] or unit["max_models"] == unit["min_models"]:
                        points = unit["base_pts"]
                    elif unit["alt_pts"] is not None and models >= unit["max_models"]:
                        points = unit["alt_pts"]
                    elif unit["alt_pts"] is not None and unit["max_models"] != unit["min_models"]:
                        span = (models - unit["min_models"]) / (unit["max_models"] - unit["min_models"])
                        points = unit["base_pts"] + (unit["alt_pts"] - unit["base_pts"]) * span
                    else:
                        points = unit["base_pts"] * models / max(1, unit["min_models"])
                    new_pl = max(1, round(points / 20))
                    if new_pl != current:
                        edits.append((child_id, new_pl))
                text, count = insert_links(text, hit["id"], desired_keywords(unit), categories)
                if count:
                    changed = True
        for child_id, new_pl in sorted(edits, key=lambda item: text.find(f'id="{item[0]}"'), reverse=True):
            text, did = replace_pl(text, child_id, new_pl)
            changed = changed or did
        if fresh:
            new_categories = []
            for unit in fresh:
                label = unit["name"].replace("[Legends]", "").strip()
                if label not in categories:
                    new_categories.append(
                        f'    <categoryEntry id="{IDS.get()}" name="{esc(label)}" hidden="false"/>'
                    )
                    categories[label] = new_categories[-1].split('id="')[1].split('"')[0]
            if new_categories and re.search(r"^  </categoryEntries>$", text, re.M):
                text = insert_before(text, r"^  </categoryEntries>$", "\n".join(new_categories) + "\n")
            blocks = [unit_xml(unit, categories, faction_link) for unit in fresh]
            text = insert_before(text, root_insert_pattern(text, filename), "\n".join(blocks) + "\n")
            changed = True
            for unit in fresh:
                apoc_index.setdefault(norm(unit["name"]), []).append(
                    {"file": filename, "id": "", "name": unit["name"], "type": "unit"}
                )
        if changed:
            text = bump_revision(text)
            ET.fromstring(text)
            path.write_text(text, encoding="utf-8")
        created_total += len(fresh)
        print(f"{filename}: {len(fresh)} new Legends, {len(already)} already present")
        summary.append(
            f"- `{filename}`: {len(fresh)} new Legends datasheets, {len(already)} already present."
        )
        detail = [f"# {filename}", "", f"New: {len(fresh)}. Already present: {len(already)}.", "", "## New", ""]
        detail.extend(legend_line(unit) for unit in fresh)
        detail.extend(["", "## Already present", ""])
        detail.extend(f"- {unit['name']}" for unit in already)
        detail.append("")
        legends_dir = REPORTS / "legends"
        legends_dir.mkdir(exist_ok=True)
        (legends_dir / f"{Path(filename).stem}.md").write_text("\n".join(detail), encoding="utf-8")

    summary.extend(["", f"Created {created_total} Legends datasheets.", ""])
    (REPORTS / "legends_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Created {created_total} Legends datasheets")


def update_game_system(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'name="Warhammer 40,000 Apocalypse 10th Edition"',
        'name="Warhammer 40,000 Apocalypse 11th Edition"',
    )
    if 'name="11th edition datasheets"' not in text:
        publication = (
            f'    <publication id="{IDS.get()}" name="11th edition datasheets" '
            f'shortName="11e" publicationDate="2026"/>\n'
        )
        text = text.replace("  </publications>", publication + "  </publications>")
    existing = category_ids(text)
    additions = []
    for name in EXTRA_KEYWORDS:
        if name not in existing:
            additions.append(
                f'    <categoryEntry id="{IDS.get()}" name="{name}" hidden="false"/>'
            )
    if additions:
        text = text.replace("  </categoryEntries>", "\n".join(additions) + "\n  </categoryEntries>")
    match = re.search(r'(<gameSystem[^>]*revision=")(\d+)(")', text)
    if match:
        text = text[: match.start(2)] + str(int(match.group(2)) + 1) + text[match.end(2) :]
    ET.fromstring(text)
    dest = ROOT / GST_NAME
    dest.write_text(text, encoding="utf-8")
    if path.name != GST_NAME and path.exists():
        path.unlink()
    print(f"Game system written to {dest.name}")


if __name__ == "__main__":
    apply_legends()
