"""
Bitmap-to-SVG vectorization using scikit-image contour tracing.

Replaces vtracer (which segfaults on Python 3.14 / Windows) with a
robust pure-Python pipeline: alpha cleanup → color quantization →
per-color masking → marching-squares contour detection → SVG output.
"""

import numpy as np
from PIL import Image
from skimage.measure import find_contours, approximate_polygon
from lxml import etree


def _clean_alpha(img_rgba: np.ndarray, threshold: int = 128) -> np.ndarray:
    """
    Hard-threshold the alpha channel so the quantizer never sees
    semi-transparent edge artifacts left by background removal.
    Pixels below threshold become fully transparent (zeroed RGB too).
    """
    out = img_rgba.copy()
    transparent = out[:, :, 3] < threshold
    out[transparent] = [0, 0, 0, 0]
    out[~transparent, 3] = 255
    return out


def _quantize_colors(img_rgba: np.ndarray, max_colors: int = 12) -> np.ndarray:
    """
    Histogram-peak colour quantisation — fully deterministic and robust.

    Instead of K-means (which is sensitive to random initialisation) or
    Pillow's median-cut (which drowns dark regions when transparent pixels
    collapse to black), this method:
      1. Bins RGB space into 32-unit cells to find dominant colour peaks.
      2. Takes the top-N peaks by pixel count as palette candidates.
      3. Merges any palette entries within distance 40 of each other.
      4. Snaps near-black (<25 brightness) to #000000 and
         near-white (>235 brightness) to #ffffff.
      5. Maps every opaque pixel to its nearest palette entry.
    """
    opaque_mask = img_rgba[:, :, 3] == 255
    if not np.any(opaque_mask):
        return img_rgba.copy()

    opaque_rgb = img_rgba[opaque_mask][:, :3].astype(np.int32)

    # ── Step 1: coarse histogram (32-unit bins) ──────────────────────────
    BIN = 32
    br = (opaque_rgb[:, 0] // BIN).astype(np.int32)
    bg = (opaque_rgb[:, 1] // BIN).astype(np.int32)
    bb = (opaque_rgb[:, 2] // BIN).astype(np.int32)
    bin_keys = br * 256 + bg * 16 + bb        # 8³ = 512 possible bins

    unique_bins, bin_counts = np.unique(bin_keys, return_counts=True)

    # Keep enough candidates to allow for merging
    n_cand = min(max_colors * 4, len(unique_bins))
    top_idx = np.argsort(-bin_counts)[:n_cand]
    top_keys = unique_bins[top_idx]

    # ── Step 2: compute the mean colour within each top bin ──────────────
    raw_centroids = []
    for bk in top_keys:
        bR = (bk // 256) * BIN
        bG = ((bk % 256) // 16) * BIN
        bB = (bk % 16) * BIN
        in_bin = (
            (opaque_rgb[:, 0] >= bR) & (opaque_rgb[:, 0] < bR + BIN) &
            (opaque_rgb[:, 1] >= bG) & (opaque_rgb[:, 1] < bG + BIN) &
            (opaque_rgb[:, 2] >= bB) & (opaque_rgb[:, 2] < bB + BIN)
        )
        raw_centroids.append(opaque_rgb[in_bin].mean(axis=0))

    # ── Step 3: snap near-black / near-white ────────────────────────────
    snapped = []
    for c in raw_centroids:
        brightness = float(c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114)
        if brightness < 25:
            snapped.append(np.array([0.0, 0.0, 0.0]))
        elif brightness > 235:
            snapped.append(np.array([255.0, 255.0, 255.0]))
        else:
            snapped.append(c.astype(float))

    # ── Step 4: greedy merge of near-duplicate centroids ────────────────
    MERGE_DIST = 40.0
    merged = []
    for c in snapped:
        close = False
        for m in merged:
            if float(np.linalg.norm(c - m)) < MERGE_DIST:
                close = True
                break
        if not close:
            merged.append(c)
        if len(merged) >= max_colors:
            break

    palette = np.array(merged, dtype=np.float32)

    # ── Step 5: map every opaque pixel to nearest palette entry ─────────
    # Use int32 (NOT int16) — channel differences up to 255 square to 65025
    # which overflows int16 (max 32767), corrupting distance comparisons.
    pal_i32 = palette.astype(np.int32)
    h, w = img_rgba.shape[:2]
    out = img_rgba.copy()
    rgb_flat = out[:, :, :3].reshape(-1, 3)
    alpha_flat = out[:, :, 3].reshape(-1)
    opaque_idx = np.where(alpha_flat == 255)[0]

    chunk = 80_000
    for start in range(0, len(opaque_idx), chunk):
        end = min(start + chunk, len(opaque_idx))
        batch_idx = opaque_idx[start:end]
        batch = rgb_flat[batch_idx].astype(np.int32)
        dists = np.sum((batch[:, None, :] - pal_i32[None, :, :]) ** 2, axis=2)
        nearest = np.argmin(dists, axis=1)
        rgb_flat[batch_idx] = np.clip(palette[nearest], 0, 255).astype(np.uint8)

    out[:, :, :3] = rgb_flat.reshape(h, w, 3)
    return out


def _find_unique_colors(img_rgba: np.ndarray):
    """Return list of unique (R,G,B) tuples from fully opaque pixels."""
    mask = img_rgba[:, :, 3] == 255
    pixels = img_rgba[mask][:, :3]
    if len(pixels) == 0:
        return []
    unique = np.unique(pixels, axis=0)
    return [tuple(c) for c in unique]


def _contour_area(contour: np.ndarray) -> float:
    """Signed area via the shoelace formula (positive = CCW)."""
    n = len(contour)
    if n < 3:
        return 0.0
    x = contour[:, 1]
    y = contour[:, 0]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _contour_to_path_d(contour: np.ndarray) -> str:
    if len(contour) < 3:
        return ""
    # Strip closing duplicate: find_contours returns closed loops where
    # last point ≈ first point; the SVG Z command already closes the path.
    if np.allclose(contour[0], contour[-1], atol=0.05):
        contour = contour[:-1]
    if len(contour) < 3:
        return ""
    parts = [f"M {contour[0, 1]:.2f} {contour[0, 0]:.2f}"]
    for i in range(1, len(contour)):
        parts.append(f"L {contour[i, 1]:.2f} {contour[i, 0]:.2f}")
    parts.append("Z")
    return " ".join(parts)


def _rgb_hex(color: tuple) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def trace_image_to_svg(
    input_path: str,
    output_path: str,
    max_colors: int = 32,
    alpha_threshold: int = 128,
    contour_level: float = 0.5,
    simplify_tolerance: float = 1.5,
):
    """
    Trace a transparent PNG into an SVG file.

    1. Hard-threshold alpha to kill edge artifacts.
    2. Quantize colors (histogram-peak).
    3. For each unique opaque color, build a binary mask.
    4. Dilate each mask by 1 px (clipped to opaque area) to seal hairline
       gaps between adjacent colour regions — prevents the base-plate colour
       from showing through cracks in the 3D extrusion.
    5. Run marching-squares contour detection on each dilated mask.
    6. Skip contours that cover >70% of the image (background ghosts).
    7. Emit SVG <path> elements with the correct fill color.
    """
    from skimage.morphology import dilation, disk as sk_disk

    img = Image.open(input_path).convert("RGBA")
    img_arr = np.array(img)
    h, w = img_arr.shape[:2]
    image_area = float(h * w)

    # Kill semi-transparent artifacts then quantize with histogram-peak
    cleaned = _clean_alpha(img_arr, alpha_threshold)
    merged = _quantize_colors(cleaned, max_colors)
    colors = _find_unique_colors(merged)
    if not colors:
        raise ValueError("Image has no opaque pixels to trace")

    # Global opaque mask — colour dilation must not bleed into transparent bg
    opaque_mask = (merged[:, :, 3] == 255)

    # Sort colours by pixel count DESCENDING so the thinnest/rarest regions
    # (e.g. the white outline) are processed LAST and their paths/triangles are
    # added on top.  This ensures their 1-px dilated edge overwrites any bleed
    # from the larger neighbouring colour (e.g. blue bleeding into white).
    def _px_count(c):
        r, g, b = c
        return int(np.sum(
            (merged[:, :, 0] == r) & (merged[:, :, 1] == g) &
            (merged[:, :, 2] == b) & (merged[:, :, 3] == 255)
        ))
    colors = sorted(colors, key=_px_count, reverse=True)

    svg = etree.Element("svg")
    svg.set("xmlns", "http://www.w3.org/2000/svg")
    svg.set("viewBox", f"0 0 {w} {h}")
    svg.set("width", str(w))
    svg.set("height", str(h))

    color_idx = 0
    min_area = max(100.0, image_area * 0.0002)  # filter small artifacts
    max_area_ratio = 0.70  # ignore contours covering >70% of image

    for color in colors:
        r, g, b = color
        raw_mask = (
            (merged[:, :, 0] == r)
            & (merged[:, :, 1] == g)
            & (merged[:, :, 2] == b)
            & (merged[:, :, 3] == 255)
        )

        # Dilate by 1 px within the opaque region to seal inter-colour gaps.
        # Adjacent colours overlap by ≤1 px so no visible colour bleed occurs.
        dilated = dilation(raw_mask.astype(np.uint8), sk_disk(1))
        mask = (dilated.astype(bool) & opaque_mask).astype(np.float64)

        # Pad mask so contours that touch edges close properly
        padded = np.pad(mask, 1, mode="constant", constant_values=0)
        contours = find_contours(padded, contour_level)

        if not contours:
            continue

        color_idx += 1
        hex_color = _rgb_hex(color)
        added = False

        for contour in contours:
            # Undo padding offset
            contour = contour - 1.0

            area = _contour_area(contour)
            if area < min_area:
                continue
            if area / image_area > max_area_ratio:
                continue

            simplified = approximate_polygon(contour, tolerance=simplify_tolerance)
            if len(simplified) < 3:
                continue

            d = _contour_to_path_d(simplified)
            if not d:
                continue

            path_el = etree.SubElement(svg, "path")
            path_el.set("d", d)
            path_el.set("fill", hex_color)
            path_el.set("id", f"color-{color_idx}")
            path_el.set("data-color-group", str(color_idx))
            added = True

        if not added:
            color_idx -= 1

    tree = etree.ElementTree(svg)
    tree.write(output_path, xml_declaration=True, encoding="utf-8")
    return output_path
