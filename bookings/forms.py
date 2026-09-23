import phonenumbers
from django import forms
from phonenumber_field.formfields import SplitPhoneNumberField

from .models import ServiceCategory


class ProblemForm(forms.Form):
    """
    Pasul 1: pacientul scrie cu cuvintele lui ce-l supără.

    Nu i se cere să aleagă un serviciu. Omul cu măseaua umflată nu știe
    ce e o „obturație fizionomică" — știe că îl doare. Categoria e
    opțională, doar ca indiciu; serviciul îl stabilește medicul la
    confirmare.
    """

    notes = forms.CharField(
        label="Ce te supără?",
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": (
                "De exemplu: mă doare o măsea jos în dreapta de vreo trei "
                "zile, mai tare noaptea și când beau ceva rece."
            ),
        }),
        error_messages={
            "min_length": "Scrie câteva cuvinte, ca să știm la ce să ne așteptăm.",
            "required": "Scrie câteva cuvinte, ca să știm la ce să ne așteptăm.",
        },
    )

    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.none(),
        required=False,
        empty_label=None,
        label="Știi deja de ce ai nevoie?",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Interogarea stă în __init__, nu la nivel de clasă: altfel se
        # evaluează o singură dată, la pornirea procesului, și categoriile
        # adăugate ulterior din dashboard n-ar mai apărea.
        self.fields["category"].queryset = (
            ServiceCategory.objects.filter(is_active=True)
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # SplitPhoneNumberField e un MultiWidget: [0] = țara, [1] = numărul.
        # Placeholder-ul nu se poate pune din declarația câmpului, doar aici.
        self.fields["patient_phone"].widget.widgets[1].attrs.update({
            "placeholder": "7xx xxx xxx",
        })

    def clean_patient_phone(self):
        phone = self.cleaned_data["patient_phone"]

        try:
            parsed = phonenumbers.parse(str(phone), None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Numărul de telefon nu este valid.")

        return phone