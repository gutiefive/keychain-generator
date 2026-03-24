# Keychain Generator

A full-stack web app that converts a logo image (PNG/JPG) into 3D-printable **keychain** STL and multi-color 3MF files optimized for Bambu Lab printers with AMS.

Forked from [helmet-logo-generator](https://github.com/gutiefive/helmet-logo-generator) with a product framework designed for easy extension to other items (coasters, ornaments, phone stands, etc.).

## Features

### Three Logo Styles
- **Raised** — Logo extruded on top of a flat base shape (like a stamp)
- **Embedded** — Logo engraved/recessed into the base shape surface
- **Silhouette** — Logo's own outline IS the keychain shape

### Base Shapes
Rectangle (rounded corners), Circle, Oval, Dog Tag, Shield/Badge

### Customization
- **Size presets**: Small (40x25mm), Medium (50x35mm), Large (65x45mm)
- **Logo position**: Center, Top, Bottom, Left, Right
- **Key ring hole**: Round hole, Tab loop, or None

### Shared Pipeline
- Drag-and-drop logo upload with real-time progress stepper
- Background removal via rembg (u2net)
- Automatic color quantization (up to 3 logo colors + 1 base = 4 AMS slots)
- Multi-color 3MF with per-triangle `paint_color` for Bambu Studio

## Tech Stack

| Layer    | Technology |
|----------|-----------|
| Backend  | FastAPI, Python 3.10+ |
| Frontend | Vite + React + Tailwind CSS + Framer Motion |
| 3D       | numpy-stl, mapbox-earcut, scikit-image |
| AI       | rembg (u2net) for background removal |

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Setup & Run

**Windows:**
```
run.bat
```

**macOS/Linux:**
```bash
chmod +x run.sh
./run.sh
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Adding New Product Types

The product framework makes it easy to add new items. Create a new file in `backend/products/`:

```python
from products.base import BaseProduct

class CoasterProduct(BaseProduct):
    name = "coaster"
    display_name = "Coaster"

    @classmethod
    def get_config(cls):
        return { "fields": [ ... ] }

    def generate(self, svg_path, png_path, config):
        # Build geometry, return (color_meshes, base_plate)
        ...
```

Register it in `backend/products/__init__.py`:

```python
from products.coaster import CoasterProduct
PRODUCTS["coaster"] = CoasterProduct
```

The frontend auto-renders configuration controls from the schema.

## License

MIT
