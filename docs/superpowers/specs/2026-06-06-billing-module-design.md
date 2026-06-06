# Billing Module Design
_Date: 2026-06-06_

## Overview

Add a procurement billing module to the Surprice Co Rewards Django app. Bills are the primary mechanism for awarding points. Admins can also manually adjust points. A WhatsApp notify button builds a `wa.me` URL with a customisable message template.

---

## Architecture

Two Django apps:

- **`users`** — existing app, handles auth and user profiles. Gets a new admin-facing Create User page and a revamped dashboard.
- **`billing`** — new app, owns products, bills, bill items, point adjustments, and WhatsApp template. Registered in `INSTALLED_APPS` and included in root `urls.py` under `/billing/`.

---

## Data Models

### `users` app — no new models

`CustomUser` already has `first_name`, `last_name`, `mobile`. The Create User form makes these required on submission (no migration needed). `Points` (FK → user, `total_points` int) remains the running balance, updated atomically on every bill save or adjustment save.

### `billing` app — new models

#### `Product` (moved from `users`, extended)
| Field | Type | Notes |
|---|---|---|
| `name` | CharField(100) | |
| `description` | TextField | blank=True |
| `price` | DecimalField(10,2) | ₹ amount per unit |
| `point_value` | IntegerField | Points awarded per unit |

Migration: delete `users.Product`, create `billing.Product`. Any existing FK references to the old model in `users` app are removed (old `add_point` view is replaced entirely).

#### `Bill`
| Field | Type | Notes |
|---|---|---|
| `user` | FK → CustomUser, SET_NULL | Who bought |
| `created_at` | DateTimeField(auto_now_add) | Bill timestamp |
| `total_amount` | DecimalField(10,2) | Sum of all line totals |
| `total_points` | IntegerField | Points awarded by this bill |
| `note` | TextField | blank=True, admin note |

#### `BillItem`
| Field | Type | Notes |
|---|---|---|
| `bill` | FK → Bill, CASCADE | Parent bill |
| `product` | FK → Product, SET_NULL | Which product |
| `quantity` | PositiveIntegerField | Units bought |
| `unit_price` | DecimalField(10,2) | Snapshot of price at billing time |
| `unit_points` | IntegerField | Snapshot of point_value at billing time |
| `line_total_amount` | DecimalField(10,2) | unit_price × quantity |
| `line_total_points` | IntegerField | unit_points × quantity |

Prices and points are snapshotted so historical bills stay correct after product edits.

#### `PointAdjustment`
| Field | Type | Notes |
|---|---|---|
| `user` | FK → CustomUser, CASCADE | Who |
| `delta` | IntegerField | Positive = add, negative = deduct |
| `reason` | CharField(200) | Short label e.g. "Correction" |
| `created_at` | DateTimeField(auto_now_add) | |

#### `WhatsAppTemplate`
| Field | Type | Notes |
|---|---|---|
| `body` | TextField | Supports `{name}`, `{points}`, `{amount}` placeholders |

Single-row table. Seeded with a default template on first run via a data migration. Admin edits from `/billing/whatsapp-template/`.

---

## URL Map

### `users` app additions
| URL | View | Purpose |
|---|---|---|
| `/users/create/` | `create_user` | Admin creates a user with all fields + initial points |

### `billing` app (`/billing/…`)
| URL | View | Purpose |
|---|---|---|
| `/billing/products/` | `product_list` | Table: name, price, points, edit/delete actions |
| `/billing/products/create/` | `product_create` | Form: name, description, price, point_value |
| `/billing/products/<id>/edit/` | `product_edit` | Same form pre-filled |
| `/billing/products/<id>/delete/` | `product_delete` | POST-only confirm delete |
| `/billing/bill/create/<user_id>/` | `bill_create` | Dynamic bill form (see below) |
| `/billing/bills/` | `bill_list` | All bills, grouped by date, filterable by user |
| `/billing/bills/<id>/` | `bill_detail` | Line-item breakdown of one bill |
| `/billing/adjust/<user_id>/` | `point_adjust` | POST-only, handles modal form |
| `/billing/whatsapp-template/` | `whatsapp_template` | Edit template body |

---

## Page & Flow Details

### Dashboard (`/`) — revamped
- Table/card toggle retained from previous work.
- Each user row shows: avatar, full name, username, mobile, current points.
- Three action buttons per row:
  - **Bill** → navigates to `/billing/bill/create/<user_id>/`
  - **Adjust** → opens inline modal (no page load), submits to `/billing/adjust/<user_id>/`
  - **Notify** → opens inline modal (no page load), shows pre-filled WhatsApp message, admin can edit, clicking "Open WhatsApp" opens `wa.me/91{mobile}?text={encoded}` in new tab

### Create User (`/users/create/`)
- Fields: username, first_name (required), last_name (optional), mobile (required), initial points (int, default 0).
- On save: creates `CustomUser` + `Points` record with the given initial value.
- Accessible only to `is_superuser` users.

### Create Bill (`/billing/bill/create/<user_id>/`)
- User pre-filled, read-only at top.
- Dynamic line-item table: admin clicks "+ Add Item", selects product from dropdown, enters quantity. JS calculates line amount and line points live.
- Running totals at bottom: Total Amount (₹), Total Points.
- Optional note field.
- On save (POST):
  1. Create `Bill` record.
  2. Create `BillItem` records with snapshotted prices.
  3. Update `Points.total_points` by adding `bill.total_points` (using `F()` expression for safety).
  4. Redirect to dashboard.

### Point Adjustment modal (POST → `/billing/adjust/<user_id>/`)
- Fields: delta (signed int), reason.
- On save: create `PointAdjustment`, update `Points.total_points` with `F()` expression.
- Redirect back to dashboard.

### Bill List (`/billing/bills/`)
- Grouped by calendar date.
- Each date group header shows: total bills, total items, total ₹, total points for that day.
- Filter: user dropdown, date range.
- Links to Bill Detail.

### Bill Detail (`/billing/bills/<id>/`)
- Bill metadata: user, date, note.
- Line items table: product, qty, unit price, unit points, line total amount, line total points.
- Footer: grand total amount, grand total points.

### WhatsApp Template (`/billing/whatsapp-template/`)
- Single textarea for the template body.
- Placeholder reference shown below: `{name}`, `{points}`, `{amount}`.
- Default template: `"Hi {name}! You've earned {points} reward points (₹{amount} purchase). Thank you for shopping with us!"`

### WhatsApp Notify modal (on dashboard)
- Textarea pre-filled by rendering the template with the user's actual name, current points, and latest bill amount.
- Admin can freely edit the text.
- "Open WhatsApp" button builds: `https://wa.me/91{mobile}?text={encodeURIComponent(text)}` and opens in new tab.
- No API call. No AiSensy involved.

---

## Points Balance Integrity

- `Points.total_points` is always updated with Django `F()` expressions to avoid race conditions.
- Bills and adjustments never overwrite the balance — they always increment/decrement.
- The admin "manual adjust" form replaces the old overwrite-based `update_points` and `delete_points` views, which are removed.

---

## What's Removed / Replaced

| Old | Replaced by |
|---|---|
| `users.Product` model | `billing.Product` (extended) |
| `add_point` view + form | `billing.bill_create` view |
| `update_points` view | Dashboard Adjust modal → `billing.point_adjust` |
| `delete_points` view | Same Adjust modal with negative delta |
| Auto AiSensy send on every change | Manual WhatsApp notify modal (admin-triggered) |

---

## Access Control

All `billing` views and the new `users/create/` view require `is_superuser=True`. Non-admin users continue to see only their own `user_home.html`.

---

## Migration Plan

1. Create `billing` app, define models.
2. Move `Product` data: write a data migration that copies existing `users.Product` rows into `billing.Product`.
3. Remove `users.Product` model.
4. Apply all migrations in one `migrate` run.
