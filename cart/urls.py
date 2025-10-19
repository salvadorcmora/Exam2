from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='cart.index'),
    path('<int:id>/add/', views.add, name='cart.add'),
    path('clear/', views.clear, name='cart.clear'),
    path('purchase/', views.purchase, name='cart.purchase'),

    # Fix: use the correct function name
    path('popularity/', views.popularity_page, name='cart.popularity'),
    path('popularity/map/', views.popularity_map, name='cart.popularity_map'),
    path('popularity.json', views.popularity_json, name='cart.popularity_json'),
]
