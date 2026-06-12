# UEFN Design Book — Overview

> **The rule (same as verse-book): consult this book BEFORE building any map
> content.** `design_book_search("<concept>")` or `design_book_chapter("<topic>")`
> from any MCP client. Building without checking metrics and lessons repeats
> mistakes that are already documented here.

The Toolbelt's technical docs (UEFN_QUIRKS, PIPELINE) answer *how to call the
API*. This book answers *what to build* — the level-design knowledge an AI
agent needs to produce maps that look intentional, play well, and pass
publishing.

## Chapters

| File | Topic | Read before |
|---|---|---|
| `01_metrics.md` | Fortnite units, player dimensions, kit grids | placing anything |
| `02_composition.md` | Landmarks, silhouettes, visual grounding | layout / vistas |
| `03_readability.md` | Navigation, lighting as signage, zone identity | any playable space |
| `04_flow.md` | Spawns, engagement distances, loops vs dead ends | combat / movement spaces |
| `05_theming.md` | Kit discipline, color, prop vignettes, palettes | choosing assets |
| `06_horror.md` | Genre playbook: darkness, pacing, wrongness | horror maps |
| `07_optimization.md` | Memory, LODs, HISM, scalability budgets | big maps, before publish |
| `08_publishing.md` | Asset restrictions, validation, publish checklist | before save/publish |
| `09_lessons.md` | **Living log of mistakes already made — append yours** | every session |

## How this pairs with the tools

```
asset_catalog_query(publishable=True)   ← 08_publishing namespaces
palette_save(...)                       ← 05_theming kit discipline
building_generate(ground_snap=True)     ← 01_metrics grids, 02 grounding
building_decorate(...)                  ← 05_theming vignettes
road_build(...)                         ← 02 leading lines, 03 navigation
map_lint(...)                           ← catches 02/09 violations mathematically
capture_uefn_window.ps1                 ← visual review per 09 protocols
```

Sources this book distills: Epic's Fortnite Creative documentation
(dev.epicgames.com — Level Design Best Practices, Unreal Units, Architectural
Modeling Guidelines, Memory Management) and The Level Design Book by Robert
Yang et al. (book.leveldesignbook.com, CC BY-NC-SA 4.0) — concepts adapted
with attribution, plus live findings from this fork's build sessions.
