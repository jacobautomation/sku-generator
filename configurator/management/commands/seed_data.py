import json
from pathlib import Path

from django.core.management.base import BaseCommand

from configurator.models import Category, Product, LookupOption

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "seed_data.json"


class Command(BaseCommand):
    help = "Load Category / Product / LookupOption records extracted from the Logic sheet."

    def handle(self, *args, **options):
        with open(DATA_FILE) as f:
            data = json.load(f)

        LookupOption.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        for attribute, rows in data["lookups"].items():
            for i, row in enumerate(rows):
                LookupOption.objects.create(
                    attribute=attribute,
                    code=row["code"],
                    label=row["label"],
                    sort_order=i,
                )

        cat_cache = {}
        created = 0
        for p in data["products"]:
            cat_name = p["category"] or "UNCATEGORISED"
            if cat_name not in cat_cache:
                cat_cache[cat_name], _ = Category.objects.get_or_create(name=cat_name)
            Product.objects.create(
                prefix=p["prefix"],
                family_name=p["family_name"],
                category=cat_cache[cat_name],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {LookupOption.objects.count()} lookup options, "
            f"{len(cat_cache)} categories, {created} products."
        ))
