"""
Regulile de rezervare, într-un singur loc.

Atât fluxul public (pacientul), cât și dashboard-ul (medicul) folosesc
funcțiile de aici. Când o regulă se schimbă, se schimbă o singură dată.
"""

from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Appointment, ScheduleBlock, WorkingHours
from .schedule_utils import SLOT_MINUTES


def get_schedule_blocks(date):
    """Blocările active într-o zi, inclusiv cele care se întind pe mai multe zile."""
    return ScheduleBlock.objects.filter(
        date__lte=date
    ).filter(
        Q(end_date__gte=date) |
        Q(end_date__isnull=True, date=date)
    )


def slot_is_available(date, start_time, duration, exclude_id=None):
    """
    Intervalul cerut este liber?

    exclude_id: ignoră o programare anume — necesar la editare, altfel
    programarea se ciocnește cu ea însăși.
    """
    requested_start = datetime.combine(date, start_time)
    requested_end = requested_start + timedelta(minutes=duration)

    for block in get_schedule_blocks(date):
        if block.all_day:
            return False

        # Blocare fără ore (creată din shell sau admin) — o sărim,
        # altfel datetime.combine(date, None) aruncă TypeError.
        if block.start_time is None or block.end_time is None:
            continue

        block_start = datetime.combine(date, block.start_time)
        block_end = datetime.combine(date, block.end_time)

        if requested_start < block_end and requested_end > block_start:
            return False

    appointments = (
        Appointment.objects
        .filter(
            date=date,
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
        )
        .select_related("service")
    )

    if exclude_id:
        appointments = appointments.exclude(id=exclude_id)

    for appointment in appointments:
        existing_start = datetime.combine(date, appointment.time)
        existing_end = existing_start + timedelta(
            minutes=appointment.service.duration
        )

        if requested_start < existing_end and requested_end > existing_start:
            return False

    return True


def generate_slots(date, service):
    """Orele libere dintr-o zi, pentru un serviciu."""
    working_hours = WorkingHours.objects.filter(weekday=date.weekday()).first()

    if not working_hours or working_hours.is_closed:
        return []

    slots = []

    current = datetime.combine(date, working_hours.opening_time)
    closing = datetime.combine(date, working_hours.closing_time)
    now = timezone.localtime()

    while current + timedelta(minutes=service.duration) <= closing:
        slot_time = current.time()

        if date == now.date() and slot_time <= now.time():
            current += timedelta(minutes=SLOT_MINUTES)
            continue

        if slot_is_available(date, slot_time, service.duration):
            slots.append(slot_time)

        current += timedelta(minutes=SLOT_MINUTES)

    return slots


def validate_booking(date, start_time, service, exclude_id=None):
    """
    Verifică o programare din toate unghiurile.

    Returnează None dacă e în regulă, altfel mesajul de arătat pacientului.

    Aceasta este singura poartă de intrare. Lista de ore libere e doar
    o sugestie afișată în pagină — cererea POST poate veni de oriunde,
    deci ea trebuie validată, nu ce a apărut pe ecran.
    """
    requested_start = datetime.combine(date, start_time)
    now = timezone.localtime().replace(tzinfo=None)

    if requested_start <= now:
        return "Ora aleasă a trecut deja. Te rugăm să alegi altă oră."

    if not service.is_active:
        return "Serviciul selectat nu mai este disponibil."

    working_hours = WorkingHours.objects.filter(weekday=date.weekday()).first()

    if not working_hours or working_hours.is_closed:
        return "Cabinetul este închis în ziua selectată."

    requested_end = requested_start + timedelta(minutes=service.duration)
    opening = datetime.combine(date, working_hours.opening_time)
    closing = datetime.combine(date, working_hours.closing_time)

    if requested_start < opening or requested_end > closing:
        return (
            f"În ziua selectată programul este "
            f"{working_hours.opening_time:%H:%M}–{working_hours.closing_time:%H:%M}."
        )

    if not slot_is_available(date, start_time, service.duration, exclude_id):
        return "Intervalul tocmai a fost ocupat. Te rugăm să alegi altă oră."

    return None


def get_alternative_slots(date, service, limit=3):
    """Primele ore rămase libere în aceeași zi — pentru mesajele de eroare."""
    return generate_slots(date, service)[:limit]