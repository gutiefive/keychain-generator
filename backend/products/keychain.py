"""
Keychain product — generates 3D keychain geometry from a logo.

Supports three styles:
  - Raised:     Logo extruded on top of a flat base shape
  - Embedded:   Logo recessed into a full-height base shape
  - Silhouette: Logo's own outline IS the keychain shape

Optionally adds up to two lines of custom text with font selection.
"""

from typing import Any, Dict, List, Optional, Tuple

from products.base import BaseProduct
from shapes import get_shape, SHAPE_REGISTRY
from keyhole import round_hole, tab_loop
from decorations import DECORATION_REGISTRY, DECORATION_LABELS as _DECORATION_LABELS
from svg_to_stl import (
    parse_svg,
    classify_contours,
    rdp_simplify,
    extrude_polygon_with_walls,
    extrude_watertight_separated,
    create_silhouette_base_plate,
    _trace_alpha_contours,
    _trace_combined_silhouette_base,
    _fallback_base_plate,
    _signed_area,
)

SIZE_PRESETS = {
    "small":  (55.0, 35.0),
    "medium": (85.0, 55.0),
    "large":  (100.0, 65.0),
}

PADDING = 2.0  # mm inset from edge
LOGO_FILL = 0.80  # logo fills 80% of its zone when solo

BASE_COLORS = {
    "black":  "#1a1a1a",
    "white":  "#f0f0f0",
    "gray":   "#cccccc",
    "red":    "#cc0000",
    "blue":   "#003399",
    "green":  "#006633",
}

TEXT_COLORS = {
    "match_logo": None,
    "white":  "#ffffff",
    "black":  "#000000",
}

FONT_MAP = {
    "inter":        "Inter-Bold.ttf",
    "roboto_slab":  "RobotoSlab-Bold.ttf",
    "jetbrains":    "JetBrainsMono-Bold.ttf",
    "bebas":        "BebasNeue-Regular.ttf",
    "pacifico":     "Pacifico-Regular.ttf",
}

_FONT_OPTIONS = [
    {"value": "inter", "label": "Inter (Sans)"},
    {"value": "roboto_slab", "label": "Roboto Slab (Serif)"},
    {"value": "jetbrains", "label": "JetBrains Mono"},
    {"value": "bebas", "label": "Bebas Neue (Display)"},
    {"value": "pacifico", "label": "Pacifico (Script)"},
]


class KeychainProduct(BaseProduct):
    name = "keychain"
    display_name = "Keychain"

    # ------------------------------------------------------------------
    # Config schema
    # ------------------------------------------------------------------

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return {
            "fields": [
                {
                    "key": "style",
                    "label": "Logo Style",
                    "type": "select",
                    "options": [
                        {"value": "raised", "label": "Raised (logo on top)"},
                        {"value": "embedded", "label": "Embedded (engraved)"},
                        {"value": "silhouette", "label": "Silhouette (logo shape)"},
                    ],
                    "default": "raised",
                },
                {
                    "key": "shape",
                    "label": "Base Shape",
                    "type": "select",
                    "options": [
                        {"value": k, "label": k.replace("_", " ").title()}
                        for k in SHAPE_REGISTRY.keys()
                    ],
                    "default": "rectangle",
                    "hide_if": {"field": "style", "value": "silhouette"},
                },
                {
                    "key": "size",
                    "label": "Size",
                    "type": "select",
                    "options": [
                        {"value": "small", "label": "Small (keychain)"},
                        {"value": "medium", "label": "Medium (bag tag)"},
                        {"value": "large", "label": "Large (luggage tag)"},
                    ],
                    "default": "medium",
                },
                {
                    "key": "logo_position",
                    "label": "Logo Position",
                    "type": "select",
                    "options": [
                        {"value": "center", "label": "Center"},
                        {"value": "top", "label": "Top"},
                        {"value": "bottom", "label": "Bottom"},
                        {"value": "left", "label": "Left"},
                        {"value": "right", "label": "Right"},
                        {"value": "top_left", "label": "Top Left"},
                        {"value": "top_right", "label": "Top Right"},
                        {"value": "bottom_left", "label": "Bottom Left"},
                        {"value": "bottom_right", "label": "Bottom Right"},
                    ],
                    "default": "center",
                    "hide_if": {"field": "style", "value": "silhouette"},
                },
                {
                    "key": "keyhole",
                    "label": "Key Ring Hole",
                    "type": "select",
                    "options": [
                        {"value": "round_hole", "label": "Round Hole"},
                        {"value": "tab_loop", "label": "Tab Loop"},
                        {"value": "none", "label": "No Hole"},
                    ],
                    "default": "round_hole",
                },
                {
                    "key": "base_color",
                    "label": "Base Color",
                    "type": "color_select",
                    "options": [
                        {"value": k, "label": k.title(), "hex": v}
                        for k, v in BASE_COLORS.items()
                    ],
                    "default": "black",
                },
                {
                    "key": "text",
                    "label": "Custom Text",
                    "type": "text",
                    "default": "",
                    "placeholder": "e.g. your name, team, etc.",
                },
                {
                    "key": "font",
                    "label": "Font",
                    "type": "select",
                    "options": list(_FONT_OPTIONS),
                    "default": "bebas",
                    "show_if": {"field": "text", "not_empty": True},
                },
                {
                    "key": "text_position",
                    "label": "Text Position",
                    "type": "select",
                    "options": [
                        {"value": "below_logo", "label": "Below Logo"},
                        {"value": "above_logo", "label": "Above Logo"},
                        {"value": "left_of_logo", "label": "Left of Logo"},
                        {"value": "right_of_logo", "label": "Right of Logo"},
                        {"value": "replace_logo", "label": "Text Only (no logo)"},
                    ],
                    "default": "below_logo",
                    "show_if": {"field": "text", "not_empty": True},
                },
                {
                    "key": "text_color",
                    "label": "Text Color",
                    "type": "select",
                    "options": [
                        {"value": "white", "label": "White"},
                        {"value": "black", "label": "Black"},
                        {"value": "match_logo", "label": "Match Logo"},
                    ],
                    "default": "white",
                    "show_if": {"field": "text", "not_empty": True},
                },
                {
                    "key": "text_line2",
                    "label": "Second Line",
                    "type": "text",
                    "default": "",
                    "placeholder": "e.g. jersey number",
                    "show_if": {"field": "text", "not_empty": True},
                },
                {
                    "key": "font_line2",
                    "label": "Line 2 Font",
                    "type": "select",
                    "options": list(_FONT_OPTIONS),
                    "default": "bebas",
                    "show_if": {"field": "text_line2", "not_empty": True},
                },
                {
                    "key": "decoration",
                    "label": "Decoration",
                    "type": "select",
                    "options": [
                        {"value": k, "label": v}
                        for k, v in _DECORATION_LABELS.items()
                    ],
                    "default": "none",
                },
                {
                    "key": "decoration_position",
                    "label": "Decoration Position",
                    "type": "select",
                    "options": [
                        {"value": "left", "label": "Left Side"},
                        {"value": "right", "label": "Right Side"},
                        {"value": "above", "label": "Above"},
                        {"value": "below", "label": "Below"},
                    ],
                    "default": "left",
                    "show_if": {"field": "decoration", "not_value": "none"},
                },
                {
                    "key": "decoration_color",
                    "label": "Decoration Color",
                    "type": "select",
                    "options": [
                        {"value": "default", "label": "Default Colors"},
                        {"value": "match_logo", "label": "Match Logo"},
                        {"value": "match_text", "label": "Match Text"},
                        {"value": "white", "label": "White"},
                        {"value": "black", "label": "Black"},
                    ],
                    "default": "default",
                    "show_if": {"field": "decoration", "not_value": "none"},
                },
            ]
        }

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def generate(
        self,
        svg_path: str,
        png_path: str,
        config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        style = config.get("style", "raised")

        if style == "silhouette":
            return self._generate_silhouette(svg_path, png_path, config)
        elif style == "embedded":
            return self._generate_embedded(svg_path, png_path, config)
        else:
            return self._generate_raised(svg_path, png_path, config)

    # ------------------------------------------------------------------
    # Logo helpers
    # ------------------------------------------------------------------

    def _extract_logo_contours(self, svg_path: str):
        groups, vb_w, vb_h = parse_svg(svg_path)
        if not groups:
            raise ValueError("SVG contains no usable paths")
        return groups, vb_w, vb_h

    def _dominant_logo_color(self, svg_path: str) -> str:
        """Return the hex colour of the first (largest-area) SVG group."""
        try:
            groups, _, _ = parse_svg(svg_path)
            if groups:
                return groups[0].get("color", "#ffffff")
        except Exception:
            pass
        return "#ffffff"

    def _scale_and_position_logo(
        self, groups, vb_w, vb_h,
        area_w: float, area_h: float,
        area_cx: float = 0.0, area_cy: float = 0.0,
        rdp_epsilon: float = 0.3,
        fill_ratio: float = LOGO_FILL,
    ):
        """
        Scale logo contours to fit within a rectangular area
        (area_w x area_h centred at area_cx, area_cy) at fill_ratio,
        then return the per-colour groups with scaled contours.
        """
        target_w = area_w * fill_ratio
        target_h = area_h * fill_ratio
        scale_w = target_w / vb_w if vb_w > 0 else 1.0
        scale_h = target_h / vb_h if vb_h > 0 else 1.0
        scale = min(scale_w, scale_h)

        logo_w = vb_w * scale
        logo_h = vb_h * scale

        cx = area_cx - logo_w / 2
        cy = area_cy - logo_h / 2

        scaled_groups = []
        for group in groups:
            classified = classify_contours(group["contours"])
            new_contours = []
            for outer_raw, holes_raw in classified:
                outer = rdp_simplify(outer_raw, rdp_epsilon)
                if len(outer) < 3:
                    continue
                outer_s = [
                    [p[0] * scale + cx, (vb_h - p[1]) * scale + cy]
                    for p in outer
                ]
                holes_s = []
                for h in holes_raw:
                    hs = rdp_simplify(h, rdp_epsilon)
                    if len(hs) >= 3:
                        holes_s.append([
                            [p[0] * scale + cx, (vb_h - p[1]) * scale + cy]
                            for p in hs
                        ])
                new_contours.append((outer_s, holes_s))
            if new_contours:
                scaled_groups.append({
                    "color": group["color"],
                    "id": group["id"],
                    "contours": new_contours,
                })
        return scaled_groups

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def _resolve_text_color(self, config, svg_path: str) -> str:
        key = config.get("text_color", "white")
        color = TEXT_COLORS.get(key, "#ffffff")
        if color is None:
            color = self._dominant_logo_color(svg_path)
        return color

    def _render_text_at(
        self, text: str, font_key: str,
        cx: float, cy: float, max_w: float, max_h: float,
        color: str, z_bottom: float, z_top: float,
        mesh_id: str = "text",
    ) -> Optional[dict]:
        """Render one line of text centred at (cx, cy) and return a mesh dict."""
        if not text.strip() or max_w <= 0 or max_h <= 0:
            return None

        from text_renderer import render_text_contours

        font_file = FONT_MAP.get(font_key, "BebasNeue-Regular.ttf")
        contours = render_text_contours(text, font_file, max_w, max_h)
        if not contours:
            return None

        shifted = [[[p[0] + cx, p[1] + cy] for p in c] for c in contours]

        top_tris: List = []
        gray_tris: List = []
        for contour in shifted:
            if len(contour) < 3:
                continue
            t, g = extrude_watertight_separated(contour, None, z_bottom, z_top)
            top_tris.extend(t)
            gray_tris.extend(g)

        if not top_tris and not gray_tris:
            return None

        return {
            "color": color,
            "id": mesh_id,
            "triangles": top_tris + gray_tris,
            "top_triangles": top_tris,
            "gray_triangles": gray_tris,
        }

    def _render_decoration(
        self, deco_key: str, cx: float, cy: float,
        diameter: float, z_bottom: float, z_top: float,
        override_color: Optional[str] = None,
    ) -> List[dict]:
        """Render a decoration centred at (cx, cy) and return mesh dicts."""
        factory = DECORATION_REGISTRY.get(deco_key)
        if factory is None:
            return []

        layers = factory(diameter)
        meshes: List[dict] = []

        for layer in layers:
            color = override_color if override_color else layer["color"]
            top_tris: List = []
            gray_tris: List = []
            for contour in layer["contours"]:
                shifted = [[p[0] + cx, p[1] + cy] for p in contour]
                if len(shifted) < 3:
                    continue
                t, g = extrude_watertight_separated(
                    shifted, None, z_bottom, z_top,
                )
                top_tris.extend(t)
                gray_tris.extend(g)

            if top_tris or gray_tris:
                meshes.append({
                    "color": color,
                    "id": layer.get("id", "decoration"),
                    "triangles": top_tris + gray_tris,
                    "top_triangles": top_tris,
                    "gray_triangles": gray_tris,
                })

        return meshes

    def _resolve_decoration_color(
        self, config: dict, svg_path: str,
    ) -> Optional[str]:
        """Return a single override color for the decoration, or None for default."""
        dc = config.get("decoration_color", "default")
        if dc == "default":
            return None
        if dc == "match_logo":
            return self._dominant_logo_color(svg_path)
        if dc == "match_text":
            return self._resolve_text_color(config, svg_path)
        return TEXT_COLORS.get(dc, "#ffffff")

    def _add_decoration_to_shape(
        self, color_meshes: List[dict], config: dict, svg_path: str,
        shape_w: float, shape_h: float,
        z_bottom: float, z_top: float,
    ) -> List[dict]:
        """Add decoration to raised/embedded styles within the shape bounds."""
        deco_key = config.get("decoration", "none")
        if not deco_key or deco_key == "none":
            return color_meshes

        all_tris = [tri for m in color_meshes for tri in m["triangles"]]
        if not all_tris:
            return color_meshes

        all_xs = [v[0] for tri in all_tris for v in tri]
        all_ys = [v[1] for tri in all_tris for v in tri]
        content_cx = (min(all_xs) + max(all_xs)) / 2
        content_cy = (min(all_ys) + max(all_ys)) / 2
        content_min_x = min(all_xs)
        content_max_x = max(all_xs)
        content_min_y = min(all_ys)
        content_max_y = max(all_ys)

        avail_w = shape_w / 2
        avail_h = shape_h / 2
        deco_diameter = min(avail_w, avail_h) * 0.5
        deco_gap = 2.0
        deco_pos = config.get("decoration_position", "left")

        if deco_pos == "right":
            deco_cx = min(content_max_x + deco_gap + deco_diameter / 2,
                         shape_w / 2 - deco_diameter / 2 - 1)
            deco_cy = content_cy
        elif deco_pos == "left":
            deco_cx = max(content_min_x - deco_gap - deco_diameter / 2,
                         -shape_w / 2 + deco_diameter / 2 + 1)
            deco_cy = content_cy
        elif deco_pos == "above":
            deco_cx = content_cx
            deco_cy = min(content_max_y + deco_gap + deco_diameter / 2,
                         shape_h / 2 - deco_diameter / 2 - 1)
        else:
            deco_cx = content_cx
            deco_cy = max(content_min_y - deco_gap - deco_diameter / 2,
                         -shape_h / 2 + deco_diameter / 2 + 1)

        deco_override = self._resolve_decoration_color(config, svg_path)
        deco_meshes = self._render_decoration(
            deco_key, deco_cx, deco_cy, deco_diameter,
            z_bottom, z_top, deco_override,
        )
        color_meshes.extend(deco_meshes)
        return color_meshes

    # ------------------------------------------------------------------
    # Layout computation
    # ------------------------------------------------------------------

    def _compute_layout(
        self, shape_w: float, shape_h: float,
        config: Dict[str, Any], padding: float = PADDING,
    ) -> dict:
        """
        Returns a layout dict:
          logo_area:  (cx, cy, w, h) or None
          logo_fill:  float
          text1_area: (cx, cy, w, h) or None
          text2_area: (cx, cy, w, h) or None
        All coordinates are in mm, centred on the shape origin.
        """
        text_pos = config.get("text_position", "below_logo")
        has_text = bool((config.get("text") or "").strip())
        has_line2 = bool((config.get("text_line2") or "").strip())

        aw = shape_w - 2 * padding
        ah = shape_h - 2 * padding
        if aw <= 0 or ah <= 0:
            aw, ah = shape_w * 0.9, shape_h * 0.9

        # No text — logo fills most of the tag
        if not has_text:
            return dict(
                logo_area=(0.0, 0.0, aw, ah),
                logo_fill=LOGO_FILL,
                text1_area=None,
                text2_area=None,
            )

        # Text replaces logo entirely
        if text_pos == "replace_logo":
            if has_line2:
                t1_h = ah * 0.55
                t2_h = ah * 0.38
                gap = ah * 0.07
                t1_cy = (t2_h + gap) / 2
                t2_cy = -(t1_h + gap) / 2
            else:
                t1_h = ah * 0.60
                t1_cy = 0.0
                t2_h = t2_cy = 0.0
            return dict(
                logo_area=None,
                logo_fill=0.0,
                text1_area=(0.0, t1_cy, aw * 0.95, t1_h),
                text2_area=(0.0, t2_cy, aw * 0.95, t2_h) if has_line2 else None,
            )

        # Vertical split: above/below
        if text_pos in ("above_logo", "below_logo"):
            logo_frac = 0.62
            text_frac = 0.34
            gap = ah * 0.04

            logo_h = ah * logo_frac
            text_h = ah * text_frac

            if text_pos == "below_logo":
                logo_cy = (text_h + gap) / 2
                text_zone_cy = -(logo_h + gap) / 2
            else:
                logo_cy = -(text_h + gap) / 2
                text_zone_cy = (logo_h + gap) / 2

            if has_line2:
                t1_h = text_h * 0.60
                t2_h = text_h * 0.35
                sub_gap = text_h * 0.05
                t1_cy = text_zone_cy + (t2_h + sub_gap) / 2
                t2_cy = text_zone_cy - (t1_h + sub_gap) / 2
            else:
                t1_h = text_h
                t1_cy = text_zone_cy
                t2_h = t2_cy = 0.0

            return dict(
                logo_area=(0.0, logo_cy, aw, logo_h),
                logo_fill=0.90,
                text1_area=(0.0, t1_cy, aw * 0.95, t1_h),
                text2_area=(0.0, t2_cy, aw * 0.95, t2_h) if has_line2 else None,
            )

        # Horizontal split: left/right of logo
        if text_pos in ("left_of_logo", "right_of_logo"):
            logo_frac = 0.50
            text_frac = 0.46
            gap = aw * 0.04

            logo_w = aw * logo_frac
            text_w = aw * text_frac

            if text_pos == "left_of_logo":
                logo_cx = (text_w + gap) / 2
                text_cx = -(logo_w + gap) / 2
            else:
                logo_cx = -(text_w + gap) / 2
                text_cx = (logo_w + gap) / 2

            if has_line2:
                t1_h = ah * 0.55
                t2_h = ah * 0.38
                sub_gap = ah * 0.07
                t1_cy = (t2_h + sub_gap) / 2
                t2_cy = -(t1_h + sub_gap) / 2
            else:
                t1_h = ah * 0.65
                t1_cy = 0.0
                t2_h = t2_cy = 0.0

            return dict(
                logo_area=(logo_cx, 0.0, logo_w, ah),
                logo_fill=0.90,
                text1_area=(text_cx, t1_cy, text_w * 0.95, t1_h),
                text2_area=(text_cx, t2_cy, text_w * 0.95, t2_h) if has_line2 else None,
            )

        return dict(
            logo_area=(0.0, 0.0, aw, ah),
            logo_fill=LOGO_FILL,
            text1_area=None,
            text2_area=None,
        )

    # ------------------------------------------------------------------
    # Build logo + text meshes (shared by raised / embedded)
    # ------------------------------------------------------------------

    def _build_logo_and_text(
        self, svg_path: str, config: Dict[str, Any],
        shape_w: float, shape_h: float,
        z_bottom: float, z_top: float,
        padding: float = PADDING,
    ) -> List[dict]:
        """Return colour meshes for the logo and any text lines."""
        layout = self._compute_layout(shape_w, shape_h, config, padding)
        color_meshes: List[dict] = []

        # --- Logo ---
        if layout["logo_area"] is not None:
            la_cx, la_cy, la_w, la_h = layout["logo_area"]
            groups, vb_w, vb_h = self._extract_logo_contours(svg_path)
            scaled = self._scale_and_position_logo(
                groups, vb_w, vb_h,
                la_w, la_h, la_cx, la_cy,
                fill_ratio=layout["logo_fill"],
            )

            for group in scaled:
                top_tris: List = []
                gray_tris: List = []
                for outer_s, holes_s in group["contours"]:
                    t, g = extrude_watertight_separated(
                        outer_s, holes_s, z_bottom, z_top,
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

        # --- Text ---
        text_color = self._resolve_text_color(config, svg_path)
        font1 = config.get("font", "bebas")

        if layout["text1_area"] is not None:
            t1_cx, t1_cy, t1_w, t1_h = layout["text1_area"]
            text1 = (config.get("text") or "").strip()
            m = self._render_text_at(
                text1, font1, t1_cx, t1_cy, t1_w, t1_h,
                text_color, z_bottom, z_top, "text-line1",
            )
            if m:
                color_meshes.append(m)

        if layout["text2_area"] is not None:
            t2_cx, t2_cy, t2_w, t2_h = layout["text2_area"]
            text2 = (config.get("text_line2") or "").strip()
            font2 = config.get("font_line2", "bebas")
            m = self._render_text_at(
                text2, font2, t2_cx, t2_cy, t2_w, t2_h,
                text_color, z_bottom, z_top, "text-line2",
            )
            if m:
                color_meshes.append(m)

        return color_meshes

    # ------------------------------------------------------------------
    # RAISED style
    # ------------------------------------------------------------------

    def _generate_raised(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        shape_name = config.get("shape", "rectangle")
        size_key = config.get("size", "medium")
        keyhole_type = config.get("keyhole", "round_hole")
        base_color_key = config.get("base_color", "black")
        base_color = BASE_COLORS.get(base_color_key, "#1a1a1a")

        shape_w, shape_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])

        base_thickness = 2.5
        logo_height = 2.5

        shape_contour = get_shape(shape_name, shape_w, shape_h)

        hole_contour = None
        if keyhole_type == "round_hole":
            shape_contour, hole_contour = round_hole(shape_contour)
        elif keyhole_type == "tab_loop":
            shape_contour, hole_contour = tab_loop(shape_contour)

        holes = [hole_contour] if hole_contour else None
        base_tris = extrude_polygon_with_walls(shape_contour, holes, 0.0, base_thickness)

        base_plate = {
            "color": base_color,
            "id": "base-plate",
            "triangles": base_tris,
        }

        z_base_top = base_thickness
        z_logo_top = base_thickness + logo_height

        color_meshes = self._build_logo_and_text(
            svg_path, config, shape_w, shape_h,
            z_base_top, z_logo_top,
        )

        color_meshes = self._add_decoration_to_shape(
            color_meshes, config, svg_path,
            shape_w, shape_h, z_base_top, z_logo_top,
        )

        return color_meshes, base_plate

    # ------------------------------------------------------------------
    # EMBEDDED style
    # ------------------------------------------------------------------

    def _generate_embedded(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        shape_name = config.get("shape", "rectangle")
        size_key = config.get("size", "medium")
        keyhole_type = config.get("keyhole", "round_hole")
        base_color_key = config.get("base_color", "black")
        base_color = BASE_COLORS.get(base_color_key, "#1a1a1a")

        shape_w, shape_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])

        total_height = 5.0
        recess_depth = 2.0
        recess_z = total_height - recess_depth

        shape_contour = get_shape(shape_name, shape_w, shape_h)

        hole_contour = None
        if keyhole_type == "round_hole":
            shape_contour, hole_contour = round_hole(shape_contour)
        elif keyhole_type == "tab_loop":
            shape_contour, hole_contour = tab_loop(shape_contour)

        holes = [hole_contour] if hole_contour else None
        base_tris = extrude_polygon_with_walls(shape_contour, holes, 0.0, total_height)

        base_plate = {
            "color": base_color,
            "id": "base-plate",
            "triangles": base_tris,
        }

        color_meshes = self._build_logo_and_text(
            svg_path, config, shape_w, shape_h,
            recess_z, total_height,
        )

        color_meshes = self._add_decoration_to_shape(
            color_meshes, config, svg_path,
            shape_w, shape_h, recess_z, total_height,
        )

        return color_meshes, base_plate

    # ------------------------------------------------------------------
    # SILHOUETTE style
    # ------------------------------------------------------------------

    def _generate_silhouette(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        size_key = config.get("size", "medium")
        keyhole_type = config.get("keyhole", "round_hole")
        base_color_key = config.get("base_color", "black")
        base_color = BASE_COLORS.get(base_color_key, "#1a1a1a")

        target_w, target_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])
        target_size_mm = max(target_w, target_h)

        base_thickness = 2.0
        logo_height = 3.0
        margin = 1.5
        rdp_epsilon = 0.3

        groups, vb_w, vb_h = parse_svg(svg_path)
        if not groups:
            raise ValueError("SVG contains no usable paths")

        max_dim = max(vb_w, vb_h)
        scale = target_size_mm / max_dim if max_dim > 0 else 1.0

        z_base_top = base_thickness
        z_logo_top = base_thickness + logo_height

        color_meshes: List[dict] = []
        all_logo_triangles: List = []

        for group in groups:
            top_tris: List = []
            gray_tris: List = []
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
                    outer_scaled, holes_scaled, z_base_top, z_logo_top,
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

        # --- Text on silhouette ---
        has_text = bool((config.get("text") or "").strip())
        if has_text:
            all_xs = [v[0] for tri in all_logo_triangles for v in tri]
            all_ys = [v[1] for tri in all_logo_triangles for v in tri]
            logo_min_x, logo_max_x = min(all_xs), max(all_xs)
            logo_min_y, logo_max_y = min(all_ys), max(all_ys)
            logo_w = logo_max_x - logo_min_x
            logo_h = logo_max_y - logo_min_y
            logo_cx = (logo_min_x + logo_max_x) / 2
            logo_cy = (logo_min_y + logo_max_y) / 2

            text_pos = config.get("text_position", "below_logo")
            text_color = self._resolve_text_color(config, svg_path)
            font1 = config.get("font", "bebas")
            text1 = (config.get("text") or "").strip()
            text2 = (config.get("text_line2") or "").strip()
            font2 = config.get("font_line2", "bebas")

            gap = 1.5
            is_side = text_pos in ("left_of_logo", "right_of_logo")

            if is_side:
                t1_h = logo_h * 0.70
                t2_h = logo_h * 0.45 if text2 else 0
                t_max_w = logo_w * 1.8

                if text_pos == "right_of_logo":
                    t_cx = logo_max_x + gap + t_max_w / 2
                else:
                    t_cx = logo_min_x - gap - t_max_w / 2

                if text2:
                    line_gap = 1.0
                    t1_cy = logo_cy + (t2_h + line_gap) / 2
                    t2_cy = logo_cy - (t1_h + line_gap) / 2
                else:
                    t1_cy = logo_cy
            else:
                t1_h = logo_h * 0.40
                t2_h = logo_h * 0.28 if text2 else 0
                t_max_w = logo_w * 1.5

                if text_pos == "above_logo":
                    t1_cy = logo_max_y + gap + t1_h / 2
                    t2_cy = t1_cy + t1_h / 2 + 1.0 + t2_h / 2
                else:
                    t1_cy = logo_min_y - gap - t1_h / 2
                    t2_cy = t1_cy - t1_h / 2 - 1.0 - t2_h / 2

                t_cx = logo_cx

            m = self._render_text_at(
                text1, font1, t_cx, t1_cy, t_max_w, t1_h,
                text_color, z_base_top, z_logo_top, "text-line1",
            )
            if m:
                color_meshes.append(m)
                all_logo_triangles.extend(m["triangles"])

            if text2:
                m2 = self._render_text_at(
                    text2, font2, t_cx, t2_cy, t_max_w, t2_h,
                    text_color, z_base_top, z_logo_top, "text-line2",
                )
                if m2:
                    color_meshes.append(m2)
                    all_logo_triangles.extend(m2["triangles"])

        # --- Decoration on silhouette ---
        deco_key = config.get("decoration", "none")
        if deco_key and deco_key != "none":
            all_xs_d = [v[0] for tri in all_logo_triangles for v in tri]
            all_ys_d = [v[1] for tri in all_logo_triangles for v in tri]
            content_min_x = min(all_xs_d)
            content_max_x = max(all_xs_d)
            content_min_y = min(all_ys_d)
            content_max_y = max(all_ys_d)
            content_h = content_max_y - content_min_y
            content_cx = (content_min_x + content_max_x) / 2
            content_cy = (content_min_y + content_max_y) / 2

            deco_diameter = content_h * 0.60
            deco_gap = 1.5
            deco_pos = config.get("decoration_position", "left")

            if deco_pos == "right":
                deco_cx = content_max_x + deco_gap + deco_diameter / 2
                deco_cy = content_cy
            elif deco_pos == "left":
                deco_cx = content_min_x - deco_gap - deco_diameter / 2
                deco_cy = content_cy
            elif deco_pos == "above":
                deco_cx = content_cx
                deco_cy = content_max_y + deco_gap + deco_diameter / 2
            else:
                deco_cx = content_cx
                deco_cy = content_min_y - deco_gap - deco_diameter / 2

            deco_override = self._resolve_decoration_color(config, svg_path)
            deco_meshes = self._render_decoration(
                deco_key, deco_cx, deco_cy, deco_diameter,
                z_base_top, z_logo_top, deco_override,
            )
            for dm in deco_meshes:
                color_meshes.append(dm)
                all_logo_triangles.extend(dm["triangles"])

        # --- Base plate: trace combined silhouette of ALL content ---
        base_tris = _trace_combined_silhouette_base(
            all_logo_triangles, base_thickness, margin,
            keyhole_type,
        )

        base_plate = {
            "color": base_color,
            "id": "base-plate",
            "triangles": base_tris,
        }

        return color_meshes, base_plate
