from django import forms

from .models import EnrollmentPayment


class EnrollmentPaymentForm(forms.ModelForm):
    class Meta:
        model = EnrollmentPayment
        fields = ["full_name", "email", "phone", "amount", "reference", "receipt"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name", "required": True}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "required": True}),
            "phone": forms.TextInput(attrs={"placeholder": "e.g. 08012345678", "required": True}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "required": True}),
            "reference": forms.TextInput(attrs={"placeholder": "Transfer reference (optional)"}),
            "receipt": forms.ClearableFileInput(attrs={}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reference"].required = False
        self.fields["receipt"].required = False
