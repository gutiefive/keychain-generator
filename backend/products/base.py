"""
Abstract base class for all product types.

Each product defines its configuration schema and implements
geometry generation from processed logo data.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseProduct(ABC):
    """Base class that all product types must inherit from."""

    name: str = "base"
    display_name: str = "Base Product"

    @classmethod
    @abstractmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Return a JSON-serializable config schema.

        The frontend uses this to auto-render configuration controls.
        Schema format:
        {
            "fields": [
                {
                    "key": "style",
                    "label": "Logo Style",
                    "type": "select",
                    "options": [
                        {"value": "raised", "label": "Raised"},
                        ...
                    ],
                    "default": "raised",
                    "show_if": {"field": "...", "values": [...]}  # optional conditional
                },
                ...
            ]
        }
        """
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        svg_path: str,
        png_path: str,
        config: Dict[str, Any],
    ) -> Tuple[List[dict], dict]:
        """
        Generate 3D geometry for this product.

        Args:
            svg_path: Path to the vectorized logo SVG
            png_path: Path to the transparent PNG (for silhouette tracing)
            config: User-selected configuration options

        Returns:
            (color_meshes, base_plate) in the same format as
            svg_to_stl.build_color_meshes — compatible with both
            STL and 3MF exporters.
        """
        raise NotImplementedError
