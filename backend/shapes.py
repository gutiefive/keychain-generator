"""
2D contour generators for keychain base shapes.

Each function returns a list of [x, y] points forming a closed polygon
(CCW winding, coordinates in mm, centered at the origin).
"""

import math
from typing import List


def rectangle(w: float, h: float, corner_radius: float = 2.0) -> List[List[float]]:
    """Rounded-corner rectangle centered at origin."""
    r = min(corner_radius, w / 2, h / 2)
    if r < 0.1:
        hw, hh = w / 2, h / 2
        return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]]

    hw, hh = w / 2, h / 2
    pts = []
    segs = 8

    corners = [
        (hw - r, hh - r, 0),
        (-hw + r, hh - r, math.pi / 2),
        (-hw + r, -hh + r, math.pi),
        (hw - r, -hh + r, 3 * math.pi / 2),
    ]
    for cx, cy, start_angle in corners:
        for i in range(segs + 1):
            a = start_angle + (math.pi / 2) * i / segs
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a)])

    return pts


def circle(diameter: float, segments: int = 64) -> List[List[float]]:
    """Circle centered at origin."""
    r = diameter / 2
    return [
        [r * math.cos(2 * math.pi * i / segments),
         r * math.sin(2 * math.pi * i / segments)]
        for i in range(segments)
    ]


def oval(w: float, h: float, segments: int = 64) -> List[List[float]]:
    """Ellipse centered at origin."""
    rx, ry = w / 2, h / 2
    return [
        [rx * math.cos(2 * math.pi * i / segments),
         ry * math.sin(2 * math.pi * i / segments)]
        for i in range(segments)
    ]


def dog_tag(w: float, h: float, segments: int = 16) -> List[List[float]]:
    """Rectangle with semicircular short ends (like a classic dog tag)."""
    r = h / 2
    straight = w - h
    if straight < 0:
        return circle(h, segments * 4)

    half_s = straight / 2
    pts = []

    # Right semicircle
    for i in range(segments + 1):
        a = -math.pi / 2 + math.pi * i / segments
        pts.append([half_s + r * math.cos(a), r * math.sin(a)])

    # Left semicircle
    for i in range(segments + 1):
        a = math.pi / 2 + math.pi * i / segments
        pts.append([-half_s + r * math.cos(a), r * math.sin(a)])

    return pts


def shield(w: float, h: float, segments: int = 16) -> List[List[float]]:
    """Shield / badge shape: flat top with curved sides tapering to a point."""
    hw, hh = w / 2, h / 2
    pts = []

    # Flat top edge (left to right)
    pts.append([-hw, hh])
    pts.append([hw, hh])

    # Right curved side down to bottom point
    for i in range(1, segments + 1):
        t = i / segments
        x = hw * (1 - t ** 0.6)
        y = hh - t * 2 * hh
        pts.append([x, y])

    # Left curved side back up (skip bottom point, already added)
    for i in range(1, segments):
        t = 1 - i / segments
        x = -hw * (1 - t ** 0.6)
        y = hh - t * 2 * hh
        pts.append([x, y])

    return pts


SHAPE_REGISTRY = {
    "rectangle": rectangle,
    "circle": circle,
    "oval": oval,
    "dog_tag": dog_tag,
    "shield": shield,
}


def get_shape(name: str, w: float, h: float) -> List[List[float]]:
    """Look up a shape by name and generate its contour at the given size."""
    fn = SHAPE_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown shape: {name}")

    if name == "circle":
        return fn(min(w, h))
    return fn(w, h)
