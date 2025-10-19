from django.contrib import admin
from .models import Order, Item, Popularity

admin.site.register(Order)
admin.site.register(Item)
admin.site.register(Popularity)