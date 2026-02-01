# Claude Code Project Notes

## Project Overview

**Desert Trash GJ** — A Django web app for reporting and tracking illegal dumping on BLM land in Mesa County, Colorado. Users submit geotagged photos via an interactive Mapbox map; moderators review and approve submissions.

**Tech stack:** Django 5.2, PostgreSQL/PostGIS, Mapbox GL JS, Google OAuth (django-allauth), Pillow for image processing.

## Branching Workflow

**Before writing any code for a new feature or change**, always complete steps 1–2 first:

1. Fetch and checkout the latest `main` branch (`git fetch origin main && git checkout main && git pull origin main`)
2. Create a new branch named `minor/na/<feature_name>` where `feature_name` is a brief description joined by underscores (e.g., `minor/na/add_moderation_queue`)
3. Implement the changes on this branch
4. When ready, push the branch to the remote and open a PR against `main`

## Python / Django

Always use the project virtualenv when running Python or Django commands:

```
.venv/bin/python manage.py <command>
```

## Project Structure

```
deserttrashgj/
├── deserttrash/          # Django project config (settings, urls, wsgi/asgi)
├── reports/              # Main (and only) Django app
│   ├── models.py         # User, Category, Submission
│   ├── views.py          # map, submit, moderation, submission detail, geojson API
│   ├── urls.py           # App routes
│   ├── forms.py          # SubmissionForm
│   ├── admin.py          # Custom admin for User, Category, Submission
│   ├── utils.py          # EXIF extraction, image resize, temp upload cleanup
│   ├── managers.py       # Custom UserManager (email-based auth)
│   ├── decorators.py     # @moderator_required
│   └── templates/reports/
├── templates/includes/   # Shared partials (favicons)
├── static/               # CSS, JS, favicons, images
│   ├── css/              # map.css, submit.css, moderate.css, submission_detail.css
│   └── js/               # map.js, submit.js, moderate.js
├── media/                # User-uploaded photos (gitignored)
├── docker-compose.yml    # PostGIS dev database
├── requirements.txt      # Python dependencies
├── SPEC.md               # Full project specification
└── .github/workflows/ci.yml  # GitHub Actions CI
```

## Key Models (reports app)

- **User** — Custom auth model (`AUTH_USER_MODEL = "reports.User"`). Email-based login (no username). Roles: `user`, `moderator`, `admin`.
- **Category** — Dumping categories with name, slug, icon, hex color (for map markers).
- **Submission** — Photo reports with lat/lng, PostGIS `PointField`, category FK, severity (`low`/`medium`/`high`), status (`pending`/`approved`/`rejected`/`in_progress`/`cleaned`), EXIF JSON, moderation tracking.

## URL Routes

| Path | View | Auth | Purpose |
|------|------|------|---------|
| `/` | `map_view` | Public | Interactive map with filters |
| `/upload/` | `submit_view` | Login | Photo submission form |
| `/api/submissions.geojson` | `submissions_geojson` | Public | GeoJSON feed (approved only for public) |
| `/submission/<id>/` | `submission_detail` | Public | Single submission view |
| `/moderate/` | `moderate_list` | Moderator | Pending submissions queue |
| `/moderate/<id>/` | `moderate_detail` | Moderator | Review a submission |
| `/moderate/<id>/action/` | `moderate_action` | Moderator | Approve/reject (POST) |
| `/accounts/` | allauth | — | Google OAuth login/logout |
| `/admin/` | Django admin | Staff | Admin interface |

## Running the App Locally

```bash
# Start the PostGIS database
docker compose up -d

# Apply migrations
.venv/bin/python manage.py migrate

# Run the dev server
.venv/bin/python manage.py runserver
```

Required env vars (see `.env.example`): `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `MAPBOX_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

## Running Tests

```bash
.venv/bin/python manage.py test
```

CI runs on every pull request via GitHub Actions (`.github/workflows/ci.yml`). The CI job provisions a PostGIS service container and installs spatial libraries (gdal, geos, proj).

**Note:** `reports/tests.py` is currently empty — no tests have been written yet.

## Frontend

All frontend code lives in `static/js/` and `static/css/`. No build step — plain JS and CSS served by Django's staticfiles.

- **map.js** — Mapbox GL JS map with clustered GeoJSON markers, category color-coding, filter sidebar, popups. Centered on Mesa County `[-108.55, 39.07]`.
- **submit.js** — Photo preview, client-side EXIF GPS parsing, draggable Mapbox pin for location, form validation.
- **moderate.js** — Static read-only Mapbox map for submission detail views.

## Key Patterns

- **Authentication:** Google OAuth via django-allauth. Custom `User` model with email as the identifier — there is no `username` field.
- **Authorization:** `@moderator_required` decorator checks `user.role in ("moderator", "admin")`. Returns 403 if unauthorized.
- **Image handling:** Photos are validated (JPEG/PNG/WebP, <20 MB), auto-resized to 1920px longest edge at 85% JPEG quality, with EXIF orientation normalization. GPS extracted from EXIF server-side as a fallback.
- **Spatial data:** PostGIS `PointField(geography=True, srid=4326)` on Submission. GeoJSON API endpoint supports filtering by category, severity, status, and date range.
- **Temp uploads:** During form submission, photos are temporarily stored in `media/temp/` with 30-minute expiry to survive form validation errors.

## Dependencies

See `requirements.txt`: Django 5.2, psycopg 3.2.4 (binary), django-allauth 65.3.0, django-environ 0.11.2, Pillow 11.1.0, requests 2.32.5, PyJWT 2.11.0.
