"""
Keychain product — generates 3D keychain geometry from a logo.

Supports three styles:
  - Raised:     Logo extruded on top of a flat base shape
  - Embedded:   Logo recessed into a full-height base shape
  - Silhouette: Logo's own outline IS the keychain shape
"""

from typing import Any, Dict, List, Tuple

from products.base import BaseProduct
from shapes import get_shape, SHAPE_REGISTRY
from keyhole import round_hole, tab_loop
from svg_to_stl import (
    parse_svg,
    classify_contours,
    rdp_simplify,
    extrude_polygon_with_walls,
    extrude_watertight_separated,
    create_silhouette_base_plate,
    _trace_alpha_contours,
    _fallback_base_plate,
    _signed_area,
)

SIZE_PRESETS = {
    "small":  (40.0, 25.0),
    "medium": (50.0, 35.0),
    "large":  (65.0, 45.0),
}

POSITION_OFFSETS = {
    "center": (0.0, 0.0),
    "top":    (0.0, 0.3),
    "bottom": (0.0, -0.3),
    "left":   (-0.25, 0.0),
    "right":  (0.25, 0.0),
}


class KeychainProduct(BaseProduct):
    name = "keychain"
    display_name = "Keychain"

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
                        {"value": "small", "label": f"Small ({SIZE_PRESETS['small'][0]:.0f} x {SIZE_PRESETS['small'][1]:.0f} mm)"},
                        {"value": "medium", "label": f"Medium ({SIZE_PRESETS['medium'][0]:.0f} x {SIZE_PRESETS['medium'][1]:.0f} mm)"},
                        {"value": "large", "label": f"Large ({SIZE_PRESETS['large'][0]:.0f} x {SIZE_PRESETS['large'][1]:.0f} mm)"},
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
            ]
        }

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
    # Logo mesh extraction (shared by raised / embedded)
    # ------------------------------------------------------------------

    def _extract_logo_contours(self, svg_path: str, rdp_epsilon: float = 0.3):
        """Parse SVG and return per-color groups with scaled contours."""
        groups, vb_w, vb_h = parse_svg(svg_path)
        if not groups:
            raise ValueError("SVG contains no usable paths")
        return groups, vb_w, vb_h

    def _scale_and_position_logo(
        self, groups, vb_w, vb_h, shape_w, shape_h,
        position: str, padding: float = 3.0, rdp_epsilon: float = 0.3,
    ):
        """
        Scale logo contours to fit within the shape bounds (with padding)
        and offset to the requested position. Returns scaled groups.
        """
        max_dim = max(vb_w, vb_h)
        avail_w = shape_w - 2 * padding
        avail_h = shape_h - 2 * padding
        if avail_w <= 0 or avail_h <= 0:
            avail_w, avail_h = shape_w * 0.8, shape_h * 0.8

        scale_w = avail_w / vb_w if vb_w > 0 else 1.0
        scale_h = avail_h / vb_h if vb_h > 0 else 1.0
        scale = min(scale_w, scale_h)

        logo_w = vb_w * scale
        logo_h = vb_h * scale

        off_frac_x, off_frac_y = POSITION_OFFSETS.get(position, (0.0, 0.0))
        offset_x = off_frac_x * (avail_w - logo_w)
        offset_y = off_frac_y * (avail_h - logo_h)

        # Center the logo on the shape, then apply position offset
        cx = -logo_w / 2 + offset_x
        cy = -logo_h / 2 + offset_y

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
    # RAISED style
    # ------------------------------------------------------------------

    def _generate_raised(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        """Logo raised on top of a flat base shape."""
        shape_name = config.get("shape", "rectangle")
        size_key = config.get("size", "medium")
        position = config.get("logo_position", "center")
        keyhole_type = config.get("keyhole", "round_hole")

        shape_w, shape_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])

        base_thickness = 3.0
        logo_height = 2.0

        # Generate base shape contour
        shape_contour = get_shape(shape_name, shape_w, shape_h)

        # Apply keyhole
        hole_contour = None
        if keyhole_type == "round_hole":
            shape_contour, hole_contour = round_hole(shape_contour)
        elif keyhole_type == "tab_loop":
            shape_contour, hole_contour = tab_loop(shape_contour)

        holes = [hole_contour] if hole_contour else None

        # Extrude base plate
        base_tris = extrude_polygon_with_walls(shape_contour, holes, 0.0, base_thickness)

        base_plate = {
            "color": "#cccccc",
            "id": "base-plate",
            "triangles": base_tris,
        }

        # Scale and position logo on the shape
        groups, vb_w, vb_h = self._extract_logo_contours(svg_path)
        scaled = self._scale_and_position_logo(
            groups, vb_w, vb_h, shape_w, shape_h, position
        )

        z_base_top = base_thickness
        z_logo_top = base_thickness + logo_height

        color_meshes = []
        for group in scaled:
            top_tris = []
            gray_tris = []
            for outer_s, holes_s in group["contours"]:
                t, g = extrude_watertight_separated(
                    outer_s, holes_s, z_base_top, z_logo_top
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

        return color_meshes, base_plate

    # ------------------------------------------------------------------
    # EMBEDDED style
    # ------------------------------------------------------------------

    def _generate_embedded(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        """Logo engraved/recessed into the base shape."""
        shape_name = config.get("shape", "rectangle")
        size_key = config.get("size", "medium")
        position = config.get("logo_position", "center")
        keyhole_type = config.get("keyhole", "round_hole")

        shape_w, shape_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])

        total_height = 4.0
        recess_depth = 1.5
        recess_z = total_height - recess_depth

        # Generate base shape contour
        shape_contour = get_shape(shape_name, shape_w, shape_h)

        hole_contour = None
        if keyhole_type == "round_hole":
            shape_contour, hole_contour = round_hole(shape_contour)
        elif keyhole_type == "tab_loop":
            shape_contour, hole_contour = tab_loop(shape_contour)

        holes = [hole_contour] if hole_contour else None

        # Full-height base plate
        base_tris = extrude_polygon_with_walls(shape_contour, holes, 0.0, total_height)

        base_plate = {
            "color": "#cccccc",
            "id": "base-plate",
            "triangles": base_tris,
        }

        # Logo contours — extruded as recessed regions
        # They go from z=0 to z=recess_z (shorter than the base),
        # creating the engraved visual. The color shows at the bottom
        # of the recess.
        groups, vb_w, vb_h = self._extract_logo_contours(svg_path)
        scaled = self._scale_and_position_logo(
            groups, vb_w, vb_h, shape_w, shape_h, position
        )

        color_meshes = []
        for group in scaled:
            top_tris = []
            gray_tris = []
            for outer_s, holes_s in group["contours"]:
                # The "top" face of the recess sits at recess_z (the bottom
                # of the groove). We paint it with the logo colour so it's
                # visible when looking down into the engraving.
                t, g = extrude_watertight_separated(
                    outer_s, holes_s, recess_z, total_height
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

        return color_meshes, base_plate

    # ------------------------------------------------------------------
    # SILHOUETTE style
    # ------------------------------------------------------------------

    def _generate_silhouette(
        self, svg_path: str, png_path: str, config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        """
        Logo's own shape IS the keychain — same approach as the
        helmet logo generator but with a keyhole added.
        """
        size_key = config.get("size", "medium")
        keyhole_type = config.get("keyhole", "round_hole")

        target_w, target_h = SIZE_PRESETS.get(size_key, SIZE_PRESETS["medium"])
        target_size_mm = max(target_w, target_h)

        base_thickness = 1.5
        logo_height = 2.5
        margin = 2.0
        rdp_epsilon = 0.3

        groups, vb_w, vb_h = parse_svg(svg_path)
        if not groups:
            raise ValueError("SVG contains no usable paths")

        max_dim = max(vb_w, vb_h)
        scale = target_size_mm / max_dim if max_dim > 0 else 1.0

        z_base_top = base_thickness
        z_logo_top = base_thickness + logo_height

        # Build color meshes (same as helmet logo generator)
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

        # Base plate — silhouette with keyhole
        if png_path:
            margin_px = max(1, int(round(margin / scale)))
            rings = _trace_alpha_contours(png_path, vb_h, scale, dilate_px=margin_px)
        else:
            rings = None

        if rings:
            base_outer = rings[0]
            base_holes_from_rings = rings[1:] if len(rings) > 1 else []

            # Add keyhole to the base plate
            if keyhole_type == "round_hole":
                base_outer, kh = round_hole(base_outer)
                base_holes_from_rings.append(kh)
            elif keyhole_type == "tab_loop":
                base_outer, kh = tab_loop(base_outer)
                base_holes_from_rings.append(kh)

            base_tris = extrude_polygon_with_walls(
                base_outer,
                base_holes_from_rings if base_holes_from_rings else None,
                0.0, base_thickness,
            )
        else:
            base_tris = _fallback_base_plate(
                all_logo_triangles, scale, base_thickness, margin
            )

        base_plate = {
            "color": "#cccccc",
            "id": "base-plate",
            "triangles": base_tris,
        }

        return color_meshes, base_plate
