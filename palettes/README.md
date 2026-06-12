# Curated Palette Library

Publish-validated theme palettes for `building_generate` — every asset here
passes UEFN's AssetReferenceRestrictions validator (see
`docs/design_book/08_publishing.md`).

## Usage

Copy a palette into the project's saved palettes, then build:

```powershell
Copy-Item palettes\temple.json "$env:LOCALAPPDATA\UnrealEditorFortnite\Saved\UEFN_Toolbelt\palettes\"
```

```python
tb.run("building_generate", palette="temple", width=4, depth=3, floors=2,
       ground_snap=True, window_every=2)
```

## Palettes

| File | Theme | Kit(s) | Verified |
|---|---|---|---|
| `temple.json` | Jungle temple / overgrown stone | JungleTemple walls + Sidewalk floor + Broken-house roof | 2026-06-12, 62-piece two-storey build, validation-clean |

## Contributing a palette

1. Pick assets via `asset_catalog_query(..., publishable=True, measure=True)` —
   one kit family per structure (`docs/design_book/05_theming.md`).
2. `palette_save(name, roles)` — it rejects restricted assets.
3. Build + visual-review per the map-builder skill (gable-end shot!).
4. Copy `Saved/UEFN_Toolbelt/palettes/<name>.json` here, add a row above with
   the verification date.
