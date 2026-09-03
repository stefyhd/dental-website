import phonenumbers

from django.db import transaction

from .models import Patient
from .patient_matching import find_same_person


def normalize_phone(phone):
    if hasattr(phone, "as_e164"):
        return phone.as_e164

    raw = str(phone).strip()

    try:
        parsed = phonenumbers.parse(raw, "RO")

        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164,
            )
    except phonenumbers.NumberParseException:
        pass

    return raw


def get_or_create_patient(name, phone, email=""):
    """
    Găsește fișa pacientului sau creează una nouă.

    Un număr de telefon poate avea mai multe fișe — părinte și copil. Deci
    nu căutăm doar după telefon, ci după telefon ȘI nume, cu numele
    comparat pe cuvinte: „Popescu Ana” și „Ana Popescu” sunt aceeași fișă.

    Dacă numele doar SEAMĂNĂ (o literă diferită), NU contopim și nu
    întrebăm pe nimeni — fișă nouă. Asemănarea o vede medicul în fișa
    pacientului, unde are butonul de contopire.
    """
    phone = normalize_phone(phone)
    name = (name or "").strip()
    email = (email or "").strip()

    existing = find_same_person(name, phone)

    if existing is None:
        existing, _created = Patient.objects.get_or_create(
            phone=phone,
            name=name,
            defaults={"email": email},
        )

    if email and not existing.email:
        existing.email = email
        existing.save(update_fields=["email"])

    return existing


@transaction.atomic
def merge_patients(source, target):
    """
    Mută tot din fișa `source` în `target` și o șterge pe `source`.

    Pentru cazul „Ana Radu” și „Ana Maria Radu” — aceeași persoană, două
    fișe. Programările se mută, ca să nu se piardă istoricul; observațiile
    se lipesc una după alta, ca să nu se piardă nimic scris de medic.
    """
    if source.pk == target.pk:
        return target

    source.appointments.update(patient=target)

    if source.email and not target.email:
        target.email = source.email

    if source.notes:
        if target.notes:
            target.notes = f"{target.notes}\n\n{source.notes}"
        else:
            target.notes = source.notes

    target.save(update_fields=["email", "notes"])
    source.delete()

    return target


def split_phone_initial(phone):
    try:
        parsed = phonenumbers.parse(str(phone), None)

        region = phonenumbers.region_code_for_number(parsed) or "RO"
        national_number = str(parsed.national_number)

        return [region, national_number]

    except phonenumbers.NumberParseException:
        return ["RO", str(phone)]