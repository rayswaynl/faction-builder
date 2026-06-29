# Faction Builder v1 — Plan (complete + cross-tool launcher)

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. `- [ ]` steps. index.html edits SEQUENTIAL.

**Goal:** compose a whole new playable WASP faction (token + side → roster + structures + flag + Root glue), emit the **full file set + 2 registration patches** (GUE-cloned defaults for deferred parts so it plays out of the box), and **hand off** to the sibling tools via shared `localStorage`.

**Architecture:** Python generators turn the GUE faction into **templates** + catalogs (units from `arma2-co-config-reference`, structures, flags). `index.html` (vanilla JS, WDDM theme + reused thumbnail picker) collects the faction and emits the files by template substitution. Cross-tool launcher = write a handoff bundle to `localStorage` (shared across the `rayswaynl.github.io` origin) + open the sibling tool.

## Grounding (verbatim, from research) — base = `C:\Users\Steff\a2waspwarfare\Missions\[55-2hc]warfarev2_073v48co.chernarus\Common`
- **Registration** (`Init\Init_CommonConstants.sqf`): `WFBE_C_UNITS_FACTIONS_{WEST:['CDF','US','USMC'], EAST:['INS','RU','TKA'], GUER:['GUE','PMC','TKGUE']}` + `WFBE_C_UNITS_FACTION_<SIDE> = <index>`. Loader (`Init\Init_Common.sqf`) has EXPLICIT include lists for `Core\Core_<F>.sqf` + `Gear\Gear_<F>.sqf` (must add a line); `Root_*`, `Defenses_*`, `Groups_*` load dynamically via `Format["...%1.sqf", token]`.
- **Core_<F>.sqf** (roster phone-book): parallel `_c` (classnames) + `_i` (tuples `[label,pic,price,buildTime,crew,upgrade,factory,skill,factionStr,turrets]`). factory: `-1`=infantry, `-2`=vehicle, `1`=defense-static. Loaded globally.
- **Root_<F>.sqf** (master glue, takes `_side`="WEST|EAST|GUER"): sets `WFBE_%1{FLAG,CREW,PILOT,SOLDIER,REPAIRTRUCKS,SUPPLYTRUCKS,SALVAGETRUCK,AMBULANCES,STARTINGVEHICLES,PARACHUTELEVEL1/2/3,DEFAULTFACTION,_DefaultGear,_AI_Loadout_0..3,_RadioAnnouncers...}` then calls Artillery_/Units_/Squad_/Structures_/Upgrades_ (+ client Loadout_). `WFBE_%1FLAG = '<.paa path>'` (e.g. GUE `'\ca\data\Flag_napa_co.paa'`).
- **Structures_<F>.sqf** (takes `_side`): the 8 buildings `["Headquarters","Barracks","Light","CommandCenter","Heavy","Aircraft","ServicePoint","AARadar"]` → classnames + supply costs + build times + site sizes + placement dist/dir; `WFBE_%1MHQNAME` (mobile HQ), `WFBE_%1HQ` (deployed), defense palette `WFBE_%1DEFENSENAMES`.
- **Units_<F>.sqf** (takes `_side`): the 6 factory buy lists `WFBE_%1{BARRACKS,LIGHT,HEAVY,AIRCRAFT,AIRPORT,DEPOT}UNITS` (classname arrays).
- **Deferred (GUE-clone defaults)**: `Upgrades_<F>` (→ Strategy & Economy), `Groups_<F>`/`Squad_<F>` (→ Garrison), `Gear_<F>`/`Loadout_<F>` (→ Loadout Lab), `Artillery_<F>`, `Defenses_<F>`.
- **Catalog**: `C:\Users\Steff\arma2-co-config-reference` CfgVehicles + thumbnails (reuse the items pipeline).

## Task 1: Generators → templates + catalogs
**Files:** `tools/extract_faction_template.py`, `tools/gen_unit_catalog.py` (+ tests).
- [ ] `extract_faction_template`: read the GUE faction files (`Core_GUE.sqf`, `Core_Root\Root_GUE.sqf`, `Core_Structures\Structures_GUE.sqf` + `Structures_CO_GUE.sqf`, `Core_Units\Units_GUE.sqf`, + the deferred `Upgrades_/Groups_/Squad_/Artillery_/Defenses_/Gear_/Loadout_` GUE files) → `assets/data/faction-template.json`: each file's text as a **template** with the side string + the GUE-specific classnames marked so the emitter can substitute. Capture the **Root variable set** (names + GUE values) as the editable glue schema. Capture the **flag list** (all Root_*.sqf `WFBE_%1FLAG` paths) for a flag picker. Capture the **registration arrays** + the Init_Common include-line patterns.
- [ ] `gen_unit_catalog`: from `arma2-co-config-reference` → `assets/data/units.json` (CfgVehicles classnames → {name, type:man/car/tank/air/static, thumb}) + copy thumbs to `assets/thumbs/`. Broad enough to pick a roster (infantry + vehicles + statics). (Reuse the sibling generators' approach.)
- [ ] Tests (inline fixtures): a Core `_c/_i` row parse; a Root `WFBE_%1FLAG` capture; a registration-array parse. Run → JSONs + thumbs. Sanity: GUE Root flag = `'\ca\data\Flag_napa_co.paa'`; the 8 structure keys captured; units.json has infantry+vehicles+statics with thumbs. **Commit** `feat(tools): GUE faction template + unit catalog`.

## Task 2: Shell + Identity + Roster panel
**Files:** `index.html`.
- [ ] Shell: WDDM theme, brand "FACTION BUILDER" / "WASP SIDE COMPOSER"; a stepped/tabbed layout (Identity · Roster · Structures · Glue · Export). Fetch template + units.
- [ ] **Identity**: token (validated `[A-Z0-9]`, not an existing token), side (WEST/EAST/GUER), display-name/`DEFAULTFACTION` string, faction-string for Core tuples.
- [ ] **Roster**: add units/vehicles via the **thumbnail picker** (units.json); per unit set price, buildTime, **factory slot** (Barracks/Light/Heavy/Air/Depot via factory code -1/-2 + the Units list), upgrade tier, crew. Group by factory slot. (This drives both Core_<F> tuples and Units_<F> lists.) Classname validation.
- [ ] Verify (Playwright 8110): 0 errors; token/side set; add units to slots → model updates; picker works. Screenshot. Commit `feat: shell + identity + roster panel`.

## Task 3: Structures + Flag + Glue panels
**Files:** `index.html`.
- [ ] **Structures**: the 8 buildings + MHQ/deployed-HQ classnames (picker or text), supply costs, build times (defaults from GUE). **Flag**: a flag picker (the captured `.paa` list + a custom path field). 
- [ ] **Glue**: support vehicles (repair/supply/salvage/ambulance), starting vehicles, paratroop pools (3), radio announcer, default gear class — the Root variable set, with GUE defaults pre-filled (so the user can accept defaults). 
- [ ] Verify (Playwright): edit structures/flag/glue → model updates; defaults present. 0 errors. Screenshot. Commit `feat: structures + flag + glue panels`.

## Task 4: Emit + cross-tool launcher
**Files:** `index.html`.
- [ ] **Emit** the full file set by substituting the user's data into the templates: `Core_<F>.sqf`, `Root_<F>.sqf`, `Structures_<F>.sqf`, `Units_<F>.sqf`, + GUE-clone defaults for `Upgrades_/Groups_/Squad_/Artillery_/Defenses_/Gear_/Loadout_<F>.sqf` (token-substituted). Plus the **2 registration patches** (the `Init_CommonConstants.sqf` array+index edit + the `Init_Common.sqf` include lines) shown as apply-me diffs. Output: per-file copy blocks + a **"Download faction (.zip)"** (inline a minimal store-only zip writer) containing all files in their `Common\Config\...` paths + a README with the 2 manual patches.
- [ ] **Cross-tool launcher**: write a handoff bundle `localStorage['wasp-faction-handoff'] = {token, side, factionStr, coreUnits:[...], gear?, groups?}` and provide buttons "Refine upgrades → Strategy & Economy", "Refine gear → Loadout Lab", "Refine AI squads → Garrison" that `window.open` the sibling tool URL. (Sibling read = Task 5.)
- [ ] Verify (Playwright): generate a GUER faction "PARTISANS" → emitted files contain the token (not GUE) in classnames/vars where substituted, the Root flag, the registration patch shows the token + index; the zip downloads; the launcher writes the localStorage key. 0 errors. Screenshot. Commit `feat: emit faction file set + registration patches + cross-tool launcher`.

## Task 5: Sibling handoff-reads (S&E · Garrison · Loadout Lab)
**Files:** `C:\Users\Steff\strategy-economy\index.html`, `C:\Users\Steff\garrison-editor\index.html`, `C:\Users\Steff\loadout-lab\index.html` (each its own repo/branch).
- [ ] In each sibling, on load check `localStorage['wasp-faction-handoff']`; if present + relevant, show a banner "New faction <token> from Faction Builder — add it?" → add the token to that tool's faction list/selector (seeded from the GUE defaults) so the user can refine + export. Keep it non-intrusive (dismissable; doesn't disturb normal use). Each on its own `feat/faction-handoff` branch → controller merges + deploys.

## Task 6: Verify + finish + deploy + tile
- [ ] tests pass; full smoke (compose → emit → zip → launcher); 0 errors; screenshots. README. Controller: merge `feat/v1`→main, push, Pages, verify live. Add tile to miksuu hub (`tools.ts`); user-approved deploy. Deploy the 3 sibling handoff updates too.

## Self-Review
- Composer (identity/roster/structures/glue) → Tasks 2–3; emit full set + registration patches + zip → Task 4; cross-tool launcher via shared localStorage + sibling reads → Tasks 4–5. GUE-clone defaults = playable out of the box. Capstone META-tool.
