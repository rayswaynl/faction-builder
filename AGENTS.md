# AGENTS.md — agent onboarding for faction-builder

## What this is

A browser-based, offline, single-file **faction composer** for the Arma 2 **WASP Warfare** mission
([a2waspwarfare](https://github.com/rayswaynl/a2waspwarfare)): pick a token + side, compose roster /
structures / flag / glue, and emit the full SQF file set for a new playable faction, with GUE-cloned
defaults so it plays out of the box.

- **Live:** https://rayswaynl.github.io/faction-builder/
- **Embedded at:** https://miksuu.com/tools/faction-builder (iframe; picks up Pages deploys automatically)
- **Sibling suite** (same origin, shared `localStorage` for cross-tool handoff):
  [WDDM](https://github.com/rayswaynl/WDDM) ·
  [loadout-lab](https://github.com/rayswaynl/loadout-lab) ·
  [sector-planner](https://github.com/rayswaynl/sector-planner) ·
  [strategy-economy](https://github.com/rayswaynl/strategy-economy) ·
  [garrison-editor](https://github.com/rayswaynl/garrison-editor)

## Run it locally

No build step. `index.html` IS the production artifact. But you **must serve over HTTP** — the app
`fetch()`es `assets/data/*.json` at startup, which browsers block on `file://`.

```
python -m http.server 8120
# then open http://localhost:8120/
```

## Repo map

| Path | What it is |
|---|---|
| `index.html` | The entire app (~140 KB: CSS + HTML + vanilla JS). Production file. |
| `assets/data/faction-template.json` | **GENERATED** by `tools/extract_faction_template.py` — never hand-edit, regenerate instead. 15 GUE source-file templates + root vars + structures + flags + registration arrays. |
| `assets/data/units.json` | **GENERATED** by `tools/gen_unit_catalog.py` — never hand-edit, regenerate instead. ~1300 scope=2 CfgVehicles entries `{name, type, thumb}`. |
| `assets/thumbs/*.jpg` | **GENERATED** (copied) by `tools/gen_unit_catalog.py` — ~1165 unit thumbnails. |
| `tools/` | Python extractors + their unittest suites. Dev-time only; not loaded by the app. |
| `docs/superpowers/plans/` | v1 build plan — the grounding spec for the SQF formats the emitter targets. |
| `docs/screenshots/` | Reference screenshots. |

## Data pipeline (regeneration)

Both extractors read **hard-coded path constants at the top of the script** (no CLI flags). To
regenerate, clone the source repo(s) locally, edit the constant, run the script from repo root:

1. `tools/extract_faction_template.py` → `assets/data/faction-template.json`
   - Source: the GUE faction SQF files under `Missions/[55-2hc]warfarev2_073v48co.chernarus/Common`
     in a clone of [a2waspwarfare](https://github.com/rayswaynl/a2waspwarfare).
   - Edit the `COMMON` constant to point at that `Common` dir, then: `python tools/extract_faction_template.py`
2. `tools/gen_unit_catalog.py` → `assets/data/units.json` + `assets/thumbs/*.jpg`
   - Source: `Config/CfgVehicles.txt` + `Images/` in a clone of
     [arma2-co-config-reference](https://github.com/rayswaynl/arma2-co-config-reference)
     (sibling reference dump of the A2:CO configs).
   - Edit the `REF_DIR` constant, then: `python tools/gen_unit_catalog.py`

## Export formats (what the app emits)

Emit builds these files, zipped under their in-mission paths (all relative to the mission's `Common\` dir
in a2waspwarfare) — `<TOK>` = the faction token:

- `Common\Config\Core\Core_<TOK>.sqf` — roster phone-book (parallel `_c` classnames + `_i` tuples).
- `Common\Config\Core_Root\Root_<TOK>.sqf` — master glue (`WFBE_%1FLAG/CREW/PILOT/...` setVariables).
- `Common\Config\Core_Structures\Structures_<TOK>.sqf` — 8 base buildings + MHQ/HQ + defense palette.
- `Common\Config\Core_Units\Units_<TOK>.sqf` — the factory buy lists (`WFBE_%1{BARRACKS,LIGHT,HEAVY,AIRCRAFT,DEPOT,DEFENSE}UNITS`).
- GUE-clone defaults (token-substituted): `Upgrades_/Squad_/Artillery_/Defenses_/Gear_/Groups_/Loadout_<TOK>.sqf` + CO variants.
- `README.txt` with the two **manual registration patches**:
  - `Init\Init_CommonConstants.sqf`: append token to `WFBE_C_UNITS_FACTIONS_<SIDE>` + set `WFBE_C_UNITS_FACTION_<SIDE>` index.
  - `Init\Init_Common.sqf`: two `#include` lines (`Core_<TOK>.sqf`, `Gear_<TOK>.sqf`).

The ZIP writer is inline JS, **store-only** (method 0, CRC32 in JS, local headers + central directory) —
no compression library. Keep emitted SQF byte-formats matching the templates/spec in
`docs/superpowers/plans/2026-06-29-faction-builder-v1.md`.

## Testing

Verified working (from repo root):

```
cd tools && python -m unittest discover -v .
```

53 tests, all parser/emitter logic on inline fixtures. 9 integration tests **auto-skip** when the
source repos (a2waspwarfare mission files / CfgVehicles.txt) are not present locally — that is
expected on a plain checkout. There are no JS tests; smoke the app in a browser after `index.html` changes.

## Deploy

Push to `main` = live. GitHub Pages serves the repo root; `index.html` changes are user-visible at the
live URL ~1–2 min after push, and the miksuu.com iframe picks it up automatically. There is no CI gate —
run the tests and a browser smoke yourself before pushing.

## Hard rules

- **Single-file app**: all app CSS/JS stays inline in `index.html`. Only `assets/data/*.json` +
  `assets/thumbs/` are fetched at runtime.
- **No new external requests / CDNs / libraries.** The one existing exception is the Google Fonts
  `<link>` in `<head>` (degrades gracefully offline). Don't add more.
- **Never hand-edit generated artifacts** (`assets/data/*.json`, `assets/thumbs/`) — fix the extractor
  and regenerate.
- **Don't rename `localStorage` keys**: `wasp-faction-handoff` is a cross-tool contract shared across
  the `rayswaynl.github.io` origin (read by strategy-economy, loadout-lab, garrison-editor).
- **Don't commit large binaries** beyond the existing thumbnail set; `node_modules/`, `package.json`
  are gitignored dev tooling.
- **Keep registration/emit formats byte-compatible** with the mission — the README/plan promise the
  emitted faction loads out of the box.

## Gotchas

- `file://` open silently breaks: the catalog fetch fails and the app shows "load error". Always serve HTTP.
- Extractor paths are hard-coded constants (historical dev machine paths) — expect to edit them; there is
  no `--ref` flag. Regenerated output should be diffed before committing (data tracks upstream GUE files).
- `RESERVED_TOKENS` in `index.html` hard-codes built-in WASP tokens (`US, USMC, RU, CDF, INS, GUE, TKA,
  TK, TKGUE, GUER`); emit warns before overwriting these or any token already in the registration arrays.
- Sibling tool URLs are hard-coded in the cross-tool launcher near the bottom of `index.html`.
- Sessions autosave to `localStorage` (600 ms debounce); that is a convenience, not an export path.
