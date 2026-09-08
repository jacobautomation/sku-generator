from django import forms
from django.db.models import Min

from .models import Product, LookupOption

SHAPE_CHOICES = [
    ("round", "Round (Ø)"),
    ("rectangular", "Rectangular (L x W)"),
]


def options_for(attribute):
    return LookupOption.objects.filter(attribute=attribute)


def unique_prefix_products():
    """
    The source workbook has multiple product/family names sharing the same
    prefix code (the SKU only ever includes the prefix, not the family
    name). The picker only offers one product per unique prefix so two
    different products never silently collapse onto the same SKU.
    """
    first_ids = Product.objects.values("prefix").annotate(first_id=Min("id")).values_list("first_id", flat=True)
    return Product.objects.filter(id__in=first_ids).select_related("category")


# ---------------------------------------------------------------------------
# Wizard steps — one small form per step, mirroring the real userform's
# STEP 1 OF 10 / PRODUCT / LAMP / DRIVER / CRI / CCT / BEAM / BODY /
# OPTION / EMERGENCY tab structure.
# ---------------------------------------------------------------------------

class Step1ProductForm(forms.Form):
    products = forms.ModelMultipleChoiceField(
        queryset=unique_prefix_products(),
        label="Products / Ranges",
        widget=forms.SelectMultiple(attrs={"size": 14}),
        help_text="Select one or more. Every selected product multiplies into the final batch.",
    )


class Step2InstallLampForm(forms.Form):
    install_method = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="Install Method")
    lamp_type = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="Lamp Type")
    wattage = forms.IntegerField(label="Wattage (W)", min_value=1, initial=22)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["install_method"].queryset = options_for("install_method")
        self.fields["lamp_type"].queryset = options_for("lamp_type")


class Step3DimensionsForm(forms.Form):
    shape = forms.ChoiceField(choices=SHAPE_CHOICES, label="Body Shape", initial="round")
    diameter = forms.IntegerField(label="Diameter Ø (mm)", min_value=1, initial=22, required=False)
    length = forms.IntegerField(label="Length (mm)", min_value=1, initial=22, required=False)
    width = forms.IntegerField(label="Width (mm)", min_value=1, initial=22, required=False)
    height = forms.IntegerField(label="Height (mm)", min_value=1, initial=22)
    lumen = forms.IntegerField(label="Lumen output (llm)", min_value=1, initial=2200)
    efficacy = forms.IntegerField(label="Efficacy (llm/W)", min_value=1, initial=100)

    def clean(self):
        cleaned = super().clean()
        shape = cleaned.get("shape")
        if shape == "round" and not cleaned.get("diameter"):
            self.add_error("diameter", "Required for a round body shape.")
        if shape == "rectangular" and (not cleaned.get("length") or not cleaned.get("width")):
            self.add_error("length", "Length and width are required for a rectangular body shape.")
        return cleaned


class Step4DriverForm(forms.Form):
    driver_mount = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="Driver Mount")
    drivers = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="Driver Type(s)", widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["driver_mount"].queryset = options_for("driver_mount")
        self.fields["drivers"].queryset = options_for("driver")


class Step5CRIForm(forms.Form):
    cris = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="CRI(s)", widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["cris"].queryset = options_for("cri")


class Step6CCTForm(forms.Form):
    ccts = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="CCT(s)", widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["ccts"].queryset = options_for("cct")


class Step7BeamForm(forms.Form):
    beams = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="Beam Angle(s)", widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["beams"].queryset = options_for("beam")


class Step8LightIPForm(forms.Form):
    light_dist = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="Light Distribution")
    ip_top = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="IP Rating — Top")
    ip_bottom = forms.ModelChoiceField(queryset=LookupOption.objects.none(), label="IP Rating — Bottom")
    ik_rating = forms.IntegerField(label="IK Rating", min_value=0, max_value=10, initial=8)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["light_dist"].queryset = options_for("light_dist")
        self.fields["ip_top"].queryset = options_for("ip_rating")
        self.fields["ip_bottom"].queryset = options_for("ip_rating")


class Step9BodyColourForm(forms.Form):
    body_colours = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="Body Colour(s) / RAL Finish",
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["body_colours"].queryset = options_for("body_colour")


class Step10OptionEmergencyForm(forms.Form):
    options = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="Option(s)", widget=forms.CheckboxSelectMultiple, required=False,
    )
    emergencies = forms.ModelMultipleChoiceField(
        queryset=LookupOption.objects.none(), label="Emergency Backup(s)", widget=forms.CheckboxSelectMultiple, required=False,
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["options"].queryset = options_for("option")
        self.fields["emergencies"].queryset = options_for("emergency")


class Step11TagsForm(forms.Form):
    tags = forms.CharField(
        label="Tags", required=False,
        help_text="Comma-separated tags applied to every row in this batch, e.g. \"new-2026, architectural-range, indoor\". Matches the real userform's TAGS page — used for catalog filtering, not part of the SKU or description text.",
        widget=forms.TextInput(attrs={"placeholder": "new-2026, architectural-range, indoor"}),
    )


# Step registry: (step number, url slug, title, tab label, form class)
WIZARD_STEPS = [
    (1, "product", "Product / Range", "PRODUCT", Step1ProductForm),
    (2, "install-lamp", "Install Method & Lamp Type", "LAMP", Step2InstallLampForm),
    (3, "dimensions", "Body Shape, Dimensions & Output", "DIMENSIONS", Step3DimensionsForm),
    (4, "driver", "Driver", "DRIVER", Step4DriverForm),
    (5, "cri", "CRI", "CRI", Step5CRIForm),
    (6, "cct", "CCT", "CCT", Step6CCTForm),
    (7, "beam", "Beam Angle", "BEAM", Step7BeamForm),
    (8, "light-ip", "Light Distribution & IP Rating", "IP/LIGHT", Step8LightIPForm),
    (9, "body-colour", "Body Colour", "BODY", Step9BodyColourForm),
    (10, "option-emergency", "Option & Emergency Backup", "OPTION/EMG", Step10OptionEmergencyForm),
    (11, "tags", "Tags", "TAGS", Step11TagsForm),
]
