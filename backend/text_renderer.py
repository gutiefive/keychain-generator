"""
Text-to-contour renderer.

Renders a string at a given font+size into a high-contrast bitmap,
then traces the bitmap into 2D polygon contours (lists of [x, y] points
in millimetres, centred on the origin) suitable for extrusion.
"""

import os
import math
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import find_contours
from skimage.morphology import dilation, footprint_rectangle

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DPI = 300  # render resolution — higher = smoother contours


def _load_font(font_file: str, size_px: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, font_file)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(path, size_px)


def render_text_contours(
    text: str,
    font_file: str,
    max_width_mm: float,
    max_height_mm: float,
    rdp_epsilon: float = 0.3,
) -> List[List[List[float]]]:
    """
    Returns a list of closed contours (each a list of [x, y] in mm,
    centered on the origin) representing the text outline.
    """
    if not text.strip():
        return []

    # Render at a generous size, then scale to fit
    initial_size = 120
    font = _load_font(font_file, initial_size)

    # Measure text bounding box
    dummy = Image.new("L", (1, 1), 0)
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    if tw <= 0 or th <= 0:
        return []

    # Scale font so the rendered text fits within max dimensions
    mm_per_px = max_width_mm / tw
    mm_per_px_h = max_height_mm / th
    mm_per_px = min(mm_per_px, mm_per_px_h)

    target_size = max(16, int(initial_size * (mm_per_px * tw / max_width_mm)
                                if max_width_mm > 0 else initial_size))
    # Re-approach: we want the final bitmap at a resolution that gives us
    # at least ~DPI pixels per mm.
    px_per_mm = DPI / 25.4
    render_w = int(math.ceil(max_width_mm * px_per_mm))
    render_h = int(math.ceil(max_height_mm * px_per_mm))
    if render_w < 10 or render_h < 10:
        return []

    # Find the largest font size that fits in the render buffer
    lo, hi = 8, 400
    best_size = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        f = _load_font(font_file, mid)
        bb = draw.textbbox((0, 0), text, font=f)
        if (bb[2] - bb[0]) <= render_w and (bb[3] - bb[1]) <= render_h:
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    font = _load_font(font_file, best_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad = 4
    img_w = tw + pad * 2
    img_h = th + pad * 2

    img = Image.new("L", (img_w, img_h), 0)
    d = ImageDraw.Draw(img)
    d.text((pad - bbox[0], pad - bbox[1]), text, fill=255, font=font)

    arr = np.array(img)

    # Slight dilation to close tiny gaps in thin strokes
    arr = dilation(arr, footprint_rectangle((3, 3)))
    binary = (arr > 128).astype(np.uint8)

    contours_raw = find_contours(binary, 0.5)
    if not contours_raw:
        return []

    # Convert pixel contours to mm, centred on origin
    # find_contours returns (row, col) so swap to (x, y)
    scale_x = max_width_mm / img_w
    scale_y = max_height_mm / img_h
    # Use uniform scale to prevent distortion
    sc = min(scale_x, scale_y)
    cx = img_w / 2
    cy = img_h / 2

    result = []
    for c in contours_raw:
        if len(c) < 4:
            continue
        pts = [[(row[1] - cx) * sc, -(row[0] - cy) * sc] for row in c]
        # RDP simplify
        pts = _rdp(pts, rdp_epsilon * 0.5)
        if len(pts) >= 3:
            result.append(pts)

    return result


def _rdp(points, epsilon):
    """Ramer-Douglas-Peucker simplification."""
    if len(points) <= 2:
        return points

    dmax = 0.0
    idx = 0
    end = len(points) - 1
    for i in range(1, end):
        d = _point_line_dist(points[i], points[0], points[end])
        if d > dmax:
            dmax = d
            idx = i

    if dmax > epsilon:
        left = _rdp(points[:idx + 1], epsilon)
        right = _rdp(points[idx:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[end]]


def _point_line_dist(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    proj_x = a[0] + t * dx
    proj_y = a[1] + t * dy
    return math.hypot(p[0] - proj_x, p[1] - proj_y)
