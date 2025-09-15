from django.shortcuts import render, redirect
from contact.models import contact
from shop.models import product, order
import json
from django.db.models import Case, When
from math import ceil
from django.db.models import Q
from django.http import JsonResponse

def index(request, category=None):
    # Get search query from request
    search_query = request.GET.get('search', '')
    data = {}

    # Counts for each category (by slug via ForeignKey)
    drop_shoulders_count = product.objects.filter(product_category__slug='drop-shoulders').count()
    baggy_joggers_count = product.objects.filter(product_category__slug='baggy-joggers').count()
    baggy_shirts_count = product.objects.filter(product_category__slug='baggy-shirts').count()
    cargo_pants_count = product.objects.filter(product_category__slug='cargo-pants').count()
    head_wear_count = product.objects.filter(product_category__slug='head-wear').count()
    baggy_shorts_count = product.objects.filter(product_category__slug='baggy-shorts').count()

    # Latest arrivals
    latest_arrivals = product.objects.filter(latest_arrival='yes')

    # Trending products
    product_counts = {}
    for ord in order.objects.all():
        items = json.loads(ord.items_json)
        for product_code, details in items.items():
            product_counts[product_code] = product_counts.get(product_code, 0) + details[0]

    top_product_codes = sorted(product_counts, key=product_counts.get, reverse=True)[:6]
    order_by_case = Case(*[When(id=int(code.split('_')[0][2:]), then=pos) for pos, code in enumerate(top_product_codes)])
    trending_products = product.objects.filter(id__in=[int(code.split('_')[0][2:]) for code in top_product_codes]).order_by(order_by_case)

    # Filtered Products
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and search_query:
        matching_products = product.objects.filter(
            Q(product_name__icontains=search_query)
        )

        results = []
        for p in matching_products:
            results.append({
                'id': p.id,
                'product_name': p.product_name,
                'product_price': str(p.product_price),
                'product_image_url': p.product_image_1.url if p.product_image_1 else '',
                'stock_status': p.stock_status,
            })

        data = {'results': results}
        return JsonResponse(data)

    data = {
        'drop_shoulders_count': drop_shoulders_count,
        'baggy_joggers_count': baggy_joggers_count,
        'baggy_shirts_count': baggy_shirts_count,
        'cargo_pants_count': cargo_pants_count,
        'head_wear_count': head_wear_count,
        'baggy_shorts_count': baggy_shorts_count,
        'latest_arrivals': latest_arrivals,
        'trending_products': trending_products,
    }

    return render(request, "index.html", data)

def aboutUs(request):
    return render(request, "about.html")

def contactUs(request):
    if request.method == 'POST':
       
        data = contact(
            contact_name = request.POST.get('contact-name'),
            contact_email = request.POST.get('contact-email'),
            contact_subject = request.POST.get('contact-subject'),
            contact_message = request.POST.get('contact-message'),
        )
        data.save()
        return redirect('/')
    
    return render(request, "contact.html")

def developer(request):
    return render(request, "developer.html")