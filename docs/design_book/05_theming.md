# 05 — Theming: Kit Discipline, Color, Vignettes

## Kit discipline

- **One kit family per structure.** Mixing JungleTemple walls with City roofs
  reads as a bug, not eclecticism.
- **2–3 kits max per zone**: one architectural kit, one terrain/nature kit,
  one prop kit. More = visual noise.
- Exceptions must be deliberate: a sci-fi door in a medieval wall is a story
  beat, and needs framing (lighting, wear, cables) to look intended.

## Palettes are the contract

`palette_save` freezes a theme: roles → assets, with measured sizes. Curated,
publish-validated palettes live in the repo's `palettes/` folder — copy to
`Saved/UEFN_Toolbelt/palettes/` to use. Before inventing a palette, check
the library; after proving a new one live, export it back to the repo.

## Color: 60-30-10

Per zone: ~60% dominant material family, ~30% secondary, ~10% accent color.
The accent marks gameplay-relevant elements (03_readability). Material
presets (`material_apply_preset`) can retint kit pieces for zone identity —
prefer tinting ONE family rather than mixing more kits.

## Props in vignettes, not sprinkles

Uniform random scatter reads as procedural debris. Group props into
**vignettes of 3–7 items that tell a micro-story**: a table + two chairs +
fallen bottle; a mausoleum + dolls circle (horror). `building_decorate`
gives the ring; pass curated asset lists per vignette type and run it 2–3
times with different seeds/bands rather than one big uniform pass.
- Cluster spacing inside a vignette: 50–250 cm.
- Vignette-to-vignette: 800+ cm of breathing room.
- Rotate props toward the vignette's focus, not random — well, random yaw is
  fine for organic items (rocks, debris), wrong for furniture.

## Wear and weather consistency

Damage/dirt has a direction: if the west side of town is ruined, ALL west
facades show it. Kits ship _Dmg/_Broken variants — concentrate them, don't
salt-and-pepper.

## Publishable namespaces (hard constraint)

Themes can only be built from: `/Game/Creative/**`, `/Game/Packages/**`,
`*_Assets` gallery mounts (see 08_publishing). The gorgeous
`/Game/Environments` library FAILS validation. `asset_catalog_query`
publishable=True is mandatory when picking theme assets.

Sources: The Level Design Book (environment art), 60-30-10 interior design
rule; live validator findings June 2026.
