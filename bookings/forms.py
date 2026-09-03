import phonenumbers
from django import forms
from phonenumber_field.formfields import SplitPhoneNumberField

class AppointmentForm(forms.Form):
    patient_name = forms.CharField(
        max_length=120,
        label="Nume și prenume",
        widget=forms.TextInput(attrs={"placeholder": "Nume și prenume"}),
    )

    patient_phone = SplitPhoneNumberField(
        region="RO",
        label="Telefon",
    )

    patient_email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Email opțional"}),
    )

    def clean_patient_phone(self):
        phone = self.cleaned_data["patient_phone"]

        try:
            parsed = phonenumbers.parse(str(phone), None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        return phone