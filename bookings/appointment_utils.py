from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment


def appointment_has_ended(appointment, now=None):
    now = now or timezone.localtime()

    start = datetime.combine(
        appointment.date,
        appointment.time,
    )

    start = timezone.make_aware(
        start,
        timezone.get_current_timezone(),
    )

    end = start + timedelta(
        minutes=appointment.service.duration
    )

    return end <= now


def update_past_appointments():
    now = timezone.localtime()

    appointments = (
        Appointment.objects
        .filter(
            status=Appointment.Status.CONFIRMED,
            date__lte=now.date(),
        )
        .select_related("service")
    )

    completed_ids = [
        appointment.id
        for appointment in appointments
        if appointment_has_ended(appointment, now)
    ]

    if completed_ids:
        Appointment.objects.filter(
            id__in=completed_ids
        ).update(status=Appointment.Status.COMPLETED)

    return completed_ids