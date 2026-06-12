# 02 — Composition: Making Space Look Intentional

## Landmarks ("weenies")

Every zone needs one dominant vertical element visible from most of the zone —
a tower, a chimney, a glowing sign. Players orient by it subconsciously.
- One PRIMARY landmark per map (tallest, unique silhouette).
- One secondary landmark per zone, visually distinct from the primary.
- Landmarks must break the roofline/treeline — check with a long-distance
  screenshot from player height (~200 cm), not from a god view.

## Silhouette first

A structure reads through its outline before its texture. Vary roof heights,
add towers/chimneys/antennas, avoid perfectly rectangular blocks. When
reviewing a build, squint test: capture a screenshot and judge the dark shape
only. If two buildings have the same silhouette, vary floors/roof style.

## Grounding — nothing floats, nothing sinks

The #1 amateur tell. Every actor's bbox bottom must touch its support:
- terrain: `ground_snap=True` / `trace_ground_z`
- props on furniture: place on the surface, not intersecting it
- `map_lint` flags floaters and buried actors mathematically — run it after
  every generation pass.
Edge of placement area = edge of support: positions whose ground trace misses
are skipped, never "placed at fallback height" (lesson 2026-06-13).

## Repetition with variation

Tiling one mesh N times reads as procedural. Break repetition every 3–5
repeats: swap in a damaged variant, rotate 180°, change a material, insert a
window/door piece. Kits ship variants (_01/_02/_03, _Dmg) — use ≥2 variants
in any run of ≥6 pieces. `building_generate window_every` is one such breaker.

## Leading lines

Roads, fences, cables, light rows — linear elements pull the eye and the feet.
Aim them at landmarks or entrances. A road that ends at nothing is a promise
broken (`road_build` paths should terminate at a POI, gate, or vista).

## Edges of the world

The map boundary must read as deliberate: cliffs, water, fog wall, barrier
ridge — not an abrupt floor edge with void beyond. Decor density fades
toward edges; gameplay content never sits against the boundary.

## Visual hierarchy by contrast

The most important thing in view should have the highest contrast (light,
color saturation, or scale). Decor stays low-contrast. If a screenshot's
brightest spot is a random prop, lighting needs rework.

Sources: The Level Design Book (composition/blockout chapters, CC BY-NC-SA),
classic "weenie" theory (Disney imagineering via LDB); live sessions.
