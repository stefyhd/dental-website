from datetime import datetime, time, timedelta

import phonenumbers
from rapidfuzz import fuzz

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.appointment_utils import appointment_has_ended, update_past_appointments
from bookings.models import Appointment, Patient, ScheduleBlock, Service, WorkingHours
from bookings.patient_utils import (
    get_or_create_patient,
    normalize_phone,
    split_phone_initial,
)
from bookings.schedule_utils import get_manual_time_choices

from .forms import (
    AppointmentEditForm,
    ManualAppointmentForm,
    PatientEditForm,
    ScheduleBlockForm,
    ServiceForm,
    WorkingHoursForm,
)
from django.forms import modelformset_factory
from bookings.schedule_utils import (
    get_manual_time_choices,
    get_schedule_time_choices,
)

SLOT_MINUTES = 30

@staff_member_required(login_url="dashboard_login")
def schedule_block_times(request):
    date_string = request.GET.get("date")

    try:
        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        selected_date = timezone.localdate()

    times = [
        value
        for value, _ in get_schedule_time_choices(selected_date)
    ]

    return JsonResponse({
        "times": times,
    })

def get_selected_date(request):
    date_string = request.GET.get("date")

    if not date_string:
        return timezone.localdate()

    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def build_agenda(selected_date):
    working_hours = WorkingHours.objects.filter(
        weekday=selected_date.weekday()
    ).first()

    appointments = list(
        Appointment.objects
        .filter(date=selected_date)
        .exclude(status=Appointment.Status.REJECTED)
        .select_related("patient", "service")
        .order_by("time", "id")
    )

    blocks = list(
        ScheduleBlock.objects
        .filter(date__lte=selected_date)
        .filter(
            Q(end_date__gte=selected_date) |
            Q(end_date__isnull=True, date=selected_date)
        )
    )

    if working_hours and not working_hours.is_closed:
        agenda_start = datetime.combine(
            selected_date,
            working_hours.opening_time,
        )
        agenda_end = datetime.combine(
            selected_date,
            working_hours.closing_time,
        )
    else:
        agenda_start = datetime.combine(selected_date, time(8, 0))
        agenda_end = datetime.combine(selected_date, time(19, 0))

    for appointment in appointments:
        start = datetime.combine(selected_date, appointment.time)
        end = start + timedelta(minutes=appointment.service.duration)

        agenda_start = min(agenda_start, start)
        agenda_end = max(agenda_end, end)

    for block in blocks:
        if block.all_day:
            continue

        start = datetime.combine(selected_date, block.start_time)
        end = datetime.combine(selected_date, block.end_time)

        agenda_start = min(agenda_start, start)
        agenda_end = max(agenda_end, end)

    agenda_start = agenda_start.replace(
        minute=(agenda_start.minute // SLOT_MINUTES) * SLOT_MINUTES,
        second=0,
        microsecond=0,
    )

    if agenda_end.minute % SLOT_MINUTES != 0:
        agenda_end = agenda_end.replace(
            minute=(agenda_end.minute // SLOT_MINUTES) * SLOT_MINUTES,
            second=0,
            microsecond=0,
        ) + timedelta(minutes=SLOT_MINUTES)

    rows = []
    current = agenda_start

    while current < agenda_end:
        slot_end = current + timedelta(minutes=SLOT_MINUTES)

        block_matches = []

        for block in blocks:
            if block.all_day:
                block_matches.append(block)
                continue

            block_start = datetime.combine(selected_date, block.start_time)
            block_end = datetime.combine(selected_date, block.end_time)

            if current < block_end and slot_end > block_start:
                block_matches.append(block)

        active_appointments = []

        for appointment in appointments:
            appointment_start = datetime.combine(
                selected_date,
                appointment.time,
            )

            appointment_end = appointment_start + timedelta(
                minutes=appointment.service.duration
            )

            if current < appointment_end and slot_end > appointment_start:
                active_appointments.append(appointment)

        if block_matches:
            rows.append({
                "time": current.time(),
                "kind": "block",
                "blocks": block_matches,
            })

        for appointment in active_appointments:
            appointment_start = datetime.combine(
                selected_date,
                appointment.time,
            )

            rows.append({
                "time": current.time(),
                "kind": "appointment",
                "appointment": appointment,
                "starts_here": appointment_start == current,
                "has_ended": appointment_has_ended(appointment),
                "status_choices": get_status_choices(appointment),
            })

        if not block_matches and not active_appointments:
            rows.append({
                "time": current.time(),
                "kind": "free",
            })

        current += timedelta(minutes=SLOT_MINUTES)

    return rows

@staff_member_required(login_url="dashboard_login")
def manual_day_data(request):
    date_string = request.GET.get("date")

    try:
        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        selected_date = timezone.localdate()

    update_past_appointments()

    agenda = []

    for row in build_agenda(selected_date):
        data = {
            "time": row["time"].strftime("%H:%M"),
            "kind": row["kind"],
        }

        if row["kind"] == "appointment":
            appointment = row["appointment"]

            data.update({
                "name": appointment.patient.name,
                "service": appointment.service.name,
                "notes": appointment.notes,
                "status": appointment.get_status_display(),
                "starts_here": row["starts_here"],
            })

        elif row["kind"] == "block":
            data["reasons"] = [
                block.reason or "Interval blocat"
                for block in row["blocks"]
            ]

        agenda.append(data)

    return JsonResponse({
        "date": selected_date.isoformat(),
        "times": [
            value
            for value, _ in get_manual_time_choices(selected_date)
        ],
        "agenda": agenda,
    })


@staff_member_required(login_url="dashboard_login")
def home(request):
    update_past_appointments()
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
            phone = normalize_phone(form.cleaned_data["patient_phone"])
            patient = None

            patient_id = form.cleaned_data.get("patient_id")

            if patient_id:
                selected_patient = Patient.objects.filter(id=patient_id).first()

                if selected_patient and selected_patient.phone == phone:
                    patient = selected_patient

            if patient is None:
                patient = get_or_create_patient(
                    form.cleaned_data["patient_name"],
                    form.cleaned_data["patient_phone"],
                    form.cleaned_data["patient_email"],
                )

            follow_up = None
            follow_up_id = form.cleaned_data.get("follow_up_of")

            if follow_up_id:
                follow_up = Appointment.objects.filter(id=follow_up_id).first()

            appointment = Appointment.objects.create(
                patient=patient,
                service=form.cleaned_data["service"],
                date=form.cleaned_data["date"],
                time=form.cleaned_data["time"],
                notes=form.cleaned_data["notes"],
                follow_up_of=follow_up,
                status=Appointment.Status.CONFIRMED,
            )

            return redirect(
                f"{reverse('dashboard_home')}?date={appointment.date}"
            )

    else:
        initial = {
            "date": request.GET.get("date") or timezone.localdate(),
            "time": request.GET.get("time") or "",
        }

        follow_up_id = request.GET.get("follow_up_of")

        if follow_up_id:
            original = get_object_or_404(
                Appointment.objects.select_related("patient", "service"),
                id=follow_up_id,
            )

            follow_up_date = original.date + timedelta(days=7)
            candidate_time = original.time.strftime("%H:%M")

            valid_times = {
                value
                for value, _ in get_manual_time_choices(follow_up_date)
            }

            if candidate_time not in valid_times:
                candidate_time = ""

            initial.update({
                "patient_id": original.patient.id,
                "patient_name": original.patient.name,
                "patient_phone": split_phone_initial(original.patient.phone),
                "patient_email": original.patient.email,
                "service": original.service.id,
                "date": follow_up_date,
                "time": candidate_time,
                "follow_up_of": original.id,
            })

        form = ManualAppointmentForm(initial=initial)

    return render(request, "dashboard/manual_appointment.html", {
        "form": form,
    })

@staff_member_required(login_url="dashboard_login")
def appointments(request):
    update_past_appointments()
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

@staff_member_required(login_url="dashboard_login")
def appointment_delete(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "service"),
        id=appointment_id,
    )

    return_date = request.GET.get("return_date") or request.POST.get("return_date")
    error = None

    if request.method == "POST":
        password = request.POST.get("password", "")

        if not request.user.check_password(password):
            error = "Parola este incorectă."
        else:
            appointment.delete()

            if return_date:
                return redirect(
                    f"{reverse('dashboard_home')}?date={return_date}"
                )

            return redirect("dashboard_appointments")

    return render(
        request,
        "dashboard/appointment_delete_confirm.html",
        {
            "appointment": appointment,
            "return_date": return_date,
            "error": error,
        },
    )

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

#fuzzy search
@staff_member_required(login_url="dashboard_login")
def patient_search(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"patients": []})

    query_normalized = query.casefold()
    matches = []

    for patient in Patient.objects.all():
        score = fuzz.token_set_ratio(
            query_normalized,
            patient.name.casefold(),
        )

        if score < 60:
            continue

        country = "RO"
        national_number = patient.phone

        try:
            parsed = phonenumbers.parse(patient.phone, None)
            country = phonenumbers.region_code_for_number(parsed) or "RO"
            national_number = str(parsed.national_number)
        except phonenumbers.NumberParseException:
            pass

        matches.append({
            "id": patient.id,
            "name": patient.name,
            "phone": patient.phone,
            "email": patient.email,
            "country": country,
            "national_number": national_number,
            "score": score,
        })

    matches.sort(key=lambda patient: patient["score"], reverse=True)

    return JsonResponse({
        "patients": matches[:5],
    })

@staff_member_required(login_url="dashboard_login")
def patients(request):
    query = request.GET.get("q", "").strip()

    patients_query = Patient.objects.all()

    if query:
        patients_query = patients_query.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    return render(request, "dashboard/patients.html", {
        "patients": patients_query,
        "query": query,
    })


@staff_member_required(login_url="dashboard_login")
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        form = PatientEditForm(request.POST, instance=patient)

        if form.is_valid():
            form.save()
            messages.success(request, "Fișa pacientului a fost actualizată.")
            return redirect("patient_detail", patient_id=patient.id)
    else:
        form = PatientEditForm(instance=patient)

    history = (
        patient.appointments
        .select_related("service")
        .order_by("-date", "-time")
    )

    return render(request, "dashboard/patient_detail.html", {
        "patient": patient,
        "form": form,
        "history": history,
    })

@require_POST
@staff_member_required(login_url="dashboard_login")
def refresh_statuses(request):
    updated = update_past_appointments()

    return JsonResponse({
        "updated": updated,
    })

@require_POST
@staff_member_required(login_url="dashboard_login")
def appointment_status(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("service"),
        id=appointment_id,
    )

    status = request.POST.get("status")
    allowed = {value for value, _ in get_status_choices(appointment)}

    if status not in allowed:
        return HttpResponseBadRequest("Status invalid.")

    appointment.status = status
    appointment.save(update_fields=["status"])

    return_date = request.POST.get("return_date")
    url = reverse("dashboard_home")

    if return_date:
        url += f"?date={return_date}"

    return redirect(url)

def get_status_choices(appointment):
    if appointment_has_ended(appointment):
        return [
            (Appointment.Status.COMPLETED, "Finalizată"),
            (Appointment.Status.NO_SHOW, "Neprezentat"),
            (Appointment.Status.CANCELLED, "Anulată"),
        ]

    if appointment.status in [
        Appointment.Status.PENDING,
        Appointment.Status.REJECTED,
    ]:
        return [
            (Appointment.Status.PENDING, "În așteptare"),
            (Appointment.Status.CONFIRMED, "Confirmată"),
            (Appointment.Status.REJECTED, "Respinsă"),
            (Appointment.Status.CANCELLED, "Anulată"),
        ]

    return [
        (Appointment.Status.CONFIRMED, "Confirmată"),
        (Appointment.Status.CANCELLED, "Anulată"),
    ]