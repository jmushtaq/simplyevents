from django.urls import path

from . import views
from custom.order import views as order_views

urlpatterns = [
    path('api/hire-dates/', views.get_hire_dates, name='get_hire_dates'),
    path('api/hire-dates/set/', views.set_hire_dates, name='set_hire_dates'),
    path('api/hire-dates/clear/', views.clear_hire_dates, name='clear_hire_dates'),
    path('api/check-availability/', views.check_availability, name='check_availability'),
    
    # Staff search views
    path('admin/hire-search/', order_views.search_hires, name='hire_search'),
    path('admin/order/<str:order_number>/hires/', order_views.get_order_hires, name='order_hires'),
]