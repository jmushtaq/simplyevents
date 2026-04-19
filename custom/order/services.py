from datetime import timedelta
from django.core.exceptions import ValidationError

def validate_hire_period(start_date, end_date):
    """
    Validate hire period follows Thursday 5pm to Monday 7pm rule
    
    Rules:
    - Start must be Thursday at 5pm (17:00)
    - End must be Monday at 7pm (19:00)
    - Duration must be 4 days (Thursday to Monday)
    """
    
    # Check start is Thursday at 5pm
    if start_date.weekday() != 3:  # 3 = Thursday
        raise ValidationError("Hire must start on Thursday")
    if start_date.hour != 17 or start_date.minute != 0:
        raise ValidationError("Hire must start at 5pm")
    
    # Check end is Monday at 7pm
    if end_date.weekday() != 0:  # 0 = Monday
        raise ValidationError("Hire must end on Monday")
    if end_date.hour != 19 or end_date.minute != 0:
        raise ValidationError("Hire must end at 7pm")
    
    # Check duration is 4 days (Thursday to Monday)
    duration = (end_date - start_date).days
    if duration != 4:
        raise ValidationError("Hire period must be Thursday to Monday (4 days)")
    
    return True


def get_unavailable_week_range(hire_start):
    """
    Return date range where product should be marked unavailable
    From Wednesday before hire to Tuesday after
    """
    unavailable_start = hire_start - timedelta(days=1)  # Wednesday
    unavailable_end = hire_start + timedelta(days=5)    # Tuesday
    return unavailable_start, unavailable_end


def is_product_available_for_hire(product, start_date, end_date):
    """
    Check if product is available for the requested hire period
    
    Returns:
        tuple: (bool available, str message)
    """
    
    # Validate the hire period format
    try:
        validate_hire_period(start_date, end_date)
    except ValidationError as e:
        return False, str(e)
    
    # Get the unavailable week range
    unavailable_start, unavailable_end = get_unavailable_week_range(start_date)
    
    # Check existing confirmed hires (using our custom HirePeriod model)
    try:
        from custom.order.models import HirePeriod
        from oscar.apps.catalogue.models import Product
        
        # Get the actual product ID if this is a variant
        product_id = product.id if hasattr(product, 'id') else product.pk
        
        conflicting_hires = HirePeriod.objects.filter(
            order_line__product_id=product_id,
            start_date__lt=unavailable_end,
            end_date__gt=unavailable_start
        ).exclude(
            # Allow if the hire period has been cancelled/completed
            order_line__order__status__in=['cancelled', 'refunded', 'completed']
        )
        
        if conflicting_hires.exists():
            return False, "Product already hired for this period"
            
    except ImportError:
        pass  # If model not available yet, skip this check
    
    # Check pending baskets with this product (from basket lines with hire dates)
    from oscar.apps.basket.models import Line as BasketLine
    
    pending_lines = BasketLine.objects.filter(
        product_id=product_id,
        hire_start_date__lt=unavailable_end,
        hire_end_date__gt=unavailable_start,
        basket__status='Open'
    )
    
    if pending_lines.exists():
        return False, "Product is in another customer's basket for this period"
    
    # Also check against stock - if no stock, not available
    from oscar.apps.partner.models import StockRecord
    stock_record = StockRecord.objects.filter(product_id=product_id).first()
    if stock_record and stock_record.net_stock_level <= 0:
        return False, "No stock available"
    
    return True, "Available"


def calculate_hire_price(product, start_date, end_date):
    """
    Calculate the hire price based on duration
    Currently uses the product's base price (for 4-day hire period)
    """
    from oscar.apps.partner.strategy import PurchaseInfo
    from custom.partner.strategy import UseFirstStockRecord, HireStockRequired, NoTax, Structured
    
    # Get price from stockrecord
    stock_record = StockRecord.objects.filter(product_id=product.id).first()
    if not stock_record:
        return None
    
    return stock_record.price  # Price per 4-day hire period