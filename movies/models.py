from django.db import models
import uuid
from django.contrib.auth.models import User
from django.utils import timezone

class Genre(models.Model):
    name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=255)
    genres = models.ManyToManyField(Genre)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    rating = models.FloatField(db_index=True)
    release_date = models.DateField(db_index=True)
    trailer_id = models.CharField(max_length=50, blank=True, null=True)
    price = models.IntegerField(default=200) 


    def __str__(self):
        return self.title

class Booking(models.Model):
    movie_name = models.CharField(max_length=100)
    show_time = models.CharField(max_length=50)
    seats = models.CharField(max_length=50)
    theater = models.CharField(max_length=100)
    amount = models.IntegerField(default=0)
    email = models.EmailField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    idempotency_key = models.CharField(
        max_length=100,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movie_name} - {self.status}"

class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    signature = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20)
    webhook_event_id = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_id} - {self.status}"

class EmailLog(models.Model):
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Seat(models.Model):
    seat_number = models.CharField(max_length=10)

    is_reserved = models.BooleanField(default=False)
    reserved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    reserved_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        if self.reserved_at:
            return timezone.now() > self.reserved_at + timezone.timedelta(minutes=2)
        return False

    def __str__(self):
        return self.seat_number