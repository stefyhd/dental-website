from datetime import date as date_type, datetime

import phonenumbers
from django import forms
from django.utils import timezone
from phonenumber_field.formfields import SplitPhoneNumberField

from bookings.appointment_utils import appointment_has_ended
from bookings.models import Appointment, Patient, ScheduleBlock, Service, WorkingHours
from bookings.patient_utils import split_phone_initial
from bookings.schedule_utils import (
    get_manual_time_choices,
    get_schedule_time_choices,
)

class ManualAppointmentForm(forms.Form):
    patient_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    follow_up_of = forms.IntegerField(required=False, widget=forms.HiddenInput())

    patient_name = forms.CharField(
        max_length=120,
        label="Nume pacient",
    )

    patient_phone = SplitPhoneNumberField(
        region="RO",
        label="Telefon",
    )

    patient_email = forms.EmailField(
        required=False,
        label="Email",
    )

    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        label="Serviciu",
    )

    date = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    time = forms.ChoiceField(
        label="Ora",
        choices=[],
    )

    notes = forms.CharField(
        required=False,
        label="Observații consultație",
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Ex: Implant 26, control vindecare...",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        raw_date = self.data.get("date") if self.is_bound else self.initial.get("date")

        if isinstance(raw_date, date_type):
            selected_date = raw_date
        else:
            try:
                selected_date = date_type.fromisoformat(str(raw_date))
            except (TypeError, ValueError):
                selected_date = timezone.localdate()

        self.fields["time"].choices = [
            ("", "Alege ora"),
            *get_manual_time_choices(selected_date),
        ]

    def clean_patient_phone(self):
        phone = self.cleaned_data["patient_phone"]

        try:
            parsed = phonenumbers.parse(str(phone), None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        return phone

    def clean_time(self):
        value = self.cleaned_data["time"]
        return datetime.strptime(value, "%H:%M").time()

class AppointmentEditForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["service", "date", "time", "status", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            return

        if appointment_has_ended(self.instance):
            choices = [
                (Appointment.Status.COMPLETED, "Finalizată"),
                (Appointment.Status.NO_SHOW, "Neprezentat"),
                (Appointment.Status.CANCELLED, "Anulată"),
            ]

            if self.instance.status == Appointment.Status.REJECTED:
                choices.append(
                    (Appointment.Status.REJECTED, "Respinsă")
                )

            self.fields["status"].choices = choices

        elif self.instance.status == Appointment.Status.PENDING:
            self.fields["status"].choices = [
                (Appointment.Status.PENDING, "În așteptare"),
                (Appointment.Status.CONFIRMED, "Confirmată"),
                (Appointment.Status.REJECTED, "Respinsă"),
                (Appointment.Status.CANCELLED, "Anulată"),
            ]

        else:
            self.fields["status"].choices = [
                (Appointment.Status.CONFIRMED, "Confirmată"),
                (Appointment.Status.CANCELLED, "Anulată"),
            ]


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "duration", "price", "is_active"]


class WorkingHoursForm(forms.ModelForm):
    class Meta:
        model = WorkingHours
        fields = ["opening_time", "closing_time", "is_closed"]
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }


class ScheduleBlockForm(forms.ModelForm):
    start_time = forms.ChoiceField(
        label="Ora început",
        choices=[],
        required=False,
    )

    end_time = forms.ChoiceField(
        label="Ora sfârșit",
        choices=[],
        required=False,
    )

    class Meta:
        model = ScheduleBlock
        fields = [
            "date",
            "end_date",
            "start_time",
            "end_time",
            "all_day",
            "reason",
        ]

        labels = {
            "date": "Data început",
            "end_date": "Data sfârșit",
            "all_day": "Toată ziua",
            "reason": "Motiv",
        }

        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        raw_date = (
            self.data.get("date")
            if self.is_bound
            else self.initial.get("date")
            or getattr(self.instance, "date", None)
            or timezone.localdate()
        )

        if isinstance(raw_date, date_type):
            selected_date = raw_date
        else:
            try:
                selected_date = date_type.fromisoformat(str(raw_date))
            except (TypeError, ValueError):
                selected_date = timezone.localdate()

        choices = [
            ("", "--:--"),
            *get_schedule_time_choices(selected_date),
        ]

        self.fields["start_time"].choices = choices
        self.fields["end_time"].choices = choices

    def clean_start_time(self):
        value = self.cleaned_data["start_time"]

        if not value:
            return None

        return datetime.strptime(value, "%H:%M").time()

    def clean_end_time(self):
        value = self.cleaned_data["end_time"]

        if not value:
            return None

        return datetime.strptime(value, "%H:%M").time()

    def clean(self):
        cleaned = super().clean()

        start_date = cleaned.get("date")
        end_date = cleaned.get("end_date")
        all_day = cleaned.get("all_day")

        if start_date and not end_date:
            cleaned["end_date"] = start_date

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "Data de sfârșit nu poate fi înaintea datei de început."
            )

        if not all_day:
            start = cleaned.get("start_time")
            end = cleaned.get("end_time")

            if not start or not end:
                raise forms.ValidationError(
                    "Selectează ora de început și ora de sfârșit."
                )

            if start >= end:
                raise forms.ValidationError(
                    "Ora de sfârșit trebuie să fie după ora de început."
                )

        return cleaned

class PatientEditForm(forms.ModelForm):
    phone = SplitPhoneNumberField(
        region="RO",
        label="Telefon",
    )

    class Meta:
        model = Patient
        fields = ["name", "phone", "email", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={
                "rows": 7,
                "placeholder": "Observații generale despre pacient...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk and self.instance.phone:
            self.initial["phone"] = split_phone_initial(self.instance.phone)

    def clean_phone(self):
        return self.cleaned_data["phone"].as_e164