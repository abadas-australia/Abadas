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

    product_id = models.AutoField
    product_name = models.CharField(max_length=100)
    product_category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT, null=True, blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    product_desc = models.TextField()
    product_color = models.TextField()
    product_size = models.TextField()
    product_image_1 = models.ImageField(upload_to='product-images/')
    product_image_2 = models.ImageField(upload_to='product-images/')
    product_image_3 = models.ImageField(upload_to='product-images/')
    product_image_4 = models.ImageField(upload_to='product-images/')
    product_image_5 = models.ImageField(upload_to='product-images/')
    latest_arrival = models.CharField(max_length=3, choices=LATEST_ARRIVAL_CHOICES, default='no')

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


class order(models.Model):
    order_id = models.AutoField(primary_key=True)
    items_json =  models.CharField(max_length=5000)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    name = models.CharField(max_length=90)
    email = models.CharField(max_length=90)
    address1 = models.CharField(max_length=200)
    address2 = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=100)
    oid=models.CharField(max_length=150,blank=True)
    amountpaid=models.CharField(max_length=500,blank=True,null=True)
    paymentstatus=models.CharField(max_length=20,blank=True)
    phone = models.CharField(max_length=100,default="")
    payid_proof = models.ImageField(upload_to='payment-proofs/', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who placed the order (null for guest orders)")
    is_guest_order = models.BooleanField(default=False, help_text="True if this is a guest order")
    STATUS_CHOICES = [
        ("PLACED", "Placed"),
        ("CONFIRMED", "Confirmed"),
        ("REJECTED", "Rejected"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PLACED")

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

class orderUpdate(models.Model):
    update_id = models.AutoField(primary_key=True)
    order_id = models.IntegerField(default="")
    update_desc = models.CharField(max_length=5000)
    delivered=models.BooleanField(default=False)
    timestamp = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.update_desc[0:7] + "..."