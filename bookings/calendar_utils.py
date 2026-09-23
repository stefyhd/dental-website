"""
Grila de calendar pentru pasul 2 al programării.

Regula de aur a fișierului: NU se apelează `generate_slots()` pentru
fiecare zi din lună. Ar însemna ~30 × (blocări + programări) interogări
pentru un singur ecran. Calendarul răspunde la întrebarea ieftină —
„e cabinetul deschis în ziua asta?" — din două interogări, iar lista de
ore de sub el răspunde la cea scumpă, pentru o singură zi.

Distincția e și onestă față de pacient: o zi verde înseamnă „se poate
încerca", nu „sigur are loc".
"""

import calendar
from datetime import date as date_cls, timedelta

from django.utils import timezone

from .models import ScheduleBlock, WorkingHours


# Cât de departe în viitor se poate programa cineva.
HORIZON_DAYS = 30

# Luni întâi, ca în România.
WEEKDAY_LABELS = ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]


def month_bounds(year, month):
    """Prima și ultima zi calendaristică a lunii."""
    last = calendar.monthrange(year, month)[1]
    return date_cls(year, month, 1), date_cls(year, month, last)


def fully_blocked_days(first, last):
    """
    Zilele din interval acoperite integral de o blocare.

    O interogare. Blocările care se întind pe mai multe zile sunt
    desfășurate aici, nu în baza de date.
    """
    blocked = set()

    blocks = ScheduleBlock.objects.filter(
        all_day=True,
        date__lte=last,
    )

    for block in blocks:
        end = block.end_date or block.date

        if end < first:
            continue

        day = max(block.date, first)

        while day <= min(end, last):
            blocked.add(day)
            day += timedelta(days=1)

    return blocked


def month_grid(year, month, horizon_days=HORIZON_DAYS):
    """
    Săptămânile lunii, ca liste de câte 7 celule.

    Fiecare celulă: {"date", "day", "in_month", "open", "reason"}.
    `open` False înseamnă că ziua nu se poate alege, iar `reason` spune
    de ce — folosit pentru `title` pe celulă.
    """
    today = timezone.localdate()
    horizon = today + timedelta(days=horizon_days)

    first, last = month_bounds(year, month)

    # Interogarea 1: programul săptămânal (7 rânduri, o dată).
    schedule = {
        hours.weekday: hours
        for hours in WorkingHours.objects.all()
    }

    # Interogarea 2: zilele blocate integral.
    blocked = fully_blocked_days(first, last)

    # Grila începe de luni și se termină duminică, ca să fie dreptunghi.
    start = first - timedelta(days=first.weekday())
    end = last + timedelta(days=6 - last.weekday())

    weeks = []
    week = []
    day = start

    while day <= end:
        hours = schedule.get(day.weekday())

        if day < today:
            state = (False, "A trecut")
        elif day > horizon:
            state = (False, f"Programările se fac cu cel mult {horizon_days} de zile înainte")
        elif not hours or hours.is_closed:
            state = (False, "Cabinetul e închis")
        elif day in blocked:
            state = (False, "Zi indisponibilă")
        else:
            state = (True, "")

        week.append({
            "date": day,
            "day": day.day,
            "in_month": day.month == month,
            "open": state[0],
            "reason": state[1],
            "is_today": day == today,
        })

        if len(week) == 7:
            weeks.append(week)
            week = []

        day += timedelta(days=1)

    return weeks


def month_steps(year, month, horizon_days=HORIZON_DAYS):
    """
    Luna anterioară și cea următoare, dar numai dacă au sens.

    Întoarce (prev, next) ca perechi (an, lună) sau None. Nu se poate
    merge în trecut, nici dincolo de orizont — altfel pacientul
    răsfoiește luni goale.
    """
    today = timezone.localdate()
    horizon = today + timedelta(days=horizon_days)

    current = date_cls(year, month, 1)

    previous_month = (current - timedelta(days=1)).replace(day=1)
    next_month = (month_bounds(year, month)[1] + timedelta(days=1))

    prev = None
    if previous_month >= today.replace(day=1):
        prev = (previous_month.year, previous_month.month)

    nxt = None
    if next_month <= horizon:
        nxt = (next_month.year, next_month.month)

    return prev, nxt


def next_open_day(service, start=None, horizon_days=HORIZON_DAYS):
    """
    Prima zi din orizont care chiar are ore libere pentru serviciul dat.

    Asta CHEAMĂ `generate_slots()`, deci e scumpă — se folosește doar
    pentru scurtătura „Următoarea zi liberă", niciodată pentru grilă.
    Se oprește la primul rezultat.
    """
    from .booking_utils import generate_slots

    today = timezone.localdate()
    day = start or today
    limit = today + timedelta(days=horizon_days)

    while day <= limit:
        if generate_slots(day, service):
            return day
        day += timedelta(days=1)

    return None