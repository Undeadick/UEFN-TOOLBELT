"""
UEFN TOOLBELT — API Capability Crawler
========================================
Headless reflection and debugging crawler for UEFN.
Because UEFN locks down many internal properties, Epic's documentation is often
incomplete. This tool brute-forces introspection on live level actors to map
out exactly what variables are exposed to Python in the current patch.
"""

import os
import json
import unreal
from typing import Any, Dict, List, Set
from .. import core
from ..registry import register_tool


def _is_valid(obj) -> bool:
    """Check if an Unreal object is safe to access (non-null C++ pointer)."""
    try:
        return obj is not None and bool(obj)
    except Exception:
        return False


def _introspect_object(obj: unreal.Object) -> Dict[str, Any]:
    """
    Use Python reflection to determine what properties are exposed
    on a given Unreal Object.

    Safe version: no component recursion, validates objects before access,
    skips callables that could dereference null C++ pointers.
    """
    if not _is_valid(obj):
        return {"class": "Invalid", "properties": {}, "methods": []}

    schema: Dict[str, Any] = {
        "class": type(obj).__name__,
        "properties": {},
        "methods": [],
    }

    # Only probe get_editor_property — never call getattr on unknown attrs
    # as shiboken can dereference null C++ pointers and crash the editor.
    _skips = frozenset({
        "set_editor_property", "get_editor_property", "set_editor_properties",
        "get_class", "get_components_by_class", "get_outer", "get_typed_outer",
        "get_world", "get_level", "static_class",
    })

    # 1. Collect method names via dir() — callable check only, no invocation
    for attr in dir(obj):
        if attr.startswith("_") or attr in _skips:
            continue
        try:
            val = getattr(obj, attr)
            if callable(val):
                schema["methods"].append(attr)
        except Exception:
            pass

    # 2. Probe editor properties — the only safe reflection path in UEFN
    for attr in list(schema["methods"]):
        pass  # methods already collected above

    # Probe known-safe property names via get_editor_property
    for attr in dir(obj):
        if attr.startswith("_") or attr in _skips or attr in schema["methods"]:
            continue
        try:
            val = obj.get_editor_property(attr)
            if not _is_valid(val) and val is not None:
                continue
            val_type = type(val).__name__ if val is not None else "Any"
            rep = None
            if isinstance(val, (int, float, str, bool)):
                rep = val
            elif isinstance(val, unreal.EnumBase):
                rep = str(val)
            elif isinstance(val, unreal.Name):
                rep = str(val)
            elif isinstance(val, unreal.Vector):
                rep = {"x": round(val.x, 3), "y": round(val.y, 3), "z": round(val.z, 3)}
            schema["properties"][attr] = {
                "type": val_type,
                "readable": True,
                "example_value": rep,
            }
        except Exception as e:
            err = str(e)
            if "not found" not in err.lower() and "cannot" not in err.lower():
                schema["properties"][attr] = {
                    "type": "Unknown/Restricted",
                    "readable": False,
                    "error": err[:120],
                }

    return schema


@register_tool(
    name="api_crawl_selection",
    category="API Explorer",
    description="Deep introspect selected actors, components, and properties to JSON.",
    tags=["crawler", "fuzz", "reflection", "deep scan", "capabilities"],
)
def crawl_selection(**kwargs) -> dict:
    """
    Reads the deeply nested exposed properties of the currently selected
    actor(s) and writes a comprehensive JSON graph to disk.
    Invaluable for Verse devs trying to reverse-engineer Fortnite devices.
    """
    actors = core.require_selection()
    if not actors:
        return {"status": "error", "message": "No actors selected.", "path": ""}

    core.log_info(f"Crawling capabilities for {len(actors)} actor(s)...")

    report = {
        "scan_target": "selection",
        "actor_count": len(actors),
        "data": {}
    }

    for actor in actors:
        label = actor.get_actor_label()
        core.log_info(f"Crawling: {label}")
        report["data"][label] = _introspect_object(actor)

    # Save to disk
    import unreal
    saved_dir = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt")
    os.makedirs(saved_dir, exist_ok=True)
    out_path = os.path.join(saved_dir, "api_selection_crawl.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    core.log_info(f"✓ Selection crawl saved: {out_path}")
    return {"status": "ok", "path": out_path, "count": len(actors)}


def _sync_to_repo(src_path: str, filename: str) -> str:
    """
    Helper to copy a generated file from the Saved/ directory to the project's docs/ 
    folder for Git tracking and AI context.
    """
    import shutil
    try:
        # Find project root
        curr = os.path.abspath(__file__)
        project_root = None
        while curr and os.path.dirname(curr) != curr:
            curr = os.path.dirname(curr)
            if os.path.basename(curr) == "Content":
                project_root = os.path.dirname(curr)
                break
        
        if not project_root:
            import unreal
            project_root = unreal.Paths.project_dir()
            
        repo_docs = os.path.join(project_root, "docs")
        os.makedirs(repo_docs, exist_ok=True)
        dst_path = os.path.join(repo_docs, filename)
        
        shutil.copy2(src_path, dst_path)
        return dst_path
    except Exception as e:
        core.log_warning(f"Schema Sync: Failed to copy {filename} to project docs: {e}")
        return ""


@register_tool(
    name="api_crawl_level_classes",
    category="API Explorer",
    description="Headless map of all unique classes (and exposed properties) in the current level.",
    tags=["crawler", "fuzz", "level", "deep scan", "capabilities"],
)
def crawl_level_classes(**kwargs) -> dict:
    """
    Headlessly scans every actor in the map. Aggregates them by Class.
    Runs deep introspection on exactly one instance of each class.
    Generates a master schema of what properties exist on the Fortnite devices
    used in your level.
    """
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_sub.get_all_level_actors()
    if not all_actors:
        core.log_warning("No actors in the level.")
        return {"status": "error", "message": "No actors in the level.", "path": ""}

    class_map: Dict[str, unreal.Actor] = {}
    for a in all_actors:
        cls_name = type(a).__name__
        if cls_name not in class_map:
            class_map[cls_name] = a

    core.log_info(f"Found {len(all_actors)} total actors, distilling to {len(class_map)} unique classes...")

    report = {
        "scan_target": "level_unique_classes",
        "total_actors": len(all_actors),
        "unique_classes": len(class_map),
        "classes": {}
    }

    # Sort to scan alphabetically — no progress bar (PySide6 ticking during
    # heavy reflection can dereference null C++ pointers and crash the editor)
    sorted_classes = sorted(list(class_map.keys()))
    for i, cls_name in enumerate(sorted_classes):
        actor = class_map[cls_name]
        unreal.log(f"[TOOLBELT] Crawling {i+1}/{len(sorted_classes)}: {cls_name}")
        report["classes"][cls_name] = _introspect_object(actor)

    # Save to disk
    saved_dir = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt")
    os.makedirs(saved_dir, exist_ok=True)
    out_path = os.path.join(saved_dir, "api_level_classes_schema.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    core.log_info(f"✓ Level class schema saved: {out_path}")

    # Sync to repo docs for AI context
    repo_path = _sync_to_repo(out_path, "api_level_classes_schema.json")
    if repo_path:
        core.log_info(f"✓ Auto-synced to repo: {repo_path}")

    return {"status": "ok", "path": out_path, "unique_classes": len(class_map), "total_actors": len(all_actors)}


@register_tool(
    name="api_sync_master",
    category="API Explorer",
    description="The Ultimate One-Click Sync: Combines Level Crawling + Verse Schema IQ and updates docs/DEVICE_API_MAP.md.",
    tags=["sync", "docs", "master", "capabilities", "automation"],
)
def api_sync_master(**kwargs) -> dict:
    """
    Unifies all Toolbelt intelligence into one command.
    1. Scans live actors for Python API methods.
    2. Scans Verse digests for Schema properties/events.
    3. Merges and updates DEVICE_API_MAP.md automatically.
    """
    from .verse_schema import _parser as verse_parser

    # 1. Run Level Crawler
    core.log_info("Step 1/3: Crawling live level actors...")
    crawl_result = crawl_level_classes()
    level_schema_path = crawl_result.get("path", "") if isinstance(crawl_result, dict) else crawl_result
    if not level_schema_path or not os.path.exists(level_schema_path):
        return {"status": "error", "message": "Failed to crawl level classes."}
        
    with open(level_schema_path, 'r', encoding='utf-8') as f:
        level_data = json.load(f)
    
    # 2. Refresh Verse Schema
    core.log_info("Step 2/3: Refreshing Verse Schema IQ from digests...")
    verse_parser.load_digests()
    
    # 3. Merge and Document
    core.log_info("Step 3/3: Merging data and updating DEVICE_API_MAP.md...")
    
    md_content = [
        "# Fortnite Device API Map (Master Sync)",
        "",
        "This document is a unified map of Python-exposed methods and Verse-exposed properties.",
        "Generated automatically by `api_sync_master`.",
        "",
        "| Class | Source | Key Methods / Properties / Events |",
        "| :--- | :--- | :--- |"
    ]
    
    all_classes = sorted(list(set(list(level_data["classes"].keys()) + list(verse_parser.device_schemas.keys()))))
    
    for cls in all_classes:
        level_info = level_data["classes"].get(cls)
        verse_info = verse_parser.device_schemas.get(cls)
        
        source = []
        if level_info: source.append("Live")
        if verse_info: source.append("Verse")
        
        # Collect top items
        items = []
        if level_info:
            # Add top 3 methods
            methods = [m for m in level_info.get("methods", []) if not m.startswith("get_") and not m.startswith("set_")]
            items.extend(methods[:3])
            
        if verse_info:
            # Add top 3 properties/events
            props = list(verse_info.get("properties", {}).keys())[:2]
            events = verse_info.get("events", [])[:1]
            items.extend(props)
            items.extend(events)
            
        entry = ", ".join([f"`{i}`" for i in items]) or "*(Introspecting...)*"
        md_content.append(f"| `{cls}` | {[' + '.join(source)]} | {entry} |")

    md_content.append("\n---\n*Last Sync: Generated by UEFN Toolbelt Master Sync Tool*")
    
    # Write to project docs (Self-resolving path for UEFN project structures)
    curr = os.path.abspath(__file__)
    project_root = None
    while curr and os.path.dirname(curr) != curr:
        curr = os.path.dirname(curr)
        if os.path.basename(curr) == "Content":
            project_root = os.path.dirname(curr)
            break
    
    if not project_root:
        project_root = unreal.Paths.project_dir()
    doc_path = os.path.join(project_root, "docs", "DEVICE_API_MAP.md")
    os.makedirs(os.path.dirname(doc_path), exist_ok=True)
    
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    core.log_info(f"✓ Master Sync Complete! Document updated: {doc_path}")
    return {"status": "ok", "path": doc_path}


@register_tool(
    name="world_state_export",
    category="API Explorer",
    description="Export the full live state of every actor in the level — transforms + readable device properties — to a single JSON Claude can reason about.",
    tags=["world", "state", "export", "ai", "automation", "snapshot"],
    example='result = tb.run("world_state_export")  # → Saved/UEFN_Toolbelt/world_state.json with all actors + transforms + properties',
)
def world_state_export(**kwargs) -> dict:
    """
    Captures the complete live state of the level as a machine-readable JSON:
      - Every actor's label, class, location, rotation, scale, tags, visibility
      - Every readable editor property on each actor (device settings, channel
        assignments, game rules, etc.)

    This is the AI read layer — Claude loads this file to understand exactly
    what is in the level and how every device is currently configured before
    deciding what actions to take.

    Output: Saved/UEFN_Toolbelt/world_state.json
    Also auto-synced to docs/world_state.json for git tracking.
    """
    from datetime import datetime

    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_sub.get_all_level_actors()
    if not all_actors:
        return {"status": "error", "message": "No actors in the level.", "count": 0}

    unreal.log(f"[TOOLBELT] world_state_export: capturing {len(all_actors)} actors...")

    actors_out = []
    for actor in all_actors:
        if not _is_valid(actor):
            continue

        # --- Transform ---
        try:
            loc = actor.get_actor_location()
            location = {"x": round(loc.x, 2), "y": round(loc.y, 2), "z": round(loc.z, 2)}
        except Exception:
            location = {}

        try:
            rot = actor.get_actor_rotation()
            rotation = {"pitch": round(rot.pitch, 2), "yaw": round(rot.yaw, 2), "roll": round(rot.roll, 2)}
        except Exception:
            rotation = {}

        try:
            sc = actor.get_actor_scale3d()
            scale = {"x": round(sc.x, 3), "y": round(sc.y, 3), "z": round(sc.z, 3)}
        except Exception:
            scale = {}

        # --- Tags ---
        try:
            tags = [str(t) for t in actor.tags] if actor.tags else []
        except Exception:
            tags = []

        # --- Visibility ---
        try:
            hidden = actor.is_hidden_ed()
        except Exception:
            hidden = False

        # --- World Outliner folder ---
        try:
            fp = actor.get_folder_path()
            folder = str(fp).strip("/") if fp else ""
        except Exception:
            folder = ""

        # --- Parent actor ---
        try:
            parent_actor = actor.get_attach_parent_actor()
            parent = parent_actor.get_actor_label() if parent_actor else ""
        except Exception:
            parent = ""

        # --- Bounds (center + half-extent in cm) ---
        try:
            origin, box_extent = actor.get_actor_bounds(False)
            bounds = {
                "center": {"x": round(origin.x, 1), "y": round(origin.y, 1), "z": round(origin.z, 1)},
                "extent": {"x": round(box_extent.x, 1), "y": round(box_extent.y, 1), "z": round(box_extent.z, 1)},
            }
        except Exception:
            bounds = {}

        # --- Static mesh asset path ---
        asset_path = ""
        try:
            if isinstance(actor, unreal.StaticMeshActor):
                mesh = actor.static_mesh_component.get_editor_property("static_mesh")
                if mesh:
                    asset_path = mesh.get_path_name().split(".")[0]
        except Exception:
            pass

        # --- Device properties (readable primitives only) ---
        props = {}
        for attr in dir(actor):
            if attr.startswith("_"):
                continue
            try:
                val = actor.get_editor_property(attr)
                if isinstance(val, (int, float, str, bool)):
                    props[attr] = val
                elif isinstance(val, unreal.EnumBase):
                    props[attr] = str(val)
                elif isinstance(val, unreal.Name):
                    props[attr] = str(val)
                elif isinstance(val, unreal.Vector):
                    props[attr] = {"x": round(val.x, 2), "y": round(val.y, 2), "z": round(val.z, 2)}
                elif isinstance(val, unreal.Rotator):
                    props[attr] = {"pitch": round(val.pitch, 2), "yaw": round(val.yaw, 2), "roll": round(val.roll, 2)}
            except Exception:
                pass

        actors_out.append({
            "label":      actor.get_actor_label(),
            "class":      type(actor).__name__,
            "folder":     folder,
            "parent":     parent,
            "location":   location,
            "rotation":   rotation,
            "scale":      scale,
            "bounds":     bounds,
            "asset_path": asset_path,
            "hidden":     hidden,
            "tags":       tags,
            "properties": props,
        })

    # Build summary for fast AI reasoning without scanning all actors
    class_counts: dict = {}
    folder_map: dict = {}
    for a in actors_out:
        class_counts[a["class"]] = class_counts.get(a["class"], 0) + 1
        f = a["folder"] or "(root)"
        folder_map[f] = folder_map.get(f, 0) + 1

    state = {
        "exported_at": datetime.now().isoformat(),
        "actor_count": len(actors_out),
        "summary": {
            "class_counts": dict(sorted(class_counts.items(), key=lambda x: x[1], reverse=True)),
            "folder_map":   dict(sorted(folder_map.items(), key=lambda x: x[1], reverse=True)),
        },
        "actors": actors_out,
    }

    saved_dir = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt")
    os.makedirs(saved_dir, exist_ok=True)
    out_path = os.path.join(saved_dir, "world_state.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    unreal.log(f"[TOOLBELT] ✓ World state saved: {out_path}")

    repo_path = _sync_to_repo(out_path, "world_state.json")
    if repo_path:
        unreal.log(f"[TOOLBELT] ✓ Auto-synced to repo: {repo_path}")

    return {"status": "ok", "path": out_path, "count": len(actors_out)}


# ─────────────────────────────────────────────────────────────────────────────
#  Device Catalog Scan
# ─────────────────────────────────────────────────────────────────────────────

# Class name fragments that identify Creative / Verse device Blueprints.
_DEVICE_CLASS_HINTS = [
    "Device", "Creative", "FortAthena", "Fortnite",
    "Timer", "Capture", "Score", "Trigger", "Spawner",
    "Manager", "Barrier", "Button", "Zone", "Tracker",
    "Mutator", "Beacon", "Guard", "Ammo", "Chest",
    "Camera", "Lock", "Switch", "Audio", "Race", "Stat",
    "Supply", "Round", "Pulse", "NPC", "Creature", "Zipline",
    "Teleporter", "Prop", "Pad", "Gate", "Relay",
]

# Top-level package paths to search in the Asset Registry.
# /Fortnite covers the live Creative device Blueprints.
# /Game covers any project-specific or imported device BPs.
_SEARCH_PATHS = ["/Fortnite", "/Game", "/FortniteGame"]


@register_tool(
    name="device_catalog_scan",
    category="API Explorer",
    description=(
        "Scan the Asset Registry for every Creative/Verse device class available "
        "in Fortnite — not just what is placed in the current level. "
        "Builds a complete device palette Claude can use to design levels from scratch."
    ),
    tags=["device", "catalog", "scan", "asset", "registry", "ai", "automation", "creative"],
    example='tb.run("device_catalog_scan")  # → docs/device_catalog.json — full palette of spawnable Creative devices',
)
def device_catalog_scan(
    extra_paths: list = None,
    save_to_docs: bool = True,
    **kwargs,
) -> dict:
    """
    Query the UEFN Asset Registry for every Blueprint that looks like a Creative
    device — covering all Fortnite packages, not just the current level.

    This is the AI design layer: once Claude knows every placeable device that
    exists (not just what's already in the level), it can propose what a level
    *should* have, generate the Verse wiring for it, and tell you exactly which
    device to drag from the Content Browser.

    Args:
        extra_paths:  Additional package paths to search (default: /Fortnite, /Game).
        save_to_docs: If True, auto-sync the result to docs/device_catalog.json
                      so it persists across sessions and is visible to Claude.

    Returns:
        {
          "status": "ok",
          "total": int,               # total assets scanned
          "devices_found": int,       # entries matching device hints
          "path": str,                # saved JSON path
          "categories": {             # devices grouped by hint keyword
            "Timer": [...],
            "Capture": [...],
            ...
          }
        }

    Output: Saved/UEFN_Toolbelt/device_catalog.json
            docs/device_catalog.json  (if save_to_docs=True)

    Historical note:
        First run on Device_API_Mapping (March 2026) — 521-actor level.
        This tool was built to answer: "What can Claude place in a level it
        has never seen?" The answer is the full Creative device palette.
    """
    from datetime import datetime

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    search_paths = list(_SEARCH_PATHS)
    if extra_paths:
        search_paths.extend(extra_paths)

    # Deduplicate while preserving order
    seen = set()
    search_paths = [p for p in search_paths if not (p in seen or seen.add(p))]

    unreal.log(f"[device_catalog_scan] Searching {len(search_paths)} package paths...")

    # ── Phase 1: gather all Blueprint assets across target paths ──────────────
    all_assets: List[unreal.AssetData] = []
    for pkg_path in search_paths:
        try:
            flt = unreal.ARFilter(
                package_paths=[pkg_path],
                class_names=["Blueprint", "BlueprintGeneratedClass"],
                recursive_paths=True,
            )
            batch = ar.get_assets(flt)
            unreal.log(f"[device_catalog_scan]   {pkg_path}: {len(batch)} Blueprint assets")
            all_assets.extend(batch)
        except Exception as e:
            unreal.log(f"[device_catalog_scan]   {pkg_path}: skipped ({e})")

    unreal.log(f"[device_catalog_scan] Total Blueprint assets found: {len(all_assets)}")

    # ── Phase 2: filter by device-hint keywords ───────────────────────────────
    hints_lower = [h.lower() for h in _DEVICE_CLASS_HINTS]

    devices: List[Dict[str, Any]] = []
    categories: Dict[str, List[Dict]] = {}

    for asset in all_assets:
        # asset_name is the only required field — skip if unavailable
        try:
            asset_name = str(asset.asset_name)
        except Exception:
            continue

        # Optional fields: use new UE5 API with fallbacks for deprecated properties
        try:
            package_path = str(asset.package_path)
        except Exception:
            package_path = ""

        try:
            # get_full_name() replaced the deprecated object_path property
            object_path = asset.get_full_name()
        except Exception:
            object_path = package_path + "." + asset_name if package_path else asset_name

        try:
            # asset_class_path replaced the deprecated asset_class property
            class_name = str(asset.asset_class_path)
        except Exception:
            class_name = "Unknown"

        name_lower = asset_name.lower()
        matched_hint = next((h for h in _DEVICE_CLASS_HINTS if h.lower() in name_lower), None)
        if matched_hint is None:
            continue

        entry = {
            "name":         asset_name,
            "class":        class_name,
            "package_path": package_path,
            "object_path":  object_path,
            "hint":         matched_hint,
        }
        devices.append(entry)
        categories.setdefault(matched_hint, []).append(entry)

    unreal.log(f"[device_catalog_scan] Devices identified: {len(devices)} "
               f"across {len(categories)} categories.")

    # ── Phase 3: build output ─────────────────────────────────────────────────
    catalog = {
        "scanned_at":    datetime.now().isoformat(),
        "total_scanned": len(all_assets),
        "devices_found": len(devices),
        "search_paths":  search_paths,
        "categories":    {k: sorted(v, key=lambda x: x["name"])
                          for k, v in sorted(categories.items())},
        "all_devices":   sorted(devices, key=lambda x: x["name"]),
    }

    # ── Phase 4: save ─────────────────────────────────────────────────────────
    saved_dir = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt")
    os.makedirs(saved_dir, exist_ok=True)
    out_path = os.path.join(saved_dir, "device_catalog.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    unreal.log(f"[device_catalog_scan] ✓ Catalog saved: {out_path}")

    repo_path = None
    if save_to_docs:
        repo_path = _sync_to_repo(out_path, "device_catalog.json")
        if repo_path:
            unreal.log(f"[device_catalog_scan] ✓ Auto-synced to repo: {repo_path}")

    # Summary log — give Claude a readable breakdown
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
        unreal.log(f"  [{cat:20s}] {len(items):4d} devices")

    return {
        "status":        "ok",
        "total_scanned": len(all_assets),
        "devices_found": len(devices),
        "categories":    {k: len(v) for k, v in categories.items()},
        "path":          out_path,
        "repo_path":     repo_path or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Asset Catalog — the full Fortnite content palette
#  (StaticMesh / Materials / Niagara FX / Audio — not just device Blueprints)
# ─────────────────────────────────────────────────────────────────────────────

# Class groups the scanner knows how to catalog. Keys are the user-facing
# group names accepted by asset_catalog_scan(groups=[...]).
_CATALOG_CLASS_GROUPS: Dict[str, List[str]] = {
    "meshes":    ["StaticMesh"],
    "materials": ["Material", "MaterialInstanceConstant"],
    "fx":        ["NiagaraSystem", "ParticleSystem"],
    "audio":     ["SoundWave", "SoundCue"],
    "textures":  ["Texture2D"],
}

# Script module for each class — needed for the UE5.1+ class_paths filter
# fallback when class_names is rejected by the running engine build.
_CATALOG_CLASS_MODULE: Dict[str, str] = {
    "StaticMesh":               "/Script/Engine",
    "Material":                 "/Script/Engine",
    "MaterialInstanceConstant": "/Script/Engine",
    "NiagaraSystem":            "/Script/Niagara",
    "ParticleSystem":           "/Script/Engine",
    "SoundWave":                "/Script/Engine",
    "SoundCue":                 "/Script/Engine",
    "Texture2D":                "/Script/Engine",
}

# Asset name prefixes stripped before tokenizing (Epic naming conventions).
_CATALOG_NAME_PREFIXES = (
    "SM_", "SK_", "M_", "MI_", "MF_", "NS_", "P_", "PS_",
    "T_", "S_", "SW_", "SC_", "A_", "BP_",
)

# In-process cache for asset_catalog_query — avoids re-reading a multi-MB
# JSON from disk on every query. Invalidated by file mtime.
_catalog_cache: Dict[str, Any] = {"mtime": None, "data": None}

# Namespaces the UEFN AssetReferenceRestrictions validator accepts in user maps
# (verified empirically 2026-06: hand-placed actors reference only these).
# Everything else in the mounted library — e.g. /Game/Environments/Sets/* —
# fails validation and blocks publishing.
_PUBLISHABLE_PREFIXES = ("/Game/Creative/", "/Game/Packages/", "/Engine/BasicShapes/")


def is_publishable_path(path: str) -> bool:
    """True if a user map may legally reference this asset path."""
    if path.startswith(_PUBLISHABLE_PREFIXES):
        return True
    parts = path.split("/")
    # Gallery plugin mounts: /City_Assets/..., /Suburban_Assets/..., etc.
    return len(parts) > 1 and parts[1].endswith("_Assets")


def _gallery_mounts() -> List[str]:
    """Discover all *_Assets gallery plugin mounts from the Asset Registry."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    roots: Set[str] = set()
    try:
        for p in ar.get_all_cached_paths():
            root = str(p).strip("/").split("/")[0]
            if root.endswith("_Assets"):
                roots.add(f"/{root}")
    except Exception as e:
        unreal.log_warning(f"[asset_catalog] gallery mount discovery failed: {e}")
    return sorted(roots)


def _catalog_json_path() -> str:
    saved_dir = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt")
    os.makedirs(saved_dir, exist_ok=True)
    return os.path.join(saved_dir, "asset_catalog.json")


def _catalog_tag(asset, tag_name: str):
    """Read one Asset Registry tag as a string — never loads the asset."""
    try:
        v = asset.get_tag_value(tag_name)
        if v is None:
            return None
        s = str(v)
        return s if s and s != "None" else None
    except Exception:
        return None


def _catalog_parse_size(approx: str):
    """Parse the StaticMesh 'ApproxSize' tag ('128x64x256') into [x, y, z]."""
    try:
        parts = [int(float(p)) for p in approx.lower().split("x")]
        return parts if len(parts) == 3 else None
    except Exception:
        return None


def _catalog_name_tokens(name: str) -> List[str]:
    """Tokenize an asset name for keyword search: strip prefix, split, lowercase."""
    import re as _re
    n = name
    for p in _CATALOG_NAME_PREFIXES:
        if n.startswith(p):
            n = n[len(p):]
            break
    tokens: List[str] = []
    for part in _re.split(r"[_\-\s.]+", n):
        for tok in _re.findall(r"[A-Z]+[a-z]*|[a-z]+", part):
            if len(tok) >= 3:
                tokens.append(tok.lower())
    return tokens


def _catalog_ar_query(ar, pkg_path: str, cls: str) -> list:
    """One batched Asset Registry query: (package path × class). Returns AssetData list."""
    # Proven path in this UEFN build first (device_catalog_scan uses class_names),
    # then the UE5.1+ class_paths API as fallback.
    try:
        flt = unreal.ARFilter(
            package_paths=[pkg_path],
            class_names=[cls],
            recursive_paths=True,
        )
        return list(ar.get_assets(flt))
    except Exception:
        pass
    try:
        flt = unreal.ARFilter(
            package_paths=[pkg_path],
            class_paths=[unreal.TopLevelAssetPath(_CATALOG_CLASS_MODULE.get(cls, "/Script/Engine"), cls)],
            recursive_paths=True,
        )
        return list(ar.get_assets(flt))
    except Exception as e:
        unreal.log_warning(f"[asset_catalog_scan]   {pkg_path} × {cls}: query failed ({e})")
        return []


def _catalog_build_entry(asset, cls: str):
    """Build one compact catalog entry from AssetData tags only — zero asset loads."""
    try:
        name = str(asset.asset_name)
        path = str(asset.package_name)
    except Exception:
        return None
    entry: Dict[str, Any] = {"name": name, "path": path}

    if cls == "StaticMesh":
        tris = _catalog_tag(asset, "Triangles")
        if tris:
            try:
                entry["tris"] = int(float(tris))
            except Exception:
                pass
        approx = _catalog_tag(asset, "ApproxSize")
        if approx:
            size = _catalog_parse_size(approx)
            if size:
                entry["size"] = size
        nanite = _catalog_tag(asset, "NaniteEnabled")
        if nanite == "True":
            entry["nanite"] = True
    elif cls in ("SoundWave", "SoundCue"):
        dur = _catalog_tag(asset, "Duration")
        if dur:
            try:
                entry["duration"] = round(float(dur), 2)
            except Exception:
                pass
    elif cls == "Texture2D":
        dims = _catalog_tag(asset, "Dimensions")
        if dims:
            entry["dims"] = dims

    return entry


@register_tool(
    name="asset_catalog_scan",
    category="API Explorer",
    description=(
        "Catalog the full Fortnite content library by asset class — StaticMeshes, "
        "Materials, Niagara FX, Audio — via batched Asset Registry queries. "
        "Builds the visual palette Claude uses to construct non-primitive maps."
    ),
    tags=["asset", "catalog", "mesh", "material", "fx", "audio", "scan", "registry", "ai", "palette"],
    example='tb.run("asset_catalog_scan", groups=["meshes"], max_per_class=5000)',
)
def asset_catalog_scan(
    groups: list = None,
    extra_paths: list = None,
    max_per_class: int = 0,
    include_gallery_mounts: bool = True,
    **kwargs,
) -> dict:
    """
    Scan the Asset Registry for every content asset of the requested classes
    across the Fortnite library mounts — not just the current level or project.

    Unlike device_catalog_scan (Blueprints/devices only), this catalogs the
    *visual* palette: meshes with triangle counts and bounding sizes, materials,
    Niagara effects, and audio with durations — all read from Asset Registry
    tags without loading a single asset (pak-safe, Quirk #32 aware: queries are
    batched per (path × class), never a whole-mount enumeration).

    Args:
        groups:        Class groups to scan. Any of: "meshes", "materials",
                       "fx", "audio", "textures". Default: meshes, materials,
                       fx, audio (textures excluded — usually huge and rarely
                       needed for layout work).
        extra_paths:   Additional package paths to search (default: /Fortnite,
                       /Game, /FortniteGame).
        max_per_class: Safety cap per class per path. 0 = unlimited. Use a few
                       thousand on the first run in a new project to gauge scale.

    Returns:
        {"status": "ok", "counts": {class: n}, "total": int, "path": str}

    Output: Saved/UEFN_Toolbelt/asset_catalog.json (compact JSON — query it
    with asset_catalog_query, do not read it whole over MCP).
    """
    from datetime import datetime

    if groups is None:
        groups = ["meshes", "materials", "fx", "audio"]
    bad = [g for g in groups if g not in _CATALOG_CLASS_GROUPS]
    if bad:
        return {"status": "error",
                "error": f"Unknown group(s) {bad}. Valid: {sorted(_CATALOG_CLASS_GROUPS)}"}

    classes: List[str] = []
    for g in groups:
        classes.extend(_CATALOG_CLASS_GROUPS[g])

    search_paths = list(_SEARCH_PATHS)
    if include_gallery_mounts:
        search_paths.extend(_gallery_mounts())
    if extra_paths:
        search_paths.extend(extra_paths)
    seen: Set[str] = set()
    search_paths = [p for p in search_paths if not (p in seen or seen.add(p))]

    unreal.log(f"[asset_catalog_scan] Scanning {len(classes)} classes × "
               f"{len(search_paths)} paths (max_per_class={max_per_class or 'unlimited'})...")

    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets_by_class: Dict[str, List[dict]] = {}
    seen_paths: Set[str] = set()

    for cls in classes:
        entries = assets_by_class.setdefault(cls, [])
        for pkg_path in search_paths:
            batch = _catalog_ar_query(ar, pkg_path, cls)
            unreal.log(f"[asset_catalog_scan]   {pkg_path} × {cls}: {len(batch)} assets")
            added = 0
            for asset in batch:
                if max_per_class and added >= max_per_class:
                    unreal.log(f"[asset_catalog_scan]   {pkg_path} × {cls}: "
                               f"capped at {max_per_class}")
                    break
                entry = _catalog_build_entry(asset, cls)
                if entry is None or entry["path"] in seen_paths:
                    continue
                seen_paths.add(entry["path"])
                entries.append(entry)
                added += 1
            del batch

    counts = {cls: len(v) for cls, v in assets_by_class.items()}
    total = sum(counts.values())

    catalog = {
        "scanned_at":   datetime.now().isoformat(),
        "search_paths": search_paths,
        "groups":       groups,
        "counts":       counts,
        "assets":       {cls: sorted(v, key=lambda x: x["name"])
                         for cls, v in assets_by_class.items()},
    }

    out_path = _catalog_json_path()
    # Compact separators — a full library scan can hold 100k+ entries and
    # indent=2 would triple the file size.
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, separators=(",", ":"))

    _catalog_cache["mtime"] = None   # force reload on next query

    unreal.log(f"[asset_catalog_scan] ✓ {total} assets cataloged → {out_path}")
    for cls, n in sorted(counts.items(), key=lambda x: -x[1]):
        unreal.log(f"  [{cls:24s}] {n:6d}")

    return {"status": "ok", "counts": counts, "total": total, "path": out_path}


@register_tool(
    name="asset_catalog_query",
    category="API Explorer",
    description=(
        "Search the cached asset catalog (asset_catalog.json) by keywords, class, "
        "triangle budget, and size — returns compact entries ready for spawn_actor. "
        "Run asset_catalog_scan first."
    ),
    tags=["asset", "catalog", "query", "search", "mesh", "material", "ai", "palette"],
    example='tb.run("asset_catalog_query", query="wall stone", class_filter="StaticMesh", max_results=20)',
)
def asset_catalog_query(
    query: str = "",
    class_filter: str = "",
    path_filter: str = "",
    max_tris: int = 0,
    max_size: int = 0,
    max_results: int = 50,
    sort: str = "name",
    stats_only: bool = False,
    measure: bool = False,
    publishable: bool = False,
    **kwargs,
) -> dict:
    """
    Query the asset catalog produced by asset_catalog_scan — without re-scanning
    and without ever loading assets. This is the AI selection layer: find the
    right wall/tree/rock/material by keyword, filtered to a sane polygon and
    size budget, and feed the returned path straight into spawn_actor.

    Args:
        query:        Space-separated keywords — ALL must appear in the asset
                      name or path (case-insensitive). E.g. "wall stone".
        class_filter: Substring match on the asset class, e.g. "StaticMesh",
                      "Material", "Niagara", "Sound".
        path_filter:  Substring that must appear in the package path, e.g.
                      "/Fortnite/Environments".
        max_tris:     Skip meshes with more triangles than this. 0 = no limit.
        max_size:     Skip meshes whose largest bounding dimension (cm) exceeds
                      this. 0 = no limit.
        max_results:  Cap on returned entries (default 50).
        sort:         "name" | "tris" (ascending) | "size" (largest dim, asc).
        stats_only:   Return only per-class counts and the most frequent name
                      tokens among matches — use this first to orient in an
                      unfamiliar library before pulling entries.
        measure:      Load each RETURNED StaticMesh (max_results of them, never
                      the whole catalog) and fill real "size" [x,y,z] cm,
                      "tris", and "slots". Needed in UEFN: the cooked pak
                      Asset Registry strips Triangles/ApproxSize tags, so
                      scan-time metadata is empty there (~45 ms per asset).
        publishable:  Only return assets a user map may legally reference
                      (/Game/Creative, /Game/Packages, *_Assets gallery
                      mounts). Anything else fails the UEFN
                      AssetReferenceRestrictions validator and blocks
                      publishing — ALWAYS set True when picking assets to
                      place in a real map.

    Returns:
        {"status": "ok", "total_matches": int, "shown": int, "results": [...],
         "counts_by_class": {...}}
    """
    cat_path = _catalog_json_path()
    if not os.path.isfile(cat_path):
        return {"status": "error",
                "error": "No asset catalog found. Run asset_catalog_scan first."}

    mtime = os.path.getmtime(cat_path)
    if _catalog_cache["mtime"] != mtime:
        with open(cat_path, encoding="utf-8") as f:
            _catalog_cache["data"] = json.load(f)
        _catalog_cache["mtime"] = mtime
    data = _catalog_cache["data"]

    tokens = [t for t in query.lower().split() if t]
    cls_f  = class_filter.lower()
    path_f = path_filter.lower()

    matches: List[dict] = []
    counts_by_class: Dict[str, int] = {}
    token_freq: Dict[str, int] = {}

    for cls, entries in data.get("assets", {}).items():
        if cls_f and cls_f not in cls.lower():
            continue
        for e in entries:
            if publishable and not is_publishable_path(e["path"]):
                continue
            hay = (e["name"] + " " + e["path"]).lower()
            if tokens and not all(t in hay for t in tokens):
                continue
            if path_f and path_f not in e["path"].lower():
                continue
            if max_tris and e.get("tris", 0) > max_tris:
                continue
            if max_size and e.get("size") and max(e["size"]) > max_size:
                continue
            counts_by_class[cls] = counts_by_class.get(cls, 0) + 1
            if stats_only:
                for tok in _catalog_name_tokens(e["name"]):
                    token_freq[tok] = token_freq.get(tok, 0) + 1
            else:
                matches.append({**e, "class": cls})

    total = sum(counts_by_class.values())

    if stats_only:
        top_tokens = sorted(token_freq.items(), key=lambda x: -x[1])[:100]
        return {"status": "ok", "total_matches": total,
                "counts_by_class": counts_by_class,
                "top_tokens": dict(top_tokens),
                "scanned_at": data.get("scanned_at", "")}

    if sort == "tris":
        matches.sort(key=lambda e: e.get("tris", 0))
    elif sort == "size":
        matches.sort(key=lambda e: max(e["size"]) if e.get("size") else 0)
    else:
        matches.sort(key=lambda e: e["name"])

    shown = matches[:max_results]

    if measure:
        for e in shown:
            if "size" in e and "tris" in e:
                continue
            try:
                obj = unreal.EditorAssetLibrary.load_asset(e["path"])
            except Exception:
                obj = None
            if obj is None or not isinstance(obj, unreal.StaticMesh):
                continue
            try:
                bb = obj.get_bounding_box()
                e["size"] = [round(bb.max.x - bb.min.x),
                             round(bb.max.y - bb.min.y),
                             round(bb.max.z - bb.min.z)]
            except Exception:
                pass
            try:
                e["tris"] = obj.get_num_triangles(0)
            except Exception:
                pass
            try:
                e["slots"] = obj.get_num_sections(0)
            except Exception:
                pass

    return {"status": "ok", "total_matches": total, "shown": len(shown),
            "counts_by_class": counts_by_class, "results": shown,
            "scanned_at": data.get("scanned_at", "")}


@register_tool(
    name="kit_metrics",
    category="API Explorer",
    description=(
        "Measure one building kit's native grid: load a capped sample of its "
        "meshes, group by role keyword (wall/floor/door/roof/...), and report "
        "per-role size medians + the inferred build cell. Ground truth for "
        "building on a kit's own grid instead of guessing 512."
    ),
    tags=["kit", "metrics", "grid", "measure", "palette", "building", "ai"],
    example='tb.run("kit_metrics", path_filter="JungleTemple")',
)
def kit_metrics(
    path_filter: str = "",
    max_measure: int = 40,
    **kwargs,
) -> dict:
    """
    Derive a kit's native metrics from real geometry.

    Reads the asset catalog (run asset_catalog_scan first), filters StaticMesh
    entries whose path contains path_filter, loads up to max_measure of them
    (~45 ms each), and aggregates bbox sizes per role keyword found in the
    asset name: wall, floor, door, window, roof, stair, pillar, trim, corner.

    Returns per-role piece counts and median [x, y, z], plus "cell" (median
    wall X-length) and "wall_height" — the two numbers building layout math
    needs.

    Args:
        path_filter: Substring of the kit's package path (e.g. "JungleTemple",
                     "Fortress_Broken_Walls"). Required.
        max_measure: Cap on loaded assets (default 40).
    """
    if not path_filter:
        return {"status": "error", "error": "path_filter is required (kit path substring)"}

    cat_path = _catalog_json_path()
    if not os.path.isfile(cat_path):
        return {"status": "error", "error": "No asset catalog — run asset_catalog_scan first."}
    mtime = os.path.getmtime(cat_path)
    if _catalog_cache["mtime"] != mtime:
        with open(cat_path, encoding="utf-8") as f:
            _catalog_cache["data"] = json.load(f)
        _catalog_cache["mtime"] = mtime
    data = _catalog_cache["data"]

    pf = path_filter.lower()
    meshes = [e for e in data.get("assets", {}).get("StaticMesh", [])
              if pf in e["path"].lower()]
    if not meshes:
        return {"status": "error", "error": f"No StaticMesh in catalog matching '{path_filter}'"}

    roles = ("wall", "floor", "door", "window", "roof", "stair", "pillar", "trim", "corner")
    by_role: Dict[str, list] = {r: [] for r in roles}
    publishable_count = 0

    measured = 0
    for e in meshes:
        if measured >= max_measure:
            break
        name_l = e["name"].lower()
        role = next((r for r in roles if r in name_l), None)
        if role is None:
            continue
        obj = unreal.EditorAssetLibrary.load_asset(e["path"])
        if obj is None or not isinstance(obj, unreal.StaticMesh):
            continue
        measured += 1
        if is_publishable_path(e["path"]):
            publishable_count += 1
        try:
            bb = obj.get_bounding_box()
            size = sorted([bb.max.x - bb.min.x, bb.max.y - bb.min.y], reverse=True) \
                + [bb.max.z - bb.min.z]
            # store as [long_horizontal, short_horizontal, height]
            by_role[role].append([round(v, 1) for v in size])
        except Exception:
            continue

    def _median(vals):
        s = sorted(vals)
        return s[len(s) // 2] if s else None

    role_stats = {}
    for r, sizes in by_role.items():
        if not sizes:
            continue
        role_stats[r] = {
            "count": len(sizes),
            "median_size": [_median([s[0] for s in sizes]),
                            _median([s[1] for s in sizes]),
                            _median([s[2] for s in sizes])],
        }

    cell = role_stats.get("wall", {}).get("median_size", [None])[0]
    wall_h = role_stats.get("wall", {}).get("median_size", [None, None, None])[2]

    out = {
        "status": "ok",
        "kit": path_filter,
        "meshes_in_catalog": len(meshes),
        "measured": measured,
        "publishable_measured": publishable_count,
        "cell": cell,
        "wall_height": wall_h,
        "roles": role_stats,
    }
    unreal.log(f"[kit_metrics] {path_filter}: cell={cell} wall_h={wall_h} "
               f"roles={ {r: v['count'] for r, v in role_stats.items()} }")
    return out
