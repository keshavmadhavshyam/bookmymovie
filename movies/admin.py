from django.contrib import admin
from .models import Movie, Genre, Language
from .models import EmailLog, Booking, Payment, Seat

admin.site.register(EmailLog)
admin.site.register(Movie)
admin.site.register(Genre)
admin.site.register(Language)
admin.site.register(Booking)
admin.site.register(Payment)
admin.site.register(Seat)

