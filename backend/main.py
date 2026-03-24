"""
FastAPI backend for the Keychain Generator pipeline.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pipeline import new_job, step_remove_bg, step_vectorize, step_generate_stl, get_file_path
from products import get_all_configs

app = FastAPI(title="Keychain Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/product-config")
async def product_config():
    """Return configuration schemas for all registered product types."""
    return get_all_configs()


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        raise HTTPException(400, "Only PNG, JPG, and WebP images are accepted.")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20 MB).")
    job_id = new_job(data, file.filename)
    return {"job_id": job_id}


@app.post("/api/remove-bg/{job_id}")
async def remove_bg(job_id: str):
    try:
        step_remove_bg(job_id)
        return {"status": "ok", "file": "transparent.png"}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Background removal failed: {e}")


@app.post("/api/vectorize/{job_id}")
async def vectorize(job_id: str):
    try:
        step_vectorize(job_id)
        return {"status": "ok", "file": "logo.svg"}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Vectorization failed: {e}")


@app.post("/api/generate-stl/{job_id}")
async def generate_stl(job_id: str, request: Request):
    """
    Generate STL + 3MF. Accepts an optional JSON body with product config:
    {
        "product": "keychain",
        "style": "raised",
        "shape": "rectangle",
        "size": "medium",
        "logo_position": "center",
        "keyhole": "round_hole"
    }
    """
    try:
        config = None
        body = await request.body()
        if body:
            import json
            config = json.loads(body)

        step_generate_stl(job_id, config=config)
        return {"status": "ok", "file": "logo.stl", "file_3mf": "logo.3mf"}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"STL generation failed: {e}")


@app.get("/api/files/{job_id}/{filename}")
async def serve_file(job_id: str, filename: str):
    try:
        path = get_file_path(job_id, filename)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")

    media_types = {
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".stl": "application/octet-stream",
        ".3mf": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    mt = media_types.get(ext, "application/octet-stream")
    return FileResponse(str(path), media_type=mt, filename=filename)
