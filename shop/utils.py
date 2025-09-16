from .models import Category, product, ProductStock
import json

def global_categories(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    return {
        'global_categories': categories
    }


def deduct_stock_for_order(order_instance):
    """Decrease ProductStock quantities based on an order's items_json.
    Safely handles missing variants and keeps product stock_status in sync.
    """
    try:
        items = json.loads(order_instance.items_json or '{}')
    except Exception:
        return
    for key, details in items.items():
        try:
            qty = int(details[0])
            color = details[3]
            size = details[4]
            pid_part = key.split('_')[0]
            pid = int(pid_part.replace('pr', ''))
        except Exception:
            continue

        prod = product.objects.filter(id=pid).first()
        if not prod:
            continue
        stock = ProductStock.objects.filter(product=prod, color=color, size=size).first()
        if not stock:
            continue
        stock.quantity = stock.quantity - qty if stock.quantity > qty else 0
        stock.save(update_fields=['quantity'])
        prod.update_stock_status_from_stocks()

