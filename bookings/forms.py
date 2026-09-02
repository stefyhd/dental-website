from django import forms
from .models import Appointment
from django import forms
from bookings.models import Appointment, ScheduleBlock, Service, WorkingHours


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["patient_name", "patient_phone", "patient_email"]
        widgets = {
            "patient_name": forms.TextInput(attrs={"placeholder": "Nume și prenume"}),
            "patient_phone": forms.TextInput(attrs={"placeholder": "Telefon"}),
            "patient_email": forms.EmailInput(attrs={"placeholder": "Email opțional"}),
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