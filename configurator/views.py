import itertools
import time
import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect

from .forms import WIZARD_STEPS
from .models import GeneratedSKU, LookupOption, Product


def build_dimension_string(shape, diameter, length, width, height):
    if shape == "round":
        return f"Nom. {diameter}(Ø)x{height}(H)"
    return f"{length}(L)x{width}(W)x{height}(H)"


def build_sku_code(product, driver, cri, cct, beam, body_colour, option, emergency):
    parts = [product.prefix, driver.code, cri.code, cct.code, beam.code, body_colour.code]
    sku = "-".join(str(p) for p in parts)
    tail = []
    if option:
        tail.append(option.code)
    if emergency:
        tail.append(emergency.code)
    if tail:
        sku += "." + ".".join(tail)
    return sku


def build_description(product, dimension, spec, install_method, lamp_type, driver_mount,
                       driver, cri, cct, beam, light_dist, body_colour,
                       ip_top, ip_bottom, option, emergency):
    sentence = (
        f"{install_method.label} {spec['wattage']}W {lamp_type.label} "
        f"{dimension} {product.category.name.title()}, "
        f"c/w {spec['lumen']}llm({light_dist.code}) {spec['efficacy']}llm/W, "
        f"{cct.label} {cri.label}, "
        f"{driver_mount.label} {driver.label}, "
        f"{light_dist.label} Light Distribution, {beam.label}, "
        f"{ip_top.code}, {ip_bottom.code}, IK{spec['ik_rating']:02d}, "
        f"{body_colour.label}"
    )
    extra_lines = []
    if option:
        extra_lines.append(f"+ {option.label}")
    if emergency:
        extra_lines.append(f"+ {emergency.label}")
    if extra_lines:
        sentence += "\n\n" + "\n".join(extra_lines)
    return sentence


def step_config_by_num(step_num):
    for cfg in WIZARD_STEPS:
        if cfg[0] == step_num:
            return cfg
    return None


def serialize_cleaned_data(cleaned_data):
    """Model instances/querysets aren't JSON-serialisable for the session,
    so store plain ids instead."""
    serialized = {}
    for name, value in cleaned_data.items():
        if hasattr(value, "model"):  # queryset from a ModelMultipleChoiceField
            serialized[name] = list(value.values_list("id", flat=True))
        elif hasattr(value, "pk"):  # single model instance
            serialized[name] = value.pk
        else:
            serialized[name] = value
    return serialized


@login_required
def home_redirect(request):
    step = request.session.get("wizard_max_step", 1)
    return redirect("wizard_step", step=step)


@login_required
def wizard_step(request, step):
    cfg = step_config_by_num(step)
    if cfg is None:
        raise Http404("No such step")
    step_num, slug, title, tab, FormClass = cfg

    wizard_data = request.session.get("wizard", {})
    max_step_reached = request.session.get("wizard_max_step", 1)

    if step_num > max_step_reached:
        return redirect("wizard_step", step=max_step_reached)

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            wizard_data[str(step_num)] = serialize_cleaned_data(form.cleaned_data)
            request.session["wizard"] = wizard_data
            request.session["wizard_max_step"] = max(max_step_reached, step_num + 1)
            request.session.modified = True

            if step_num == len(WIZARD_STEPS):
                return redirect("wizard_review")
            return redirect("wizard_step", step=step_num + 1)
    else:
        initial = wizard_data.get(str(step_num), {})
        form = FormClass(initial=initial)

    return render(request, "configurator/wizard_step.html", {
        "form": form,
        "step_num": step_num,
        "title": title,
        "total_steps": len(WIZARD_STEPS),
        "steps": WIZARD_STEPS,
        "max_step_reached": max_step_reached,
        "prev_step": step_num - 1 if step_num > 1 else None,
        "is_last": step_num == len(WIZARD_STEPS),
    })


@login_required
def wizard_reset(request):
    request.session.pop("wizard", None)
    request.session.pop("wizard_max_step", None)
    return redirect("wizard_step", step=1)


GENERATION_CHUNK_SIZE = 5000
# Rough measured throughput on the dev server (SQLite, bulk_create in
# chunks): used only to show a time estimate on the review page, not to
# enforce anything.
ESTIMATED_ROWS_PER_SECOND = 12000


def resolve_wizard_selection(wizard_data):
    s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11 = (wizard_data[str(i)] for i in range(1, 12))

    products = list(Product.objects.filter(id__in=s1["products"]).select_related("category"))
    install_method = LookupOption.objects.get(id=s2["install_method"])
    lamp_type = LookupOption.objects.get(id=s2["lamp_type"])
    wattage = s2["wattage"]

    dimension = build_dimension_string(s3["shape"], s3.get("diameter"), s3.get("length"), s3.get("width"), s3["height"])
    lumen, efficacy = s3["lumen"], s3["efficacy"]

    driver_mount = LookupOption.objects.get(id=s4["driver_mount"])
    drivers = list(LookupOption.objects.filter(id__in=s4["drivers"]))

    cris = list(LookupOption.objects.filter(id__in=s5["cris"]))
    ccts = list(LookupOption.objects.filter(id__in=s6["ccts"]))
    beams = list(LookupOption.objects.filter(id__in=s7["beams"]))

    light_dist = LookupOption.objects.get(id=s8["light_dist"])
    ip_top = LookupOption.objects.get(id=s8["ip_top"])
    ip_bottom = LookupOption.objects.get(id=s8["ip_bottom"])
    ik_rating = s8["ik_rating"]

    body_colours = list(LookupOption.objects.filter(id__in=s9["body_colours"]))

    options_list = list(LookupOption.objects.filter(id__in=s10["options"])) or [None]
    emergencies_list = list(LookupOption.objects.filter(id__in=s10["emergencies"])) or [None]

    tags = s11.get("tags", "").strip()

    total = len(products) * len(drivers) * len(cris) * len(ccts) * len(beams) * len(body_colours) \
        * len(options_list) * len(emergencies_list)

    return {
        "products": products, "install_method": install_method, "lamp_type": lamp_type,
        "wattage": wattage, "dimension": dimension, "lumen": lumen, "efficacy": efficacy,
        "driver_mount": driver_mount, "drivers": drivers, "cris": cris, "ccts": ccts, "beams": beams,
        "light_dist": light_dist, "ip_top": ip_top, "ip_bottom": ip_bottom, "ik_rating": ik_rating,
        "body_colours": body_colours, "options_list": options_list, "emergencies_list": emergencies_list,
        "tags": tags, "total": total,
        "counts": {
            "Products": len(products), "Drivers": len(drivers), "CRI": len(cris), "CCT": len(ccts),
            "Beam": len(beams), "Body Colour": len(body_colours),
            "Option": len(options_list) if options_list != [None] else 0,
            "Emergency": len(emergencies_list) if emergencies_list != [None] else 0,
        },
        "tags_display": tags or "(none)",
    }


def run_generation(resolved):
    """
    Generates and bulk-inserts rows in fixed-size chunks so memory stays
    bounded no matter how large the selection is — a 73-million-row worst
    case (select-all on every field) still streams through in constant
    memory rather than building one giant list first.
    """
    spec = {"wattage": resolved["wattage"], "lumen": resolved["lumen"],
            "efficacy": resolved["efficacy"], "ik_rating": resolved["ik_rating"]}

    batch_id = uuid.uuid4().hex
    t0 = time.perf_counter()
    buffer = []
    total_written = 0

    combos = itertools.product(
        resolved["products"], resolved["drivers"], resolved["cris"], resolved["ccts"],
        resolved["beams"], resolved["body_colours"], resolved["options_list"], resolved["emergencies_list"],
    )
    for (product, driver, cri, cct, beam, body_colour, option, emergency) in combos:
        sku_code = build_sku_code(product, driver, cri, cct, beam, body_colour, option, emergency)
        description = build_description(
            product, resolved["dimension"], spec, resolved["install_method"], resolved["lamp_type"],
            resolved["driver_mount"], driver, cri, cct, beam, resolved["light_dist"], body_colour,
            resolved["ip_top"], resolved["ip_bottom"], option, emergency,
        )
        buffer.append(GeneratedSKU(
            product=product, sku_code=sku_code, description=description,
            tags=resolved["tags"], batch_id=batch_id,
        ))

        if len(buffer) >= GENERATION_CHUNK_SIZE:
            GeneratedSKU.objects.bulk_create(buffer, batch_size=GENERATION_CHUNK_SIZE)
            total_written += len(buffer)
            buffer = []

    if buffer:
        GeneratedSKU.objects.bulk_create(buffer, batch_size=GENERATION_CHUNK_SIZE)
        total_written += len(buffer)

    gen_ms = round((time.perf_counter() - t0) * 1000, 2)
    return batch_id, total_written, gen_ms


@login_required
def wizard_review(request):
    wizard_data = request.session.get("wizard", {})
    if len(wizard_data) < len(WIZARD_STEPS):
        return redirect("wizard_step", step=request.session.get("wizard_max_step", 1))

    resolved = resolve_wizard_selection(wizard_data)
    total = resolved["total"]
    estimated_seconds = round(total / ESTIMATED_ROWS_PER_SECOND, 1)

    if request.method == "POST":
        batch_id, total_written, gen_ms = run_generation(resolved)
        request.session.pop("wizard", None)
        request.session.pop("wizard_max_step", None)
        request.session[f"gen_ms_{batch_id}"] = gen_ms
        return redirect("wizard_result", batch_id=batch_id)

    return render(request, "configurator/wizard_review.html", {
        "total": total,
        "counts": resolved["counts"],
        "tags_display": resolved["tags_display"],
        "estimated_seconds": estimated_seconds,
    })


@login_required
def wizard_result(request, batch_id):
    total_generated = GeneratedSKU.objects.filter(batch_id=batch_id).count()
    if total_generated == 0:
        raise Http404("Batch not found")
    preview = GeneratedSKU.objects.filter(batch_id=batch_id).select_related("product")[:50]
    gen_ms = request.session.pop(f"gen_ms_{batch_id}", None)

    return render(request, "configurator/wizard_result.html", {
        "batch_id": batch_id,
        "total_generated": total_generated,
        "gen_ms": gen_ms,
        "preview": preview,
    })


@login_required
def wizard_history(request):
    from django.db.models import Count, Min, Max

    batches = (
        GeneratedSKU.objects.exclude(batch_id="")
        .values("batch_id")
        .annotate(row_count=Count("id"), started=Min("created_at"), finished=Max("created_at"))
        .order_by("-started")
    )
    return render(request, "configurator/wizard_history.html", {"batches": batches})


@login_required
def export_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    batch = request.GET.get("batch", "")
    qs = GeneratedSKU.objects.select_related("product", "product__category").order_by("-created_at")
    if batch:
        qs = qs.filter(batch_id=batch)

    # Name the sheet after the product prefix (e.g. "LS1003") when the
    # batch covers a single product — matches what you'd actually be
    # looking at. Batches spanning multiple products fall back to
    # "Output" since a single sheet can't carry multiple names.
    distinct_prefixes = list(
        qs.order_by().values_list("product__prefix", flat=True).distinct()
    )
    if len(distinct_prefixes) == 1 and distinct_prefixes[0]:
        invalid_chars = set(r'[]:*?/\\')
        sheet_title = "".join(c for c in distinct_prefixes[0] if c not in invalid_chars)[:31] or "Output"
    else:
        sheet_title = "Output"

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    headers = ["ItemCode", "Short Description", "DetailedDescription", "Category", "Tags", "Generated"]
    ws.append(headers)

    thin = Side(style="thin", color="B0B0B0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill(start_color="2D3242", end_color="2D3242", fill_type="solid")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(vertical="top")
    ws.freeze_panes = "A2"

    # Column-level default styles turned out not to be reliable: inspecting
    # the actual XML showed openpyxl writes data cells with no style index
    # at all, and Excel does not consistently fall back to a column's
    # default style for populated cells (only reliably for blank ones) —
    # so wrap/border/height silently failed to render despite looking
    # correct in the raw <cols> definition.
    #
    # Setting cell.alignment and cell.border as two separate attribute
    # mutations per cell was also measured and found too slow at scale
    # (9,600 rows took 10+ seconds — each property assignment does its own
    # read-modify-write of that cell's style). A NamedStyle assigned via
    # cell.style = "name" is a single reference assignment instead, and
    # measured dramatically faster for the same result.
    from openpyxl.styles import NamedStyle

    wrap_style = NamedStyle(name="wrap_cell")
    wrap_style.alignment = Alignment(wrap_text=True, vertical="top")
    wrap_style.border = border
    wb.add_named_style(wrap_style)

    plain_style = NamedStyle(name="plain_cell")
    plain_style.alignment = Alignment(vertical="top")
    plain_style.border = border
    wb.add_named_style(plain_style)

    col_widths = {"A": 26, "B": 24, "C": 65, "D": 16, "E": 22, "F": 16}
    for col, w in col_widths.items():
        ws.column_dimensions[col].width = w

    # Fixed sheet-wide row height, applied once (not per row), so opening
    # the file always shows every row at this height regardless of size.
    ws.sheet_format.defaultRowHeight = 100

    rows_iter = qs.values_list(
        "sku_code", "product__family_name", "description",
        "product__category__name", "tags", "created_at",
    ).iterator(chunk_size=2000)

    r = 1  # header is row 1; incrementing manually avoids ws.max_row,
           # which rescans every cell on each call and turns this loop
           # quadratic at scale — that was the actual cause of the slowdown.
    for sku_code, family_name, description, category_name, tags, created_at in rows_iter:
        ws.append([sku_code, family_name, description, category_name, tags, created_at.strftime("%Y-%m-%d %H:%M")])
        r += 1
        for col_idx in range(1, len(headers) + 1):
            ws.cell(row=r, column=col_idx).style = "wrap_cell" if col_idx == 3 else "plain_cell"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    fname = f"generated_skus_{batch[:8]}.xlsx" if batch else "generated_skus_all.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    wb.save(response)
    return response
