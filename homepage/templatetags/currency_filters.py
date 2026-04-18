from decimal import Decimal as D, InvalidOperation
from django import template

register = template.Library()

@register.filter(name="currency")
def currency(value, currency_code=None):
    """
    Currency filter that displays as $ without A prefix.
    """
    try:
        value = D(value)
    except (TypeError, InvalidOperation):
        return ""
    
    return f"${value:.2f}"