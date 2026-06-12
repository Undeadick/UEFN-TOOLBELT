# 06 — Horror Playbook (labyrinths, dread, jump scares)

The project's home genre. Horror is pacing + denial of information.

## Darkness with purpose

- NEVER total darkness — players quit, screens differ. Floor of visibility:
  silhouettes readable at 500 cm.
- Light pools are the navigation channel (03): small warm sources (candles,
  bulbs) marking the route; the scare lives just OUTSIDE the pool.
- Flicker sparingly (1–2 sources per zone max) — constant flicker fatigues.
- Cold ambient + warm route lights is the cheapest dread combo
  (`postprocess_preset horror`, `light_place` color warm ~#FFB46B).

## Sightline denial

Fear = not seeing what you hear. Corners every 500–800 cm, doorways into
black, fog walls, half-height occluders. BUT honor 04_flow: the player must
still have routes; denial of sight, not denial of agency.

## Tension–release cycle

Map the intensity curve: quiet (explore) → buildup (audio + narrowing) →
spike (scare/chase) → release (safe room, light). 3–5 minutes per cycle.
Two spikes back-to-back devalue both. Safe rooms: brighter, one entrance
visible at a time, ambient drops.

## The labyrinth specifically

- Corridor width: alternate 200 (squeeze) / 384 / 512 — uniform width numbs.
- Ceiling: drop to 256–300 in dread sections; open to void/sky for release.
- Micro-landmarks every 3–4 junctions (a doll, a crack, a hanging light) —
  players who feel they're learning stay; players who feel random leave.
- Dead ends: each one pays off — prop vignette, pickup, or scare. Empty dead
  end = refund demanded.
- One audible/visible "presence" landmark (the thing hunting you) that
  players triangulate by — dread scales with knowing roughly where it is.

## Mundane wrongness

The strongest horror props are normal things misplaced: dolls in a circle,
furniture covered indoors-style but outdoors, a single chair facing a wall.
The Spooky prop set (dolls, covered furniture, mausoleum — all publishable
in /Game/Creative/Sets/Spooky) is built for this. Place with intent (05
vignettes), not scatter.

## Audio (don't skip)

- Ambient loop per zone (`audio_place`, radius covering the zone, volume
  0.3–0.5): wind, drone, heartbeat.
- Point sources as bait: a radio, dripping water — players investigate sound.
- Silence is a tool: cut ambience entirely in the 5 s before a spike.

Sources: genre-standard practice distilled (LDB environment art / pacing,
horror design talks); Spooky set findings from the live catalog.
