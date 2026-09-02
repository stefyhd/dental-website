from datetime import datetime, time, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.models import Appointment
from .forms import ManualAppointmentForm
from bookings.models import Appointment, Service
from django.forms import modelformset_factory
from bookings.models import Appointment, ScheduleBlock, Service, WorkingHours
from .forms import ManualAppointmentForm, ScheduleBlockForm, WorkingHoursForm
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import (
    AppointmentEditForm,
    ManualAppointmentForm,
    ScheduleBlockForm,
    ServiceForm,
    WorkingHoursForm,
)
from bookings.models import Appointment, ScheduleBlock, Service, WorkingHours
from django.db.models import Q


SLOT_MINUTES = 30


def get_selected_date(request):
    date_string = request.GET.get("date")

    if not date_string:
        return timezone.localdate()

    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def build_agenda(selected_date):
    try:
        working_hours = WorkingHours.objects.get(
            weekday=selected_date.weekday()
        )
    except WorkingHours.DoesNotExist:
        return []

    if working_hours.is_closed:
        return []

    appointments = list(
        Appointment.objects
        .filter(date=selected_date)
        .exclude(status__in=[
            Appointment.Status.REJECTED,
            Appointment.Status.CANCELLED,
        ])
        .select_related("service")
        .order_by("time")
    )

    blocks = list(
        ScheduleBlock.objects
        .filter(date__lte=selected_date)
        .filter(
            Q(end_date__gte=selected_date) |
            Q(end_date__isnull=True, date=selected_date)
        )
        )

    rows = []

    current = datetime.combine(
        selected_date,
        working_hours.opening_time
    )
    closing = datetime.combine(
        selected_date,
        working_hours.closing_time
    )

    while current < closing:
        slot_end = current + timedelta(minutes=SLOT_MINUTES)
        matches = []
        block_matches = []

        for block in blocks:
            if block.all_day:
                block_matches.append(block)
                continue

            block_start = datetime.combine(selected_date, block.start_time)
            block_end = datetime.combine(selected_date, block.end_time)

            if current < block_end and slot_end > block_start:
                block_matches.append(block)

        for appointment in appointments:
            appointment_start = datetime.combine(
                selected_date,
                appointment.time
            )

            appointment_end = appointment_start + timedelta(
                minutes=appointment.service.duration
            )

            if appointment_start < slot_end and appointment_end > current:
                matches.append({
                    "appointment": appointment,
                    "starts_here": appointment_start == current,
                })

        rows.append({
            "time": current.time(),
            "appointments": matches,
            "blocks": block_matches,
        })

        current += timedelta(minutes=SLOT_MINUTES)

    return rows


@staff_member_required(login_url="dashboard_login")
def home(request):
    selected_date = get_selected_date(request)

    pending = (
        Appointment.objects
        .filter(status=Appointment.Status.PENDING)
        .select_related("service")
        .order_by("date", "time")
    )

    return render(request, "dashboard/home.html", {
        "selected_date": selected_date,
        "previous_date": selected_date - timedelta(days=1),
        "next_date": selected_date + timedelta(days=1),
        "agenda": build_agenda(selected_date),
        "pending": pending,
        "pending_count": pending.count(),
    })


@require_POST
@staff_member_required(login_url="dashboard_login")
def confirm_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = Appointment.Status.CONFIRMED
    appointment.save(update_fields=["status"])

    return_date = request.POST.get("return_date", "")
    url = reverse("dashboard_home")

    if return_date:
        url += f"?date={return_date}"

    return redirect(url)


@require_POST
@staff_member_required(login_url="dashboard_login")
def reject_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = Appointment.Status.REJECTED
    appointment.save(update_fields=["status"])

    return_date = request.POST.get("return_date", "")
    url = reverse("dashboard_home")

    if return_date:
        url += f"?date={return_date}"

    return redirect(url)


@staff_member_required(login_url="dashboard_login")
def manual_appointment(request):
    if request.method == "POST":
        form = ManualAppointmentForm(request.POST)

        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.status = Appointment.Status.CONFIRMED
            appointment.save()

            return redirect(
                f"{reverse('dashboard_home')}?date={appointment.date}"
            )
    else:
        form = ManualAppointmentForm(initial={
            "date": timezone.localdate(),
        })

    return render(request, "dashboard/manual_appointment.html", {
        "form": form,
    })

@staff_member_required(login_url="dashboard_login")
def appointments(request):
    appointments = (
        Appointment.objects
        .select_related("service")
        .order_by("-date", "-time")
    )

    return render(request, "dashboard/appointments.html", {
        "appointments": appointments,
    })


@staff_member_required(login_url="dashboard_login")
def schedule(request):
    for weekday, _ in WorkingHours.Weekday.choices:
        WorkingHours.objects.get_or_create(
            weekday=weekday,
            defaults={
                "opening_time": time(9, 0),
                "closing_time": time(17, 0),
                "is_closed": weekday >= 5,
            },
        )

    HoursFormSet = modelformset_factory(
        WorkingHours,
        form=WorkingHoursForm,
        extra=0,
    )

    hours_formset = HoursFormSet(
        request.POST or None,
        queryset=WorkingHours.objects.all(),
        prefix="hours",
    )

    block_form = ScheduleBlockForm(
        request.POST or None,
        prefix="block",
    )

    if request.method == "POST":
        if "save_hours" in request.POST and hours_formset.is_valid():
            hours_formset.save()
            return redirect("dashboard_schedule")

        if "add_block" in request.POST and block_form.is_valid():
            block_form.save()
            return redirect("dashboard_schedule")

    blocks = ScheduleBlock.objects.filter(
        date__gte=timezone.localdate()
    ).order_by("date", "start_time")

    return render(request, "dashboard/schedule.html", {
        "hours_formset": hours_formset,
        "block_form": block_form,
        "blocks": blocks,
    })


@staff_member_required(login_url="dashboard_login")
def services(request):
    services = Service.objects.order_by("name")

    return render(request, "dashboard/services.html", {
        "services": services,
    })

@require_POST
@staff_member_required(login_url="dashboard_login")
def delete_schedule_block(request, block_id):
    block = get_object_or_404(ScheduleBlock, id=block_id)
    block.delete()
    return redirect("dashboard_schedule")

@staff_member_required(login_url="dashboard_login")
def appointment_edit(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        form = AppointmentEditForm(request.POST, instance=appointment)

        if form.is_valid():
            form.save()
            messages.success(request, "Programarea a fost actualizată.")
            return redirect("dashboard_appointments")
    else:
        form = AppointmentEditForm(instance=appointment)

    return render(request, "dashboard/appointment_edit.html", {
        "form": form,
        "appointment": appointment,
    })

@require_POST
@staff_member_required(login_url="dashboard_login")
def appointment_delete(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.delete()

    messages.success(request, "Programarea a fost ștearsă.")
    return redirect("dashboard_appointments")

@staff_member_required(login_url="dashboard_login")
def services(request):
    services = Service.objects.order_by("name")

    return render(request, "dashboard/services.html", {
        "services": services,
    })

@staff_member_required(login_url="dashboard_login")
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Serviciul a fost adăugat.")
            return redirect("dashboard_services")
    else:
        form = ServiceForm()

    return render(request, "dashboard/service_form.html", {
        "form": form,
        "title": "Serviciu nou",
    })


@staff_member_required(login_url="dashboard_login")
def service_edit(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)

        if form.is_valid():
            form.save()
            messages.success(request, "Serviciul a fost actualizat.")
            return redirect("dashboard_services")
    else:
        form = ServiceForm(instance=service)

    return render(request, "dashboard/service_form.html", {
        "form": form,
        "title": "Editează serviciul",
        "service": service,
    })

@require_POST
@staff_member_required(login_url="dashboard_login")
def service_delete(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if service.appointments.exists():
        service.is_active = False
        service.save(update_fields=["is_active"])

        messages.warning(
            request,
            "Serviciul are programări asociate și nu poate fi șters. A fost dezactivat."
        )
    else:
        service.delete()
        messages.success(request, "Serviciul a fost șters.")

    return redirect("dashboard_services")