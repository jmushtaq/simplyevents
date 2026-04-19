from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q

@staff_member_required
def search_hires(request):
    """
    Search hires by user email or product name
    """
    search_type = request.GET.get('type', 'email')
    query = request.GET.get('q', '')
    
    # Try to import - may fail if models not created yet
    try:
        from custom.order.models import HirePeriod
        
        if search_type == 'email':
            # Search by user email
            hires = HirePeriod.objects.filter(
                Q(order_line__order__guest_email__icontains=query) |
                Q(order_line__order__user__email__icontains=query)
            ).select_related('order_line', 'order_line__product', 'order_line__order').order_by('-created_at')[:50]
        elif search_type == 'product':
            # Search by product name
            hires = HirePeriod.objects.filter(
                order_line__product__title__icontains=query
            ).select_related('order_line', 'order_line__product', 'order_line__order').order_by('-created_at')[:50]
        else:
            hires = []
        
        return render(request, 'admin/hire_search_results.html', {
            'hires': hires,
            'search_type': search_type,
            'query': query
        })
    except ImportError:
        return render(request, 'admin/hire_search_results.html', {
            'hires': [],
            'search_type': search_type,
            'query': query,
            'error': 'HirePeriod model not available. Please run migrations.'
        })


@staff_member_required
def get_order_hires(request, order_number):
    """
    Get all hire periods for a specific order
    """
    try:
        from custom.order.models import HirePeriod
        from oscar.apps.order.models import Order
        
        try:
            order = Order.objects.get(number=order_number)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        hires = HirePeriod.objects.filter(
            order_line__order=order
        ).select_related('order_line', 'order_line__product')
        
        data = [{
            'id': h.id,
            'product': h.order_line.product.title if h.order_line.product else h.order_line.title,
            'start_date': h.start_date.isoformat() if h.start_date else None,
            'end_date': h.end_date.isoformat() if h.end_date else None,
            'confirmed_start': h.confirmed_start.isoformat() if h.confirmed_start else None,
            'confirmed_end': h.confirmed_end.isoformat() if h.confirmed_end else None,
            'duration_days': h.duration_days if hasattr(h, 'duration_days') else None,
        } for h in hires]
        
        return JsonResponse({'hires': data})
    except ImportError:
        return JsonResponse({'error': 'Model not available'}, status=500)