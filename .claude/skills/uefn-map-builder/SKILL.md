---
name: uefn-map-builder
description: Build publishable, good-looking UEFN maps via the Toolbelt MCP bridge — asset catalog, theme palettes, modular buildings, decor, roads, lint, visual review. Use whenever the user asks to build, generate, decorate, or improve map/level content in UEFN (houses, POIs, roads, props, themes).
---

# UEFN Map Builder

End-to-end pipeline for AI map building through the UEFN Toolbelt. The MCP
listener must be running in UEFN (`tb.run("mcp_start")`).

## Before anything

1. `design_book_chapter("lessons")` — mistakes already made; do not repeat them.
2. `design_book_chapter("metrics")` — units, grids, player scale.
3. Analyze the level: `run_toolbelt_tool("world_state_export")` or
   `get_all_actors` → find occupied bounds. **Build BESIDE existing content,
   never at origin** (the user's maps are not empty).
4. NEVER auto-save. The user saves manually. Remind before risky ops at most.

## The pipeline

```
1. PALETTE  asset_catalog_query(query=..., publishable=True, measure=True)
            → pick wall/floor/door/window/roof from ONE kit (theming!)
            → palette_save(name, roles={...})        # rejects unpublishable
            → check repo palettes/ for curated ones first

2. BUILD    building_generate(palette, width, depth, floors,
                              location=<clear spot>, ground_snap=True,
                              window_every=2, roof_style="gable", dry_run=True)
            → inspect plan + terrain corner deltas → run real

3. DRESS    building_decorate(assets=[publishable props], around_folder=...,
                              count, band, seed)     # vignettes > sprinkles
            road_build(asset_path=<tile>, points=[[x,y],...])  # roads end AT something

4. LINT     run_toolbelt_tool("map_lint", {"folder": <build folder>})
            → fix floaters/clipping before any visual pass

5. REVIEW   position camera via execute_python (Rotator KEYWORD args only:
            unreal.Rotator(roll=0, pitch=..., yaw=...)), then
            powershell -File scripts/capture_uefn_window.ps1 -OutPath <png>
            → Read the png. NEVER in-engine screenshots (OOM crash on 6GB GPU).

            Mandatory angles per structure:
            - GABLE END view (roof errors hide from the front — lesson L1)
            - elevated 3/4
            - player-height shot at the entrance (~camera z = ground+170)

6. ITERATE  fix → re-run → re-capture. New non-obvious mistake? APPEND to
            docs/design_book/09_lessons.md.
```

## Hard rules

- Publishable namespaces only: `/Game/Creative`, `/Game/Packages`,
  `*_Assets` mounts, `/Engine/BasicShapes` (design_book_chapter("publishing")).
- Unknown kit piece → probe solo first: spawn ONE, capture two axes (L2).
- Ground trace miss = skip placement, never fallback height (L4).
- Mass placement → `spawn_actors_bulk` (one transaction) or generator tools;
  never loops of single spawn_actor.
- One kit family per structure; 2–3 kits per zone; props in 3–7-item
  vignettes (design_book_chapter("theming")).

## Quick reference: proven assets

- Walls/doors/windows: `/Game/Creative/BuildingActors/Walls/Meshes/CP_S_JungleTemple_*`
- Floors: `/Game/Creative/BuildingActors/Floors/Meshes/CP_S_Sidewalk_1x1_Street`
- Roof: `/Game/Packages/Fortress_Broken_Walls/SM/Mesh/DestroyedHouse_Roof_Straight`
- Road: `/Game/Packages/DS_Fortnight/SM/Mesh/S_Asphalt_1x1`
- Horror props: `/Game/Creative/Sets/Spooky/Props/Meshes/*` (dolls, mausoleum,
  covered furniture)
- Curated palettes: repo `palettes/*.json` → copy to
  `Saved/UEFN_Toolbelt/palettes/`
