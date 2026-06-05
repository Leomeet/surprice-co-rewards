# Surprice Co Rewards — Developer Book

## Stack Overview

| Layer | Technology |
|---|---|
| Backend | Django 4.2 (Python) |
| Database | PostgreSQL (ElephantSQL hosted) |
| WhatsApp | AiSensy Campaign API |
| Frontend | Django Templates + Bootstrap 5.3.2 CDN |
| Deployment | Vercel |

---

## 1. Prerequisites

- Python 3.10+
- pip
- Git
- (Optional) `psql` CLI for database inspection

Check versions:
```bash
python3 --version
pip --version
```

---

## 2. Local Environment Setup

### Activate the existing virtual environment
```bash
cd /Users/leomeet/Projects/Parekh/surprice-co-rewards
source .venv/bin/activate
```

### Or create a fresh virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

> ⚠️ Python 3.14 can't build `psycopg2-binary` from source. Install core packages directly:

```bash
pip install Django==4.2.5 django-cors-headers requests phonenumbers python-dateutil
pip install "psycopg[binary]"   # psycopg3 — works on Python 3.14
```

### Verify installation
```bash
python -c "import django; print(django.__version__)"
# Expected: 4.2.5
```

---

## 3. Database

**Local dev:** SQLite (configured in `reward/settings.py`). No setup needed — the `db.sqlite3` file is created automatically on first migrate.

**Production:** PostgreSQL via environment variables (see section 16 for env var setup).

> ⚠️ **Note:** The original ElephantSQL host (`trumpet.db.elephantsql.com`) shut down in January 2025 and is no longer accessible. A new PostgreSQL provider will be needed for production deployment.

### Test database connection
```bash
python manage.py dbshell
# Opens sqlite3 shell locally. Type .quit to exit.
```

---

## 4. Local Development Fix

> **Important:** `DEBUG = False` is set in `settings.py`. For local development, temporarily set it to `True` so Django serves static files and shows error pages properly.

Edit `reward/settings.py`:
```python
DEBUG = True
```

Remember to revert before committing.

---

## 5. Run Migrations

Apply all database migrations (run once after setup, and after any model changes):
```bash
python manage.py migrate
```

Check migration status:
```bash
python manage.py showmigrations
```

Create new migrations after model changes:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 6. Create a Superuser (Admin)

The admin account manages users, products, and points from the web UI:
```bash
python manage.py createsuperuser
# Prompts: Username, Password
```

Log in at: `http://localhost:8000/admin/`

---

## 7. Seed Products

Products must exist before the Add Points form works. Add them via Django shell:
```bash
python manage.py shell
```

```python
from users.models import Product

Product.objects.create(name="Gold Wash", point_value=100)
Product.objects.create(name="Silver Wash", point_value=50)
Product.objects.create(name="Basic Wash", point_value=20)

# Verify
print(list(Product.objects.values()))
exit()
```

Or add products directly from the Django admin at `http://localhost:8000/admin/users/product/add/`.

---

## 8. Run the Development Server

```bash
python manage.py runserver
```

App is available at: `http://localhost:8000`

Run on a custom port:
```bash
python manage.py runserver 8080
```

---

## 9. URL Map

| URL | View | Access |
|---|---|---|
| `/` | Home / Dashboard | Authenticated users |
| `/login/` | Login page | Public |
| `/logout/` | Logout | Authenticated |
| `/register/` | Register new user | Public |
| `/addpoint/` | Add points to a user | Admin only |
| `/update_points/<user_id>/<username>/` | Edit user points | Admin only |
| `/delete_points/<user_id>/<username>/` | Deduct user points | Admin only |
| `/admin/` | Django admin panel | Superuser only |

---

## 10. WhatsApp Integration (AiSensy)

WhatsApp messages are sent automatically on three events:

| Event | Campaign Name | Template Params |
|---|---|---|
| Points added | `surprise rewards add` | username, previous points, new total |
| Points updated | `surprise rewards update` | username, new points |
| Points deducted | `surprise rewards delete` | username, deducted amount, remaining total |

The integration lives in `users/views.py` → `send_api_request()`.

**Provider:** AiSensy  
**Endpoint:** `https://backend.aisensy.com/campaign/t1/api/v2`  
**Phone format:** `+91` prefix is prepended to the `mobile` field stored on the user.

To test WhatsApp messages locally, a user must have a valid `mobile` number (10 digits, no country code) stored in their profile.

---

## 11. Django Admin — Quick Reference

```bash
# Access the admin panel
open http://localhost:8000/admin/
```

From admin you can:
- Add / edit / delete **CustomUser** records
- Add / edit / delete **Product** records (name + point value)
- View / edit **Points** records directly

---

## 12. Useful Management Commands

```bash
# Interactive Python shell with Django context loaded
python manage.py shell

# Check for any project issues
python manage.py check

# View all registered URL patterns
python manage.py show_urls   # requires django-extensions (not currently installed)

# Collect static files (required for Vercel deployment)
python manage.py collectstatic --noinput

# Reset a user's password via shell
python manage.py shell
>>> from users.models import CustomUser
>>> u = CustomUser.objects.get(username='someuser')
>>> u.set_password('newpassword')
>>> u.save()
>>> exit()
```

---

## 13. Common Django Shell Queries

```python
python manage.py shell

# List all non-admin users with their points
from django.db.models import Sum
from users.models import CustomUser
users = CustomUser.objects.exclude(is_superuser=True).annotate(total=Sum('points__total_points')).values('username','mobile','total')
for u in users: print(u)

# Check a specific user's points
from users.models import Points
Points.objects.get(host__username='someuser').total_points

# List all products and their point values
from users.models import Product
list(Product.objects.values())

exit()
```

---

## 14. Models Reference

### CustomUser
| Field | Type | Notes |
|---|---|---|
| `username` | CharField (unique) | Used for login |
| `mobile` | CharField | 10-digit number, no country code |
| `email` | EmailField (unique, optional) | |
| `first_name`, `last_name` | CharField | Optional |
| `is_staff` | Boolean | Access to admin panel |
| `is_superuser` | Boolean | Full admin privileges |

### Points
| Field | Type | Notes |
|---|---|---|
| `host` | FK → CustomUser | One-to-one per user |
| `total_points` | IntegerField | Cumulative points balance |

### Product
| Field | Type | Notes |
|---|---|---|
| `name` | CharField | Product/service name |
| `point_value` | IntegerField | Points awarded per unit |

---

## 15. Deployment (Vercel)

The app deploys automatically to Vercel via `vercel.json`.

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy (from project root)
vercel

# Deploy to production
vercel --prod
```

Static files must be collected before deployment:
```bash
python manage.py collectstatic --noinput
```

---

## 16. Security Notes (To Fix)

These are currently hardcoded in the repo and should be moved to environment variables:

- `SECRET_KEY` in `reward/settings.py`
- Database credentials (`NAME`, `USER`, `PASSWORD`, `HOST`) in `reward/settings.py`
- AiSensy `apiKey` in `users/views.py`
- `DEBUG = False` but `ALLOWED_HOSTS = ["*"]` — overly permissive

Recommended fix — create a `.env` file and load it with `python-decouple` or `django-environ`:
```bash
pip install python-decouple
```

```env
# .env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=abvszfjp
DB_USER=abvszfjp
DB_PASSWORD=your-password
DB_HOST=trumpet.db.elephantsql.com
AISENSY_API_KEY=your-api-key
```

---

## 17. Full Fresh Start Checklist

```bash
# 1. Clone and enter project
cd /Users/leomeet/Projects/Parekh/surprice-co-rewards

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Local dev) Temporarily set DEBUG=True in reward/settings.py

# 5. Apply migrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser

# 7. Add products via admin or shell
python manage.py shell
# >>> from users.models import Product
# >>> Product.objects.create(name="Gold Wash", point_value=100)
# >>> exit()

# 8. Start the server
python manage.py runserver

# 9. Open the app
open http://localhost:8000
```
