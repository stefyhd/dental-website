from django.db.models import Prefetch
from django.shortcuts import render
from django.utils import timezone

from bookings.models import Service, ServiceCategory, WorkingHours


def get_week_hours():
    """
    Programul săptămânal pentru tabelul din Contact.

    Marchez ziua de azi ca s-o pot evidenția — pacientul se uită întâi
    dacă e deschis ACUM, nu ce program e joia.
    """
    today = timezone.localdate().weekday()
    saved = {hours.weekday: hours for hours in WorkingHours.objects.all()}

    week = []

    for weekday, label in WorkingHours.Weekday.choices:
        hours = saved.get(weekday)

        week.append({
            "label": label,
            "is_today": weekday == today,
            "is_closed": hours.is_closed if hours else True,
            "opening_time": hours.opening_time if hours else None,
            "closing_time": hours.closing_time if hours else None,
        })

    return week


def home(request):
    # Doar categoriile care CHIAR au servicii active. Cele 10 categorii
    # standard sunt semănate la instalare; până le umple medicul, o
    # categorie goală pe site-ul public e un card care nu duce nicăieri.
    categories = (
        ServiceCategory.objects
        .filter(is_active=True, services__is_active=True)
        .distinct()
        .prefetch_related(
            Prefetch(
                "services",
                queryset=Service.objects.filter(is_active=True),
                to_attr="active_services",
            )
        )
    )

    return render(request, "core/home.html", {
        "categories": categories,
        "week_hours": get_week_hours(),
    })