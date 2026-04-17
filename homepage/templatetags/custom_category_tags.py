from django import template
from oscar.apps.catalogue.models import Category, Product
from easy_thumbnails.files import get_thumbnailer

register = template.Library()

@register.simple_tag
def get_top_categories():
    return Category.objects.filter(depth=1)

@register.simple_tag
def get_category_products(category, limit=3):
    """
    Get products for a specific category
    """
    products = Product.objects.filter(
        categories=category,
        is_public=True
    )[:limit]
    return products

@register.simple_tag
def get_thumbnail_url(image, size='portfolio'):
    """Get thumbnail URL for consistent sizing"""
    if not image:
        return None
    try:
        thumbnail_options = {'size': (400, 300), 'crop': True}
        if size == 'portfolio_small':
            thumbnail_options = {'size': (200, 150), 'crop': True}
        elif size == 'portfolio_large':
            thumbnail_options = {'size': (1200, 900), 'crop': True}
        thumbnail_url = get_thumbnailer(image).get_thumbnail(thumbnail_options).url
        return thumbnail_url
    except Exception as e:
        # Fallback to original image if thumbnail generation fails
        return image.url
