"""
Logo-to-keychain conversion pipeline.

Steps:
  1. Remove background (rembg / u2net)
  2. Vectorize to SVG (scikit-image contour tracing)
  3. Configure product (user picks shape, style, size, etc.)
  4. Generate STL + 3MF via the product framework
"""

import uuid
from pathlib import Path
from typing import Dict, Any

import numpy as np
from PIL import Image
from rembg import remove, new_session

from trace_svg import trace_image_to_svg
from svg_to_stl import svg_to_stl
from threemf import generate_3mf
from products import get_product

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _job_dir(job_id: str) -> Path:
    d = UPLOAD_DIR / job_id
    d.mkdir(exist_ok=True)
    return d


def new_job(file_bytes: bytes, filename: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    d = _job_dir(job_id)
    ext = Path(filename).suffix.lower() or ".png"
    src = d / f"original{ext}"
    src.write_bytes(file_bytes)
    return job_id


def _has_transparency(img: Image.Image, threshold: float = 0.05) -> bool:
    if img.mode != "RGBA":
        return False
    alpha = np.array(img)[:, :, 3]
    transparent_ratio = np.sum(alpha < 128) / alpha.size
    return transparent_ratio > threshold


def step_remove_bg(job_id: str) -> str:
    d = _job_dir(job_id)
    originals = list(d.glob("original.*"))
    if not originals:
        raise FileNotFoundError("Original image not found")
    src_path = originals[0]

    img = Image.open(src_path).convert("RGBA")

    max_side = 2048
    if max(img.size) > max_side:
        ratio = max_side / max(img.size)
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS
        )

    out_path = d / "transparent.png"

    if _has_transparency(img):
        img.save(str(out_path))
    else:
        session = new_session("u2net")
        result = remove(img, session=session)
        result.save(str(out_path))

    return str(out_path)


def step_vectorize(job_id: str) -> str:
    d = _job_dir(job_id)
    png_path = d / "transparent.png"
    if not png_path.exists():
        raise FileNotFoundError("Transparent PNG not found – run remove_bg first")

    svg_path = str(d / "logo.svg")

    trace_image_to_svg(
        str(png_path),
        svg_path,
        max_colors=3,
        alpha_threshold=128,
        simplify_tolerance=1.0,
    )

    return svg_path


def step_generate_stl(job_id: str, config: Dict[str, Any] = None) -> str:
    """
    Generate STL + 3MF using the product framework.

    If config is provided, it must include a "product" key (e.g. "keychain")
    plus any product-specific configuration fields.
    Falls back to the helmet-logo-generator behaviour if no config is given.
    """
    d = _job_dir(job_id)
    svg_path = d / "logo.svg"
    if not svg_path.exists():
        raise FileNotFoundError("SVG not found – run vectorize first")

    png_path = d / "transparent.png"
    png_str = str(png_path) if png_path.exists() else None

    stl_path = str(d / "logo.stl")
    tmf_path = str(d / "logo.3mf")

    if config and config.get("product"):
        product = get_product(config["product"])
        color_meshes, base_plate = product.generate(
            str(svg_path), png_str, config
        )

        # STL export — combine all triangles into one mesh
        import numpy as np
        from stl import mesh as stl_mesh_mod

        all_triangles = []
        for cm in color_meshes:
            all_triangles.extend(cm["triangles"])
        all_triangles.extend(base_plate["triangles"])

        tri_array = np.array(all_triangles)
        m = stl_mesh_mod.Mesh(np.zeros(len(tri_array), dtype=stl_mesh_mod.Mesh.dtype))
        for i, tri in enumerate(tri_array):
            m.vectors[i] = tri
        m.update_normals()
        m.save(stl_path)

        # 3MF export — uses the same color_meshes / base_plate format
        from threemf import generate_3mf_from_meshes
        generate_3mf_from_meshes(color_meshes, base_plate, tmf_path)
    else:
        # Fallback: original helmet-logo behaviour
        params = dict(
            target_size_mm=80.0,
            base_thickness=1.5,
            logo_height=2.5,
            margin=2.0,
            rdp_epsilon=0.3,
            png_path=png_str,
        )
        svg_to_stl(str(svg_path), stl_path, **params)
        generate_3mf(str(svg_path), tmf_path, **params)

    return stl_path


def get_file_path(job_id: str, filename: str) -> Path:
    p = _job_dir(job_id) / filename
    if not p.exists():
        raise FileNotFoundError(f"{filename} not found for job {job_id}")
    return p
