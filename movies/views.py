from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .models import Movie, Review, MovieRating

def index(request):
    search_term = request.GET.get('search')
    if search_term:
        movies = Movie.objects.filter(name__icontains=search_term)
    else:
        movies = Movie.objects.all()

    template_data = {}
    template_data['title'] = 'Movies'
    template_data['movies'] = movies
    return render(request, 'movies/index.html', {'template_data': template_data})

def show(request, id):
    movie = get_object_or_404(Movie, id=id)
    reviews = Review.objects.filter(movie=movie)
    avg = MovieRating.objects.filter(movie=movie).aggregate(avg=Avg('value'))['avg']
    user_rating = None
    if request.user.is_authenticated:
        r = MovieRating.objects.filter(movie=movie, user=request.user).first()
        user_rating = r.value if r else None
    ctx = {'template_data': {
        'title': movie.name, 'movie': movie, 'reviews': reviews,
        'average_rating': avg, 'user_rating': user_rating
    }}
    return render(request, 'movies/show.html', ctx)

@login_required
def create_review(request, id):
    movie = get_object_or_404(Movie, id=id)
    if request.method == 'POST' and request.POST.get('comment'):
        Review.objects.create(movie=movie, user=request.user, comment=request.POST['comment'])
    return redirect('movies.show', id=id)

@login_required
def edit_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id, movie_id=id, user=request.user)
    if request.method == 'GET':
        return render(request, 'movies/edit_review.html', {'template_data': {'title': 'Edit Review', 'review': review}})
    if request.method == 'POST' and request.POST.get('comment'):
        review.comment = request.POST['comment']; review.save()
    return redirect('movies.show', id=id)

@login_required
def delete_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id, movie_id=id, user=request.user)
    review.delete()
    return redirect('movies.show', id=id)



@login_required
def rate_movie(request, id):
    movie = get_object_or_404(Movie, id=id)
    if request.method == 'POST':
        val = request.POST.get('rating')
        if val and val.isdigit():
            n = int(val)
            if 1 <= n <= 5:
                MovieRating.objects.update_or_create(
                    movie=movie, user=request.user, defaults={'value': n}
                )
    return redirect('movies.show', id=id)
