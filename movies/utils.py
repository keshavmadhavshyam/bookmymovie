from django.utils import timezone
from datetime import timedelta

def release_if_expired(seat):
    if seat.is_reserved and seat.reserved_at:
        if timezone.now() > seat.reserved_at + timedelta(minutes=2):
            seat.is_reserved = False
            seat.reserved_by = None
            seat.reserved_at = None
            seat.save()
            return True
    return False