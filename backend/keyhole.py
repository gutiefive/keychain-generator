"""
Keyhole geometry generators for keychains.

Adds a hole for a key ring to a base shape — either a round hole
cut into the shape, or a tab that extends from the top with a hole.
"""

import math
from typing import List, Tuple, Optional


def _circle_pts(cx: float, cy: float, r: float, segments: int = 32) -> List[List[float]]:
    """Generate a circle contour (CW winding — suitable as a hole)."""
    return [
        [cx + r * math.cos(2 * math.pi * i / segments),
         cy + r * math.sin(2 * math.pi * i / segments)]
        for i in range(segments - 1, -1, -1)
    ]


def round_hole(
    shape_contour: List[List[float]],
    diameter: float = 4.0,
    offset_from_top: float = 3.0,
) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Add a round keyhole near the top of the shape.

    Returns (shape_contour_unchanged, hole_contour).
    The hole is positioned at the horizontal center, offset down from the
    topmost point of the shape.
    """
    max_y = max(p[1] for p in shape_contour)
    xs_at_top = [p[0] for p in shape_contour if p[1] > max_y - 1.0]
    cx = (min(xs_at_top) + max(xs_at_top)) / 2
    cy = max_y - offset_from_top

    r = diameter / 2
    hole = _circle_pts(cx, cy, r)
    return shape_contour, hole


def tab_loop(
    shape_contour: List[List[float]],
    tab_width: float = 8.0,
    tab_height: float = 6.0,
    hole_diameter: float = 4.0,
    segments: int = 16,
) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Extend a tab from the top of the shape with a hole in it.

    Returns (modified_outer_contour, hole_contour).
    The tab is a rounded rectangle that merges with the top edge.
    """
    max_y = max(p[1] for p in shape_contour)
    xs_at_top = [p[0] for p in shape_contour if p[1] > max_y - 0.5]
    cx = (min(xs_at_top) + max(xs_at_top)) / 2

    # Tab is a rounded rectangle extending upward
    tw, th = tab_width / 2, tab_height
    tab_r = min(tw, th / 2)
    tab_top = max_y + th

    tab_pts = []
    # Left side straight up from shape top
    tab_pts.append([cx - tw, max_y])
    tab_pts.append([cx - tw, tab_top - tab_r])

    # Top-left corner arc
    for i in range(segments // 2 + 1):
        a = math.pi / 2 + (math.pi / 2) * i / (segments // 2)
        tab_pts.append([
            cx - tw + tab_r + tab_r * math.cos(a),
            tab_top - tab_r + tab_r * math.sin(a),
        ])

    # Top-right corner arc
    for i in range(segments // 2 + 1):
        a = 0 + (math.pi / 2) * i / (segments // 2)
        tab_pts.append([
            cx + tw - tab_r + tab_r * math.cos(a),
            tab_top - tab_r + tab_r * math.sin(a),
        ])

    # Right side straight down
    tab_pts.append([cx + tw, tab_top - tab_r])
    tab_pts.append([cx + tw, max_y])

    # Merge the tab into the shape contour: find the two points closest
    # to the tab attachment edges and splice the tab in.
    merged = list(shape_contour)

    # Find insertion point — the vertex closest to (cx - tw, max_y)
    best_left = 0
    best_right = 0
    best_ld = float("inf")
    best_rd = float("inf")

    for i, p in enumerate(merged):
        dl = math.hypot(p[0] - (cx - tw), p[1] - max_y)
        dr = math.hypot(p[0] - (cx + tw), p[1] - max_y)
        if dl < best_ld:
            best_ld = dl
            best_left = i
        if dr < best_rd:
            best_rd = dr
            best_right = i

    # Ensure left index < right index for slicing
    if best_left > best_right:
        best_left, best_right = best_right, best_left
        tab_pts = tab_pts[::-1]

    # Replace the top edge segment with the tab contour
    new_contour = merged[:best_left + 1] + tab_pts + merged[best_right:]

    # Hole in the center of the tab
    hole_cy = max_y + th / 2
    hole = _circle_pts(cx, hole_cy, hole_diameter / 2)

    return new_contour, hole


KEYHOLE_REGISTRY = {
    "round_hole": round_hole,
    "tab_loop": tab_loop,
    "none": None,
}
