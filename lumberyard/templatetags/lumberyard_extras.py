from django import template

register = template.Library()


MATERIAL_IMAGES = {
    "OAK-BOARD-25": "lumberyard/images/public/material-oak-board.webp",
    "PINE-BEAM-100": "lumberyard/images/public/material-pine-beam.webp",
    "ASH-BOARD-30": "lumberyard/images/public/material-ash-board.webp",
    "SPRUCE-BATTEN-50": (
        "lumberyard/images/public/material-spruce-batten.webp"
    ),
    "BIRCH-PLY-18": (
        "lumberyard/images/public/material-birch-plywood.webp"
    ),
    "OSB3-12": "lumberyard/images/public/material-osb3-panel.webp",
    "MDF-16": "lumberyard/images/public/material-mdf-panel.webp",
    "CHIPBOARD-18": (
        "lumberyard/images/public/material-chipboard.webp"
    ),
}

CATEGORY_IMAGES = {
    "boards": "lumberyard/images/public/category-boards.webp",
    "planks": "lumberyard/images/public/category-boards.webp",
    "lumber": "lumberyard/images/public/category-boards.webp",
    "beams": "lumberyard/images/public/category-beams.webp",
    "battens": "lumberyard/images/public/category-beams.webp",
    "sheet materials": (
        "lumberyard/images/public/category-sheet-materials.webp"
    ),
    "sheet goods": (
        "lumberyard/images/public/category-sheet-materials.webp"
    ),
    "plywood": "lumberyard/images/public/category-sheet-materials.webp",
}
DEFAULT_CATEGORY_IMAGE = (
    "lumberyard/images/public/category-mixed-timber.webp"
)


@register.filter
def category_image(category):
    """Return a curated static image path for a material category."""
    category_name = getattr(category, "name", category)

    if not category_name:
        return DEFAULT_CATEGORY_IMAGE

    normalized_name = str(category_name).strip().lower()

    for keyword, image_path in CATEGORY_IMAGES.items():
        if keyword in normalized_name:
            return image_path

    return DEFAULT_CATEGORY_IMAGE


@register.filter
def material_image(material):
    """Return a material image, falling back to its category image."""
    material_sku = getattr(material, "sku", "")
    image_path = MATERIAL_IMAGES.get(str(material_sku).strip().upper())

    if image_path:
        return image_path

    return category_image(getattr(material, "category", None))
