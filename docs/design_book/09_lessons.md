# 09 — Lessons: Mistakes Already Made (append yours)

> Living document — the design-side sibling of UEFN_QUIRKS.md. When a build
> session uncovers a non-obvious mistake, APPEND it here with date and
> context. Future agents: read this BEFORE building; repeating a documented
> lesson is a process failure.

## L1 — Review roofs from the GABLE END (2026-06-12)

A two-storey house looked fine from the front while its roof slopes were
assembled inverted (V/butterfly) and its gable ends were open triangles.
Front/three-quarter views MASK roof errors.
**Protocol:** every structure review includes an end-on capture + one
elevated 3/4. For roofs specifically: end-on first.

## L2 — Probe unknown pieces solo before tiling (2026-06-12)

Kit pieces' slope/pivot/orientation conventions vary per kit
(DestroyedHouse_Roof slopes toward local −Y). Guessing wastes a build-review
cycle. **Protocol:** spawn ONE piece at a clear spot, capture from two axes,
then write the layout math. `building_generate roof_flip` exists because of
this.

## L3 — "Cap" pieces are often NOT ridge caps (2026-06-12)

DestroyedHouse_Roof_Cap (554×102×395) is a gable-end piece; tiled along a
ridge it reads as teeth/fins. Verify any cap/trim piece visually (L2 probe)
before adding it to a palette's roof_cap role.

## L4 — No ground = no placement (2026-06-13)

Props whose ground trace misses (island edge, holes) must be SKIPPED, not
placed at a fallback height — fallback left furniture floating in mid-air
beyond the plate edge. All placement tools now skip; keep it that way in
new tools.

## L5 — The pretty library is unpublishable (2026-06-12)

`/Game/Environments/Sets/**` (PrincessCastle etc.) fails
AssetReferenceRestrictions. A 52-piece castle had to be deleted. ALWAYS
filter publishable=True when selecting assets for a real map (08).

## L6 — unreal.Rotator positional order is (roll, pitch, yaw) (2026-06-12)

Positional rotations silently ROLL cameras/actors sideways. Keyword args
only. See UEFN_QUIRKS #35. The user's tilted camera was this.

## L7 — In-engine screenshots OOM-crash low-VRAM machines (2026-06-12, ×2)

take_high_res_screenshot allocates render targets; on a 6 GB GPU it killed
the editor twice ("Out of video memory", D3D12). Use external window capture
(`scripts/capture_uefn_window.ps1`) — zero engine cost. Remind the user to
save before any risky operation (but never auto-save — user instruction).

## L8 — Background UEFN throttles ticks (2026-06-12)

With the editor window unfocused, slate ticks crawl — tick-driven tools
stall. `system_optimize_background_cpu` is sandboxed in UEFN
(EditorPerformanceSettings missing). Either keep the window focused or use
console vars `t.IdleWhenNotForeground 0`.

## L9 — Test spawns go BESIDE existing content (2026-06-12)

User maps are not empty. Analyze the level first (world_state_export /
get_all_actors → occupied bounds), then build in clear space. Origin (0,0,0)
landed a test wall inside the user's labyrinth.

## L10 — Localized editor logs (2026-06-13)

Build/result markers in logs are localized (Russian: "УСПЕШНО — сборка
завершена"). English-only regexes report UNKNOWN forever. Parse both; prefer
the main editor log (UnrealEditorFortnite.log), not "newest .log".
