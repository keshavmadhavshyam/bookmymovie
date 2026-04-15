from django.urls import path
from .views import movie_list
from .views import booking_view
from . import views

urlpatterns = [
    path('', movie_list, name='movie_list'),
    path('booking/', booking_view, name='booking_view'),
    path('movie/<int:id>/', views.movie_detail, name='movie_detail'),
    path('pay/', views.simple_payment, name='simple_payment'),
    path('demo-payment-success/', views.demo_payment_success, name='demo_payment_success'),
    path('verify-payment/', views.verify_payment),
    path('booking/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('reserve-seat/', views.reserve_seat_lock, name='reserve_seat_lock'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
]