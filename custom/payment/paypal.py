from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def get_paypal_config():
    """Get PayPal configuration"""
    from django.conf import settings
    
    config = {
        'mode': getattr(settings, 'PAYPAL_MODE', 'sandbox'),
        'client_id': settings.PAYPAL_CLIENT_ID,
        'client_secret': settings.PAYPAL_CLIENT_SECRET,
    }
    logger.info("PayPal config: mode=%s, client_id=%s", config['mode'], config['client_id'][:10] if config.get('client_id') else 'None')
    return config

def configure_paypal():
    """Configure PayPal REST SDK"""
    import paypalrestsdk
    config = get_paypal_config()
    logger.info("Configuring PayPal with mode: %s", config['mode'])
    paypalrestsdk.configure(config)
    logger.info("PayPal configured successfully")

def create_payment(basket, return_url, cancel_url):
    """Create PayPal payment for the given basket with line items"""
    from paypalrestsdk import Payment
    
    amount = basket.total_incl_tax
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    items = []
    
    for line in basket.all_lines():
        line_quantity = int(line.quantity)
        
        line_price = line.unit_price_incl_tax
        if hasattr(line_price, 'quantize'):
            line_price = Decimal(str(line_price))
        elif not isinstance(line_price, Decimal):
            line_price = Decimal(str(line_price))
        
        product_name = line.product.title[:127] if hasattr(line.product, 'title') else str(line.product)[:127]
        
        items.append({
            "name": product_name,
            "description": f"Qty: {line_quantity}",
            "unit_amount": {
                "currency_code": basket.currency,
                "value": f"{line_price:.2f}",
            },
            "quantity": str(line_quantity),
        })
    
    shipping = 0
    try:
        shipping = basket.shipping_incl_tax or 0
    except AttributeError:
        pass
    if shipping:
        if isinstance(shipping, Decimal):
            shipping_amount = shipping
        else:
            shipping_amount = Decimal(str(shipping))
        if shipping_amount > 0:
            items.append({
                "name": "Shipping & Handling",
                "unit_amount": {
                    "currency_code": basket.currency,
                    "value": f"{shipping_amount:.2f}",
                },
                "quantity": "1",
            })
    
    transaction = {
        "amount": {
            "currency_code": basket.currency,
            "value": f"{amount:.2f}",
        },
        "description": f"Order for Simply Events",
        "invoice_id": f"BASKET-{basket.pk}",
        "soft_descriptor": "SimplyEvents",
    }
    
    if items:
        transaction["item_list"] = {"items": items}
    
    payment = Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
        "transactions": [transaction],
    })
    
    return payment

def find_payment(payment_id):
    """Find an existing payment"""
    from paypalrestsdk import Payment
    return Payment.find(payment_id)

def execute_payment(payment_id, payer_id):
    """Execute approved PayPal payment"""
    payment = find_payment(payment_id)
    if payment and payment.execute({"payer_id": payer_id}):
        return payment
    return None