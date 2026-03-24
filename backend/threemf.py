"""
3MF multi-color export — Bambu Studio / OrcaSlicer native format.

Uses Bambu Studio's per-triangle ``paint_color`` attribute to assign
filament colors to individual faces within a SINGLE unified mesh.
This avoids the multi-part overlap / z-fighting issues that plague
the multi-object approach.

paint_color encoding (from BambuStudio source / community research):
  filament 1 → "4"
  filament 2 → "8"
  filament 3 → "0C"
  filament 4 → "1C"
  (up to 16 filaments with further codes)
"""

import json
import zipfile
import io
from xml.etree.ElementTree import Element, SubElement, tostring

from svg_to_stl import build_color_meshes

_APP_VERSION = "BambuStudio-01.10.00.50"

_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />
</Types>"""

_RELS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0"
    Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />
</Relationships>"""

# paint_color codes for filament slots 1-16
_PAINT_CODES = [
    "4", "8", "0C", "1C", "2C", "3C", "4C", "5C",
    "6C", "7C", "8C", "9C", "AC", "BC", "CC", "DC",
]


def _hex_color(color: str) -> str:
    """Return 8-digit #RRGGBBFF hex."""
    c = color.strip()
    if not c.startswith("#"):
        c = "#" + c
    if len(c) == 4:
        c = "#" + c[1]*2 + c[2]*2 + c[3]*2
    if len(c) == 7:
        c = c + "FF"
    return c.upper()


def _build_model_xml(color_meshes, base_plate):
    """
    Build a single-object 3MF model where ALL triangles live in one mesh.
    Each triangle gets a paint_color attribute for its filament assignment.
    """
    NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    NS_PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"

    model = Element("model")
    model.set("xmlns", NS_CORE)
    model.set("xmlns:p", NS_PROD)
    model.set("unit", "millimeter")
    model.set("xml:lang", "en-US")

    for name, val in [
        ("Application", _APP_VERSION),
        ("BambuStudio:3mfVersion", "1"),
        ("Title", "3DPipe Logo"),
        ("CreationDate", "2026-01-01"),
    ]:
        m = SubElement(model, "metadata")
        m.set("name", name)
        m.text = val

    resources = SubElement(model, "resources")

    # Build the colour → filament-index mapping.
    # Filament 1 = base plate (gray), then each logo colour gets 2, 3, 4…
    all_parts = [base_plate] + color_meshes
    color_to_filament = {}
    for i, part in enumerate(all_parts):
        color_to_filament[part["color"]] = i  # 0-based index into _PAINT_CODES

    gray_code = _PAINT_CODES[0]  # filament 1 = gray base

    # ── Single object with one mesh containing ALL triangles ──────────
    obj_id = "1"
    obj = SubElement(resources, "object")
    obj.set("id", obj_id)
    obj.set("type", "model")
    obj.set("p:UUID", "10000000-0000-0000-0000-000000000001")

    mesh_el = SubElement(obj, "mesh")
    verts_el = SubElement(mesh_el, "vertices")
    tris_el = SubElement(mesh_el, "triangles")

    vert_map = {}
    vert_list = []

    def _add_vert(v):
        key = (round(v[0], 6), round(v[1], 6), round(v[2], 6))
        if key not in vert_map:
            vert_map[key] = len(vert_list)
            vert_list.append(key)
        return vert_map[key]

    def _add_tri(tri, paint_code):
        i0 = _add_vert(tri[0])
        i1 = _add_vert(tri[1])
        i2 = _add_vert(tri[2])
        te = SubElement(tris_el, "triangle")
        te.set("v1", str(i0))
        te.set("v2", str(i1))
        te.set("v3", str(i2))
        te.set("paint_color", paint_code)

    # Base plate — all triangles gray
    for tri in base_plate["triangles"]:
        _add_tri(tri, gray_code)

    # Colour regions — top faces get the colour, bottom+walls get gray.
    for part in color_meshes:
        filament_idx = color_to_filament[part["color"]]
        color_code = _PAINT_CODES[filament_idx] if filament_idx < len(_PAINT_CODES) else gray_code

        for tri in part.get("top_triangles", []):
            _add_tri(tri, color_code)
        for tri in part.get("gray_triangles", []):
            _add_tri(tri, gray_code)

    # Write vertices
    for vx, vy, vz in vert_list:
        ve = SubElement(verts_el, "vertex")
        ve.set("x", f"{vx:.6f}")
        ve.set("y", f"{vy:.6f}")
        ve.set("z", f"{vz:.6f}")

    # Build section
    build = SubElement(model, "build")
    item = SubElement(build, "item")
    item.set("objectid", obj_id)
    item.set("p:UUID", "40000000-0000-0000-0000-000000000001")

    return tostring(model, encoding="unicode", xml_declaration=True), all_parts, obj_id


def _build_model_settings(obj_id):
    """model_settings.config — single object, single part, extruder 1."""
    config = Element("config")

    obj_el = SubElement(config, "object")
    obj_el.set("id", obj_id)

    name_m = SubElement(obj_el, "metadata")
    name_m.set("key", "name")
    name_m.set("value", "Logo")

    ext_m = SubElement(obj_el, "metadata")
    ext_m.set("key", "extruder")
    ext_m.set("value", "1")

    # Plate definition
    plate = SubElement(config, "plate")
    for key, val in [
        ("plater_id", "1"),
        ("plater_name", ""),
        ("locked", "false"),
    ]:
        pm = SubElement(plate, "metadata")
        pm.set("key", key)
        pm.set("value", val)

    inst = SubElement(plate, "model_instance")
    for key, val in [
        ("object_id", obj_id),
        ("instance_id", "0"),
        ("identify_id", obj_id),
    ]:
        im = SubElement(inst, "metadata")
        im.set("key", key)
        im.set("value", val)

    return tostring(config, encoding="unicode", xml_declaration=True)


def _build_project_settings(all_parts):
    """Filament colour list so Bambu Studio knows which colours to show."""
    settings = {
        "filament_colour": [_hex_color(part["color"]) for part in all_parts],
    }
    return json.dumps(settings, indent=2)


def _build_slice_info(all_parts):
    config = Element("config")
    plate = SubElement(config, "plate")
    for i, part in enumerate(all_parts):
        f = SubElement(plate, "filament")
        f.set("id", str(i + 1))
        f.set("type", "PLA")
        f.set("color", _hex_color(part["color"]))
        f.set("used_m", "0")
        f.set("used_g", "0")
    return tostring(config, encoding="unicode", xml_declaration=True)


def generate_3mf(
    svg_path: str,
    output_path: str,
    target_size_mm: float = 80.0,
    base_thickness: float = 1.5,
    logo_height: float = 2.5,
    margin: float = 2.0,
    rdp_epsilon: float = 0.3,
    png_path: str = None,
):
    """
    Generate a Bambu-Studio-native multi-color 3MF from an SVG.

    All geometry is merged into a single mesh.  Per-triangle paint_color
    attributes tell Bambu Studio which filament to use for each face —
    no multi-part overlap issues, no z-fighting, correct multi-colour
    slicing every time.
    """
    color_meshes, base_plate = build_color_meshes(
        svg_path, target_size_mm, base_thickness, logo_height, margin, rdp_epsilon,
        png_path=png_path,
    )

    model_xml, all_parts, obj_id = _build_model_xml(color_meshes, base_plate)
    settings_xml = _build_model_settings(obj_id)
    project_json = _build_project_settings(all_parts)
    slice_info = _build_slice_info(all_parts)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("3D/3dmodel.model", model_xml)
        zf.writestr("Metadata/model_settings.config", settings_xml)
        zf.writestr("Metadata/project_settings.config", project_json)
        zf.writestr("Metadata/slice_info.config", slice_info)

    with open(output_path, "wb") as f:
        f.write(buf.getvalue())

    return output_path


def generate_3mf_from_meshes(
    color_meshes,
    base_plate,
    output_path: str,
):
    """
    Generate a 3MF directly from pre-built color_meshes and base_plate dicts.

    Used by the product framework which builds geometry independently
    of the SVG→mesh pipeline.
    """
    model_xml, all_parts, obj_id = _build_model_xml(color_meshes, base_plate)
    settings_xml = _build_model_settings(obj_id)
    project_json = _build_project_settings(all_parts)
    slice_info = _build_slice_info(all_parts)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("3D/3dmodel.model", model_xml)
        zf.writestr("Metadata/model_settings.config", settings_xml)
        zf.writestr("Metadata/project_settings.config", project_json)
        zf.writestr("Metadata/slice_info.config", slice_info)

    with open(output_path, "wb") as f:
        f.write(buf.getvalue())

    return output_path
