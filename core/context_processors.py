"""
Date disponibile în ORICE șablon.

Datele cabinetului și programul de azi apar în bara de sus, în navbar și în
footer — adică pe fiecare pagină, inclusiv în fluxul de rezervare. Dacă
le-am pune în `home`, celelalte pagini ar rămâne cu footerul gol.
"""

from django.conf import settings
from django.utils import timezone

from bookings.models import WorkingHours


def clinic(request):
    """Numele, telefonul, adresa — din settings.CLINIC."""
    return {"clinic": settings.CLINIC}


def today_hours(request):
    """
    Programul de azi, pentru bara de sus („Astăzi deschis 9-17”).

    Întoarce None dacă ziua nu e configurată — șablonul tratează cazul
    ca „închis”, ceea ce e răspunsul sigur.
    """
    weekday = timezone.localdate().weekday()

    return {
        "today_hours": WorkingHours.objects.filter(weekday=weekday).first(),
    }