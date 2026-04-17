from django import template
from oscar.apps.catalogue.models import Category, ProductCategory, ProductImage

register = template.Library()

@register.simple_tag
def get_top_categories():
    cats = Category.objects.filter(depth=2, is_public=True)
    result = []
    for cat in cats:
        pc = ProductCategory.objects.filter(category=cat, product__is_public=True).select_related('product').first()
        img = None
        if pc and pc.product:
            img = pc.product.images.first()
        result.append({
            'category': cat,
            'image': img
        })
    return result

@register.simple_tag
def get_category_products(category, limit=3):
    from oscar.apps.catalogue.models import Product
    products = Product.objects.filter(
        categories=category,
        is_public=True
    )[:limit]
    return products

@register.simple_tag
def get_thumbnail_url(image, size='portfolio'):
    if not image:
        return None
    from easy_thumbnails.files import get_thumbnailer
    try:
        thumbnail_options = {'size': (400, 300), 'crop': True}
        if size == 'portfolio_small':
            thumbnail_options = {'size': (200, 150), 'crop': True}
        elif size == 'portfolio_large':
            thumbnail_options = {'size': (1200, 900), 'crop': True}
        thumbnail_url = get_thumbnailer(image).get_thumbnail(thumbnail_options).url
        return thumbnail_url
    except Exception as e:
        return image.original.url if hasattr(image, 'original') else None
