from django.db import models
from django.utils.html import format_html
from django.contrib.auth.models import User
import json
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    image = models.ImageField(upload_to='category-images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class product(models.Model):
    LATEST_ARRIVAL_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]
    
    STOCK_STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    product_id = models.AutoField
    product_name = models.CharField(max_length=100)
    product_category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT, null=True, blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product_desc = models.TextField()
    # Kept for backward compatibility with existing data entry; now optional.
    # New stock tracking uses ProductStock rows below.
    product_color = models.TextField(blank=True, default="")
    product_size = models.TextField(blank=True, default="")
    product_image_1 = models.ImageField(upload_to='product-images/')
    product_image_2 = models.ImageField(upload_to='product-images/')
    product_image_3 = models.ImageField(upload_to='product-images/')
    product_image_4 = models.ImageField(upload_to='product-images/')
    product_image_5 = models.ImageField(upload_to='product-images/')
    latest_arrival = models.CharField(max_length=3, choices=LATEST_ARRIVAL_CHOICES, default='no')
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default='in_stock')

    def save(self, *args, **kwargs):
        for image_field in ['product_image_1', 'product_image_2', 'product_image_3', 'product_image_4', 'product_image_5']:
            image = getattr(self, image_field)
            if image and not image.closed:
                img = Image.open(image)
                img = img.convert("RGB")
                output = BytesIO()
                
                max_size = (1080, 1080)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                img.save(output, format='JPEG', quality=100)
                output.seek(0)
                setattr(self, image_field, ContentFile(output.read(), image.name))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.product_name

    def total_stock_quantity(self):
        total = sum(
            s.quantity for s in getattr(self, 'stocks', []).all()
        ) if hasattr(self, 'stocks') else sum(
            s.quantity for s in ProductStock.objects.filter(product=self)
        )
        return total

    def update_stock_status_from_stocks(self):
        total = self.total_stock_quantity()
        new_status = 'out_of_stock' if total <= 0 else 'in_stock'
        if self.stock_status != new_status:
            self.stock_status = new_status
            self.save(update_fields=['stock_status'])


class ProductStock(models.Model):
    SIZE_MAX_LEN = 20
    COLOR_MAX_LEN = 30

    product = models.ForeignKey(product, on_delete=models.CASCADE, related_name='stocks')
    size = models.CharField(max_length=SIZE_MAX_LEN)
    color = models.CharField(max_length=COLOR_MAX_LEN)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size", "color")
        verbose_name = "Product Stock"
        verbose_name_plural = "Product Stock"

    def __str__(self):
        return f"{self.product.product_name} - {self.color}/{self.size} ({self.quantity})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After saving, update parent product stock status
        self.product.update_stock_status_from_stocks()


class order(models.Model):
    order_id = models.AutoField(primary_key=True)
    items_json =  models.CharField(max_length=5000)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    name = models.CharField("Name", max_length=90)
    email = models.CharField("Email", max_length=90)
    address1 = models.CharField("Address 1", max_length=200)
    address2 = models.CharField("Address 2", max_length=200)
    city = models.CharField("Suburb", max_length=100)
    state = models.CharField("State", max_length=100)
    zip_code = models.CharField("Post Code", max_length=100)
    oid=models.CharField("Order Id", max_length=150, blank=True)
    amountpaid=models.CharField("Amount Paid", max_length=500, blank=True, null=True)
    paymentstatus=models.CharField("Payment Status", max_length=20, blank=True)
    phone = models.CharField("Phone", max_length=100, default="")
    payid_proof = models.ImageField("PayID Proof", upload_to='payment-proofs/', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who placed the order (null for guest orders)")
    is_guest_order = models.BooleanField("Guest Order", default=False, help_text="True if this is a guest order")
    shipping_method = models.CharField("Shipping Method", max_length=50, blank=True, help_text="Selected shipping method")
    shipping_cost = models.DecimalField("Shipping Cost", max_digits=10, decimal_places=2, default=0.00, help_text="Shipping cost applied")
    STATUS_CHOICES = [
        ("PLACED", "Placed"),
        ("CONFIRMED", "Confirmed"),
        ("REJECTED", "Rejected"),
    ]
    status = models.CharField("Status", max_length=10, choices=STATUS_CHOICES, default="PLACED")

    def formatted_items(self):
        try:
            items = json.loads(self.items_json)  # Parse items_json
            formatted = ""
            for item_id, details in items.items():
                qty, name, price, color, size, image_url = details
                formatted += f"""
                    <div>
                        <strong>Product Name:</strong> {name}<br>
                        <strong>Quantity:</strong> {qty}<br>
                        <strong>Price:</strong> ${price}<br>
                        <strong>Color:</strong> {color}<br>
                        <strong>Size:</strong> {size}<br>
                        <img src="{image_url}" alt="{name}" style="width: 50px; height: 50px;"/><br><br>
                    </div>
                """
            return format_html(formatted)
        except (ValueError, KeyError, TypeError):
            return "Invalid items format"

    formatted_items.short_description = "Order Details"

    def __str__(self):
        return self.name

class ShippingOption(models.Model):
    name = models.CharField(max_length=100, help_text="Shipping method name (e.g., 'Regular Post', 'Express Post')")
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Shipping cost in dollars")
    description = models.CharField(max_length=200, blank=True, help_text="Optional description for the shipping method")
    is_active = models.BooleanField(default=True, help_text="Whether this shipping option is available")
    is_default = models.BooleanField(default=False, help_text="Whether this is the default selected option")
    sort_order = models.PositiveIntegerField(default=0, help_text="Order in which options appear (lower numbers first)")

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Shipping Option"
        verbose_name_plural = "Shipping Options"

    def __str__(self):
        return f"{self.name} - ${self.cost}"

    def save(self, *args, **kwargs):
        # Ensure only one default option
        if self.is_default:
            ShippingOption.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class orderUpdate(models.Model):
    update_id = models.AutoField(primary_key=True)
    order_id = models.IntegerField(default="")
    update_desc = models.CharField(max_length=5000)
    delivered=models.BooleanField(default=False)
    timestamp = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.update_desc[0:7] + "..."