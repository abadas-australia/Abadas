from django.contrib import admin
from shop.models import product, order, orderUpdate, Category
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.shortcuts import redirect
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings

@admin.register(product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_category', 'product_price', 'stock_status', 'latest_arrival')
    list_filter = ('product_category', 'stock_status', 'latest_arrival')
    search_fields = ('product_name', 'product_desc')
    list_editable = ('stock_status',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'product_category', 'product_price', 'product_desc')
        }),
        ('Product Details', {
            'fields': ('product_color', 'product_size', 'stock_status', 'latest_arrival')
        }),
        ('Images', {
            'fields': ('product_image_1', 'product_image_2', 'product_image_3', 'product_image_4', 'product_image_5')
        }),
    )

# admin.site.register(orderUpdate)

class orderAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'status', 'formatted_items', 'confirm_action', 'reject_action')
    readonly_fields = ('formatted_items', 'payid_proof_preview')
    list_filter = ('is_guest_order', 'status', 'paymentstatus')
    search_fields = ('email', 'name', 'order_id')

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/confirm/', self.admin_site.admin_view(self.process_confirm), name='shop_order_confirm'),
            path('<int:order_id>/reject/', self.admin_site.admin_view(self.process_reject), name='shop_order_reject'),
        ]
        return custom_urls + urls

    def confirm_action(self, obj):
        if obj.status != 'CONFIRMED':
            url = reverse('admin:shop_order_confirm', args=[obj.order_id])
            return format_html('<a class="button" href="{}">Confirm</a>', url)
        return '—'
    confirm_action.short_description = 'Confirm'

    def reject_action(self, obj):
        if obj.status != 'REJECTED':
            url = reverse('admin:shop_order_reject', args=[obj.order_id])
            return format_html('<a class="button" href="{}" style="color:#c00;">Reject</a>', url)
        return '—'
    reject_action.short_description = 'Reject'

    def payid_proof_thumb(self, obj):
        if getattr(obj, 'payid_proof', None):
            return format_html('<img src="{}" style="height:48px;width:auto;border-radius:4px;"/>', obj.payid_proof.url)
        return '—'
    payid_proof_thumb.short_description = 'PayID Proof'

    def payid_proof_preview(self, obj):
        if getattr(obj, 'payid_proof', None):
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height:300px;width:auto;border:1px solid #ddd;border-radius:6px;"/></a>', obj.payid_proof.url)
        return 'No proof uploaded'

    def process_confirm(self, request, order_id, *args, **kwargs):
        try:
            obj = order.objects.get(order_id=order_id)
            obj.status = 'CONFIRMED'
            obj.save(update_fields=['status'])
            self._send_order_confirmed_email(obj)
            self.message_user(request, f"Order #{order_id} confirmed and email sent.", level=messages.SUCCESS)
        except order.DoesNotExist:
            self.message_user(request, f"Order #{order_id} not found.", level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:shop_order_changelist')))

    def process_reject(self, request, order_id, *args, **kwargs):
        try:
            obj = order.objects.get(order_id=order_id)
            obj.status = 'REJECTED'
            obj.save(update_fields=['status'])
            self._send_order_rejected_email(obj)
            self.message_user(request, f"Order #{order_id} rejected and email sent.", level=messages.WARNING)
        except order.DoesNotExist:
            self.message_user(request, f"Order #{order_id} not found.", level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', reverse('admin:shop_order_changelist')))

    def _send_order_confirmed_email(self, order_instance):
        subject = "Order Confirmed"
        message = render_to_string('order-confirmed-email.html', {
            'customer_name': order_instance.name,
            'order_id': order_instance.order_id,
            'amount': order_instance.amount,
            'payment_status': order_instance.paymentstatus,
            'order_items': order_instance.formatted_items(),
        })
        email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [order_instance.email])
        email.content_subtype = "html"
        email.send()

    def _send_order_rejected_email(self, order_instance):
        subject = "Order Rejected"
        message = render_to_string('order-rejected-email.html', {
            'customer_name': order_instance.name,
            'order_id': order_instance.order_id,
            'amount': order_instance.amount,
            'payment_status': order_instance.paymentstatus,
            'order_items': order_instance.formatted_items(),
        })
        email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [order_instance.email])
        email.content_subtype = "html"
        email.send()

admin.site.register(order, orderAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}

# Register your models here.
