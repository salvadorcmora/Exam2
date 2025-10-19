from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, CharField, Value
from django.db.models.functions import Substr, Concat
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from movies.models import Movie
from .utils import calculate_cart_total
from .models import Order, Item, Popularity


def index(request):
    cart_total = 0
    movies_in_cart = []
    cart = request.session.get('cart', {})
    movie_ids = list(cart.keys())
    if movie_ids:
        movies_in_cart = Movie.objects.filter(id__in=movie_ids)
        cart_total = calculate_cart_total(cart, movies_in_cart)

    template_data = {
        'title': 'Cart',
        'movies_in_cart': movies_in_cart,
        'cart_total': cart_total,
    }
    return render(request, 'cart/index.html', {'template_data': template_data})


def add(request, id):
    get_object_or_404(Movie, id=id)
    cart = request.session.get('cart', {})
    cart[id] = request.POST['quantity']
    request.session['cart'] = cart
    return redirect('cart.index')


def clear(request):
    request.session['cart'] = {}
    return redirect('cart.index')


@login_required
def purchase(request):
    if request.method != 'POST':
        return redirect('cart.index')

    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart.index")

    try:
        movie_ids = [int(k) for k in cart.keys()]
    except ValueError:
        movie_ids = []
    movies = list(Movie.objects.filter(id__in=movie_ids))

    line_items = []
    total = Decimal("0.00")
    for m in movies:
        qty = int(cart.get(str(m.id), 0))
        if qty <= 0:
            continue
        unit_price = Decimal(str(getattr(m, "price", 0)))
        line_total = unit_price * qty
        total += line_total
        line_items.append(
            {"movie": m, "qty": qty, "unit_price": unit_price, "line_total": line_total}
        )

    if not line_items:
        return redirect("cart.index")

    zip_code = (request.POST.get("zip") or "").strip() or "00000"

    with transaction.atomic():
        order = Order.objects.create(user=request.user, total=total)
        for li in line_items:
            movie, qty, unit_price = li["movie"], li["qty"], li["unit_price"]
            try:
                Item.objects.create(order=order, movie=movie, quantity=qty, price=unit_price)
            except TypeError:
                # fallback if model doesn't accept price
                Item.objects.create(order=order, movie=movie, quantity=qty)
            pop, _ = Popularity.objects.get_or_create(
                movie=movie, zip=zip_code, defaults={"count": 0}
            )
            pop.count = (pop.count or 0) + qty
            pop.save()

    request.session["cart"] = {}

    context = {
        "template_data": {
            "title": "Purchase Complete",
            "order": order,
            "items": line_items,
            "total": total,
            "zip": zip_code,
        }
    }
    return render(request, "cart/purchase.html", context)


# ---------- Popularity (List) ----------
def popularity_page(request):
    rows = (
        Popularity.objects
        .annotate(zip3=Substr('zip', 1, 3))
        .annotate(region=Concat('zip3', Value('**'), output_field=CharField()))
        .values('region', 'movie_id', 'movie__name')
        .annotate(total=Sum('count'))
        .order_by('region', '-total', 'movie__name')
    )

    regions = defaultdict(list)
    for r in rows:
        regions[r['region']].append({
            'movie_id': r['movie_id'],
            'movie_name': r['movie__name'],
            'total': r['total'],
        })

    top_by_region = [{'region': k, 'top': v[:5]} for k, v in regions.items()]
    ctx = {'template_data': {'title': 'Local Popularity', 'regions': top_by_region}}
    return render(request, 'cart/popularity.html', ctx)


# ---------- Popularity (Map JSON + Page) ----------
def popularity_json(request):
    """
    Aggregated popularity by ZIP for the map:
    { "data": [ { "zip": "30332", "total": 8, "top": [ {"movie_name": "...", "total": 5}, ... ] }, ... ] }
    """
    rows = (
        Popularity.objects
        .values('zip', 'movie__name')
        .annotate(total=Sum('count'))
        .order_by('zip', '-total', 'movie__name')
    )

    grouped = defaultdict(list)
    for r in rows:
        grouped[r['zip']].append({'movie_name': r['movie__name'], 'total': r['total']})

    payload = [{
        'zip': z,
        'total': sum(i['total'] for i in items),
        'top': items[:5]
    } for z, items in grouped.items()]

    return JsonResponse({'data': payload})


def popularity_map(request):
    """Renders the Leaflet map page; it fetches data from popularity_json."""
    return render(request, 'cart/popularity_map.html',
                  {'template_data': {'title': 'Local Popularity (Map)'}})
