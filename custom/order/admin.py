from django.contrib import admin

from oscar.core.loading import get_model

Order = get_model("order", "Order")
OrderNote = get_model("order", "OrderNote")
OrderStatusChange = get_model("order", "OrderStatusChange")
CommunicationEvent = get_model("order", "CommunicationEvent")
BillingAddress = get_model("order", "BillingAddress")
ShippingAddress = get_model("order", "ShippingAddress")
Line = get_model("order", "Line")
LinePrice = get_model("order", "LinePrice")
ShippingEvent = get_model("order", "ShippingEvent")
ShippingEventType = get_model("order", "ShippingEventType")
PaymentEvent = get_model("order", "PaymentEvent")
PaymentEventType = get_model("order", "PaymentEventType")
PaymentEventQuantity = get_model("order", "PaymentEventQuantity")
LineAttribute = get_model("order", "LineAttribute")
OrderDiscount = get_model("order", "OrderDiscount")
Surcharge = get_model("order", "Surcharge")

# Try to import HirePeriod - it may not exist if models haven't been created yet
try:
    HirePeriod = get_model("order", "HirePeriod")
except Exception:
    HirePeriod = None


class LineInline(admin.TabularInline):
    model = Line
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = [
        "user",
        "billing_address",
        "shipping_address",
    ]
    list_display = (
        "number",
        "total_incl_tax",
        "site",
        "user",
        "billing_address",
        "date_placed",
    )
    readonly_fields = (
        "number",
        "basket",
        "total_incl_tax",
        "total_excl_tax",
        "shipping_incl_tax",
        "shipping_excl_tax",
    )
    inlines = [LineInline]


class LineAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "stockrecord", "quantity")


class LinePriceAdmin(admin.ModelAdmin):
    list_display = ("order", "line", "price_incl_tax", "quantity")


class ShippingEventTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)


class PaymentEventQuantityInline(admin.TabularInline):
    model = PaymentEventQuantity
    extra = 0


class PaymentEventAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "event_type",
        "amount",
        "num_affected_lines",
        "date_created",
    )
    inlines = [PaymentEventQuantityInline]


class PaymentEventTypeAdmin(admin.ModelAdmin):
    pass


class OrderDiscountAdmin(admin.ModelAdmin):
    readonly_fields = (
        "order",
        "category",
        "offer_id",
        "offer_name",
        "voucher_id",
        "voucher_code",
        "amount",
    )
    list_display = ("order", "category", "offer", "voucher", "voucher_code", "amount")


class SurchargeAdmin(admin.ModelAdmin):
    raw_id_fields = ("order",)


admin.site.register(Order, OrderAdmin)
admin.site.register(OrderNote)
admin.site.register(OrderStatusChange)
admin.site.register(ShippingAddress)
admin.site.register(Line, LineAdmin)
admin.site.register(LinePrice, LinePriceAdmin)
admin.site.register(ShippingEvent)
admin.site.register(ShippingEventType, ShippingEventTypeAdmin)
admin.site.register(PaymentEvent, PaymentEventAdmin)
admin.site.register(PaymentEventType, PaymentEventTypeAdmin)
admin.site.register(LineAttribute)
admin.site.register(OrderDiscount, OrderDiscountAdmin)
admin.site.register(CommunicationEvent)
admin.site.register(BillingAddress)
admin.site.register(Surcharge, SurchargeAdmin)

# Hire Period Admin - for event hire system
if HirePeriod:
    class HirePeriodAdmin(admin.ModelAdmin):
        list_display = ('order_line', 'start_date', 'end_date', 'confirmed_start', 'confirmed_end', 'created_at')
        list_filter = ('start_date', 'end_date')
        search_fields = ('order_line__product__title', 'order_line__order__guest_email', 'order_line__order__number')
        date_hierarchy = 'created_at'
        
        fieldsets = (
            ('Hire Period', {
                'fields': ('order_line', 'start_date', 'end_date')
            }),
            ('Staff Override (Special Requests)', {
                'fields': ('confirmed_start', 'confirmed_end', 'modified_by'),
                'classes': ('collapse',)
            }),
            ('Metadata', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
        
        readonly_fields = ('created_at', 'updated_at')
        
        def save_model(self, request, obj, form, change):
            if change and (obj.confirmed_start or obj.confirmed_end):
                obj.modified_by = request.user
            super().save_model(request, obj, form, change)

    admin.site.register(HirePeriod, HirePeriodAdmin)
