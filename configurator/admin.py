from django.contrib import admin

from .models import Category, Product, LookupOption, GeneratedSKU


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("prefix", "family_name", "category")
    list_filter = ("category",)
    search_fields = ("prefix", "family_name")


@admin.register(LookupOption)
class LookupOptionAdmin(admin.ModelAdmin):
    list_display = ("attribute", "code", "label", "sort_order")
    list_filter = ("attribute",)
    search_fields = ("code", "label")
    ordering = ("attribute", "sort_order")


@admin.register(GeneratedSKU)
class GeneratedSKUAdmin(admin.ModelAdmin):
    list_display = ("sku_code", "product", "created_at")
    readonly_fields = ("created_at",)
