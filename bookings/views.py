from datetime import datetime

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .booking_utils import (
    generate_slots,
    get_alternative_slots,
    validate_booking,
)
from .forms import AppointmentForm
from .models import Appointment, Service
from .patient_utils import get_or_create_patient


def parse_int(value):
    """'12' -> 12. None dacă lipsește sau nu e număr."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """'2026-09-04' -> date. None dacă lipsește sau e aiurea."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_time(value):
    """'14:30' -> time. None dacă lipsește sau e aiurea."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return None


def booking(request):
    services = Service.objects.filter(is_active=True).select_related("category")
    selected_service = None
    slots = []

    service_id = parse_int(request.GET.get("service"))
    selected_date = parse_date(request.GET.get("date"))

    if service_id:
        selected_service = get_object_or_404(
            Service, id=service_id, is_active=True
        )

    if selected_service and selected_date:
        if selected_date >= timezone.localdate():
            slots = generate_slots(selected_date, selected_service)

    return render(request, "bookings/booking.html", {
        "services": services,
        "selected_service": selected_service,
        "selected_date": selected_date,
        "slots": slots,
    })


def booking_details(request):
    service_id = parse_int(request.GET.get("service"))
    date = parse_date(request.GET.get("date"))
    selected_time = parse_time(request.GET.get("time"))

    if not service_id or not date or not selected_time:
        return redirect("booking")

    service = get_object_or_404(Service, id=service_id)
    error = validate_booking(date, selected_time, service)

    if error:
        return render(request, "bookings/booking_form.html", {
            "service": service,
            "date": date,
            "time": selected_time,
            "booking_error": error,
            "alternatives": get_alternative_slots(date, service),
        })

    return render(request, "bookings/booking_form.html", {
        "form": AppointmentForm(),
        "service": service,
        "date": date,
        "time": selected_time,
    })


def create_appointment(request):
    if request.method != "POST":
        return redirect("booking")

    service_id = parse_int(request.POST.get("service"))
    date = parse_date(request.POST.get("date"))
    selected_time = parse_time(request.POST.get("time"))

    if not service_id or not date or not selected_time:
        return redirect("booking")

    service = get_object_or_404(Service, id=service_id)

    form = AppointmentForm(request.POST)
    booking_error = validate_booking(date, selected_time, service)

    if form.is_valid() and not booking_error:
        # Fișa se alege singură: același nume (indiferent de ordine sau
        # majuscule) pe același telefon = aceeași persoană. Orice altceva
        # primește fișă nouă. Pacientul nu e întrebat nimic — nu are voie
        # să afle numele altor pacienți.
        patient = get_or_create_patient(
            form.cleaned_data["patient_name"],
            form.cleaned_data["patient_phone"],
            form.cleaned_data["patient_email"],
        )

        Appointment.objects.create(
            patient=patient,
            service=service,
            date=date,
            time=selected_time,
            status=Appointment.Status.PENDING,
        )

        return redirect("booking_success")

    return render(request, "bookings/booking_form.html", {
        "form": form,
        "service": service,
        "date": date,
        "time": selected_time,
        "booking_error": booking_error,
        "alternatives": (
            get_alternative_slots(date, service) if booking_error else []
        ),
    })


def booking_success(request):
    return render(request, "bookings/success.html")