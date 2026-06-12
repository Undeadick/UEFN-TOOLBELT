"""
UEFN TOOLBELT — Theme Palettes & Modular Building Generator
============================================================
The bridge between the asset catalog and beautiful maps.

A *palette* maps abstract building roles (floor, wall, door, roof, ...) to
concrete Fortnite library assets, with measured sizes and local bounding
boxes stored at save time. Generators then consume palettes instead of
hardcoded mesh paths — switch the palette and the same building plan
re-materializes as a castle, a suburban house, or a neon arcade.

Workflow (AI or human):
    1. asset_catalog_scan                       → know the library
    2. asset_catalog_query("castle wall", measure=True)
                                                → pick pieces
    3. palette_save("castle", roles={...})      → freeze the theme
    4. building_generate(palette="castle", width=4, depth=3, floors=2)
                                                → modular building, one undo

Placement math: every piece is positioned via its *local bounding box*
(captured by palette_save), so kits with corner pivots, bottom pivots, or
center pivots all land exactly where intended.

Palettes live in Saved/UEFN_Toolbelt/palettes/{name}.json.
"""

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import unreal

from ..core import (
    load_asset, log_info, log_warning, log_error, undo_transaction,
)
from ..registry import register_tool

# Roles a palette may define. Only ROLE_REQUIRED are mandatory for
# building_generate — everything else upgrades the result when present.
ROLE_REQUIRED = ("floor", "wall")
ROLE_OPTIONAL = ("door", "roof", "corner", "window", "stairs", "pillar", "trim")
ALL_ROLES = ROLE_REQUIRED + ROLE_OPTIONAL

_SIDES = ("south", "north", "west", "east")


# ─────────────────────────────────────────────────────────────────────────────
#  Palette storage
# ─────────────────────────────────────────────────────────────────────────────

def _palettes_dir() -> str:
    d = os.path.join(unreal.Paths.project_saved_dir(), "UEFN_Toolbelt", "palettes")
    os.makedirs(d, exist_ok=True)
    return d


def _palette_path(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in "-_").strip() or "palette"
    return os.path.join(_palettes_dir(), f"{safe}.json")


def _load_palette(name: str) -> Optional[dict]:
    p = _palette_path(name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _measure_role_asset(asset_path: str) -> Optional[dict]:
    """Load a StaticMesh once and capture size + local bbox for placement math."""
    obj = load_asset(asset_path)
    if obj is None or not isinstance(obj, unreal.StaticMesh):
        return None
    try:
        bb = obj.get_bounding_box()
        bb_min = [bb.min.x, bb.min.y, bb.min.z]
        bb_max = [bb.max.x, bb.max.y, bb.max.z]
    except Exception:
        return None
    entry = {
        "path":     asset_path,
        "size":     [round(bb_max[0] - bb_min[0], 1),
                     round(bb_max[1] - bb_min[1], 1),
                     round(bb_max[2] - bb_min[2], 1)],
        "bbox_min": [round(v, 1) for v in bb_min],
        "bbox_max": [round(v, 1) for v in bb_max],
    }
    try:
        entry["tris"] = obj.get_num_triangles(0)
    except Exception:
        pass
    return entry


@register_tool(
    name="palette_save",
    category="Procedural",
    description=(
        "Save a named theme palette mapping building roles (floor, wall, door, "
        "roof, ...) to library asset paths. Measures each piece's size and local "
        "bounding box so generators place any kit pivot-correctly."
    ),
    tags=["palette", "theme", "building", "modular", "ai", "save"],
    example='tb.run("palette_save", name="castle", roles={"wall": "/Game/.../PC_Tower_Wall_1", "floor": "/Game/.../PC_Floor_1"})',
)
def palette_save(name: str = "", roles: dict = None, overwrite: bool = True, **kwargs) -> dict:
    """
    Create or update a theme palette.

    Args:
        name:      Palette name (file-safe characters survive).
        roles:     {role: asset_path}. Required roles: floor, wall.
                   Optional: door, roof, corner, window, stairs, pillar, trim.
        overwrite: Replace an existing palette of the same name (default True).

    Each asset is loaded once to capture real dimensions and the local
    bounding box — the data building_generate needs for exact placement.
    """
    if not name:
        return {"status": "error", "error": "name is required"}
    if not roles:
        return {"status": "error", "error": "roles dict is required, e.g. "
                '{"wall": "/Game/...", "floor": "/Game/..."}'}

    unknown = [r for r in roles if r not in ALL_ROLES]
    if unknown:
        return {"status": "error",
                "error": f"Unknown role(s) {unknown}. Valid: {list(ALL_ROLES)}"}

    if not overwrite and os.path.isfile(_palette_path(name)):
        return {"status": "error", "error": f"Palette '{name}' exists (overwrite=False)"}

    measured: Dict[str, dict] = {}
    failed: List[str] = []
    for role, path in roles.items():
        info = _measure_role_asset(path)
        if info is None:
            failed.append(f"{role}: {path}")
        else:
            measured[role] = info

    if failed:
        return {"status": "error",
                "error": "Could not load/measure as StaticMesh: " + "; ".join(failed)}

    missing = [r for r in ROLE_REQUIRED if r not in measured]
    if missing:
        return {"status": "error", "error": f"Missing required role(s): {missing}"}

    data = {"name": name, "saved_at": datetime.now().isoformat(), "roles": measured}
    with open(_palette_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    log_info(f"[palette_save] '{name}' saved with roles: {sorted(measured)}")
    return {"status": "ok", "name": name, "roles": {r: m["size"] for r, m in measured.items()},
            "path": _palette_path(name)}


@register_tool(
    name="palette_list",
    category="Procedural",
    description="List all saved theme palettes with their roles and piece sizes.",
    tags=["palette", "theme", "building", "list"],
    example='tb.run("palette_list")',
)
def palette_list(**kwargs) -> dict:
    """List every saved palette: name, roles, and per-piece sizes."""
    out = []
    for fn in sorted(os.listdir(_palettes_dir())):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(_palettes_dir(), fn), encoding="utf-8") as f:
                d = json.load(f)
            out.append({"name": d.get("name", fn[:-5]),
                        "roles": {r: m.get("size") for r, m in d.get("roles", {}).items()},
                        "saved_at": d.get("saved_at", "")})
        except Exception as e:
            out.append({"name": fn[:-5], "error": str(e)})
    return {"status": "ok", "count": len(out), "palettes": out}


@register_tool(
    name="palette_get",
    category="Procedural",
    description="Return the full definition of one saved palette — paths, sizes, bounding boxes.",
    tags=["palette", "theme", "building", "get", "inspect"],
    example='tb.run("palette_get", name="castle")',
)
def palette_get(name: str = "", **kwargs) -> dict:
    """Full palette definition, including measured bounding boxes per role."""
    d = _load_palette(name)
    if d is None:
        return {"status": "error", "error": f"No palette named '{name}'"}
    return {"status": "ok", "palette": d}


@register_tool(
    name="palette_delete",
    category="Procedural",
    description="Delete a saved theme palette by name.",
    tags=["palette", "theme", "building", "delete"],
    example='tb.run("palette_delete", name="castle")',
)
def palette_delete(name: str = "", **kwargs) -> dict:
    """Delete one palette file."""
    p = _palette_path(name)
    if not os.path.isfile(p):
        return {"status": "error", "error": f"No palette named '{name}'"}
    os.remove(p)
    return {"status": "ok", "deleted": name}


# ─────────────────────────────────────────────────────────────────────────────
#  Building generator
# ─────────────────────────────────────────────────────────────────────────────

def _rot_z(v: List[float], yaw_deg: float) -> List[float]:
    """Rotate a local-space vector around Z by yaw degrees (UE yaw convention)."""
    r = math.radians(yaw_deg)
    c, s = math.cos(r), math.sin(r)
    return [v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2]]


class _Spawner:
    """Spawns palette pieces so their bbox center lands exactly at a target point."""

    def __init__(self, folder: str):
        self.actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.folder = folder
        self.assets: Dict[str, Any] = {}
        self.spawned: List[Any] = []

    def _asset(self, info: dict):
        path = info["path"]
        if path not in self.assets:
            self.assets[path] = load_asset(path)
        return self.assets[path]

    def place(self, info: dict, bbox_center_world: List[float], yaw: float, label: str):
        asset = self._asset(info)
        if asset is None:
            return None
        bmin, bmax = info["bbox_min"], info["bbox_max"]
        local_center = [(bmin[i] + bmax[i]) / 2.0 for i in range(3)]
        off = _rot_z(local_center, yaw)
        loc = unreal.Vector(bbox_center_world[0] - off[0],
                            bbox_center_world[1] - off[1],
                            bbox_center_world[2] - off[2])
        actor = self.actor_sub.spawn_actor_from_object(asset, loc, unreal.Rotator(0.0, yaw, 0.0))
        if actor is None:
            return None
        actor.set_actor_label(label)
        try:
            actor.set_folder_path(unreal.Name(self.folder))
        except Exception:
            pass
        self.spawned.append(actor)
        return actor


@register_tool(
    name="building_generate",
    category="Procedural",
    description=(
        "Generate a modular building from a saved theme palette — tiled floors, "
        "perimeter walls per storey, optional door and roof. Pivot-exact placement "
        "via stored bounding boxes. One undo reverts the whole building."
    ),
    tags=["building", "generate", "modular", "palette", "procedural", "ai", "house"],
    example='tb.run("building_generate", palette="castle", width=4, depth=3, floors=2, door_side="south")',
)
def building_generate(
    palette: str = "",
    width: int = 3,
    depth: int = 3,
    floors: int = 1,
    location: list = None,
    door_side: str = "south",
    folder: str = "Building",
    dry_run: bool = False,
    focus: bool = False,
    **kwargs,
) -> dict:
    """
    Build a rectangular modular structure from palette pieces.

    Layout model:
        - The wall piece's bbox X-length defines the grid cell.
        - Footprint = width × depth cells, centered on `location`.
        - Walls line the perimeter on every storey; the middle segment of
          `door_side` on the ground floor becomes the door piece (if defined).
        - Floor pieces tile the footprint with their bbox top at location.z.
        - Roof pieces (if defined) tile the footprint at the top wall plane.

    Args:
        palette:   Saved palette name (palette_save first).
        width:     Footprint width in wall segments (1–40).
        depth:     Footprint depth in wall segments (1–40).
        floors:    Storeys to stack (1–10).
        location:  [x, y, z] of the building center at ground level.
                   Default: current viewport camera position (z kept).
        door_side: "south" | "north" | "west" | "east" — ground-floor door wall.
        folder:    World Outliner folder for all spawned actors.
        dry_run:   Plan only — return piece counts and bounds, spawn nothing.
        focus:     Jump the viewport to an overhead view after generation.

    Returns:
        {"status": "ok", "pieces": {...}, "total": n, "cell": cm,
         "bounds": {"center": [...], "extent": [...]}}
    """
    pal = _load_palette(palette)
    if pal is None:
        return {"status": "error", "error": f"No palette named '{palette}'. "
                "Run palette_save first (see palette_list)."}
    roles = pal["roles"]
    missing = [r for r in ROLE_REQUIRED if r not in roles]
    if missing:
        return {"status": "error", "error": f"Palette '{palette}' lacks role(s): {missing}"}

    width = max(1, min(int(width), 40))
    depth = max(1, min(int(depth), 40))
    floors = max(1, min(int(floors), 10))
    if door_side not in _SIDES:
        return {"status": "error", "error": f"door_side must be one of {_SIDES}"}

    wall = roles["wall"]
    floor = roles["floor"]
    door = roles.get("door")
    roof = roles.get("roof")

    cell = float(wall["size"][0])
    wall_h = float(wall["size"][2])
    if cell <= 10.0 or wall_h <= 10.0:
        return {"status": "error", "error": f"Wall piece too small to tile: size={wall['size']}"}

    if location is None:
        try:
            cam_loc, _cam_rot = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
            location = [cam_loc.x, cam_loc.y, cam_loc.z]
        except Exception:
            location = [0.0, 0.0, 0.0]
    cx, cy, base_z = float(location[0]), float(location[1]), float(location[2])

    w_total = width * cell
    d_total = depth * cell
    ox = cx - w_total / 2.0   # footprint origin (south-west corner)
    oy = cy - d_total / 2.0

    # ── Plan all pieces as (role_info, bbox_center_world, yaw, label) ─────────
    plan: List[tuple] = []

    # Floors — tile with the floor piece's own footprint, bbox top at base_z.
    fx, fy, fz = (max(float(floor["size"][0]), 10.0),
                  max(float(floor["size"][1]), 10.0),
                  float(floor["size"][2]))
    nx = max(1, round(w_total / fx))
    ny = max(1, round(d_total / fy))
    sx = w_total / nx   # stretch-free spacing; small seams beat overlaps
    sy = d_total / ny
    for i in range(nx):
        for j in range(ny):
            plan.append((floor,
                         [ox + (i + 0.5) * sx, oy + (j + 0.5) * sy, base_z - fz / 2.0],
                         0.0, f"BLD_Floor_{i}_{j}"))

    # Walls — perimeter, every storey. Door replaces the middle ground segment.
    door_index = {"south": width // 2, "north": width // 2,
                  "west": depth // 2, "east": depth // 2}[door_side]

    def wall_piece(side: str, idx: int, storey: int):
        use_door = (door is not None and storey == 0 and side == door_side and idx == door_index)
        info = door if use_door else wall
        z = base_z + storey * wall_h + float(info["size"][2]) / 2.0
        if side == "south":
            pos, yaw = [ox + (idx + 0.5) * cell, oy, z], 0.0
        elif side == "north":
            pos, yaw = [ox + (idx + 0.5) * cell, oy + d_total, z], 180.0
        elif side == "west":
            pos, yaw = [ox, oy + (idx + 0.5) * cell, z], 90.0
        else:  # east
            pos, yaw = [ox + w_total, oy + (idx + 0.5) * cell, z], 270.0
        tag = "Door" if use_door else "Wall"
        plan.append((info, pos, yaw, f"BLD_{tag}_{side}_{storey}_{idx}"))

    for storey in range(floors):
        for i in range(width):
            wall_piece("south", i, storey)
            wall_piece("north", i, storey)
        for j in range(depth):
            wall_piece("west", j, storey)
            wall_piece("east", j, storey)

    # Roof — tile at the top wall plane, bbox bottom resting on it.
    if roof is not None:
        rx, ry, rz = (max(float(roof["size"][0]), 10.0),
                      max(float(roof["size"][1]), 10.0),
                      float(roof["size"][2]))
        top_z = base_z + floors * wall_h
        rnx = max(1, round(w_total / rx))
        rny = max(1, round(d_total / ry))
        rsx = w_total / rnx
        rsy = d_total / rny
        for i in range(rnx):
            for j in range(rny):
                plan.append((roof,
                             [ox + (i + 0.5) * rsx, oy + (j + 0.5) * rsy, top_z + rz / 2.0],
                             0.0, f"BLD_Roof_{i}_{j}"))

    counts: Dict[str, int] = {}
    for _info, _pos, _yaw, label in plan:
        kind = label.split("_")[1]
        counts[kind] = counts.get(kind, 0) + 1

    bounds = {"center": [cx, cy, base_z + (floors * wall_h) / 2.0],
              "extent": [w_total / 2.0, d_total / 2.0, (floors * wall_h) / 2.0]}

    if len(plan) > 3000:
        return {"status": "error",
                "error": f"Plan of {len(plan)} pieces exceeds the 3000-actor safety cap. "
                "Reduce width/depth/floors."}

    if dry_run:
        return {"status": "ok", "dry_run": True, "pieces": counts, "total": len(plan),
                "cell": cell, "wall_height": wall_h, "bounds": bounds}

    # ── Spawn ────────────────────────────────────────────────────────────────
    spawner = _Spawner(folder)
    failed = 0
    with undo_transaction(f"Toolbelt: building_generate '{palette}' {width}x{depth}x{floors}"):
        for info, pos, yaw, label in plan:
            if spawner.place(info, pos, yaw, label) is None:
                failed += 1

    if focus:
        try:
            unreal.EditorLevelLibrary.set_level_viewport_camera_info(
                unreal.Vector(cx, cy - d_total, base_z + floors * wall_h + max(w_total, d_total)),
                unreal.Rotator(-45.0, 90.0, 0.0))
        except Exception:
            pass

    log_info(f"[building_generate] '{palette}': {len(spawner.spawned)} pieces "
             f"({width}x{depth}x{floors}), {failed} failed, folder '{folder}'")
    return {"status": "ok", "pieces": counts, "total": len(spawner.spawned),
            "failed": failed, "cell": cell, "wall_height": wall_h,
            "bounds": bounds, "folder": folder}
