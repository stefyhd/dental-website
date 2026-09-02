from django import forms
from bookings.models import Appointment, ScheduleBlock, Service, WorkingHours


class ManualAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "patient_name",
            "patient_phone",
            "patient_email",
            "service",
            "date",
            "time",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
        }


class AppointmentEditForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "patient_name",
            "patient_phone",
            "patient_email",
            "service",
            "date",
            "time",
            "status",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
        }


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
    class Meta:
        model = ScheduleBlock
        fields = ["date", "end_date", "start_time", "end_time", "all_day", "reason"]
        labels = {
            "date": "Data început",
            "end_date": "Data sfârșit",
            "start_time": "Ora început",
            "end_time": "Ora sfârșit",
            "all_day": "Toată ziua",
            "reason": "Motiv",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()

        start_date = cleaned.get("date")
        end_date = cleaned.get("end_date")

        if start_date and not end_date:
            cleaned["end_date"] = start_date

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "Data de sfârșit nu poate fi înaintea datei de început."
            )

        if not cleaned.get("all_day"):
            start = cleaned.get("start_time")
            end = cleaned.get("end_time")

            if not start or not end:
                raise forms.ValidationError(
                    "Completează ora de început și ora de sfârșit."
                )

            if start >= end:
                raise forms.ValidationError(
                    "Ora de sfârșit trebuie să fie după ora de început."
                )

        return cleaned