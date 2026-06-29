# Faction Builder

A browser-based, offline, single-file **faction composer** for Arma 2 **WASP "Warfare"** — the capstone of the [Miksuu's Warfare tools](https://miksuu.com/tools) suite (sibling to [WDDM](https://github.com/rayswaynl/WDDM), [Loadout Lab](https://github.com/rayswaynl/loadout-lab), [Sector & Town Planner](https://github.com/rayswaynl/sector-planner), [Strategy & Economy](https://github.com/rayswaynl/strategy-economy), [Garrison & AI Groups](https://github.com/rayswaynl/garrison-editor)).

> Status: **in development**.

## What it does

Assemble a **whole new playable faction** — the way the GUER insurgents were hand-built, but visually. Pick a token + side, then compose:

- **Roster** — units/vehicles from the catalog (thumbnail picker), each with price · factory slot (Barracks/Light/Heavy/Air) · upgrade tier · faction string. → `Core_<F>.sqf` + `Units_<F>.sqf`.
- **Structures** — the 8 base buildings + MHQ classnames, supply costs, build times. → `Structures_<F>.sqf`.
- **Flag** — the `.paa` texture path.
- **Glue** — support vehicles (repair/supply/salvage/ambulance), starting vehicles, paratroop pools, radio, default-faction. → `Root_<F>.sqf`.

It **emits the full faction file set** plus the two registration patches (`Init_CommonConstants.sqf` token+index, `Init_Common.sqf` includes), with GUE-cloned defaults for the deferred parts so the faction **loads and plays out of the box**.

## Cross-tool launcher

Because all the tools share the `rayswaynl.github.io` origin (and thus `localStorage`), the Faction Builder hands its new faction straight to the sibling tools to refine the deferred parts:
- **Upgrades** → Strategy & Economy
- **Gear / loadouts** → Loadout Lab
- **AI squads** → Garrison & AI Groups

## Unique core

Where the other five tools each edit one slice, this one **composes a whole side** — the META-tool that produces the files the rest refine.

## License

Unofficial, non-commercial reference tool for mission development. Arma 2 / WASP config + unit imagery © **Bohemia Interactive** / WFBE authors.
