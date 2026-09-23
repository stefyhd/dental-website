"""
Fluxul public de programare, în trei pași.

  1. /programari/          Ce te supără?      (descriere + categorie opțională)
  2. /programari/data/     Când vrei să vii?  (calendar + ore)
  3. /programari/detalii/  Cum te contactăm?  (nume, telefon, email)
     /programari/succes/   Confirmarea cererii

Ce ține fluxul legat: descrierea și categoria stau în sesiune (textul
liber n-are ce căuta într-un parametru GET), iar data și ora stau în URL
(ca butonul Înapoi să funcționeze și să nu apară avertismente de
retrimitere a formularului).

Serviciul NU e ales de pacient. Se pune automat consultația — prima
întâlnire cu medicul e oricum o consultație — iar medicul îl schimbă la
confirmare, din dashboard.
"""

from datetime import datetime, timedelta

from django.shortcuts import redirect, render
from django.utils import timezone

from .booking_utils import (
    generate_slots,
    get_alternative_slots,
    validate_booking,
)
from .calendar_utils import (
    HORIZON_DAYS,
    WEEKDAY_LABELS,
    month_grid,
    month_steps,
    next_open_day,
)
from .forms import AppointmentForm, ProblemForm
from .models import Appointment, Service, ServiceCategory
from .patient_utils import get_or_create_patient
from .telegram import notify_new_request


DRAFT = "booking_draft"

# Sub ora asta e dimineață, de la ea în sus e după-amiază. Doar pentru
# gruparea cartonașelor — 16 ore într-o grămadă nu se mai citesc.
NOON = 13


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


def parse_month(value, fallback):
    """'2026-09' -> (2026, 9). Cade pe luna curentă dacă nu se poate."""
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except (TypeError, ValueError):
        return fallback.year, fallback.month

    return parsed.year, parsed.month


def date_in_range(date):
    """
    Ziua e în intervalul în care pacientul are voie să se programeze?

    Verificarea stă AICI, nu în `validate_booking()`: aceea e folosită și
    de dashboard, iar medicul are voie să programeze oricât de departe.
    Limita de 30 de zile e o regulă a fluxului public, nu a rezervărilor.

    Fără ea, un URL scris de mână putea rezerva peste un an.
    """
    if not date:
        return False

    today = timezone.localdate()
    return today <= date <= today + timedelta(days=HORIZON_DAYS)


def default_service():
    """
    Serviciul pus pe cererile venite din site.

    Medicul bifează unul singur din pagina de servicii. Dacă n-a bifat
    niciunul, luăm cel mai scurt serviciu activ — e cea mai bună
    aproximare a unei consultații și ține agenda strânsă. Dacă nu există
    niciun serviciu activ, întoarcem None și pasul 3 refuză politicos.
    """
    return (
        Service.objects.filter(is_active=True, is_default=True).first()
        or Service.objects.filter(is_active=True).order_by("duration").first()
    )


def get_draft(request):
    """Ce a scris pacientul la pasul 1. Dicționar gol dacă n-a trecut pe-acolo."""
    draft = request.session.get(DRAFT)
    return draft if isinstance(draft, dict) else {}


def draft_category(draft):
    category_id = draft.get("category_id")
    if not category_id:
        return None

    return ServiceCategory.objects.filter(
        id=category_id, is_active=True
    ).first()


def split_slots(slots):
    """Orele, tăiate în dimineață și după-amiază."""
    morning = [slot for slot in slots if slot.hour < NOON]
    afternoon = [slot for slot in slots if slot.hour >= NOON]
    return morning, afternoon


# ------------------------------------------------------------------
# Pasul 1 — Ce te supără?
# ------------------------------------------------------------------

def booking(request):
    draft = get_draft(request)

    if request.method == "POST":
        form = ProblemForm(request.POST)

        if form.is_valid():
            category = form.cleaned_data["category"]

            request.session[DRAFT] = {
                "notes": form.cleaned_data["notes"],
                "category_id": category.id if category else None,
            }

            return redirect("booking_date")
    else:
        form = ProblemForm(initial={
            "notes": draft.get("notes", ""),
            "category": draft.get("category_id"),
        })

    return render(request, "bookings/booking.html", {
        "step": 1,
        "form": form,
    })


# ------------------------------------------------------------------
# Pasul 2 — Când vrei să vii?
# ------------------------------------------------------------------

def booking_date(request):
    draft = get_draft(request)

    # Fără descriere n-are rost pasul 2 — trimitem omul înapoi la început.
    if not draft.get("notes"):
        return redirect("booking")

    service = default_service()
    if not service:
        return render(request, "bookings/booking_date.html", {
            "step": 2,
            "no_service": True,
        })

    today = timezone.localdate()
    year, month = parse_month(request.GET.get("month"), today)

    # O zi din trecut sau de peste orizont se ignoră complet. Afișată cu
    # „nu mai sunt ore libere" ar minți: ziua nu e plină, e interzisă.
    selected_date = parse_date(request.GET.get("date"))

    if not date_in_range(selected_date):
        selected_date = None

    slots = generate_slots(selected_date, service) if selected_date else []

    morning, afternoon = split_slots(slots)
    previous_month, next_month = month_steps(year, month)

    # Scurtătura se calculează doar când chiar e nevoie de ea: fie n-a
    # ales încă nicio zi, fie ziua aleasă s-a dovedit plină.
    suggestion = None
    if not selected_date or not slots:
        suggestion = next_open_day(service, start=selected_date or today)

    return render(request, "bookings/booking_date.html", {
        "step": 2,
        "draft_notes": draft.get("notes", ""),
        "draft_category": draft_category(draft),
        "weeks": month_grid(year, month),
        "weekday_labels": WEEKDAY_LABELS,
        "month_label": datetime(year, month, 1),
        "previous_month": previous_month,
        "next_month": next_month,
        "selected_date": selected_date,
        "slots": slots,
        "morning": morning,
        "afternoon": afternoon,
        "suggestion": suggestion,
        "horizon_days": HORIZON_DAYS,
        "service": service,
    })


# ------------------------------------------------------------------
# Pasul 3 — Cum te contactăm?
# ------------------------------------------------------------------

def booking_details(request):
    draft = get_draft(request)

    if not draft.get("notes"):
        return redirect("booking")

    date = parse_date(request.GET.get("date"))
    selected_time = parse_time(request.GET.get("time"))

    if not date_in_range(date) or not selected_time:
        return redirect("booking_date")

    service = default_service()
    if not service:
        return redirect("booking_date")

    context = {
        "step": 3,
        "draft_notes": draft.get("notes", ""),
        "draft_category": draft_category(draft),
        "date": date,
        "time": selected_time,
        "service": service,
    }

    error = validate_booking(date, selected_time, service)

    if error:
        context.update({
            "booking_error": error,
            "alternatives": get_alternative_slots(date, service),
        })
        return render(request, "bookings/booking_form.html", context)

    context["form"] = AppointmentForm()
    return render(request, "bookings/booking_form.html", context)


def create_appointment(request):
    if request.method != "POST":
        return redirect("booking")

    draft = get_draft(request)

    if not draft.get("notes"):
        return redirect("booking")

    date = parse_date(request.POST.get("date"))
    selected_time = parse_time(request.POST.get("time"))

    if not date_in_range(date) or not selected_time:
        return redirect("booking_date")

    service = default_service()
    if not service:
        return redirect("booking_date")

    form = AppointmentForm(request.POST)

    # A doua verificare, cea care contează. Lista de ore afișată la pasul
    # 2 e doar o sugestie — între timp poate să fi luat altcineva ora, sau
    # cererea poate veni de oriunde, nu neapărat din pagina noastră.
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

        appointment = Appointment.objects.create(
            patient=patient,
            service=service,
            category=draft_category(draft),
            date=date,
            time=selected_time,
            notes=draft.get("notes", ""),
            status=Appointment.Status.PENDING,
        )

    
        notify_new_request(appointment)

        # Ciorna și-a făcut treaba. Dacă rămâne, următoarea programare
        # pornește cu textul celei vechi.
        request.session.pop(DRAFT, None)

        request.session["last_booking"] = appointment.id

        return redirect("booking_success")

    return render(request, "bookings/booking_form.html", {
        "step": 3,
        "form": form,
        "draft_notes": draft.get("notes", ""),
        "draft_category": draft_category(draft),
        "service": service,
        "date": date,
        "time": selected_time,
        "booking_error": booking_error,
        "alternatives": (
            get_alternative_slots(date, service) if booking_error else []
        ),
    })


# ------------------------------------------------------------------
# Confirmare
# ------------------------------------------------------------------

def booking_success(request):
    appointment_id = request.session.pop("last_booking", None)

    appointment = None
    if appointment_id:
        appointment = (
            Appointment.objects
            .select_related("service", "category")
            .filter(id=appointment_id)
            .first()
        )

    return render(request, "bookings/success.html", {
        "appointment": appointment,
    })