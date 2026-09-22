from decimal import Decimal

from django import forms

# Applied to every network/provider-style ChoiceField so the frontend
# (static/js/glab-select.js) can progressively enhance the plain <select>
# into a custom dropdown with colored network/provider badges, instead of
# the browser's bare native control.
GLAB_SELECT_ATTRS = {"data-glab-select": "1"}

NETWORK_CHOICES = [
    ("mtn", "MTN"),
    ("glo", "Glo"),
    ("airtel", "Airtel"),
    ("etisalat", "9mobile"),
]

NETWORK_DATA_CHOICES = [
    ("mtn-data", "MTN Data"),
    ("glo-data", "Glo Data"),
    ("airtel-data", "Airtel Data"),
    ("etisalat-data", "9mobile Data"),
]

CABLE_CHOICES = [
    ("dstv", "DStv"),
    ("gotv", "GOtv"),
    ("startimes", "StarTimes"),
]

ELECTRICITY_CHOICES = [
    ("ikeja-electric", "Ikeja Electric"),
    ("eko-electric", "Eko Electric"),
    ("kano-electric", "Kano Electric"),
    ("portharcourt-electric", "Port Harcourt Electric"),
    ("jos-electric", "Jos Electric"),
    ("ibadan-electric", "Ibadan Electric (IBEDC)"),
    ("kaduna-electric", "Kaduna Electric"),
    ("abuja-electric", "Abuja Electric (AEDC)"),
    ("enugu-electric", "Enugu Electric (EEDC)"),
    ("benin-electric", "Benin Electric (BEDC)"),
]

METER_TYPE_CHOICES = [("prepaid", "Prepaid"), ("postpaid", "Postpaid")]

EDUCATION_CHOICES = [
    ("waec-registration", "WAEC Registration PIN"),
    ("waec", "WAEC Result Checker PIN"),
    ("jamb", "JAMB PIN"),
]


class AirtimeForm(forms.Form):
    network = forms.ChoiceField(choices=NETWORK_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={"placeholder": "08012345678"}))
    amount = forms.DecimalField(min_value=50, max_digits=10, decimal_places=2)


class DataForm(forms.Form):
    network = forms.ChoiceField(choices=NETWORK_DATA_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={"placeholder": "08012345678"}))
    variation_code = forms.CharField(widget=forms.HiddenInput())
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=10, decimal_places=2, widget=forms.HiddenInput())


class CableVerifyForm(forms.Form):
    provider = forms.ChoiceField(choices=CABLE_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    smartcard_number = forms.CharField(max_length=20)


class CablePurchaseForm(forms.Form):
    provider = forms.ChoiceField(choices=CABLE_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    smartcard_number = forms.CharField(max_length=20)
    variation_code = forms.CharField()
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=10, decimal_places=2, widget=forms.HiddenInput())


class ElectricityVerifyForm(forms.Form):
    provider = forms.ChoiceField(choices=ELECTRICITY_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    meter_number = forms.CharField(max_length=20)
    meter_type = forms.ChoiceField(choices=METER_TYPE_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))


class ElectricityPurchaseForm(forms.Form):
    provider = forms.ChoiceField(choices=ELECTRICITY_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    meter_number = forms.CharField(max_length=20)
    meter_type = forms.ChoiceField(choices=METER_TYPE_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    amount = forms.DecimalField(min_value=500, max_digits=10, decimal_places=2)
    phone = forms.CharField(max_length=15)


class EducationForm(forms.Form):
    exam_type = forms.ChoiceField(choices=EDUCATION_CHOICES, widget=forms.Select(attrs=GLAB_SELECT_ATTRS))
    phone = forms.CharField(max_length=15)
    quantity = forms.IntegerField(min_value=1, max_value=10, initial=1)
