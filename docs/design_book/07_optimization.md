# 07 — Optimization: Budgets That Keep the Island Shippable

Fortnite islands must run on phones and Switch, not just PC. Epic enforces a
**memory budget** — exceed it and the island cannot be published.

## The budgets

| Resource | Budget / guidance |
|---|---|
| Island memory | Use UEFN's **Memory Calculation** tool (Island Settings) — it lists the most expensive assets. Stay under the bar with headroom (~10%). |
| Textures | ≤ 512×512 preferred for mobile; never >2048 without need (`memory_scan_textures`) |
| Meshes | LOD0–LOD2 required for real-time assets; high-poly only near player paths (`memory_scan_meshes`, warn at 50k tris) |
| Materials | Fewest possible; 1 material section per mesh ideal (`material_parent_audit`) |
| Actors | Prefer < 5 000 placed actors; 100+ repeats of one mesh → `scatter_hism` / `convert_to_hism` (one draw call) |

## Toolbelt audit chain (run before publish)

```
tb.run("memory_scan")            # textures + meshes over budget
tb.run("memory_top_offenders")   # heaviest assets ranked
tb.run("level_health_report")    # 6-category health score
tb.run("map_lint")               # geometric QA (floaters, clipping)
tb.run("publish_audit")          # the final gate: ready/warnings/blocked
```

## Structural techniques

- **HISM** for grass/debris/repeated props — thousands of instances, one actor.
- **HLOD / World Partition / Data Layers** for big maps (UEFN supports them;
  see `world_partition_status`, `data_layer_*` tools).
- Distance culling: small props should not render at 10 000 cm — kit assets
  usually handle this; custom imports need LODs.
- Lights are expensive: prefer few meaningful sources (06_horror wants this
  anyway); avoid overlapping attenuation radii of many dynamic lights.

## On this machine specifically (6 GB VRAM dev box)

Editor-side: streaming pool capped (Engine.ini r.Streaming.PoolSize=512),
viewport at 67% resolution, GI/Reflections off. In-engine screenshots are
banned (OOM crash) — external capture only. These are EDITOR settings; they
do not affect the published island.

Sources: Epic "Memory Management in UEFN", "Fortnite-Ready Assets Best
Practices", "Mobile Design and Optimization in Fortnite".
