"""
SVG to STL conversion with 3D-print optimization.

Handles: SVG parsing, Ramer-Douglas-Peucker simplification,
earcut triangulation, watertight extrusion, and base plate generation.
"""

import math
import re
from typing import List, Tuple, Optional

import mapbox_earcut as earcut
import numpy as np
from PIL import Image
from lxml import etree
from skimage.measure import find_contours, approximate_polygon
from stl import mesh

# ---------------------------------------------------------------------------
# Ramer-Douglas-Peucker simplification
# ---------------------------------------------------------------------------

def _perpendicular_dist(pt, line_start, line_end):
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    mag_sq = dx * dx + dy * dy
    if mag_sq == 0:
        return math.hypot(pt[0] - line_start[0], pt[1] - line_start[1])
    t = ((pt[0] - line_start[0]) * dx + (pt[1] - line_start[1]) * dy) / mag_sq
    t = max(0, min(1, t))
    proj_x = line_start[0] + t * dx
    proj_y = line_start[1] + t * dy
    return math.hypot(pt[0] - proj_x, pt[1] - proj_y)


def rdp_simplify(points: List[List[float]], epsilon: float) -> List[List[float]]:
    """Simplify a polyline using Ramer-Douglas-Peucker."""
    if len(points) <= 2:
        return points

    d_max = 0.0
    idx = 0
    for i in range(1, len(points) - 1):
        d = _perpendicular_dist(points[i], points[0], points[-1])
        if d > d_max:
            d_max = d
            idx = i

    if d_max > epsilon:
        left = rdp_simplify(points[: idx + 1], epsilon)
        right = rdp_simplify(points[idx:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


# ---------------------------------------------------------------------------
# SVG path tokenizer / parser
# ---------------------------------------------------------------------------

_CMD_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])")
_NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _tokenize_path(d: str):
    """Yield (command_char, [numbers]) tuples from an SVG path `d` string."""
    parts = _CMD_RE.split(d)
    for i in range(1, len(parts), 2):
        cmd = parts[i]
        nums = [float(n) for n in _NUM_RE.findall(parts[i + 1] if i + 1 < len(parts) else "")]
        yield cmd, nums


def _sample_cubic(p0, p1, p2, p3, n=8):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append([x, y])
    return pts


def _sample_quad(p0, p1, p2, n=8):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        x = u**2 * p0[0] + 2 * u * t * p1[0] + t**2 * p2[0]
        y = u**2 * p0[1] + 2 * u * t * p1[1] + t**2 * p2[1]
        pts.append([x, y])
    return pts


def parse_svg_path(d: str) -> List[List[List[float]]]:
    """Parse an SVG path `d` attribute into a list of closed contours."""
    contours: List[List[List[float]]] = []
    current: List[List[float]] = []
    cx, cy = 0.0, 0.0
    sx, sy = 0.0, 0.0  # subpath start
    last_ctrl = None
    last_cmd = ""

    for cmd, nums in _tokenize_path(d):
        is_rel = cmd.islower()
        C = cmd.upper()

        if C == "M":
            if current:
                contours.append(current)
                current = []
            pairs = list(zip(nums[0::2], nums[1::2]))
            for j, (x, y) in enumerate(pairs):
                if is_rel and j > 0:
                    cx += x; cy += y
                elif is_rel:
                    cx += x; cy += y
                else:
                    cx, cy = x, y
                if j == 0:
                    sx, sy = cx, cy
                current.append([cx, cy])
            last_ctrl = None

        elif C == "L":
            for x, y in zip(nums[0::2], nums[1::2]):
                if is_rel:
                    cx += x; cy += y
                else:
                    cx, cy = x, y
                current.append([cx, cy])
            last_ctrl = None

        elif C == "H":
            for x in nums:
                cx = cx + x if is_rel else x
                current.append([cx, cy])
            last_ctrl = None

        elif C == "V":
            for y in nums:
                cy = cy + y if is_rel else y
                current.append([cx, cy])
            last_ctrl = None

        elif C == "C":
            i = 0
            while i + 5 < len(nums):
                if is_rel:
                    cp1 = [cx + nums[i], cy + nums[i+1]]
                    cp2 = [cx + nums[i+2], cy + nums[i+3]]
                    ep  = [cx + nums[i+4], cy + nums[i+5]]
                else:
                    cp1 = [nums[i], nums[i+1]]
                    cp2 = [nums[i+2], nums[i+3]]
                    ep  = [nums[i+4], nums[i+5]]
                current.extend(_sample_cubic([cx, cy], cp1, cp2, ep))
                last_ctrl = cp2
                cx, cy = ep
                i += 6

        elif C == "S":
            i = 0
            while i + 3 < len(nums):
                if last_ctrl and last_cmd in ("C", "S", "c", "s"):
                    cp1 = [2 * cx - last_ctrl[0], 2 * cy - last_ctrl[1]]
                else:
                    cp1 = [cx, cy]
                if is_rel:
                    cp2 = [cx + nums[i], cy + nums[i+1]]
                    ep  = [cx + nums[i+2], cy + nums[i+3]]
                else:
                    cp2 = [nums[i], nums[i+1]]
                    ep  = [nums[i+2], nums[i+3]]
                current.extend(_sample_cubic([cx, cy], cp1, cp2, ep))
                last_ctrl = cp2
                cx, cy = ep
                i += 4

        elif C == "Q":
            i = 0
            while i + 3 < len(nums):
                if is_rel:
                    cp = [cx + nums[i], cy + nums[i+1]]
                    ep = [cx + nums[i+2], cy + nums[i+3]]
                else:
                    cp = [nums[i], nums[i+1]]
                    ep = [nums[i+2], nums[i+3]]
                current.extend(_sample_quad([cx, cy], cp, ep))
                last_ctrl = cp
                cx, cy = ep
                i += 4

        elif C == "T":
            i = 0
            while i + 1 < len(nums):
                if last_ctrl and last_cmd in ("Q", "T", "q", "t"):
                    cp = [2 * cx - last_ctrl[0], 2 * cy - last_ctrl[1]]
                else:
                    cp = [cx, cy]
                if is_rel:
                    ep = [cx + nums[i], cy + nums[i+1]]
                else:
                    ep = [nums[i], nums[i+1]]
                current.extend(_sample_quad([cx, cy], cp, ep))
                last_ctrl = cp
                cx, cy = ep
                i += 2

        elif C == "A":
            i = 0
            while i + 6 < len(nums):
                if is_rel:
                    ep = [cx + nums[i+5], cy + nums[i+6]]
                else:
                    ep = [nums[i+5], nums[i+6]]
                current.append(ep)
                cx, cy = ep
                i += 7
            last_ctrl = None

        elif C == "Z":
            if current:
                if current[0] != [sx, sy]:
                    current.append([sx, sy])
                contours.append(current)
                current = []
            cx, cy = sx, sy
            last_ctrl = None

        last_cmd = cmd

    if current:
        contours.append(current)

    return contours


# ---------------------------------------------------------------------------
# SVG file parsing
# ---------------------------------------------------------------------------

def parse_svg(svg_path: str):
    """
    Parse SVG, extract polygon contours grouped by fill color.
    Returns (groups, viewbox_w, viewbox_h) where groups is:
    [{color, id, contours: [[(x,y),...], ...]}, ...]
    """
    tree = etree.parse(svg_path)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    vb = root.get("viewBox")
    if vb:
        parts = vb.split()
        vb_w, vb_h = float(parts[2]), float(parts[3])
    else:
        vb_w = float(root.get("width", "100"))
        vb_h = float(root.get("height", "100"))

    color_map = {}
    color_idx = 0

    paths = root.findall(".//svg:path", ns)
    if not paths:
        paths = root.findall(".//path")

    for path_el in paths:
        d = path_el.get("d", "")
        if not d:
            continue
        fill = path_el.get("fill", "#000000")
        style = path_el.get("style", "")
        if "fill:" in style:
            m = re.search(r"fill:\s*([^;]+)", style)
            if m:
                fill = m.group(1).strip()

        if fill.lower() in ("none", "transparent"):
            continue

        contours = parse_svg_path(d)
        if not contours:
            continue

        if fill not in color_map:
            color_idx += 1
            color_map[fill] = {
                "color": fill,
                "id": f"color-{color_idx}",
                "contours": [],
            }
        color_map[fill]["contours"].extend(contours)

    return list(color_map.values()), vb_w, vb_h


# ---------------------------------------------------------------------------
# Triangulation
# ---------------------------------------------------------------------------

def _signed_area(pts):
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return area / 2.0


def classify_contours(contours):
    """
    Separate contours into outer boundaries and holes.
    Returns list of (outer, [holes]) tuples.
    """
    outers = []
    holes = []
    for c in contours:
        if len(c) < 3:
            continue
        if _signed_area(c) >= 0:
            outers.append(c)
        else:
            holes.append(c)

    if not outers and holes:
        outers = [h[::-1] for h in holes]
        holes = []

    if not outers:
        return []

    results = [(o, []) for o in outers]
    for h in holes:
        hx, hy = h[0][0], h[0][1]
        best = 0
        for i, (o, _) in enumerate(results):
            if _point_in_polygon(hx, hy, o):
                best = i
                break
        results[best][1].append(h)

    return results


def _point_in_polygon(x, y, poly):
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def triangulate_polygon(outer, holes=None):
    """Triangulate polygon with holes using mapbox earcut. Returns (verts, tris)."""
    all_pts = list(outer)

    # mapbox-earcut v2 expects cumulative end-indices, not per-ring lengths
    cumulative = [len(outer)]
    if holes:
        for h in holes:
            all_pts.extend(h)
            cumulative.append(cumulative[-1] + len(h))

    coords = np.array(all_pts, dtype=np.float64)
    rings = np.array(cumulative, dtype=np.uint32)

    try:
        indices = earcut.triangulate_float64(coords, rings)
    except Exception:
        indices = earcut.triangulate_float32(
            coords.astype(np.float32), rings.astype(np.uint32)
        )

    if len(indices) == 0:
        return np.array(all_pts), np.empty((0, 3), dtype=np.int32)

    tris = np.array(indices, dtype=np.int32).reshape(-1, 3)
    return coords, tris


# ---------------------------------------------------------------------------
# 3D mesh generation
# ---------------------------------------------------------------------------

def _clean_ring(pts, tol=0.01):
    """
    Remove duplicate closing point and consecutive near-duplicate vertices.
    Prevents degenerate zero-area triangles on side walls.
    """
    if len(pts) < 3:
        return pts
    # Remove closing duplicate (last point ≈ first point)
    while len(pts) > 3 and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < tol:
        pts = pts[:-1]
    # Remove consecutive near-duplicates
    cleaned = [pts[0]]
    for i in range(1, len(pts)):
        dx = pts[i][0] - cleaned[-1][0]
        dy = pts[i][1] - cleaned[-1][1]
        if math.hypot(dx, dy) >= tol:
            cleaned.append(pts[i])
    # Also check if last cleaned point ≈ first
    if len(cleaned) > 3 and math.hypot(cleaned[-1][0] - cleaned[0][0], cleaned[-1][1] - cleaned[0][1]) < tol:
        cleaned = cleaned[:-1]
    return cleaned


def _side_walls_from_ring(ring_pts, z_bottom, z_top):
    """
    Build clean side-wall triangles from an ordered ring of 2D points.
    Deduplicates the ring first, then walks it so every quad has
    consistent outward normals.
    """
    ring_pts = _clean_ring(ring_pts)
    if len(ring_pts) < 3:
        return []
    tris = []
    n = len(ring_pts)
    for i in range(n):
        j = (i + 1) % n
        p0, p1 = ring_pts[i], ring_pts[j]
        ta = [p0[0], p0[1], z_top]
        tb = [p1[0], p1[1], z_top]
        ba = [p0[0], p0[1], z_bottom]
        bb = [p1[0], p1[1], z_bottom]
        tris.append([ta, ba, bb])
        tris.append([ta, bb, tb])
    return tris


def _triangulate_cleaned(outer_scaled, holes_scaled):
    """Clean rings and triangulate. Returns (outer_clean, holes_clean, verts_2d, tris)."""
    outer_clean = _clean_ring(list(outer_scaled))
    if len(outer_clean) < 3:
        return None, None, None, None
    holes_clean = []
    if holes_scaled:
        for h in holes_scaled:
            hc = _clean_ring(list(h))
            if len(hc) >= 3:
                holes_clean.append(hc)

    verts_2d, tris = triangulate_polygon(outer_clean, holes_clean if holes_clean else None)
    if len(tris) == 0:
        return None, None, None, None
    return outer_clean, holes_clean, verts_2d, tris


def extrude_faces_only(outer_scaled, holes_scaled, z_bottom, z_top):
    """
    Generate only top and bottom face triangles for a 2D polygon.
    No side walls — those come from the unified silhouette instead,
    eliminating z-fighting between adjacent color regions.
    """
    outer_clean, holes_clean, verts_2d, tris = _triangulate_cleaned(outer_scaled, holes_scaled)
    if verts_2d is None:
        return []

    all_triangles = []

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        all_triangles.append([
            [verts_2d[a][0], verts_2d[a][1], z_top],
            [verts_2d[b][0], verts_2d[b][1], z_top],
            [verts_2d[c][0], verts_2d[c][1], z_top],
        ])

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        all_triangles.append([
            [verts_2d[a][0], verts_2d[a][1], z_bottom],
            [verts_2d[c][0], verts_2d[c][1], z_bottom],
            [verts_2d[b][0], verts_2d[b][1], z_bottom],
        ])

    return all_triangles


def extrude_watertight_separated(outer_scaled, holes_scaled, z_bottom, z_top):
    """
    Extrude a 2D polygon into a watertight solid, returning top faces
    separately from bottom+walls.  This allows the caller to paint
    the top faces in a colour and everything else in gray.

    Returns (top_tris, other_tris).
    """
    outer_clean, holes_clean, verts_2d, tris = _triangulate_cleaned(outer_scaled, holes_scaled)
    if verts_2d is None:
        return [], []

    top_tris = []
    other_tris = []

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        top_tris.append([
            [verts_2d[a][0], verts_2d[a][1], z_top],
            [verts_2d[b][0], verts_2d[b][1], z_top],
            [verts_2d[c][0], verts_2d[c][1], z_top],
        ])

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        other_tris.append([
            [verts_2d[a][0], verts_2d[a][1], z_bottom],
            [verts_2d[c][0], verts_2d[c][1], z_bottom],
            [verts_2d[b][0], verts_2d[b][1], z_bottom],
        ])

    other_tris.extend(_side_walls_from_ring(outer_clean, z_bottom, z_top))
    if holes_clean:
        for hole in holes_clean:
            other_tris.extend(_side_walls_from_ring(hole[::-1], z_bottom, z_top))

    return top_tris, other_tris


def extrude_polygon_with_walls(outer_scaled, holes_scaled, z_bottom, z_top):
    """
    Extrude a 2D polygon into a full watertight 3D solid (top + bottom + walls).
    Used for the base plate and fallback mode.
    """
    outer_clean, holes_clean, verts_2d, tris = _triangulate_cleaned(outer_scaled, holes_scaled)
    if verts_2d is None:
        return []

    all_triangles = []

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        all_triangles.append([
            [verts_2d[a][0], verts_2d[a][1], z_top],
            [verts_2d[b][0], verts_2d[b][1], z_top],
            [verts_2d[c][0], verts_2d[c][1], z_top],
        ])

    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        all_triangles.append([
            [verts_2d[a][0], verts_2d[a][1], z_bottom],
            [verts_2d[c][0], verts_2d[c][1], z_bottom],
            [verts_2d[b][0], verts_2d[b][1], z_bottom],
        ])

    all_triangles.extend(_side_walls_from_ring(outer_clean, z_bottom, z_top))
    for hole in holes_clean:
        all_triangles.extend(_side_walls_from_ring(hole[::-1], z_bottom, z_top))

    return all_triangles


def _contour_area_np(contour: np.ndarray) -> float:
    """Absolute area via shoelace on numpy contour (row, col)."""
    n = len(contour)
    if n < 3:
        return 0.0
    x = contour[:, 1]
    y = contour[:, 0]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _trace_alpha_contours(png_path, vb_h, scale, dilate_px=0, simplify_tol=2.0, min_area=50.0):
    """
    Trace contour rings from a transparent PNG's alpha channel.
    Optionally dilate the mask before tracing.
    Returns list of cleaned 2D rings in mm coordinates (CCW winding).
    """
    from skimage.morphology import dilation, disk

    img = Image.open(png_path).convert("RGBA")
    alpha = np.array(img)[:, :, 3]
    mask = (alpha > 128).astype(np.uint8)

    if dilate_px > 0:
        mask = dilation(mask, disk(dilate_px)).astype(np.uint8)

    padded = np.pad(mask.astype(np.float64), 1, mode="constant", constant_values=0)
    contours = find_contours(padded, 0.5)
    if not contours:
        return []

    contours.sort(key=lambda c: _contour_area_np(c), reverse=True)

    rings = []
    for contour in contours:
        contour = contour - 1.0
        area = _contour_area_np(contour)
        if area < min_area:
            continue

        simplified = approximate_polygon(contour, tolerance=simplify_tol)
        if len(simplified) < 3:
            continue
        if np.allclose(simplified[0], simplified[-1], atol=0.1):
            simplified = simplified[:-1]
        if len(simplified) < 3:
            continue

        ring_mm = []
        for pt in simplified:
            y_px, x_px = float(pt[0]), float(pt[1])
            ring_mm.append([x_px * scale, (vb_h - y_px) * scale])

        sa = _signed_area(ring_mm)
        if sa < 0:
            ring_mm = ring_mm[::-1]

        ring_mm = _clean_ring(ring_mm)
        if len(ring_mm) < 3:
            continue

        rings.append(ring_mm)
    return rings


def create_silhouette_base_plate(png_path, vb_w, vb_h, scale, thickness, margin_mm=2.0):
    """
    Create a base plate whose top face sits at `thickness` and whose outer
    wall follows a dilated version of the logo silhouette.  The dilation
    produces the small rim around the logo.  Because we use the same
    undilated silhouette for the logo walls (create_silhouette_logo_walls),
    the walls land flush on the plate edge with no visible gap.
    """
    margin_px = max(1, int(round(margin_mm / scale)))
    rings = _trace_alpha_contours(png_path, vb_h, scale, dilate_px=margin_px)
    if not rings:
        return []

    all_triangles = []
    for ring_mm in rings:
        all_triangles.extend(extrude_polygon_with_walls(ring_mm, None, 0.0, thickness))
    return all_triangles


def create_logo_border_ring(png_path, vb_w, vb_h, scale, z_bottom, z_top, margin_mm=2.0):
    """
    Create a gray border ring that surrounds the logo colour regions.

    Shape = dilated silhouette (outer wall) with the undilated silhouette
    punched out as a hole.  This forms a non-overlapping gray perimeter
    around the colour volumes so:
      • Sides of the model are uniformly gray.
      • Colour volumes (watertight solids inside the ring) can be sliced
        as independent filament bodies without any overlap.
    """
    margin_px = max(1, int(round(margin_mm / scale)))
    outer_rings = _trace_alpha_contours(png_path, vb_h, scale, dilate_px=margin_px)
    inner_rings = _trace_alpha_contours(png_path, vb_h, scale, dilate_px=0)
    if not outer_rings or not inner_rings:
        return []

    all_triangles = []
    # Pair outer (dilated) rings with inner (undilated) rings by index.
    # Each pair creates one annular ring segment; the inner contour becomes
    # the hole that exposes the colour volumes underneath.
    for outer, inner in zip(outer_rings, inner_rings):
        all_triangles.extend(
            extrude_polygon_with_walls(outer, [inner], z_bottom, z_top)
        )
    # Any extra outer rings with no inner counterpart become solid pillars
    for outer in outer_rings[len(inner_rings):]:
        all_triangles.extend(extrude_polygon_with_walls(outer, None, z_bottom, z_top))
    return all_triangles


# ---------------------------------------------------------------------------
# Tag SVG with color IDs (for multi-filament / AMS support)
# ---------------------------------------------------------------------------

def tag_svg_colors(svg_path: str, output_path: str):
    """Add distinct id attributes to SVG paths grouped by fill color."""
    tree = etree.parse(svg_path)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    color_idx_map = {}
    idx_counter = 0

    paths = root.findall(".//svg:path", ns)
    if not paths:
        paths = root.findall(".//path")

    for p in paths:
        fill = p.get("fill", "#000000")
        style = p.get("style", "")
        if "fill:" in style:
            m = re.search(r"fill:\s*([^;]+)", style)
            if m:
                fill = m.group(1).strip()

        if fill not in color_idx_map:
            idx_counter += 1
            color_idx_map[fill] = idx_counter
        cid = color_idx_map[fill]
        existing = p.get("id", "")
        p.set("id", f"color-{cid}" + (f"-{existing}" if existing else ""))
        p.set("data-color-group", str(cid))

    tree.write(output_path, xml_declaration=True, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Shared geometry builder (used by both STL and 3MF exporters)
# ---------------------------------------------------------------------------

def build_color_meshes(
    svg_path: str,
    target_size_mm: float = 80.0,
    base_thickness: float = 1.5,
    logo_height: float = 2.5,
    margin: float = 2.0,
    rdp_epsilon: float = 0.3,
    png_path: str = None,
):
    """
    Parse SVG and build per-color triangle lists + a base plate.

    If png_path is provided, the base plate follows the logo's actual
    silhouette (from the alpha channel). Otherwise falls back to a
    bounding-box base plate.

    Returns:
        color_meshes: list of {"color": "#hex", "id": str, "triangles": [[[x,y,z],..]]}
        base_plate:   {"color": "#cccccc", "id": "base-plate", "triangles": [...]}
    """
    groups, vb_w, vb_h = parse_svg(svg_path)
    if not groups:
        raise ValueError("SVG contains no usable paths")

    max_dim = max(vb_w, vb_h)
    scale = target_size_mm / max_dim if max_dim > 0 else 1.0

    z_base_top = base_thickness
    z_logo_top = base_thickness + logo_height

    color_meshes = []
    all_logo_triangles = []

    for group in groups:
        top_tris = []
        gray_tris = []
        classified = classify_contours(group["contours"])
        for outer_raw, holes_raw in classified:
            outer = rdp_simplify(outer_raw, rdp_epsilon)
            if len(outer) < 3:
                continue
            holes = []
            for h in holes_raw:
                hs = rdp_simplify(h, rdp_epsilon)
                if len(hs) >= 3:
                    holes.append(hs)

            outer_scaled = [[p[0] * scale, (vb_h - p[1]) * scale] for p in outer]
            holes_scaled = [
                [[p[0] * scale, (vb_h - p[1]) * scale] for p in h] for h in holes
            ]

            t, g = extrude_watertight_separated(
                outer_scaled, holes_scaled, z_base_top, z_logo_top
            )
            top_tris.extend(t)
            gray_tris.extend(g)

        if top_tris or gray_tris:
            color_meshes.append({
                "color": group["color"],
                "id": group["id"],
                "triangles": top_tris + gray_tris,
                "top_triangles": top_tris,
                "gray_triangles": gray_tris,
            })
            all_logo_triangles.extend(top_tris + gray_tris)

    if not all_logo_triangles:
        raise ValueError("No geometry produced from SVG paths")

    if png_path:
        base_tris = create_silhouette_base_plate(
            png_path, vb_w, vb_h, scale, base_thickness, margin
        )
    else:
        base_tris = _fallback_base_plate(all_logo_triangles, scale, base_thickness, margin)

    base_plate = {
        "color": "#cccccc",
        "id": "base-plate",
        "triangles": base_tris,
    }

    return color_meshes, base_plate


def _fallback_base_plate(all_triangles, scale, thickness, margin):
    """Simple bounding-box base plate when no PNG is available."""
    all_x = []
    all_y = []
    for tri in all_triangles:
        for v in tri:
            all_x.append(v[0])
            all_y.append(v[1])
    if not all_x:
        return []
    x_min, x_max = min(all_x) - margin, max(all_x) + margin
    y_min, y_max = min(all_y) - margin, max(all_y) + margin
    rect = [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]
    return extrude_polygon_with_walls(rect, None, 0.0, thickness)


# ---------------------------------------------------------------------------
# STL export (single combined mesh)
# ---------------------------------------------------------------------------

def svg_to_stl(
    svg_path: str,
    stl_path: str,
    target_size_mm: float = 80.0,
    base_thickness: float = 1.5,
    logo_height: float = 2.5,
    margin: float = 2.0,
    rdp_epsilon: float = 0.3,
    png_path: str = None,
):
    """
    Convert an SVG file into a 3D-printable, watertight STL.

    - Adds a base plate (default 1.5 mm) so floating parts stay attached.
    - Extrudes logo paths by logo_height (default 2.5 mm) above the base.
    - Simplifies paths with Ramer-Douglas-Peucker to avoid printer stutter.
    """
    color_meshes, base_plate = build_color_meshes(
        svg_path, target_size_mm, base_thickness, logo_height, margin, rdp_epsilon,
        png_path=png_path,
    )

    all_triangles = []
    for cm in color_meshes:
        all_triangles.extend(cm["triangles"])
    all_triangles.extend(base_plate["triangles"])

    tri_array = np.array(all_triangles)
    stl_mesh = mesh.Mesh(np.zeros(len(tri_array), dtype=mesh.Mesh.dtype))
    for i, tri in enumerate(tri_array):
        stl_mesh.vectors[i] = tri

    stl_mesh.update_normals()
    stl_mesh.save(stl_path)
    return stl_path
