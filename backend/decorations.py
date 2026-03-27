"""
Pre-built decoration shapes for keychains.

Each function returns a list of contour rings (list of [x, y] points in mm,
centred on the origin).  The first ring is the outer boundary; subsequent
rings are holes / inner detail.

A decoration can contain multiple "layers" — each layer is a dict with:
  - "contours": list of contour rings
  - "color":    hex colour string
"""

import math
from typing import List, Dict, Any


def _circle(cx: float, cy: float, r: float, n: int = 64) -> List[List[float]]:
    """Generate a circle contour centred at (cx, cy) with radius r."""
    return [
        [cx + r * math.cos(2 * math.pi * i / n),
         cy + r * math.sin(2 * math.pi * i / n)]
        for i in range(n)
    ]


def _arc_points(cx, cy, r, start_deg, end_deg, n=32):
    pts = []
    start = math.radians(start_deg)
    end = math.radians(end_deg)
    for i in range(n + 1):
        t = start + (end - start) * i / n
        pts.append([cx + r * math.cos(t), cy + r * math.sin(t)])
    return pts


# ── Baseball / Softball ──────────────────────────────────────────────────

def baseball(diameter_mm: float = 20.0) -> List[Dict[str, Any]]:
    r = diameter_mm / 2
    layers = []

    # Main ball (white/yellow circle)
    layers.append({
        "contours": [_circle(0, 0, r)],
        "color": "#FFFFFF",
        "id": "ball-body",
    })

    # Stitching arcs (red)
    stitch_pts = []
    for sign in [1, -1]:
        arc = []
        for i in range(40):
            t = -0.75 * math.pi + 1.5 * math.pi * i / 39
            x = sign * r * 0.55 * math.cos(t)
            y = r * 0.85 * math.sin(t)
            arc.append([x, y])
        stitch_pts.append(arc)

    for arc in stitch_pts:
        thick = r * 0.06
        for pt in arc:
            layers.append({
                "contours": [_circle(pt[0], pt[1], thick, n=8)],
                "color": "#CC0000",
                "id": "stitch",
            })

    return layers


def softball(diameter_mm: float = 20.0) -> List[Dict[str, Any]]:
    """Same as baseball but with yellow body."""
    layers = baseball(diameter_mm)
    layers[0]["color"] = "#FFD700"
    layers[0]["id"] = "softball-body"
    return layers


# ── Basketball ────────────────────────────────────────────────────────────

def basketball(diameter_mm: float = 20.0) -> List[Dict[str, Any]]:
    r = diameter_mm / 2
    layers = []

    layers.append({
        "contours": [_circle(0, 0, r)],
        "color": "#E87722",
        "id": "ball-body",
    })

    line_thick = r * 0.05
    lines = []

    # Horizontal line
    for i in range(30):
        x = -r * 0.9 + r * 1.8 * i / 29
        lines.append([x, 0])

    # Vertical line
    for i in range(30):
        y = -r * 0.9 + r * 1.8 * i / 29
        lines.append([0, y])

    # Left arc
    for i in range(30):
        t = -0.4 * math.pi + 0.8 * math.pi * i / 29
        lines.append([-r * 0.35 + r * 0.25 * math.cos(t), r * 0.85 * math.sin(t)])

    # Right arc
    for i in range(30):
        t = -0.4 * math.pi + 0.8 * math.pi * i / 29
        lines.append([r * 0.35 - r * 0.25 * math.cos(t), r * 0.85 * math.sin(t)])

    for pt in lines:
        layers.append({
            "contours": [_circle(pt[0], pt[1], line_thick, n=6)],
            "color": "#1A1A1A",
            "id": "line",
        })

    return layers


# ── Football (American) ──────────────────────────────────────────────────

def football(diameter_mm: float = 20.0) -> List[Dict[str, Any]]:
    r = diameter_mm / 2
    layers = []

    # Oval body
    n = 64
    oval = []
    for i in range(n):
        t = 2 * math.pi * i / n
        oval.append([r * math.cos(t), r * 0.55 * math.sin(t)])
    layers.append({
        "contours": [oval],
        "color": "#6B3A1F",
        "id": "ball-body",
    })

    # Laces
    lace_w = r * 0.5
    lace_thick = r * 0.04
    lace_y = 0
    for i in range(5):
        x = -lace_w / 2 + lace_w * i / 4
        layers.append({
            "contours": [_circle(x, lace_y, lace_thick * 2, n=4)],
            "color": "#FFFFFF",
            "id": "lace",
        })

    # Center seam line
    for i in range(20):
        x = -lace_w * 0.6 + lace_w * 1.2 * i / 19
        layers.append({
            "contours": [_circle(x, 0, lace_thick, n=4)],
            "color": "#FFFFFF",
            "id": "seam",
        })

    return layers


# ── Soccer ball ──────────────────────────────────────────────────────────

def soccer(diameter_mm: float = 20.0) -> List[Dict[str, Any]]:
    r = diameter_mm / 2
    layers = []

    layers.append({
        "contours": [_circle(0, 0, r)],
        "color": "#FFFFFF",
        "id": "ball-body",
    })

    # Pentagon patches at centre and around
    patch_r = r * 0.22
    positions = [(0, 0)]
    for i in range(5):
        angle = 2 * math.pi * i / 5 - math.pi / 2
        positions.append((r * 0.52 * math.cos(angle), r * 0.52 * math.sin(angle)))

    for px, py in positions:
        pentagon = []
        for i in range(5):
            a = 2 * math.pi * i / 5 - math.pi / 2
            pentagon.append([px + patch_r * math.cos(a), py + patch_r * math.sin(a)])
        layers.append({
            "contours": [pentagon],
            "color": "#1A1A1A",
            "id": "patch",
        })

    return layers


# ── Simple shapes ────────────────────────────────────────────────────────

def star(size_mm: float = 20.0) -> List[Dict[str, Any]]:
    r_outer = size_mm / 2
    r_inner = r_outer * 0.38
    pts = []
    for i in range(10):
        angle = math.pi / 2 + 2 * math.pi * i / 10
        r = r_outer if i % 2 == 0 else r_inner
        pts.append([r * math.cos(angle), r * math.sin(angle)])
    return [{"contours": [pts], "color": "#FFD700", "id": "star"}]


def heart(size_mm: float = 20.0) -> List[Dict[str, Any]]:
    r = size_mm / 2
    pts = []
    n = 64
    for i in range(n):
        t = 2 * math.pi * i / n
        x = r * 0.9 * (16 * math.sin(t) ** 3) / 16
        y = r * 0.85 * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)) / 16
        pts.append([x, y])
    return [{"contours": [pts], "color": "#E53E3E", "id": "heart"}]


def paw(size_mm: float = 20.0) -> List[Dict[str, Any]]:
    """Simple paw print."""
    r = size_mm / 2
    layers = []
    # Main pad (oval)
    n = 48
    pad = []
    for i in range(n):
        t = 2 * math.pi * i / n
        pad.append([r * 0.5 * math.cos(t), -r * 0.15 + r * 0.4 * math.sin(t)])
    layers.append({"contours": [pad], "color": "#1A1A1A", "id": "main-pad"})

    # Toe pads
    toe_positions = [(-r*0.38, r*0.35), (-r*0.13, r*0.55),
                     (r*0.13, r*0.55), (r*0.38, r*0.35)]
    toe_r = r * 0.16
    for i, (tx, ty) in enumerate(toe_positions):
        layers.append({
            "contours": [_circle(tx, ty, toe_r, n=24)],
            "color": "#1A1A1A",
            "id": f"toe-{i}",
        })

    return layers


def music_note(size_mm: float = 20.0) -> List[Dict[str, Any]]:
    """Simple music note shape."""
    r = size_mm / 2
    layers = []
    # Note head (oval)
    n = 32
    head = []
    for i in range(n):
        t = 2 * math.pi * i / n
        head.append([r * 0.3 * math.cos(t) - r * 0.1,
                     -r * 0.5 + r * 0.2 * math.sin(t)])
    layers.append({"contours": [head], "color": "#1A1A1A", "id": "note-head"})

    # Stem (thin rectangle)
    sw = r * 0.08
    stem = [
        [r * 0.1, -r * 0.35],
        [r * 0.1 + sw, -r * 0.35],
        [r * 0.1 + sw, r * 0.6],
        [r * 0.1, r * 0.6],
    ]
    layers.append({"contours": [stem], "color": "#1A1A1A", "id": "stem"})

    # Flag
    flag = []
    for i in range(20):
        t = i / 19
        x = r * 0.1 + sw + r * 0.3 * t
        y = r * 0.6 - r * 0.5 * t
        flag.append([x, y])
    for i in range(20):
        t = 1 - i / 19
        x = r * 0.1 + sw + r * 0.3 * t
        y = r * 0.6 - r * 0.5 * t - r * 0.1
        flag.append([x, y])
    layers.append({"contours": [flag], "color": "#1A1A1A", "id": "flag"})

    return layers


# ── Registry ─────────────────────────────────────────────────────────────

DECORATION_REGISTRY = {
    "none":       None,
    "baseball":   baseball,
    "softball":   softball,
    "basketball": basketball,
    "football":   football,
    "soccer":     soccer,
    "star":       star,
    "heart":      heart,
    "paw":        paw,
    "music_note": music_note,
}

DECORATION_LABELS = {
    "none":       "None",
    "baseball":   "Baseball",
    "softball":   "Softball",
    "basketball": "Basketball",
    "football":   "Football",
    "soccer":     "Soccer Ball",
    "star":       "Star",
    "heart":      "Heart",
    "paw":        "Paw Print",
    "music_note": "Music Note",
}
