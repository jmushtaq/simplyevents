import logging
from urllib.parse import quote

from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import generic

from oscar.core.loading import get_class, get_classes, get_model

from . import signals

ShippingAddressForm, ShippingMethodForm, GatewayForm = get_classes(
    "checkout.forms", ["ShippingAddressForm", "ShippingMethodForm", "GatewayForm"]
)
UserAddressForm = get_class("address.forms", "UserAddressForm")
Repository = get_class("shipping.repository", "Repository")
RedirectRequired, UnableToTakePayment, PaymentError = get_classes(
    "payment.exceptions", ["RedirectRequired", "UnableToTakePayment", "PaymentError"])
UnableToPlaceOrder = get_class("order.exceptions", "UnableToPlaceOrder")
OrderPlacementMixin = get_class("checkout.mixins", "OrderPlacementMixin")
CheckoutSessionMixin = get_class("checkout.session", "CheckoutSessionMixin")
NoShippingRequired = get_class("shipping.methods", "NoShippingRequired")
Order = get_model("order", "Order")
ShippingAddress = get_model("order", "ShippingAddress")
UserAddress = get_model("address", "UserAddress")
Country = get_model("address", "Country")

logger = logging.getLogger("oscar.checkout")


class IndexView(CheckoutSessionMixin, generic.FormView):
    template_name = "oscar/checkout/gateway.html"
    form_class = GatewayForm
    success_url = reverse_lazy("checkout:shipping-address")
    pre_conditions = ["check_basket_is_not_empty", "check_basket_is_valid"]

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            signals.start_checkout.send_robust(sender=self, request=request)
            return self.get_success_response()
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        email = self.checkout_session.get_guest_email()
        if email:
            kwargs["initial"] = {"username": email}
        return kwargs

    def form_valid(self, form):
        if form.is_guest_checkout() or form.is_new_account_checkout():
            email = form.cleaned_data["username"]
            self.checkout_session.set_guest_email(email)
            signals.start_checkout.send_robust(sender=self, request=self.request, email=email)

            if form.is_new_account_checkout():
                messages.info(
                    self.request,
                    _("Create your account and then you will be redirected back to the checkout process"),
                )
                self.success_url = "%s?next=%s&email=%s" % (
                    reverse("customer:register"),
                    reverse("checkout:shipping-address"),
                    quote(email),
                )
        else:
            user = form.get_user()
            login(self.request, user)
            signals.start_checkout.send_robust(sender=self, request=self.request)

        return redirect(self.get_success_url())

    def get_success_response(self):
        return redirect(self.get_success_url())


class ShippingAddressView(CheckoutSessionMixin, generic.FormView):
    template_name = "oscar/checkout/shipping_address.html"
    form_class = ShippingAddressForm
    success_url = reverse_lazy("checkout:shipping-method")
    pre_conditions = [
        "check_basket_is_not_empty",
        "check_basket_is_valid",
        "check_user_email_is_captured",
    ]
    skip_conditions = ["skip_unless_basket_requires_shipping"]

    def get_initial(self):
        initial = self.checkout_session.new_shipping_address_fields()
        if initial:
            initial = initial.copy()
            try:
                initial["country"] = Country.objects.get(iso_3166_1_a2=initial.pop("country_id"))
            except Country.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            ctx["addresses"] = self.get_available_addresses()
        return ctx

    def get_available_addresses(self):
        return self.request.user.addresses.filter(
            country__is_shipping_country=True
        ).order_by("-is_default_for_shipping")

    def post(self, request, *args, **kwargs):
        if self.request.user.is_authenticated and "address_id" in self.request.POST:
            address = UserAddress._default_manager.get(
                pk=self.request.POST["address_id"], user=self.request.user
            )
            action = self.request.POST.get("action", None)
            if action == "ship_to":
                self.checkout_session.ship_to_user_address(address)
                return redirect(self.get_success_url())
            else:
                return http.HttpResponseBadRequest()
        else:
            return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        address_fields = dict(
            (k, v) for (k, v) in form.instance.__dict__.items() if not k.startswith("_")
        )
        self.checkout_session.ship_to_new_address(address_fields)
        return super().form_valid(form)


class UserAddressUpdateView(CheckoutSessionMixin, generic.UpdateView):
    template_name = "oscar/checkout/user_address_form.html"
    form_class = UserAddressForm
    success_url = reverse_lazy("checkout:shipping-address")

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.info(self.request, _("Address saved"))
        return super().get_success_url()


class UserAddressDeleteView(CheckoutSessionMixin, generic.DeleteView):
    template_name = "oscar/checkout/user_address_delete.html"
    success_url = reverse_lazy("checkout:shipping-address")

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_success_url(self):
        messages.info(self.request, _("Address deleted"))
        return super().get_success_url()


class ShippingMethodView(CheckoutSessionMixin, generic.FormView):
    template_name = "oscar/checkout/shipping_methods.html"
    form_class = ShippingMethodForm
    pre_conditions = [
        "check_basket_is_not_empty",
        "check_basket_is_valid",
        "check_user_email_is_captured",
    ]
    success_url = reverse_lazy("checkout:payment-method")

    def post(self, request, *args, **kwargs):
        self._methods = self.get_available_shipping_methods()
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not request.basket.is_shipping_required():
            self.checkout_session.use_shipping_method(NoShippingRequired().code)
            return self.get_success_response()

        if not self.checkout_session.is_shipping_address_set():
            messages.error(request, _("Please choose a shipping address"))
            return redirect("checkout:shipping-address")

        self._methods = self.get_available_shipping_methods()
        if len(self._methods) == 0:
            messages.warning(request, _("Shipping is unavailable for your chosen address"))
            return redirect("checkout:shipping-address")
        elif len(self._methods) == 1:
            self.checkout_session.use_shipping_method(self._methods[0].code)
            return self.get_success_response()

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["methods"] = self._methods
        return kwargs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["methods"] = self._methods
        return kwargs

    def get_available_shipping_methods(self):
        return Repository().get_shipping_methods(
            basket=self.request.basket,
            user=self.request.user,
            shipping_addr=self.get_shipping_address(self.request.basket),
            request=self.request,
        )

    def form_valid(self, form):
        self.checkout_session.use_shipping_method(form.cleaned_data["method_code"])
        return self.get_success_response()

    def form_invalid(self, form):
        messages.error(request, _("Your submitted shipping method is not permitted"))
        return super().form_invalid(form)

    def get_success_response(self):
        return redirect(self.get_success_url())


class PaymentMethodView(CheckoutSessionMixin, generic.TemplateView):
    pre_conditions = [
        "check_basket_is_not_empty",
        "check_basket_is_valid",
        "check_user_email_is_captured",
        "check_shipping_data_is_captured",
    ]
    skip_conditions = ["skip_unless_payment_is_required"]
    success_url = reverse_lazy("checkout:payment-details")

    def get(self, request, *args, **kwargs):
        return self.get_success_response()

    def get_success_response(self):
        return redirect(self.get_success_url())

    def get_success_url(self):
        return str(self.success_url)


class PaymentDetailsView(OrderPlacementMixin, generic.TemplateView):
    template_name = "oscar/checkout/payment_details.html"
    template_name_preview = "oscar/checkout/preview.html"

    pre_conditions = [
        "check_basket_is_not_empty",
        "check_basket_is_valid",
        "check_user_email_is_captured",
        "check_shipping_data_is_captured",
    ]

    preview = False

    def get_pre_conditions(self, request):
        if self.preview:
            return self.pre_conditions + ["check_payment_data_is_captured"]
        return super().get_pre_conditions(request)

    def get_skip_conditions(self, request):
        if not self.preview:
            return ["skip_unless_payment_is_required"]
        return super().get_skip_conditions(request)

    def post(self, request, *args, **kwargs):
        if not self.preview:
            return http.HttpResponseBadRequest()

        if request.POST.get("action", "") == "place_order":
            return self.handle_place_order_submission(request)
        return self.handle_payment_details_submission(request)

    def handle_place_order_submission(self, request):
        return self.submit(**self.build_submission())

    def handle_payment_details_submission(self, request):
        return self.render_preview(request)

    def render_preview(self, request, **kwargs):
        self.preview = True
        ctx = self.get_context_data(**kwargs)
        return self.render_to_response(ctx)

    def render_payment_details(self, request, **kwargs):
        self.preview = False
        ctx = self.get_context_data(**kwargs)
        return self.render_to_response(ctx)

    def get_default_billing_address(self):
        if not self.request.user.is_authenticated:
            return None
        try:
            return self.request.user.addresses.get(is_default_for_billing=True)
        except UserAddress.DoesNotExist:
            return None

    def submit(
        self,
        user,
        basket,
        shipping_address,
        shipping_method,
        shipping_charge,
        billing_address,
        order_total,
        payment_kwargs=None,
        order_kwargs=None,
        surcharges=None,
    ):
        if payment_kwargs is None:
            payment_kwargs = {}
        if order_kwargs is None:
            order_kwargs = {}

        assert basket.is_tax_known, "Basket tax must be set"
        assert shipping_charge.is_tax_known, "Shipping charge tax must be set"

        order_number = self.generate_order_number(basket)
        self.checkout_session.set_order_number(order_number)
        logger.info("Order #%s: beginning submission for basket #%d", order_number, basket.id)

        self.freeze_basket(basket)
        self.checkout_session.set_submitted_basket(basket)

        error_msg = _("A problem occurred while processing payment")

        signals.pre_payment.send_robust(sender=self, view=self)

        try:
            self.handle_payment(order_number, order_total, **payment_kwargs)
        except RedirectRequired as e:
            logger.info("Order #%s: redirecting to %s", order_number, e.url)
            return http.HttpResponseRedirect(e.url)
        except UnableToTakePayment as e:
            msg = str(e)
            logger.warning("Order #%s: unable to take payment (%s)", order_number, msg)
            self.restore_frozen_basket()
            return self.render_payment_details(self.request, error=msg, **payment_kwargs)
        except PaymentError as e:
            msg = str(e)
            logger.error("Order #%s: payment error (%s)", order_number, msg, exc_info=True)
            self.restore_frozen_basket()
            return self.render_preview(self.request, error=error_msg, **payment_kwargs)
        except Exception as e:
            logger.exception("Order #%s: unhandled exception while taking payment (%s)", order_number, e)
            self.restore_frozen_basket()
            return self.render_preview(self.request, error=error_msg, **payment_kwargs)

        signals.post_payment.send_robust(sender=self, view=self)

        logger.info("Order #%s: payment successful, placing order", order_number)
        try:
            return self.handle_order_placement(
                order_number,
                user,
                basket,
                shipping_address,
                shipping_method,
                shipping_charge,
                billing_address,
                order_total,
                surcharges=surcharges,
                **order_kwargs,
            )
        except UnableToPlaceOrder as e:
            msg = str(e)
            logger.error("Order #%s: unable to place order - %s", order_number, msg, exc_info=True)
            self.restore_frozen_basket()
            return self.render_preview(self.request, error=msg, **payment_kwargs)
        except Exception as e:
            logger.exception("Order #%s: unhandled exception while placing order (%s)", order_number, e)
            error_msg = _("A problem occurred while placing this order.")
            self.restore_frozen_basket()
            return self.render_preview(self.request, error=error_msg, **payment_kwargs)

    def get_template_names(self):
        return [self.template_name_preview] if self.preview else [self.template_name]


class ThankYouView(generic.DetailView):
    template_name = "oscar/checkout/thank_you.html"
    context_object_name = "order"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return redirect(settings.OSCAR_HOMEPAGE)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_object(self, queryset=None):
        order = None
        if self.request.user.is_superuser:
            kwargs = {}
            if "order_number" in self.request.GET:
                kwargs["number"] = self.request.GET["order_number"]
            elif "order_id" in self.request.GET:
                kwargs["id"] = self.request.GET["order_id"]
            if any(kwargs):
                order = Order._default_manager.filter(**kwargs).first()

        if not order:
            if "checkout_order_id" in self.request.session:
                order = Order._default_manager.filter(
                    pk=self.request.session["checkout_order_id"]
                ).first()
        return order

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if not ctx["order"].analytics_tracked:
            ctx["send_analytics_event"] = True
            ctx["order"].analytics_tracked = True
            ctx["order"].save(update_fields=["analytics_tracked"])
        else:
            ctx["send_analytics_event"] = False

        return ctx


# =========
# PayPal Payment
# =========

def paypal_initiate(request):
    """Initiate PayPal payment"""
    basket = request.basket
    
    logger.info("PayPalInitiate: basket=%s", basket)
    
    if not basket or basket.is_empty():
        messages.error(request, _("Your basket is empty"))
        return redirect('basket:summary')
    
    from custom.payment.paypal import configure_paypal, create_payment
    configure_paypal()
    
    return_url = request.build_absolute_uri(reverse('checkout:paypal-return'))
    cancel_url = request.build_absolute_uri(reverse('checkout:paypal-cancel'))
    
    logger.info("Creating PayPal payment for basket %s", basket.pk)
    
    payment = create_payment(basket, return_url, cancel_url)
    
    try:
        if payment.create():
            logger.info("PayPal payment created: %s", payment.id)
            for link in payment.links:
                if link.rel == 'approval_url':
                    request.session['paypal_payment_id'] = payment.id
                    logger.info("Redirecting to PayPal: %s", link.href)
                    return HttpResponseRedirect(link.href)
        else:
            logger.error("PayPal payment create failed: %s", payment.error)
            messages.error(request, _("PayPal error: %s") % payment.error)
    except Exception as e:
        logger.exception("PayPal error: %s", e)
        messages.error(request, _("PayPal error: %s") % str(e))
    
    return redirect('checkout:payment-details')


class PayPalReturnView(generic.TemplateView):
    """Handle PayPal return"""
    
    template_name = "oscar/checkout/paypal_return.html"
    
    def get(self, request, *args, **kwargs):
        payment_id = request.GET.get('paymentId')
        payer_id = request.GET.get('PayerID')
        
        if not payment_id or not payer_id:
            messages.error(request, _("PayPal payment failed"))
            return redirect('checkout:payment-details')
        
        from custom.payment.paypal import execute_payment
        
        payment = execute_payment(payment_id, payer_id)
        
        if payment:
            request.session['paypal_payment_id'] = payment_id
            return redirect('checkout:preview')
        
        messages.error(request, _("PayPal payment execution failed"))
        return redirect('checkout:payment-details')


class PayPalCancelView(generic.TemplateView):
    """Handle PayPal cancellation"""
    
    def get(self, request, *args, **kwargs):
        messages.info(request, _("PayPal payment was cancelled"))
        return redirect('checkout:payment-details')