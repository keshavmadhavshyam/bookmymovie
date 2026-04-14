from django.shortcuts import render
from django.shortcuts import redirect
from .models import Movie, Genre, Language
from django.db.models import Count
from django.db import models
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import Booking, Payment
from django.core.mail import EmailMessage
from django.http import JsonResponse
import json
from movies.tasks import send_booking_email
import re
import razorpay
from django.db import transaction
from django.utils import timezone
from .models import Seat
from .utils import release_if_expired
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.core.cache import cache

def extract_video_id(url):
    if not url:
        return None

    pattern = r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None

def test_email(request):

    movie_name = request.GET.get('movie_name', 'Default Movie')
    show_time = request.GET.get('show_time', '7 PM')
    seats = request.GET.get('seats', 'A1, A2')
    theater = request.GET.get('theater', 'PVR')

    # Save booking
    booking = Booking.objects.create(
        movie_name=movie_name,
        show_time=show_time,
        seats=seats,
        theater=theater
    )

    # Send email via Celery 
    send_booking_email.delay(
        "nadardivya152@gmail.com",
        {
            "movie_name": booking.movie_name,
            "show_time": booking.show_time,
            "seats": booking.seats,
            "theater": booking.theater
        }
    )

    return render(request, 'movies/booking_confirmation.html', {
        'email': "nadardivya152@gmail.com",
        'movie_name': booking.movie_name,
        'show_time': booking.show_time,
        'seats': booking.seats,
        'theater': booking.theater
    })
def movie_list(request):
    movies = Movie.objects.select_related('language').prefetch_related('genres')

    genres = request.GET.getlist('genre')
    languages = request.GET.getlist('language')
    sort = request.GET.get('sort')
    search_query = request.GET.get('search')

    if genres:
        movies = movies.filter(genres__id__in=genres).distinct()

    if languages:
        movies = movies.filter(language__id__in=languages)

    if sort == 'rating_desc':
        movies = movies.order_by('-rating')

    elif sort == 'rating_asc':
        movies = movies.order_by('rating')

    elif sort == 'date_desc':
        movies = movies.order_by('-release_date')

    elif sort == 'date_asc':
        movies = movies.order_by('release_date')
    # SEARCH FEATURE
    if search_query:
        movies = movies.filter(title__icontains=search_query)

    if not movies:
        return render(request, 'movies/movie_not_found.html', {
            'query': search_query
        })

    # Base queryset after applying filters
    filtered_movies = movies

    # Genre counts
    genre_counts = Genre.objects.annotate(
        count=Count('movie', filter=models.Q(movie__in=filtered_movies))
    )

    # Language counts
    language_counts = Language.objects.annotate(
        count=Count('movie', filter=models.Q(movie__in=filtered_movies))
    )

    paginator = Paginator(movies, 5)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'movies/list.html', {
    'page_obj': page_obj,
    'all_genres': genre_counts,
    'all_languages': language_counts,
    'selected_genres': genres,
    'selected_languages': languages
})

def booking_view(request):
    if request.method == 'POST':
        # Get form data
        user_email = request.POST.get('email')
        movie_name = request.POST.get('movie')
        show_time = request.POST.get('time')
        seats = request.POST.get('seats')
        theater = request.POST.get('theater')

        seat_numbers = seats.split(',')

        for seat_no in seat_numbers:
            try:
                seat = Seat.objects.get(seat_number=seat_no.strip())

                # release if expired
                release_if_expired(seat)

                if seat.is_reserved:
                    return HttpResponse("Seat already booked ❌")

                seat.is_reserved = True
                seat.reserved_at = timezone.now()
                seat.save()

            except Seat.DoesNotExist:
                return HttpResponse("Invalid seat ❌")

        # Save booking
        booking = Booking.objects.create(
            movie_name=movie_name,
            show_time=show_time,
            seats=seats,
            #payment_id=payment_id,
            theater=theater,
            email=user_email
        )

        booking_data = {
            'movie_name': movie_name,
            'show_time': show_time,
            'seats': seats,
            #'payment_id': payment_id,
            'theater': theater,
            'email': user_email
        }

        # Send email asynchronously
        return redirect('/pay/')

    movie_name = request.GET.get('movie', '')

    return render(request, 'movies/booking_form.html', {
        'movie_name': movie_name
    })

def booking_confirmation(request):
    booking = Booking.objects.latest('id')

    if booking.status != "success":
        return HttpResponse("Payment not completed. Booking not confirmed ❌")

    return render(request, 'movies/booking_confirmation.html', {
        'booking': booking
    })

def movie_detail(request, id):
    movie = Movie.objects.get(id=id)

    return render(request, "movies/movie_detail.html", {
        "movie": movie
    })

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def simple_payment(request):
    booking = Booking.objects.latest('id') if Booking.objects.exists() else None  # get last booking

    amount = 200  

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "receipt": str(booking.id)
    })

    Payment.objects.create(
        booking=booking,
        order_id=order['id'],
        status="created"
    )

    return render(request, "movies/payment.html", {
        "order": order,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": amount
    })

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        print("VERIFY PAYMENT CALLED")

        booking = Booking.objects.latest('id')

        if booking.status == "success":
            return JsonResponse({"status": "already_processed"})
            
        booking.status = "success"
        booking.save()

        seat_numbers = booking.seats.split(',')

        for seat_no in seat_numbers:
            try:
                seat = Seat.objects.get(seat_number=seat_no.strip())
                seat.is_reserved = True
                seat.reserved_by = None
                seat.reserved_at = None
                seat.save()
            except Seat.DoesNotExist:
                pass

        send_booking_email.delay(
            booking.email,
            {
                "movie_name": booking.movie_name,
                "show_time": booking.show_time,
                "seats": booking.seats,
                "theater": booking.theater,
                "email": booking.email
            }
        )

        return JsonResponse({"status": "success"})
   
@transaction.atomic
def reserve_seat_lock(request):
    if request.method == "POST":

        seats = request.POST.get("seats") 

        print("VIEW HIT")

        seat_list = seats.split(",")

        for seat_name in seat_list:
            seat_name = seat_name.strip()

            try:
                seat = Seat.objects.select_for_update().get(seat_number=seat_name)

                release_if_expired(seat)

                if seat.is_reserved:
                    return render(request, 'movies/seat_error.html', {
                        'message': f"Seat {seat_name} already reserved ❌"
                    })

                seat.is_reserved = True
                seat.reserved_by = request.user
                seat.reserved_at = timezone.now()
                seat.save()

            except Seat.DoesNotExist:
                return render(request, 'movies/seat_error.html', {
                    'message': f"Seat {seat_name} not found ❌"
                })

        return redirect('simple_payment')

    return redirect('booking_view')

@staff_member_required
def admin_dashboard(request):

    # Try to get cached data
    data = cache.get('dashboard_data')

    if not data:
        # Total revenue
        total_revenue = Booking.objects.aggregate(total=Sum('amount'))['total'] or 0

        # Popular movies
        popular_movies = Booking.objects.values('movie_name') \
            .annotate(count=Count('id')) \
            .order_by('-count')[:5]

        data = {
            'total_revenue': total_revenue,
            'popular_movies': popular_movies
        }

        # Store in cache for 5 minutes
        cache.set('dashboard_data', data, 300)

    return render(request, 'movies/admin_dashboard.html', data)