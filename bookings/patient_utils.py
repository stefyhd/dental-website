import phonenumbers

from .models import Patient


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
    phone = normalize_phone(phone)

    patient, created = Patient.objects.get_or_create(
        phone=phone,
        defaults={
            "name": name.strip(),
            "email": email.strip(),
        },
    )

    if not created and not patient.email and email:
        patient.email = email.strip()
        patient.save(update_fields=["email"])

    return patient

def split_phone_initial(phone):
    try:
        parsed = phonenumbers.parse(str(phone), None)

        region = phonenumbers.region_code_for_number(parsed) or "RO"
        national_number = str(parsed.national_number)

        return [region, national_number]

    except phonenumbers.NumberParseException:
        return ["RO", str(phone)]