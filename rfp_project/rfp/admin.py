from django.contrib import admin
from .models import Category, Vendor, Rfp

# Register your models here.
admin.site.register(Category)
admin.site.register(Vendor)
admin.site.register(Rfp)
