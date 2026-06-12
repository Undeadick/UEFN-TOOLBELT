# 01 — Metrics: Units, Player, Grids

Everything in UEFN is centimeters: **1 UU = 1 cm, 1 m = 100 UU**.

## The numbers that matter (Epic canon)

| Thing | Size | Notes |
|---|---|---|
| Build grid tile | **512 × 512 UU** | The atom of Fortnite space. Snap structures to it. |
| Full wall | 512 w × **384 h** | Building Actor standard |
| Half / quarter wall | 512 × 192 / 512 × 96 | |
| Wall thickness | **24 cm** | Custom walls should match |
| Floor piece | 512 × 512, ~32 thick | |
| Player | **192 cm tall**, ~90 wide | THE reference for every opening and ceiling |
| Walkable ramp | up to 45° (512 run / 512 rise) | steeper = not walkable |
| Comfortable door opening | ≥ 128 w × ≥ 224 h | player + headroom; tighter feels claustrophobic (use deliberately) |
| Interior ceiling | 384 (1 wall) normal, 768 grand | 192-tall player under 384 ceiling = domestic scale |
| Corridor width | 256 min comfortable, 512 generous | < 200 reads as a squeeze |

## Gallery kit grids (measured live — kits differ from the 512 canon!)

| Kit | Wall piece | Cell | Height |
|---|---|---|---|
| PrincessCastle (`/Game/Environments` — ⛔ NOT publishable) | SolidWall_02 | 512 | 384 |
| JungleTemple (`/Game/Creative/BuildingActors/Walls`) | Wall_03 | **548.9** | 385.4 |
| Sidewalk floors (`/Game/Creative/BuildingActors/Floors`) | 1x1 | 512 | 32 |

**Rule:** never assume 512 — measure the actual kit
(`asset_catalog_query(..., measure=True)` or `kit_metrics`) and derive the
build cell from the wall piece's bbox X-length. `building_generate` does this
automatically; manual placement must do the same.

## Engagement distances (combat spaces)

| Band | Distance | Design implication |
|---|---|---|
| Melee / shotgun | 0–1 000 | tight rooms, corners every few meters |
| SMG / close AR | 1 000–3 000 | room-to-room, short streets |
| AR / mid | 3 000–6 000 | plazas, long corridors — provide cover each 500–1000 |
| Sniper | 6 000+ | only with intentional long sightlines + flank routes |

A sightline's length defines its weapon. Audit long sightlines on purpose,
never by accident (see 04_flow).

## Scale sanity checks

- Stand a mental 192-cm player next to every doorway, window sill (~96–128 cm),
  table (~100 cm), railing (~100–110 cm).
- A building storey is 1 wall height (384–400). Two storeys ≈ 770–800.
- If a prop's size feels off in a screenshot, measure it — `measure=True`
  costs 45 ms.

Sources: Epic "Unreal Units", "Architectural Modeling Guidelines",
"Level Design Best Practices in Fortnite Creative"; live kit measurements
June 2026.
