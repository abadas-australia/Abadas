from django.shortcuts import render, redirect, get_object_or_404
from shop.models import product, order, Category, ShippingOption
from math import ceil
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import order
import paypalrestsdk
from paypalrestsdk import Payment as PayPalPayment

def shop(request, category=None):
    allProds = []

    if category:
        category_obj = Category.objects.filter(slug=category, is_active=True).first()
        if not category_obj:
            cat = category.replace("-", " ").title()
            return render(request, "shop.html", {
                'message': f"No products available in the '{cat}' category. Please check back later!"
            })
        prod = product.objects.filter(product_category=category_obj)
        if prod.exists():
            n = len(prod)
            nSlides = n // 4 + ceil((n / 4) - (n // 4))
            allProds.append([prod, range(1, nSlides), nSlides])
        else:
            cat = category.replace("-", " ").title()
            return render(request, "shop.html", {
                'message': f"No products available in the '{cat}' category. Please check back later!"
            })
    else:
        categories = Category.objects.filter(is_active=True)
        for cat in categories:
            prod = product.objects.filter(product_category=cat)
            n = len(prod)
            nSlides = n // 4 + ceil((n / 4) - (n // 4))
            allProds.append([prod, range(1, nSlides), nSlides])
    
    data = {
        'allProds': allProds,
        'message': None if allProds else "No products available at the moment. Please check back later!"
    }
    return render(request, "shop.html", data)

def productDetails(request, id):
    prod = get_object_or_404(product, id=id)
    colors = prod.product_color.split(",")
    sizes = prod.product_size.split(",")

    data = {
        'product': prod,
        'colors': colors,
        'sizes': sizes,
    }
    return render(request, "quickview.html", data)


def checkout(request):
    if request.method == "POST":
        # Common data
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = float(request.POST.get('amt'))  # Convert to float (includes shipping)
        email = request.POST.get('email', '')
        address1 = request.POST.get('address1', '')
        address2 = request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        payment_method = request.POST.get('payment_method', '')  # New field
        shipping_method = request.POST.get('shipping_method', '')
        shipping_cost = request.POST.get('shipping_cost', '0')


        # Create an order instance
        order_instance = order.objects.create(
            items_json=items_json,
            amount=amount,
            name=name,
            email=email,
            address1=address1,
            address2=address2,
            city=city,
            state=state,
            zip_code=zip_code,
            phone=phone,
            user=request.user if request.user.is_authenticated else None,
            is_guest_order=not request.user.is_authenticated,
            shipping_method=shipping_method,
            shipping_cost=shipping_cost or 0,
        )
        request.session['order_id'] = order_instance.order_id

        if payment_method == 'paypal':
            # PayPal integration
            paypalrestsdk.configure({
                "mode": "live",  # or "live"
                "client_id": settings.PAYPAL_CLIENT_ID,
                "client_secret": settings.PAYPAL_CLIENT_SECRET
            })

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": request.build_absolute_uri('/shop/payment/success/'),
                    "cancel_url": request.build_absolute_uri('/shop/payment/cancel/')
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"Order #{order_instance.order_id}",
                            "sku": f"{order_instance.order_id}",
                            "price": amount,
                            "currency": "USD",
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": "USD"
                    },
                    "description": f"Order #{order_instance.order_id}"
                }]
            })

            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)
            else:
                messages.error(request, f"Your cart is empty. Please add items to the cart before placing the order.")
                return redirect('/shop/')
        elif payment_method == 'payid':
            # Customer pays externally and uploads proof
            uploaded = request.FILES.get('payid_proof')
            if uploaded:
                order_instance.payid_proof = uploaded
            order_instance.paymentstatus = "PayID"
            order_instance.save()

            send_order_placed_email(order_instance)
            send_admin_order_notification(order_instance)
            messages.success(request, "Your order has been placed. We'll review your PayID proof shortly.")
            return render(request, 'payment_success.html')
    

    # Get active shipping options
    shipping_options = ShippingOption.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,
        'shipping_options': shipping_options,
    }
    return render(request, 'checkout.html', context)


@csrf_exempt
def payment_success(request):
    
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, "Order ID not found in session.")
        return redirect('shop')

    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    order_instance = get_object_or_404(order, order_id=order_id)

    if payment_id and payer_id:  # PayPal payment
        try:
            payment = PayPalPayment.find(payment_id)
            if payment.execute({"payer_id": payer_id}):
                order_instance.paymentstatus = "Paid"
                order_instance.oid = payment_id
                order_instance.amountpaid = order_instance.amount
                order_instance.save()


                send_order_placed_email(order_instance)
                send_admin_order_notification(order_instance)
                return render(request, 'payment_success.html')

        except Exception as e:
            print("Error processing PayPal payment:", e)
            messages.error(request, "An error occurred during payment processing.")
            return redirect('shop')
    
    else:
        try:
            # Retrieve form data
            transaction_id = request.POST.get('transaction_id')
            items_json = request.POST.get('items_json')
            amount = request.POST.get('amount')  # From form
            amount_paid = request.POST.get('amount_paid')  # From PayPal
            name = request.POST.get('name')
            email = request.POST.get('email')
            address1 = request.POST.get('address1')
            address2 = request.POST.get('address2')
            city = request.POST.get('city')
            state = request.POST.get('state')
            zip_code = request.POST.get('zip_code')
            phone = request.POST.get('phone')
            shipping_method = request.POST.get('shipping_method', '')
            shipping_cost = request.POST.get('shipping_cost', '0')


            new_order = order(
                items_json=items_json,
                amount=amount,
                name=name,
                email=email,  # Save email
                address1=address1,
                address2=address2,
                city=city,
                state=state,
                zip_code=zip_code,
                oid=transaction_id,
                amountpaid=amount_paid,  # Save amount paid
                paymentstatus="Success",
                phone=phone,
                user=request.user if request.user.is_authenticated else None,
                is_guest_order=not request.user.is_authenticated,
                shipping_method=shipping_method,
                shipping_cost=shipping_cost or 0,
            )
            new_order.save()
            send_order_placed_email(new_order)
            send_admin_order_notification(new_order)

            return render(request, 'payment_success.html', {'order': new_order})

        except Exception as e:
            return render(request, 'payment_success.html', {'order': new_order})


def send_order_placed_email(order_instance):
    subject = "Order Placed"
    message = render_to_string('order-confirmation-email.html', {
        'customer_name': order_instance.name,
        'order_id': order_instance.order_id,
        'amount': order_instance.amount,
        'payment_status': order_instance.paymentstatus,
        'order_items': order_instance.formatted_items(),
    })
    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [order_instance.email])
    email.content_subtype = "html"
    email.send()


def send_admin_order_notification(order_instance):
    """Send email notification to admin when a new order is placed"""
    admin_email = "abadasaustralia@gmail.com"
    
    # Get payment proof URL if it exists
    payment_proof_url = None
    if order_instance.payid_proof:
        payment_proof_url = order_instance.payid_proof.url
    
    # Determine user type
    user_type = "Registered User" if order_instance.user else "Guest User"
    
    # Get order date
    from django.utils import timezone
    
    subject = f"New Order Notification - Order #{order_instance.order_id}"
    message = render_to_string('admin-order-notification-email.html', {
        'order_id': order_instance.order_id,
        'amount': order_instance.amount,
        'payment_status': order_instance.paymentstatus or "Pending",
        'order_status': order_instance.status,
        'customer_name': order_instance.name,
        'customer_email': order_instance.email,
        'customer_phone': order_instance.phone,
        'user_type': user_type,
        'address1': order_instance.address1,
        'address2': order_instance.address2,
        'city': order_instance.city,
        'state': order_instance.state,
        'zip_code': order_instance.zip_code,
        'order_items': order_instance.formatted_items(),
        'payment_proof_url': payment_proof_url,
        'admin_url': f"https://abadas.vercel.app/abadas-admin/shop/order/{order_instance.order_id}/change/",
    })
    
    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [admin_email])
    email.content_subtype = "html"
    email.send()


def payment_cancel(request):
    return render(request, 'payment_cancel.html')

    
