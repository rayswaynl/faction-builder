"""
gen_unit_catalog.py
-------------------
Reads arma2-co-config-reference/Config/CfgVehicles.txt and
the Images dir, then emits:

    assets/data/units.json
        { <classname>: { name, type, thumb } }
        type: "man" | "car" | "tank" | "air" | "static" | "other"
        thumb: "<classname>.jpg" (relative to assets/thumbs/) or null

    assets/thumbs/<classname>.jpg   (copied from Images)

Coverage: every class with scope=2 in CfgVehicles (playable/visible).
          Classified by parent-class lineage.
"""

import re
import os
import json
import shutil

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REF_DIR = r"C:\Users\Steff\arma2-co-config-reference"
CFG_VEHICLES = os.path.join(REF_DIR, "Config", "CfgVehicles.txt")
IMAGES_DIR = os.path.join(REF_DIR, "Images")

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "data")
THUMBS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "thumbs")
OUT_FILE = os.path.join(OUT_DIR, "units.json")

# ---------------------------------------------------------------------------
# Classification: parent-class → type
# Known hierarchy anchors in CfgVehicles (A2/OA):
#   Man → "man"
#   Car, Truck, Motorcycle, Tank_West/East, Wheeled_APC → "car" or "tank"
#   Air (includes Plane, Helicopter) → "air"
#   Static (mortars, guns, AA) → "static"
#   The tree is deep; we classify by walking the inheritance chain.
# ---------------------------------------------------------------------------

MAN_ROOTS = {"Man"}
CAR_ROOTS = {"Car", "Truck", "Motorcycle", "APC"}
TANK_ROOTS = {"Tank", "Tank_West", "Tank_East", "Tank_Gue", "Wheeled_APC",
              "APC_Wheeled", "APC_tracked"}
AIR_ROOTS = {"Air", "Plane", "Helicopter", "UAV"}
STATIC_ROOTS = {"Static", "StaticMortar", "StaticWeapon", "StaticMGWeapon",
                "StaticATWeapon", "StaticAAWeapon", "StaticCannon"}


def classify(classname, parent_map):
    """Walk up the parent chain from classname and return a type string."""
    visited = set()
    current = classname
    chain = []
    while current and current not in visited:
        chain.append(current)
        visited.add(current)
        if current in MAN_ROOTS:
            return "man"
        if current in CAR_ROOTS:
            return "car"
        if current in TANK_ROOTS:
            return "tank"
        if current in AIR_ROOTS:
            return "air"
        if current in STATIC_ROOTS:
            return "static"
        current = parent_map.get(current)
    return "other"


# ---------------------------------------------------------------------------
# Parse CfgVehicles.txt
#
# The Bohemia CfgVehicles config is a deeply nested class tree.
# Strategy: two-pass regex scan over the full file text.
#   Pass 1: find all  class Foo : Bar  occurrences → parent_map
#   Pass 2: for each class block, extract scope and displayName.
#
# We locate each class block by finding the opening { after the class line
# and scanning for the matching closing }. This is done line-by-line but
# without the recursive descent issue: we scan ALL class lines independently
# rather than consuming inner content in an outer scan.
# ---------------------------------------------------------------------------

_CLASS_LINE_RE = re.compile(r"^\s*class\s+(\w+)\s*(?::\s*(\w+))?\s*[\r\n]")
_SCOPE_LINE_RE = re.compile(r"^\s*scope\s*=\s*(\d+)\s*;")
_NAME_LINE_RE = re.compile(r'^\s*displayName\s*=\s*"([^"]*)"')


def parse_cfg_vehicles(path):
    """
    Returns:
        parent_map  {classname: parent_classname}
        entries     {classname: {displayName, scope}}
    Only classes with scope=2 appear in entries.
    """
    parent_map = {}
    entries = {}

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    n = len(lines)

    for i, line in enumerate(lines):
        m = _CLASS_LINE_RE.match(line)
        if not m:
            continue
        classname = m.group(1)
        parent = m.group(2) or ""
        if parent:
            parent_map[classname] = parent

        # Scan the immediately following block (depth=1) for scope+displayName.
        # We look ahead up to ~200 lines to find the block opening and then
        # stop at depth=0. This avoids consuming the whole file for outer classes
        # by capping the scan at the FIRST depth-0 close (which for real leaf
        # classes is the end of their own block).
        scope = None
        display_name = ""
        depth = 0
        found_open = False
        j = i + 1
        limit = min(n, i + 500)  # leaf blocks are small; bail out if too deep

        while j < limit:
            ln = lines[j]
            if not found_open:
                if "{" in ln:
                    depth += ln.count("{")
                    depth -= ln.count("}")
                    found_open = True
                j += 1
                continue

            if "{" in ln:
                depth += ln.count("{")
            if "}" in ln:
                depth -= ln.count("}")

            if depth <= 0:
                break  # end of this class's own block

            if scope is None:
                ms = _SCOPE_LINE_RE.match(ln)
                if ms:
                    scope = int(ms.group(1))

            if not display_name:
                mn = _NAME_LINE_RE.match(ln)
                if mn:
                    display_name = mn.group(1)

            j += 1

        if scope == 2:
            entries[classname] = {
                "displayName": display_name,
                "scope": scope,
            }

    return parent_map, entries


# ---------------------------------------------------------------------------
# Build thumbnail index: recursively scan Images dir,
# build {stem_lower: full_path} for fast lookup.
# ---------------------------------------------------------------------------

def build_thumb_index(images_dir):
    index = {}
    for root, dirs, files in os.walk(images_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".jpg", ".png", ".jpeg"):
                stem = os.path.splitext(fname)[0]
                # Case-insensitive key; keep first found (A2 before OA)
                key = stem.lower()
                if key not in index:
                    index[key] = os.path.join(root, fname)
    return index


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)

    print("Parsing CfgVehicles.txt...")
    parent_map, entries = parse_cfg_vehicles(CFG_VEHICLES)
    print(f"  {len(parent_map)} class inheritances")
    print(f"  {len(entries)} scope=2 entries")

    print("Building thumbnail index...")
    thumb_index = build_thumb_index(IMAGES_DIR)
    print(f"  {len(thumb_index)} thumbnails found")

    print("Building catalog...")
    catalog = {}
    thumb_hits = 0
    type_counts = {}

    for classname, info in sorted(entries.items()):
        unit_type = classify(classname, parent_map)
        type_counts[unit_type] = type_counts.get(unit_type, 0) + 1

        # Resolve thumbnail
        key = classname.lower()
        thumb_src = thumb_index.get(key)
        thumb_ref = None
        if thumb_src:
            ext = os.path.splitext(thumb_src)[1]
            dest_name = classname + ext
            dest_path = os.path.join(THUMBS_DIR, dest_name)
            if not os.path.exists(dest_path):
                shutil.copy2(thumb_src, dest_path)
            thumb_ref = dest_name
            thumb_hits += 1

        catalog[classname] = {
            "name": info["displayName"] or classname,
            "type": unit_type,
            "thumb": thumb_ref,
        }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUT_FILE}")
    print(f"  Total classes: {len(catalog)}")
    print(f"  Thumb coverage: {thumb_hits}/{len(catalog)} "
          f"({100*thumb_hits//len(catalog)}%)")
    print(f"  Type breakdown: {type_counts}")


if __name__ == "__main__":
    main()
