from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Vendor(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_profile',
    )

    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    number_of_employee = models.PositiveIntegerField(default=1)

    gst_number = models.CharField(max_length=15, unique=True)
    gst_image = models.ImageField(
        upload_to='vendors/gst_images/',
        blank=True,
        null=True,
    )

    pan_card_number = models.CharField(max_length=50, unique=True)
    pan_card_image = models.ImageField(
        upload_to='vendors/pan_card_images/',
        blank=True,
        null=True,
    )

    mobile_number = models.CharField(max_length=15, unique=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendors',
    )

    vendor_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or self.user.email


class Rfp(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    quantity = models.PositiveIntegerField()
    last_date = models.DateField()
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='rfps',
    )

    # NEW FIELD — this vendor is selected at creation time
    assigned_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rfps',
    )

    # Vendors who give quotes (later)
    vendors = models.ManyToManyField(
        Vendor,
        through='Quote',
        related_name='rfps',
    )

    def __str__(self):
        return self.name



class Quote(models.Model):
    rfp = models.ForeignKey(
        Rfp,
        on_delete=models.CASCADE,
        related_name='quotes',
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='quotes',
    )

    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('rfp', 'vendor')

    def __str__(self):
        return f"Quote by {self.vendor} for {self.rfp}"
