# 08 — Publishing: Validation, Restrictions, the Final Gate

## Asset reference restrictions (the hard wall)

UEFN's `AssetValidator_AssetReferenceRestrictions` runs on save/publish.
User maps may ONLY reference:

| Namespace | What it is |
|---|---|
| `/Game/Creative/**` | Creative galleries: BuildingActors, prop Sets (Spooky, ...) |
| `/Game/Packages/**` | Installed content packs (PBW, DS_Fortnight, Fortress_Broken_Walls, ...) |
| `/<Name>_Assets/**` | Gallery plugin mounts (City_Assets, Suburban_Assets, ...) |
| `/Engine/BasicShapes/**` | Engine primitives |
| `/<project mount>/**` | Your own imported content |

Everything else in the Asset Registry — notably the beautiful
`/Game/Environments/Sets/**` internal library — **fails validation**: the
editor shows "недопустимые ссылки / invalid references" per actor and the
island cannot be published. DO NOT click "reset invalid references" (it
empties the actors); replace the assets instead.

Tooling enforces this: `asset_catalog_query(publishable=True)`,
`palette_save` (rejects restricted), `building_decorate` / `road_build`
(validate inputs). `is_publishable_path()` is the single source of truth
(`api_capability_crawler.py`).

## Save discipline

- Saving triggers shader compilation + validation — on this project the USER
  saves manually; agents never auto-save (explicit instruction).
- Validation errors live with the map until fixed; they don't break editing,
  only publishing.

## Pre-publish checklist

1. `map_lint` — zero floaters/clipping above threshold.
2. `memory_scan` + Memory Calculation in Island Settings — under budget.
3. `publish_audit` — returns ready/warnings/blocked with ordered next steps:
   actor budget, required devices (spawn pads!), rogue actors, Verse build
   status, unsaved changes, redirectors.
4. Verse: `verse_build_status` == SUCCESS (build via `scripts/build_verse.ps1`).
5. Island settings: name, description, thumbnail, player count, device
   minimums (at least one player spawner!).
6. Visual pass: external captures of each zone at player height (09 protocol).

## Localized editors

This machine's editor logs in Russian ("VerseBuild: УСПЕШНО"). Any log
parsing must handle localized markers — fixed in verse_build_status, but
remember for new tools.

Sources: live validator findings (June 2026), Epic publishing flow,
Toolbelt publish_audit implementation.
