"""
extract_faction_template.py
---------------------------
Reads all GUE faction SQF files and emits:
    assets/data/faction-template.json

The JSON contains:
  - files: [{relpath, text}]  raw file texts for template substitution
  - root_vars: {key: gue_value}  WFBE_%1KEY variables from Root_GUE.sqf
  - structures: [{key, classname, cost, time, mhq, hq, defense_names}]
  - core_rows: [{classname, tuple}]  from Core_GUE.sqf
  - flags: [{faction, paa}]  from all Root_*.sqf
  - registration: {factions_west, factions_east, factions_guer, indices,
                   init_common_include_pattern}
"""

import re
import json
import os
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
COMMON = (
    r"C:\Users\Steff\a2waspwarfare\Missions"
    r"\[55-2hc]warfarev2_073v48co.chernarus\Common"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "data")
OUT_FILE = os.path.join(OUT_DIR, "faction-template.json")

# GUE faction files to capture as raw templates (relpath from COMMON)
GUE_FILES = [
    r"Config\Core\Core_GUE.sqf",
    r"Config\Core_Root\Root_GUE.sqf",
    r"Config\Core_Structures\Structures_GUE.sqf",
    r"Config\Core_Structures\Structures_CO_GUE.sqf",
    r"Config\Core_Units\Units_GUE.sqf",
    r"Config\Core_Units\Units_CO_GUE.sqf",
    r"Config\Core_Upgrades\Upgrades_GUE.sqf",
    r"Config\Core_Upgrades\Upgrades_CO_GUE.sqf",
    r"Config\Core_Squads\Squad_GUE.sqf",
    r"Config\Core_Artillery\Artillery_GUE.sqf",
    r"Config\Core_Artillery\Artillery_CO_GUE.sqf",
    r"Config\Defenses\Defenses_GUE.sqf",
    r"Config\Gear\Gear_GUE.sqf",
    r"Config\Groups\Groups_GUE.sqf",
    r"Config\Loadout\Loadout_GUE.sqf",
]

ROOT_DIR = os.path.join(COMMON, r"Config\Core_Root")
INIT_CONSTANTS = os.path.join(COMMON, r"Init\Init_CommonConstants.sqf")
INIT_COMMON = os.path.join(COMMON, r"Init\Init_Common.sqf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_sqf(path):
    """Read a SQF file, trying UTF-8 then latin-1."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, encoding="latin-1") as f:
            return f.read()


# ---------------------------------------------------------------------------
# 1. Collect raw file texts
# ---------------------------------------------------------------------------

def collect_files():
    files = []
    for relpath in GUE_FILES:
        abs_path = os.path.join(COMMON, relpath)
        if not os.path.exists(abs_path):
            continue  # CO variants may not exist in all installs
        text = read_sqf(abs_path)
        files.append({"relpath": relpath, "text": text})
    return files


# ---------------------------------------------------------------------------
# 2. Parse Root_GUE.sqf → root_vars
#    Pattern: setVariable [Format["WFBE_%1KEY", _side], VALUE]
# ---------------------------------------------------------------------------

# Matches both single-line setVariable calls.
# Value capture is greedy to the end of the bracket, so we grab the raw SQF value.
_ROOT_VAR_RE = re.compile(
    r'setVariable\s*\[\s*Format\s*\[\s*"WFBE_%1([^"]+)"\s*,\s*_side\s*\]\s*,\s*'
    r'(\'[^\']*\'|"[^"]*"|\[[^\]]*\])',
    re.IGNORECASE,
)


def parse_root_vars(text):
    """Return dict {KEY: raw_value_string} from Root_GUE.sqf."""
    result = {}
    for m in _ROOT_VAR_RE.finditer(text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        result[key] = val
    return result


# ---------------------------------------------------------------------------
# 3. Parse Structures_GUE.sqf → structures list
#    Extract: MHQ classname, HQ classname, 8 building keys + classnames +
#    costs + build times.
# ---------------------------------------------------------------------------

_MHQ_RE = re.compile(r'_MHQ\s*=\s*"([^"]+)"')
_HQ_RE = re.compile(r'_HQ\s*=\s*"([^"]+)"')
_BAR_RE = re.compile(r'_BAR\s*=\s*"([^"]+)"')
_LVF_RE = re.compile(r'_LVF\s*=\s*"([^"]+)"')
_CC_RE = re.compile(r'_CC\s*=\s*"([^"]+)"')
_HEAVY_RE = re.compile(r'_HEAVY\s*=\s*"([^"]+)"')
_AIR_RE = re.compile(r'_AIR\s*=\s*"([^"]+)"')
_SP_RE = re.compile(r'_SP\s*=\s*"([^"]+)"')
_AAR_RE = re.compile(r'_AAR\s*=\s*"([^"]+)"')

# Build cost rows – matches BOTH the initial assignment and subsequent appends:
#   _c = [VALUE]       (first row – HQ)
#   _c = _c + [VALUE]  (subsequent rows)
# We capture everything inside the outermost brackets.
_COST_INIT_RE = re.compile(r'_c\s*=\s*\[([^\]]+)\]')
_COST_APPEND_RE = re.compile(r'_c\s*=\s*_c\s*\+\s*\[([^\]]+)\]')

# Build time values come from the `_t = [...] / _t = _t + [...]` rows
_TIME_INIT_RE = re.compile(r'_t\s*=\s*\[([^\]]+)\]')
_TIME_APPEND_RE = re.compile(r'_t\s*=\s*_t\s*\+\s*\[([^\]]+)\]')

_BUILDING_KEYS = ["Headquarters", "Barracks", "Light", "CommandCenter",
                  "Heavy", "Aircraft", "ServicePoint", "AARadar"]


def _extract_time(expr):
    """Extract production time from expressions like 'if (WF_Debug) then {1} else {130}'."""
    m = re.search(r'else\s*\{(\d+)\}', expr)
    if m:
        return int(m.group(1))
    m = re.search(r'\{(\d+)\}', expr)
    if m:
        return int(m.group(1))
    try:
        return int(expr.strip())
    except ValueError:
        return 0


def parse_structures(text):
    mhq = _MHQ_RE.search(text)
    hq = _HQ_RE.search(text)
    bar = _BAR_RE.search(text)
    lvf = _LVF_RE.search(text)
    cc = _CC_RE.search(text)
    heavy = _HEAVY_RE.search(text)
    air = _AIR_RE.search(text)
    sp = _SP_RE.search(text)
    aar = _AAR_RE.search(text)

    classnames = {
        "MHQ": mhq.group(1) if mhq else "",
        "HQ": hq.group(1) if hq else "",
        "Barracks": bar.group(1) if bar else "",
        "Light": lvf.group(1) if lvf else "",
        "CommandCenter": cc.group(1) if cc else "",
        "Heavy": heavy.group(1) if heavy else "",
        "Aircraft": air.group(1) if air else "",
        "ServicePoint": sp.group(1) if sp else "",
        "AARadar": aar.group(1) if aar else "",
    }

    # Costs and times are set in the "/* Structures */" section, before
    # "/* Defenses */".  Slice the text to that section to avoid capturing
    # the defense _n array assignments (which also use _n = [...]).
    defenses_start = text.find("/* Defenses */")
    struct_section = text[:defenses_start] if defenses_start != -1 else text

    # Collect cost rows in order: first the init (_c = [...]) then appends.
    # In the real file the pattern is:
    #   _c   = [missionNamespace getVariable "WFBE_C_STRUCTURES_HQ_COST_DEPLOY"];
    #   _c = _c + [200];   -- Barracks
    #   _c = _c + [600];   -- Light
    #   ...
    # We capture ALL _c = [...] and _c = _c + [...] occurrences in order.
    cost_raws = []
    for m in re.finditer(
        r'_c\s*=\s*(?:_c\s*\+\s*)?\[([^\]]+)\]',
        struct_section
    ):
        cost_raws.append(m.group(1).strip())

    time_raws = []
    for m in re.finditer(
        r'_t\s*=\s*(?:_t\s*\+\s*)?\[([^\]]+)\]',
        struct_section
    ):
        time_raws.append(m.group(1).strip())

    costs = []
    for raw in cost_raws:
        try:
            costs.append(int(raw))
        except ValueError:
            costs.append(raw)  # variable reference (HQ deploy cost)

    times = [_extract_time(r) for r in time_raws]

    structures = []
    for i, key in enumerate(_BUILDING_KEYS):
        cn_key = key if key != "Headquarters" else "HQ"
        structures.append({
            "key": key,
            "classname": classnames.get(cn_key, ""),
            "cost": costs[i] if i < len(costs) else 0,
            "time": times[i] if i < len(times) else 0,
        })

    # Add MHQ separately
    result = {
        "mhq": classnames["MHQ"],
        "buildings": structures,
    }

    # Parse defense palette
    defense_names = re.search(
        r'setVariable\s*\[\s*Format\s*\["WFBE_%1DEFENSENAMES".*?\]\s*,\s*_n\s*\]',
        text, re.DOTALL
    )
    # Extract the _n list that builds up before setVariable DEFENSENAMES
    # We look for the sequence: _n = [...]; _n = _n + [...]; ...
    # between the comment /* Defenses */ and the setVariable line
    def_section = re.search(
        r'/\*\s*Defenses\s*\*/(.*?)missionNamespace setVariable.*?DEFENSENAMES',
        text, re.DOTALL
    )
    if def_section:
        def_text = def_section.group(1)
        def_items = re.findall(r'\["([^"]+)"\]', def_text)
        result["defense_names"] = def_items
    else:
        result["defense_names"] = []

    return result


# ---------------------------------------------------------------------------
# 4. Parse Core_GUE.sqf → core_rows
#    _c = _c + ['classname']  paired with  _i = _i + [[tuple]]
# ---------------------------------------------------------------------------

_CORE_C_RE = re.compile(r"_c\s*=\s*_c\s*\+\s*\['([^']+)'\]")
_CORE_I_RE = re.compile(r"_i\s*=\s*_i\s*\+\s*\[(\[[^\]]*(?:\[[^\]]*\])*[^\]]*\])\]")


def parse_core_rows(text):
    classnames = _CORE_C_RE.findall(text)
    raw_tuples = _CORE_I_RE.findall(text)
    rows = []
    for i, cn in enumerate(classnames):
        rows.append({
            "classname": cn,
            "raw_tuple": raw_tuples[i] if i < len(raw_tuples) else "",
        })
    return rows


# ---------------------------------------------------------------------------
# 5. Parse all Root_*.sqf for flags
# ---------------------------------------------------------------------------

_FLAG_RE = re.compile(
    r"setVariable\s*\[\s*Format\s*\[\s*\"WFBE_%1FLAG\"\s*,\s*_side\s*\]\s*,\s*'([^']+)'",
    re.IGNORECASE,
)
_SIDE_ASSIGN_RE = re.compile(r'_side\s*=\s*"([^"]+)"')


def collect_flags():
    flags = []
    if not os.path.isdir(ROOT_DIR):
        return flags
    for fname in sorted(os.listdir(ROOT_DIR)):
        if not fname.startswith("Root_") or not fname.endswith(".sqf"):
            continue
        faction = fname[len("Root_"):-len(".sqf")]
        path = os.path.join(ROOT_DIR, fname)
        text = read_sqf(path)
        m = _FLAG_RE.search(text)
        if m:
            flags.append({"faction": faction, "paa": m.group(1)})
    return flags


# ---------------------------------------------------------------------------
# 6. Parse Init_CommonConstants.sqf → registration arrays
# ---------------------------------------------------------------------------

_FACTIONS_RE = re.compile(
    r"WFBE_C_UNITS_FACTIONS_(WEST|EAST|GUER)\s*=\s*\[([^\]]+)\]"
)


def parse_registration(text):
    result = {}
    for m in _FACTIONS_RE.finditer(text):
        side = m.group(1)
        items = [x.strip().strip("'\"") for x in m.group(2).split(",")]
        result[f"factions_{side.lower()}"] = items

    # Indices: WFBE_C_UNITS_FACTION_WEST = 2 etc.
    for m in re.finditer(
        r"setVariable\s*\['WFBE_C_UNITS_FACTION_(WEST|EAST|GUER)'\s*,\s*(\d+)\]",
        text,
    ):
        result[f"index_{m.group(1).lower()}"] = int(m.group(2))

    return result


# ---------------------------------------------------------------------------
# 7. Parse Init_Common.sqf for the include-line pattern
# ---------------------------------------------------------------------------

def parse_init_common_includes(text):
    """
    Return a description of how Core_<F>.sqf and Gear_<F>.sqf are included.
    In Init_Common.sqf these are loaded via explicit preprocessFileLineNumbers calls.
    We find examples like 'Common\\Config\\Core\\Core_CDF.sqf' to derive the pattern.
    """
    core_lines = re.findall(
        r'preprocessFileLineNumbers\s+"(Common\\Config\\Core\\Core_[A-Z]+\.sqf)"',
        text,
    )
    gear_lines = re.findall(
        r'preprocessFileLineNumbers\s+"(Common\\Config\\Gear\\Gear_[A-Z]+\.sqf)"',
        text,
    )
    return {
        "core_example_lines": core_lines[:5],
        "gear_example_lines": gear_lines[:5],
        "core_pattern": r"Common\Config\Core\Core_{TOKEN}.sqf",
        "gear_pattern": r"Common\Config\Gear\Gear_{TOKEN}.sqf",
        "note": (
            "Root_/Defenses_/Groups_ are loaded dynamically via Format[...%1.sqf,token]. "
            "Core_ and Gear_ must be added explicitly to Init_Common.sqf."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Collecting GUE faction files...")
    files = collect_files()
    print(f"  {len(files)} files captured")

    # Root_GUE.sqf text
    root_gue_path = os.path.join(COMMON, r"Config\Core_Root\Root_GUE.sqf")
    root_text = read_sqf(root_gue_path)
    root_vars = parse_root_vars(root_text)
    print(f"  root_vars: {len(root_vars)} entries")

    # Structures_GUE.sqf
    struct_path = os.path.join(COMMON, r"Config\Core_Structures\Structures_GUE.sqf")
    struct_text = read_sqf(struct_path)
    structures = parse_structures(struct_text)
    print(f"  structures: {len(structures['buildings'])} buildings + MHQ={structures['mhq']}")

    # Core_GUE.sqf
    core_path = os.path.join(COMMON, r"Config\Core\Core_GUE.sqf")
    core_text = read_sqf(core_path)
    core_rows = parse_core_rows(core_text)
    print(f"  core_rows: {len(core_rows)} entries")

    # Flags from all Root_*.sqf
    flags = collect_flags()
    print(f"  flags: {len(flags)} faction flags")

    # Registration
    const_text = read_sqf(INIT_CONSTANTS)
    registration = parse_registration(const_text)

    # Init_Common include pattern
    common_text = read_sqf(INIT_COMMON)
    include_patterns = parse_init_common_includes(common_text)
    registration["include_patterns"] = include_patterns

    output = {
        "files": files,
        "root_vars": root_vars,
        "structures": structures,
        "core_rows": core_rows,
        "flags": flags,
        "registration": registration,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWritten: {OUT_FILE}")

    # Sanity checks
    gue_flag = root_vars.get("FLAG", "MISSING")
    print(f"\n--- Sanity ---")
    print(f"GUE FLAG = {gue_flag}")
    print(f"Structure keys: {[b['key'] for b in structures['buildings']]}")
    print(f"root_vars keys ({len(root_vars)}): {list(root_vars.keys())}")
    print(f"flags count: {len(flags)}")
    for f in flags:
        print(f"  {f['faction']}: {f['paa']}")


if __name__ == "__main__":
    main()
