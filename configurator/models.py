from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """A base product / range, identified by its prefix (e.g. AR1002)."""
    prefix = models.CharField(max_length=20)
    family_name = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")

    class Meta:
        ordering = ["category__name", "prefix"]

    def __str__(self):
        return f"{self.prefix} — {self.family_name}"


class LookupOption(models.Model):
    """
    Generic code/label pair used for Driver, CRI, CCT, Beam, Body Colour,
    Option and Emergency lists — mirrors the two-column structure used
    throughout the Logic sheet (code in one column, description in the next).
    """
    ATTRIBUTE_CHOICES = [
        ("driver", "Driver Type"),
        ("cri", "CRI"),
        ("cct", "CCT"),
        ("beam", "Beam Angle"),
        ("body_colour", "Body Colour / RAL Finish"),
        ("option", "Option"),
        ("emergency", "Emergency Backup"),
        ("install_method", "Install Method"),
        ("lamp_type", "Lamp Type"),
        ("light_dist", "Light Distribution"),
        ("ip_rating", "IP Rating"),
        ("driver_mount", "Driver Mount"),
    ]

    attribute = models.CharField(max_length=20, choices=ATTRIBUTE_CHOICES)
    code = models.CharField(max_length=10)
    label = models.CharField(max_length=120)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["attribute", "sort_order", "label"]
        unique_together = ("attribute", "code")

    def __str__(self):
        return f"[{self.attribute}] {self.code} — {self.label}"


class GeneratedSKU(models.Model):
    """A saved record of a generated SKU + description. Rows from the same
    bulk generation run share a batch_id so they can be exported together."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="generated_skus")
    sku_code = models.CharField(max_length=200)
    description = models.TextField()
    tags = models.CharField(max_length=300, blank=True, default="")
    batch_id = models.CharField(max_length=40, db_index=True, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.sku_code
