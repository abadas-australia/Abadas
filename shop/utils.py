from .models import Category

def global_categories(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    return {
        'global_categories': categories
    }


