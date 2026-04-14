# movies/tasks.py
from celery import shared_task
import logging
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import EmailLog

# ✅ Logger defined at top
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_booking_email(self, user_email, booking_data):

    try:
        subject = "Booking Confirmation 🎬"

        html_content = render_to_string(
            "movies/booking_confirmation.html",
            {"booking": booking_data}
        )

        email = EmailMultiAlternatives(
            subject,
            "",
            "nadardivya152@gmail.com",   
            [user_email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send()

        # ✅ Save success log
        EmailLog.objects.create(
            email=user_email,
            subject=subject,
            status="SUCCESS"
        )

    except Exception as e:
       
        EmailLog.objects.create(
            email=user_email,
            subject=subject,
            status="FAILED",
            error_message=str(e)
        )
        logger.error(f"Email failed: {str(e)}")

        # ❗ Retry the task (exponential backoff)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)