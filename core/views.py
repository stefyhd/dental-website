from django.db.models import Prefetch
from django.shortcuts import render
from django.utils import timezone

from bookings.models import Service, ServiceCategory, WorkingHours


def get_week_hours():
    """
    Programul săptămânal. Marchez ziua de azi ca s-o pot evidenția —
    pacientul se uită întâi dacă e deschis ACUM, nu ce program e joia.
    """
    today = timezone.localdate().weekday()
    saved = {hours.weekday: hours for hours in WorkingHours.objects.all()}

    return [
        {
            "label": label,
            "is_today": weekday == today,
            "is_closed": saved[weekday].is_closed if weekday in saved else True,
            "opening_time": saved[weekday].opening_time if weekday in saved else None,
            "closing_time": saved[weekday].closing_time if weekday in saved else None,
        }
        for weekday, label in WorkingHours.Weekday.choices
    ]


def categories_with_services():
    """
    Categoriile active care chiar au servicii, cu serviciile atașate.

    O categorie goală e un card care nu duce nicăieri — n-are ce căuta
    pe site-ul public.
    """
    return (
        ServiceCategory.objects
        .filter(is_active=True, services__is_active=True)
        .distinct()
        .prefetch_related(
            Prefetch(
                "services",
                queryset=Service.objects.filter(is_active=True),
                to_attr="live_services",
            )
        )
    )


def home(request):
    # Pe prima pagină intră doar categoriile bifate „Pe prima pagină"
    # din dashboard. Dacă medicul n-a bifat nimic, luăm primele trei,
    # ca pagina să nu apară goală.
    featured = [c for c in categories_with_services() if c.is_featured][:4]

    if not featured:
        featured = list(categories_with_services())[:3]

    return render(request, "core/home.html", {
        "featured": featured,
        "week_hours": get_week_hours(),
    })


def services(request):
    return render(request, "core/services.html", {
        "categories": categories_with_services(),
    })


def contact(request):
    return render(request, "core/contact.html", {
        "week_hours": get_week_hours(),
    })