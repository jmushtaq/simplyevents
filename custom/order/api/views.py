from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from datetime import datetime

@require_http_methods(["GET"])
def get_hire_dates(request):
    """Get currently stored hire dates from session"""
    return JsonResponse({
        'start_date': request.session.get('hire_start_date'),
        'end_date': request.session.get('hire_end_date')
    })

@csrf_exempt
@require_http_methods(["POST"])
def set_hire_dates(request):
    """Store hire dates in session"""
    try:
        data = json.loads(request.body)
        request.session['hire_start_date'] = data.get('start_date')
        request.session['hire_end_date'] = data.get('end_date')
        request.session.modified = True
        return JsonResponse({'status': 'ok', 'start': data.get('start_date'), 'end': data.get('end_date')})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def clear_hire_dates(request):
    """Clear hire dates from session"""
    request.session.pop('hire_start_date', None)
    request.session.pop('hire_end_date', None)
    return JsonResponse({'status': 'ok'})

@require_http_methods(["GET"])
def check_availability(request):
    """Check product availability for hire dates"""
    product_id = request.GET.get('product_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([product_id, start_date, end_date]):
        return JsonResponse({
            'available': False, 
            'message': 'Missing required parameters'
        }, status=400)
    
    # Import availability checker
    from custom.order.services import is_product_available_for_hire
    
    from oscar.apps.catalogue.models import Product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({
            'available': False, 
            'message': 'Product not found'
        }, status=404)
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        return JsonResponse({
            'available': False, 
            'message': 'Invalid date format'
        }, status=400)
    
    available, message = is_product_available_for_hire(product, start, end)
    
    return JsonResponse({
        'available': available,
        'message': message
    })