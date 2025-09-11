from django.contrib import admin
from shop.models import product, order, orderUpdate, Category

admin.site.register(product)
# admin.site.register(orderUpdate)

class orderAdmin(admin.ModelAdmin):
    list_display = ('email', 'formatted_items')
    readonly_fields = ('formatted_items',)

admin.site.register(order, orderAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}

# Register your models here.
