from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AppointmentForm
from .models import Appointment, ScheduleBlock, Service, WorkingHours
from django.db.models import Q
from .patient_utils import get_or_create_patient
from bookings.appointment_utils import (
    appointment_has_ended,
    update_past_appointments,
)



SLOT_MINUTES = 30

def get_schedule_blocks(date):
    return ScheduleBlock.objects.filter(
        date__lte=date
    ).filter(
        Q(end_date__gte=date) |
        Q(end_date__isnull=True, date=date)
    )


def generate_slots(date, service):
    try:
        working_hours = WorkingHours.objects.get(
            weekday=date.weekday()
        )
    except WorkingHours.DoesNotExist:
        return []

    if working_hours.is_closed:
        return []

    slots = []

    current = datetime.combine(
        date,
        working_hours.opening_time
    )

    closing = datetime.combine(
        date,
        working_hours.closing_time
    )

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


def slot_is_available(date, start_time, duration):
    requested_start = datetime.combine(date, start_time)
    requested_end = requested_start + timedelta(minutes=duration)

    blocks = get_schedule_blocks(date)

    for block in blocks:
        if block.all_day:
            return False

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

    for appointment in appointments:
        existing_start = datetime.combine(date, appointment.time)
        existing_end = existing_start + timedelta(
            minutes=appointment.service.duration
        )

        if requested_start < existing_end and requested_end > existing_start:
            return False

    return True


def booking(request):
    services = Service.objects.filter(is_active=True)
    selected_service = None
    selected_date = None
    slots = []

    service_id = request.GET.get("service")
    date_string = request.GET.get("date")

    if service_id:
        selected_service = get_object_or_404(Service, id=service_id, is_active=True)

    if date_string:
        try:
            selected_date = datetime.strptime(date_string, "%Y-%m-%d").date()
        except ValueError:
            selected_date = None

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
    service = get_object_or_404(Service, id=request.GET.get("service"))

    date = datetime.strptime(
        request.GET.get("date"),
        "%Y-%m-%d",
    ).date()

    selected_time = datetime.strptime(
        request.GET.get("time"),
        "%H:%M",
    ).time()

    form = AppointmentForm()

    return render(request, "bookings/booking_form.html", {
        "form": form,
        "service": service,
        "date": date,
        "time": selected_time,
    })

def create_appointment(request):
    if request.method != "POST":
        return redirect("booking")

    service = get_object_or_404(Service, id=request.POST.get("service"))
    date = datetime.strptime(request.POST.get("date"), "%Y-%m-%d").date()
    selected_time = datetime.strptime(request.POST.get("time"), "%H:%M").time()

    form = AppointmentForm(request.POST)

    if form.is_valid() and slot_is_available(
        date,
        selected_time,
        service.duration,
    ):
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
    })


def booking_success(request):
    return render(request, "bookings/success.html")