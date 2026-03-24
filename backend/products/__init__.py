"""
Product registry.

Import and register all product types here. The API uses this
registry to look up products by name and serve their config schemas.
"""

from products.keychain import KeychainProduct

PRODUCTS = {
    "keychain": KeychainProduct,
}


def get_product(name: str):
    """Look up a product class by name."""
    cls = PRODUCTS.get(name)
    if cls is None:
        raise ValueError(f"Unknown product type: {name}")
    return cls()


def get_all_configs() -> dict:
    """Return config schemas for all registered products."""
    return {
        name: {"display_name": cls.display_name, "config": cls.get_config()}
        for name, cls in PRODUCTS.items()
    }
