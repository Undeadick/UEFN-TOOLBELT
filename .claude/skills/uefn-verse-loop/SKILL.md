---
name: uefn-verse-loop
description: Autonomous Verse code loop for UEFN — generate, deploy, build, read errors, fix, repeat until SUCCESS. Use when the user asks for game logic, devices wiring, Verse scripts, or gameplay mechanics in UEFN.
---

# UEFN Verse Loop (fully autonomous since June 2026)

The build click is automated — no human action required in the loop.

## Before writing any Verse

1. `verse_book_search("<construct>")` / `verse_book_chapter("<topic>")` —
   spec-accurate syntax, ALWAYS (project rule).
2. `run_toolbelt_tool("world_state_export")` — device labels in the level;
   `@editable` refs must match real labels.
3. `run_toolbelt_tool("verse_template_list")` — 6 battle-tested templates
   (game_skeleton, elimination_scoring, zone_capture, round_flow,
   item_spawner_cycle, countdown_race). Prefer adapting one over writing
   from scratch.

## The loop

```
1. WRITE    verse_write_file(filename="game_manager.verse", content=...,
                             overwrite=True)
            # or verse_template_deploy(name=..., custom_source=...)

2. BUILD    powershell -File scripts/build_verse.ps1
            # focuses UEFN, sends Ctrl+Shift+B; window must not be minimized

3. STATUS   wait ~10s → run_toolbelt_tool("verse_build_status",
                                          {"stale_threshold_sec": 60})
            # SUCCESS → done. FAILED → step 4. UNKNOWN+stale → build didn't
            # fire, retry step 2 (check window focus).

4. FIX      run_toolbelt_tool("verse_patch_errors")
            # errors with file/line/type/fix_hint + full file content
            → fix → goto 1
```

## Gotchas

- Logs are LOCALIZED (Russian editor: "VerseBuild: УСПЕШНО") — handled by
  verse_build_status; remember if parsing logs directly.
- V2 device game-logic properties (timer duration, scores, teams) are NOT
  settable from Python — configure them in Verse `OnBegin` via `@editable`
  refs, or `device_call_method` for runtime methods. See CLAUDE.md
  "V2 Device Property Wall".
- After switching projects the Python env resets — re-import tb and restart
  the MCP listener.
