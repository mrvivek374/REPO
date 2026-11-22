# NEXORA — Business Contact Management System

**Smart Connections. Smarter Management.**

NEXORA is a complete, role-based contact management platform: a contact directory,
interaction history, follow-up tracking and live reporting, wrapped in a premium
neumorphic interface built on Deep Forest Green, Warm Ivory and Soft Sage.

Everything you see is backed by the database — there is no hard-coded dashboard
data and no `localStorage` pretending to be a database.

---

## Table of contents

1. [What you get](#1-what-you-get)
2. [Technology stack (and why Django)](#2-technology-stack-and-why-django)
3. [Roles and permissions](#3-roles-and-permissions)
4. [Project structure](#4-project-structure)
5. [Requirements](#5-requirements)
6. [Setup in VS Code, step by step](#6-setup-in-vs-code-step-by-step)
7. [Connecting MySQL](#7-connecting-mysql)
8. [Demo accounts](#8-demo-accounts)
9. [Daily use: commands you will actually type](#9-daily-use-commands-you-will-actually-type)
10. [Testing](#10-testing)
11. [Database design](#11-database-design)
12. [Deploying to Vercel](#12-deploying-to-vercel)
13. [Configuration reference](#13-configuration-reference)
14. [Security notes](#14-security-notes)
15. [Troubleshooting](#15-troubleshooting)
16. [Scope: what is deliberately excluded](#16-scope-what-is-deliberately-excluded)

---

## 1. What you get

### Login
Premium split-screen sign-in with show/hide password, "keep me signed in",
server-side validation, clear invalid-credential and deactivated-account
messages, and a same-origin `next` redirect check.

### Dashboard
Greeting hero, five live KPI cards (total contacts, active contacts,
categories, upcoming follow-ups, overdue follow-ups), monthly contact growth,
category distribution, follow-up status, recent activity feed, recently added
contacts and the signed-in user's own follow-up focus.

### Contact Directory
Create, view, edit and delete contacts with confirmation. Search across name,
company, job title, email and phone. Filter by category, sort by name/company/date,
paginate with your preferred row count. Duplicate emails are rejected
case-insensitively, and duplicate phone numbers are caught even when the
formatting differs (`+91 98200 31111` vs `919820031111`).

### Contact profile
Personal and business information, click-to-call/email, address, category,
notes, record metadata (Contact ID, created by, created/updated), full
interaction timeline and every follow-up ever scheduled for that contact.

### Categories
Client, Supplier, Partner and Lead are seeded. Add, edit and delete categories
(deletion is blocked while contacts still use them, so no record is orphaned).

### Interactions
Phone Call, Meeting, Email or Other; notes, date and the recording user.
Future timestamps are rejected. The author (or an administrator) can delete a
mistaken entry.

### Follow-ups
Create tasks with an owner, due date and notes; new tasks cannot be scheduled in
the past. Statuses are **Pending**, **Completed** and a derived **Overdue** that
appears automatically when a pending task passes its due date. Tabs for
Upcoming / Overdue / Completed / All, one-click complete and reopen, and
staff-level scoping so people only manage their own queue.

### Reports & analytics
Date-range filters with quick presets, new-contact counts, interaction mix,
category distribution and share table, monthly growth, follow-up completion
rate, overdue list and team contribution — all computed with ORM aggregation
against the selected period.

### User management & roles
Administrators add team members, assign roles, activate/deactivate accounts,
delete accounts (blocked when records reference them) and edit what each role
may do through a live permission matrix. The Administrator role always keeps
full access, and the system refuses to remove the last active administrator.

### Profile & settings
Edit your own profile, change your password with Django's validators, and set
table row counts, date format, reminder visibility and compact table spacing —
stored server-side per user, not in the browser.

### Interface
Neumorphic raised cards and recessed inputs, forest-green sidebar, ivory canvas,
sage accents, responsive from desktop to phone, breadcrumbs on every page,
empty states, loading-free server rendering, confirmation dialog for destructive
actions, tooltips, focus-visible outlines, `aria` labels and reduced-motion
support.

---

## 2. Technology stack (and why Django)

| Layer | Choice |
| --- | --- |
| Frontend | HTML5, CSS3 (custom neumorphic design system), vanilla JS, Bootstrap 5.3 (grid, dropdown, tooltip), Chart.js 4 |
| Backend | Python 3.10+ / **Django 6.1** |
| Database | **MySQL 8.4+** (utf8mb4) — Django 6.1's minimum; PostgreSQL also supported for Vercel |
| Driver | PyMySQL (pure Python — no C compiler needed on Windows) |
| Editor | Visual Studio Code |

**Why Django rather than Flask?** This project is, at its core, a set of related
database entities with authentication and role-based permissions. Django gives
that to you as first-class, testable machinery:

* an ORM with real migrations, foreign keys and uniqueness constraints;
* a battle-tested authentication system with secure password hashing
  (PBKDF2-SHA256 by default) and session handling — Flask would need
  Flask-Login, Flask-WTF, Flask-Migrate and a lot of glue;
* automatic CSRF protection on every form;
* a template engine with inheritance, so the sidebar/header/design system is
  written once;
* a built-in test runner, which is how the 67 tests in this repository run.

Flask is excellent for small APIs and microservices. For a multi-module business
application with permissions and reports, Django gets you to a *secure,
maintainable* result with fewer places to make a mistake.

---

## 3. Roles and permissions

| Permission | Administrator | Manager | Staff |
| --- | :-: | :-: | :-: |
| View dashboard | ✅ | ✅ | ✅ |
| View contacts | ✅ | ✅ | ✅ |
| Add contacts | ✅ | ✅ | ✅ |
| Edit contacts | ✅ | ✅ | ✅ |
| Delete contacts | ✅ | — | — |
| View categories | ✅ | ✅ | ✅ |
| Manage categories | ✅ | — | — |
| View interactions | ✅ | ✅ | ✅ |
| Record interactions | ✅ | ✅ | ✅ |
| View follow-ups | ✅ | ✅ | ✅ own scope |
| Create follow-ups | ✅ | ✅ | ✅ |
| Update / complete follow-ups | ✅ | ✅ | ✅ own scope |
| View reports | ✅ | ✅ | — |
| Manage users, roles, permissions | ✅ | — | — |

Permissions live in `roles.permissions` (JSON) and are enforced by
`@permission_required(...)` on every server view — hiding a menu item is never
the only defence. Staff follow-up access is additionally scoped in the query
and re-checked on every task action, so a crafted URL cannot change someone
else's task.

Administrators may edit the Manager and Staff permission sets from
**Roles & Permissions**. The Administrator role is intentionally locked so you
cannot lock yourself out.

---

## 4. Project structure

```
Nexora/
├── manage.py
├── requirements.txt
├── .env                     ← your local secrets (git-ignored)
├── .env.example             ← template with every setting explained
├── README.md
│
├── nexora/                  ← project configuration
│   ├── settings.py          ← env-driven settings, MySQL/SQLite switch
│   ├── urls.py
│   ├── context_processors.py
│   ├── wsgi.py / asgi.py
│   └── __init__.py          ← registers PyMySQL as MySQLdb
│
├── apps/
│   ├── accounts/            ← users, roles, permissions, auth, settings
│   │   ├── models.py        ← Role, User, UserPreference
│   │   ├── permissions.py   ← permission catalogue + decorator
│   │   ├── forms.py, views.py, urls.py, backends.py
│   │   ├── management/commands/seed_demo.py
│   │   └── templatetags/nexora_extras.py
│   ├── contacts/            ← Category, Contact, directory, profile
│   ├── interactions/        ← Interaction model, timeline, recording
│   ├── followups/           ← FollowUp model, status derivation, tasks
│   └── reports/             ← aggregation services + dashboard/report views
│
├── templates/               ← every page, partials included
│   ├── base.html            ← app shell (sidebar + topbar + modal)
│   ├── dashboard.html
│   ├── accounts/ contacts/ interactions/ followups/ reports/ errors/
│   └── partials/            ← sidebar, topbar, fields, pagination, modal…
│
├── static/
│   ├── css/nexora.css       ← the whole neumorphic design system
│   ├── js/nexora.js         ← sidebar, password toggle, confirm dialog, charts
│   ├── img/logo.svg, icons.svg
│   └── vendor/              ← Bootstrap + Chart.js served locally (works offline)
│
├── sql/nexora_schema.sql    ← real MySQL DDL exported from the migrations
└── scripts/setup_mysql.py   ← creates the database + user, then migrates
```

---

## 5. Requirements

* **Python 3.10 or newer** (`python --version`). Tested on 3.14.
* **MySQL 8.4 or newer** running locally (MySQL Workbench optional). Django 6.1
  refuses older servers; see [Deploying to Vercel](#12-deploying-to-vercel) for
  the PostgreSQL alternative.
* **Visual Studio Code** with the Python extension (recommended).
* No Node.js, no build step, no internet connection at runtime — the fonts are
  the only optional online asset and they degrade to system fonts gracefully.

---

## 6. Setup in VS Code, step by step

> All commands below are typed into **VS Code → Terminal → New Terminal**.
> The examples use PowerShell; Git Bash and CMD work too (notes included).

### Step 1 — Open the project

`File → Open Folder… → Nexora`.

### Step 2 — Create the virtual environment

```powershell
python -m venv .venv
```

A `.venv` folder appears. This is a private Python installation for the project —
nothing is installed globally.

### Step 3 — Activate it

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script (`running scripts is disabled`), run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

CMD: `.venv\Scripts\activate.bat`
Git Bash: `source .venv/Scripts/activate`

Your prompt now starts with `(.venv)`.

> **VS Code tip:** press `Ctrl+Shift+P` → "Python: Select Interpreter" →
> choose `.venv\Scripts\python.exe`. Then new terminals activate themselves.

### Step 4 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5 — Create your environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` and set a real `DJANGO_SECRET_KEY` (any long random string).
Leave `DB_ENGINE=mysql`; the next step fills in the MySQL details for you.

### Step 6 — Connect MySQL (one command)

```powershell
python scripts/setup_mysql.py
```

The script asks for:

* host / port (press Enter for `127.0.0.1` and `3306`),
* database name (`nexora_db`),
* the application user (`nexora_user`),
* **your MySQL administrator password** (typed locally, hidden, never saved).

It then creates the database, creates `nexora_user` with a generated strong
password, grants privileges, writes those values into `.env`, runs the
migrations and offers to seed the demo records.

Prefer doing it by hand? See [Connecting MySQL](#7-connecting-mysql).

### Step 7 — Run the application

```powershell
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and sign in with one of the
[demo accounts](#8-demo-accounts).

### Step 8 — (optional) work without MySQL for a moment

If you only want to click through the UI before configuring MySQL, set
`DB_ENGINE=sqlite` in `.env`, then:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

MySQL remains the intended database; SQLite is just a convenience switch.

---

## 7. Connecting MySQL

### Option A — the helper script (recommended)

```powershell
python scripts/setup_mysql.py
```

### Option B — MySQL Workbench

1. Open your local connection and run:

```sql
CREATE DATABASE nexora_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'nexora_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
CREATE USER 'nexora_user'@'127.0.0.1' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON nexora_db.* TO 'nexora_user'@'localhost';
GRANT ALL PRIVILEGES ON nexora_db.* TO 'nexora_user'@'127.0.0.1';
FLUSH PRIVILEGES;
```

2. Put those values in `.env`:

```env
DB_ENGINE=mysql
DB_NAME=nexora_db
DB_USER=nexora_user
DB_PASSWORD=ChooseAStrongPassword
DB_HOST=127.0.0.1
DB_PORT=3306
```

3. Create the tables and demo data:

```powershell
python manage.py migrate
python manage.py seed_demo
```

### Option C — import the SQL file

`sql/nexora_schema.sql` contains the exact DDL generated from the migrations
(including Django's session/auth tables). Importing it is optional; the
migrations are the source of truth:

```powershell
mysql -u root -p < sql/nexora_schema.sql
```

### Sample records

`python manage.py seed_demo` creates fictional data: 5 users, 4 categories,
25 contacts across Indian cities, ~49 interactions and 25 follow-ups spread
over the last six months so every chart has something to show.

`python manage.py seed_demo --reset` wipes contacts, interactions and
follow-ups and rebuilds them (users, roles and categories are kept).

---

## 8. Demo accounts

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `Nexora@123` |
| Business Owner / Manager | `manager` | `Nexora@123` |
| Staff / Employee | `staff` | `Nexora@123` |

There is also `arjun` (active staff, useful for testing task scoping) and
`kavya` (an **inactive** account, useful for testing the deactivated-login
message). All demo passwords are `Nexora@123`.

> Change these passwords before using the project with real data:
> sign in as `admin` → **Settings → Change password**.

---

## 9. Daily use: commands you will actually type

```powershell
# activate the environment (once per terminal)
.\.venv\Scripts\Activate.ps1

# start the site
python manage.py runserver

# start on a different port
python manage.py runserver 127.0.0.1:8080

# after pulling schema changes
python manage.py migrate

# rebuild the demonstration data
python manage.py seed_demo --reset

# run the automated test suite
python manage.py test

# check the project for configuration problems
python manage.py check

# collect static files (only needed for a production deployment)
python manage.py collectstatic
```

---

## 10. Testing

### Automated suite

```powershell
python manage.py test
```

67 tests covering:

* login with valid credentials, email instead of username, invalid credentials
  and a deactivated account;
* logout only via POST, anonymous redirects, root redirect;
* contact creation, required-field validation, duplicate email, duplicate phone
  with different formatting, edit, delete, search/filter/sort, pagination;
* interaction recording, note validation, future-date rejection, author-only
  deletion;
* follow-up creation, past-due rejection, overdue derivation, complete/reopen,
  staff scoping and cross-user protection;
* dashboard statistics and chart series computed from records;
* report date filtering and category shares;
* role enforcement (staff → 403 on reports/team/category management/deletion),
  permission matrix editing and the locked Administrator role;
* last-administrator protection and a page-render smoke test for every screen
  in every role.

The suite passes on both SQLite and MySQL 8.4+. Django's test runner creates a
throwaway database (`test_nexora_db`), so your real data is untouched.

### Manual checklist (the 14 required scenarios)

| # | Scenario | How to check |
| --- | --- | --- |
| 1 | Valid login | Sign in as `admin` → dashboard appears |
| 2 | Invalid login | Wrong password → red error, still on login page |
| 3 | Add contact | Directory → Add contact → complete form → profile opens |
| 4 | Required fields | Submit the empty form → field-level messages appear |
| 5 | Search | Type a company name in the search bar → list narrows |
| 6 | Edit contact | Profile → Edit → change company → save → change visible |
| 7 | Delete with confirmation | Directory → bin icon → modal → Delete |
| 8 | Duplicate prevention | Add a contact using an existing email → error naming the owner |
| 9 | Record interaction | Profile → Record interaction → appears in history |
| 10 | Follow-up task | Follow-ups → New → due tomorrow → appears in Upcoming |
| 11 | Follow-up date validation | Try a due date yesterday → error |
| 12 | Reports | Reports → change dates → figures and charts update |
| 13 | Role permissions | Sign in as `manager` → no Team menu, no delete actions |
| 14 | Staff restrictions | Sign in as `staff` → open `/team/` or `/reports/` manually → styled 403 |

---

## 11. Database design

### NEXORA tables

| Table | Key columns | Relationships / rules |
| --- | --- | --- |
| `roles` | `role_id` PK, `role_name` unique, `role_key` unique, `permissions` JSON | one role → many users |
| `users` | `user_id` PK, `username` unique, `email` unique, `password_hash`, `role_id` FK, `status` | role `PROTECT`ed; status `active`/`inactive` |
| `categories` | `category_id` PK, `category_name` unique | one category → many contacts |
| `contacts` | `contact_id` PK, `phone` unique, `email` unique, `category_id` FK, `created_by` FK, `created_at` | category and creator `PROTECT`ed, indices on name/company/category/date |
| `interactions` | `interaction_id` PK, `contact_id` FK CASCADE, `user_id` FK, `interaction_type`, `interaction_date` | deleting a contact removes its history safely |
| `followups` | `followup_id` PK, `contact_id` FK CASCADE, `assigned_to` FK, `due_date`, `status`, `completed_at` | index on `(status, due_date)` and `(assigned_to, status)` |
| `user_preferences` | `user_id` PK/FK, `items_per_page`, `date_format`, `notify_followups`, `compact_tables` | one row per user |

Security details: passwords are stored as PBKDF2-SHA256 hashes (never plain
text), the `password` column is mapped to `password_hash`, all queries use the
ORM's parameterisation, forms carry CSRF tokens, and destructive actions are
POST-only.

Migrations live in each app's `migrations/` folder. `sql/nexora_schema.sql` is
an exported snapshot for reference and manual import.

---

## 12. Deploying to Vercel

NEXORA runs on Vercel as a single Python function (the ASGI app) plus static
files served from Vercel's CDN. The repository already contains everything
Vercel needs:

| File | Purpose |
| --- | --- |
| `.python-version` | Pins Python 3.12. Django 6.1 requires Python ≥ 3.12 — without the pin Vercel can pick an older runtime, `pip install Django==6.1.3` is skipped, and the build fails with `[DJANGO_SETTINGS_FAILED]`. |
| `vercel.json` | Declares the Django framework, the `nexora/asgi.py` function (60 s, 1 GB) and the build command (`migrate` → `seed_demo` → `collectstatic`). |
| `.vercelignore` | Keeps `.venv`, `.env`, `db.sqlite3` and `staticfiles/` out of the upload. |

Vercel finds `manage.py`, reads `DJANGO_SETTINGS_MODULE`, uses
`ASGI_APPLICATION`, installs `requirements.txt`, serves `/static/` from
`STATIC_ROOT` and runs the build command from `vercel.json`.

### The one thing Vercel cannot provide: the database

Vercel has **no database** and a **read-only, per-invocation filesystem**:

* `127.0.0.1:3306` on your computer does not exist inside Vercel;
* a `db.sqlite3` uploaded there would be empty and would disappear.

Every page touches the database (sessions included), so **without a database
URL the deployment builds but returns HTTP 500 on every page.** Pick one of the
two supported options.

**Option A — hosted MySQL 8.4 or newer (keeps the project's MySQL stack).**
Django 6.1 refuses any MySQL server below 8.4. Services that only speak the
MySQL 8.0 protocol (TiDB Cloud, several free tiers) fail at `migrate` with
`MySQL 8.4 or later is required (found 8.0.11)` — that is the database, not
this code. Use a provider that offers MySQL 8.4+ and paste its URL:

```text
mysql://user:password@host:3306/nexora_db?ssl=true
```

Put it in `MYSQL_URL`.

**Option B — Vercel Marketplace Postgres (one click, free tier).**
Install a Postgres/Neon integration on the Vercel project; Vercel injects
`DATABASE_URL` (and/or `POSTGRES_URL`) automatically, and the project's
`settings.py` uses it as soon as it starts with `postgres://`. The driver
(`psycopg[binary]`) is already in `requirements.txt`. MySQL stays the default;
Postgres is only used when one of those URLs is present.

### Step 1 — import the project

1. Push the repository to GitHub.
2. On vercel.com/new, import it.
3. On the configuration screen leave **Root Directory** empty (the repository
   root is the Django project root) and keep **Framework Preset: Django**.
4. Add the database (Option A: paste `MYSQL_URL`; Option B: install the
   integration).

### Step 2 — environment variables

Project → **Settings → Environment Variables** (add to Production *and*
Preview):

| Name | Value |
| --- | --- |
| `DJANGO_SECRET_KEY` | a long random string |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | optional — your custom domain, e.g. `nexora.example.com` |
| `MYSQL_URL` | Option A connection string (`?ssl=true` enables TLS) |
| `DATABASE_URL` / `POSTGRES_URL` | Option B — injected by the integration, nothing to type |
| `DB_SSL` | `True` only if your MySQL provider needs TLS and the URL has no `?ssl=true` |

`*.vercel.app` hostnames, their CSRF origins and HTTPS detection are handled in
`settings.py`, so the deployment works before you add a custom domain.

### Step 3 — deploy

Click **Deploy** (or push to the connected branch). The build runs:

```text
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py collectstatic --noinput
```

so the first deployment already has its tables and the demo accounts. The
`seed_demo` step is safe to repeat: it only creates what is missing and leaves
existing contacts alone. Open the `.vercel.app` URL and sign in with
`admin` / `Nexora@123`, then change the password.

> Prefer to run migrations yourself? Delete the `buildCommand` line from
> `vercel.json` and run the three commands locally with the database URL set
> (`$env:MYSQL_URL="..."` in PowerShell, `MYSQL_URL="..." python manage.py migrate`
> in Git Bash). Vercel never migrates on its own.

### Step 4 — reading a failed deployment

| What you see | What it means |
| --- | --- |
| `404 NOT_FOUND` on every URL | The project's **Framework Preset** is not Django or **Root Directory** points at a subfolder. Fix it in Settings → General, then redeploy. |
| Build stops at `migrate` with `Can't connect to MySQL server on '127.0.0.1'` | No database URL reached the build. Add `MYSQL_URL` (or the Postgres integration) to **all** environments, then redeploy. |
| Build stops at `migrate` with `Access denied` / `password authentication failed` | The URL is wrong or its password contains characters that must be percent-encoded (`@` → `%40`, `#` → `%23`). |
| `[DJANGO_SETTINGS_FAILED]` | Vercel could not import your settings. Read the lines **above** the error: `Ignored the following versions that require a different python version` (the Python pin is missing) or `ModuleNotFoundError: No module named 'django'` (requirements not found → Root Directory). |
| Build succeeds, page returns 500 | The function cannot reach the database at runtime: the variable was added to Production but not Preview, or the database was paused. Check Vercel → Deployments → Functions → Logs. |
| Page loads but CSS/JS is missing | `STATIC_ROOT` must stay set (it is); redeploy after changing static files. |

You can run Vercel's exact settings check locally:

```powershell
python -c "import django.core.management, runpy, os; django.core.management.execute_from_command_line=lambda *a, **k: None; runpy.run_path('manage.py', run_name='__main__'); print(os.environ.get('DJANGO_SETTINGS_MODULE'))"
```

Printing `nexora.settings` means the settings module itself is healthy.

### Serverless behaviour built into the project

* Sessions live in the database, so any function instance can serve any request.
* `CONN_MAX_AGE` is `0` on Vercel (no stale connections between invocations)
  and `60` locally.
* `SECURE_PROXY_SSL_HEADER` is enabled, so Django knows the request arrived over
  HTTPS through Vercel's proxy.
* `DEBUG` defaults to `False` whenever `VERCEL` is set, and `True` locally.

---

## 13. Configuration reference

| Variable | Purpose | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django signing key — set a long random value | insecure dev value |
| `DJANGO_DEBUG` | Debug mode (`False` in production) | `True` locally, `False` when `VERCEL` is set |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames | `127.0.0.1,localhost` (+ `*.vercel.app` on Vercel) |
| `CSRF_TRUSTED_ORIGINS` | Extra trusted origins; hosts above are added automatically | derived from hosts |
| `DJANGO_TIME_ZONE` | Business timezone | `Asia/Kolkata` |
| `DB_ENGINE` | `mysql` or `sqlite` | `mysql` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | MySQL database and credentials | `nexora_db` / `nexora_user` / empty |
| `DB_HOST` / `DB_PORT` | MySQL address | `127.0.0.1` / `3306` |
| `MYSQL_URL` | Full MySQL URL; overrides the five `DB_*` values above | empty |
| `POSTGRES_URL` / `DATABASE_URL` | PostgreSQL URL (used only when it starts with `postgres://`; injected by Vercel Marketplace Postgres) | empty |
| `DB_SSL` | Require TLS to MySQL (hosted providers) | `False` |
| `SQLITE_NAME` | File used when `DB_ENGINE=sqlite` | `db.sqlite3` |

`.env` is git-ignored; `.env.example` documents every key.

---

## 14. Security notes

* Secrets and database passwords live only in `.env`.
* Passwords use Django's PBKDF2-SHA256 hashing with per-user salts; the demo
  password is for fictional seeded accounts only.
* Every form is CSRF-protected; logout, delete and status changes are POST-only.
* Permissions are enforced server-side and re-checked on object-level actions.
* The login `next` redirect and follow-up `next` redirects are validated to
  prevent open redirects.
* Sessions are server-side, HTTP-only, expire after 8 hours and expire at
  browser close unless "Keep me signed in" is used (then 14 days).
* Database access uses a dedicated, least-privilege MySQL user.

Before production: set `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`,
serve over HTTPS, point `ALLOWED_HOSTS` at your domain, and change every demo
password.

---

## 15. Troubleshooting

**`Access denied for user 'nexora_user'@'localhost'`**
The database user does not exist yet or the password in `.env` is wrong.
Run `python scripts/setup_mysql.py`.

**`Can't connect to MySQL server on '127.0.0.1'`**
MySQL is not running. Open `services.msc` → start `MySQL80`/`MySQL267`, or:

```powershell
net start MySQL267
```

**`'python' is not recognized`**
Use the launcher `py -3 -m venv .venv` and then `.\.venv\Scripts\Activate.ps1`;
or reinstall Python with "Add python.exe to PATH" ticked.

**`Activate.ps1 cannot be loaded because running scripts is disabled`**
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then reopen the terminal.

**`mysqlclient 1.4.3 or newer is required`**
This project deliberately uses PyMySQL. Make sure `nexora/__init__.py` still
contains the `install_as_MySQLdb()` shim and that `pip install -r requirements.txt`
succeeded.

**Port 8000 already in use**

```powershell
python manage.py runserver 127.0.0.1:8080
```

**I want a clean database**

```powershell
python manage.py seed_demo --reset
```

**Timezone / date oddities**
Set `DJANGO_TIME_ZONE` in `.env` to your business timezone and restart the
server.

---

## 16. Scope: what is deliberately excluded

NEXORA is a focused Business Contact Management System. It intentionally does
**not** include AI lead scoring or predictions, bulk marketing email/SMS,
automatic call recording, external CRM/ERP/accounting integrations, or a mobile
app. Quality of the documented features was prioritised over adding more
surface area.

---

**NEXORA** — Smart Connections. Smarter Management.
Built with Django, MySQL, Bootstrap and a hand-written neumorphic design system.
