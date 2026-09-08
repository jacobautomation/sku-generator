# SKU & Description Generator — Web App Demo

A working Django rebuild of the core engine from the original
`SKU_and_Description_Generator.xlsm` workbook — now as an actual **10-step
wizard**, matching the real userform's "STEP 1 OF 10" flow (Product → Lamp
→ Dimensions → Driver → CRI → CCT → Beam → IP/Light → Body Colour →
Option/Emergency) instead of one long page.

**Login required.** Username: `david` / Password: `12345`
(Also a Django admin/superuser — see Admin panel section below.)

## What's new in this version

- **Fixed a real performance bug in the Excel export.** Setting a custom
  row height per row (to fit each description's exact line count) turned
  out to be an openpyxl performance trap — its row-dimension collection
  does O(n) work per assignment, so it scaled O(n²): a 40,500-row export
  took over two minutes. Replaced with a single sheet-wide default row
  height (set once, O(1) regardless of size). Re-benchmarked: the same
  40,500-row export now takes ~3 seconds, and 86,400 rows takes ~7.7
  seconds. (An earlier attempt blamed per-cell alignment for this and
  "fixed" that instead — it wasn't the actual cause and made no
  difference; this was found by profiling each stage separately rather
  than guessing.)
- **Batch history**: "Batch history" link in the top bar of every page
  lists every batch you've ever generated (row count, timestamp), with
  View and Export links for each — nothing is lost once you leave the
  results page.
- **Product search**: Step 1's product picker (and the Body Colour step)
  now has a type-to-filter search box above the list — type e.g. `LS1003`
  and it filters the list live, matching the real userform's "Search
  PREFIX/Range" box.
- **Tags step**: a new Step 11, matching the real userform's TAGS page.
  Free-text, comma-separated tags applied to every row in the batch —
  stored and exported as their own column, kept separate from the SKU
  code and description text since tags function as catalog metadata, not
  descriptive copy.

## How it works

Walk through 10 steps, one attribute group per page, with a progress bar
and a tab row across the top (click any completed step to jump back and
change something — locked/future steps are greyed out until you reach
them). On the final step, hitting **Generate All Combinations** produces
one unique SKU + description row for every combination across your
selections — a 30,000+ row batch generates in under 2 seconds.

- **Multi-select steps** (Driver, CRI, CCT, Beam, Body Colour, Option,
  Emergency): these are the fields that actually appear in the real
  workbook's SKU code template (`SKU.bas`) — every value you pick
  multiplies into the batch, and the SKU stays guaranteed-unique.
- **Single-select steps** (Product picker aside): Install Method, Lamp
  Type, Driver Mount, Light Distribution, IP Top/Bottom, plus the numeric
  spec fields (wattage, dimensions, lumen, efficacy, IK rating) apply once
  to the whole batch — in the real workbook these only affect the
  description text, never the SKU code.
- **Products**: the picker shows one entry per unique prefix. The source
  workbook has some prefixes shared across multiple product names (e.g.
  `AR1002` covers two different fixtures) — since the SKU only encodes
  the prefix, only one product per prefix is offered so nothing collides.

There's no cap on batch size — select as much as you want. Before anything
actually generates, a **Review & Generate** page shows you the exact row
count and an estimated time, color-coded (green under ~20k, amber up to
~200k, red above that) so a "Select all" on multiple fields never
surprises you — you confirm before it commits. Generation itself writes
in 5,000-row chunks, so memory stays bounded even at millions of rows
instead of building one giant list first.

Tested at 270,000 rows: ~13s to generate, 100% unique SKU codes, memory
stayed under 150MB. For reference, 30,000 rows generates in under 2
seconds. Select-all on every field at once (all 213 products × every
attribute) computes out to ~4.9 million rows — the review page will flag
that clearly rather than let it run unannounced. If you deploy to Railway
with gunicorn, its default worker timeout is 30 seconds — bump that
(`gunicorn core.wsgi --timeout 120`) if people will routinely generate
very large batches.

**Excel export**: row height, column C word wrap, and full grid borders
are verified as actually present in the file's underlying style data (an
earlier version applied formatting in a way Excel silently ignored for
populated cells, so it sometimes didn't render after opening). Also fixed
an unrelated O(n²) bug — a per-row lookup that rescanned the whole sheet
on every row — that had made large exports far slower than necessary;
that fix alone cut a 9,600-row export from 8.8s to 1.2s. Tested at
135,000 rows: ~17s to export.

Every multi-select field (Products, Driver, CRI, CCT, Beam, Body Colour,
Option, Emergency) has **Select all / Clear** links above it, so you don't
have to click through dozens of checkboxes one at a time.

**Scope note (~80% cut):** not included, reserved for the full paid
build: multiple separate user accounts, the supplier costing/markup
engine, and true per-category dimension/lumen calculators.

Real data — 247 products (213 unique prefixes) across 15 categories, all
Driver / CRI / CCT / Beam / Body Colour / Option / Emergency values, and
the full 69-entry IP rating table — was extracted directly from the
workbook's `Logic` and `Settings` sheets.

## Run it locally

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

Open **http://127.0.0.1:8000/**, sign in as `david` / `12345`. It lands
you on Step 1 automatically.

The database is already migrated and seeded. To reload from scratch:

```bash
python manage.py seed_data
python manage.py create_demo_user
```

## Exporting

After the final step generates a batch, click **"Export full batch to
Excel"** — downloads a real `.xlsx` with columns `ItemCode / Short
Description / DetailedDescription / Category / Generated`, matching the
structure of the workbook's own `Output Template` sheet (minus the
accounting columns, out of scope for this demo).

## Admin panel (bonus — not in the original VBA tool)

`david` also has admin access: **http://127.0.0.1:8000/admin/** — add/edit
products and lookup values through a normal web UI, no code or VBA forms.

## Deploying to GitHub + Railway

This is already set up for it — `Procfile`, `requirements.txt`, Postgres
support, and whitenoise for static files are all in place and tested
(production settings, HTTPS redirect, admin static files, and Postgres
config were all verified working before this was packaged).

### 1. Push to GitHub

```bash
cd skuweb
git init
git add .
git commit -m "SKU generator demo"
```

Create a new empty repo on github.com (no README/license — you already
have files), then:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

### 2. Create the Railway project

1. [railway.app](https://railway.app) → **New Project** → **Deploy from
   GitHub repo** → pick the repo you just pushed.
2. Railway auto-detects Python and starts a build — let it fail once,
   that's expected (no database yet).
3. In the same project, **+ New** → **Database** → **Add PostgreSQL**.
   Railway automatically injects `DATABASE_URL` into your web service —
   no manual copying needed.

### 3. Set environment variables

On your web service → **Variables** tab, add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any long random string (Railway can generate one) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | your Railway domain, e.g. `sku-generator-production.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://` + that same domain |

You'll get the actual domain after step 4 (Railway assigns it), so come
back and fill in `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` once you have it —
the app will fail with a 400 error until these match.

### 4. Deploy and get a public URL

1. Railway should redeploy automatically once the database and variables
   are set. Watch the build logs for `release: python manage.py migrate`
   running successfully.
2. Web service → **Settings** → **Networking** → **Generate Domain**.
   Copy that URL into `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` above.

### 5. Seed the database (one-time)

The migration runs automatically, but the lookup data and login don't —
run these once via Railway's web shell (web service → **⋮** → open a
shell, or use the Railway CLI: `railway run python manage.py seed_data`):

```bash
python manage.py seed_data
python manage.py create_demo_user
```

**Change the password** while you're in there — `12345` was fine for a
local demo, not for a public URL:

```bash
python manage.py changepassword david
```

### 6. Send it

Visit the Railway domain yourself first to confirm it loads and you can
log in, then send David the URL + whatever username/password you set.




