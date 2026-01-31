# Desert Trash GJ - Project Specification

## Overview

An interactive web application for reporting and tracking illegal dumping on BLM land in Mesa County, Colorado. Authenticated users upload geotagged photos of trash, select categories, and place them on a map. A moderation queue ensures quality before submissions go public. Site visitors can browse an interactive Mapbox map with filtering by category, status, and date.

---

## Decisions Log

| Question | Decision |
|----------|----------|
| Geographic scope | Mesa County BLM land, excluding towns and cities |
| Authentication | Required accounts via Google OAuth ("Sign in with Google") |
| Trash categories | Household dumping, vehicle/tire debris, hazardous materials |
| Moderation | Pre-publish review - submissions require moderator approval |
| Notifications | Internal only (moderators notified of new uploads). No external reporting initially |
| Map provider | Mapbox (satellite/terrain imagery, free tier sufficient for expected traffic) |
| Marker clustering | Yes |
| Mobile upload | Essential - primary upload flow will be from phones in the field |
| Cleanup status tracking | Yes (reported -> in progress -> cleaned) |
| Community features | Deferred to a later phase (leaderboards, events, comments). Architecture should not preclude adding these |
| Categorization | Manual user-selected categories at launch. ML auto-tagging in a future phase once labeled data exists |
| Backend framework | Django (with Django templates + Mapbox JS for frontend) |
| Frontend approach | Django templates with minimal JS. Mapbox GL JS for the map. Django REST Framework added later for API endpoints |
| Hosting | VPS initially (DigitalOcean/Linode) to control cost. Migrate to AWS in a later phase for learning and scalability |
| OAuth library | django-allauth |
| Photo upload limit | Accept up to 20 MB, resize/compress server-side to a standard resolution for storage |
| Default map style | Mapbox Outdoors (topographic with elevation contours and trails) |
| Photo storage | Decide later. Start with local filesystem, revisit once upload volume is understood |
| BLM land boundaries | Visual overlay on map initially, uploads allowed from anywhere in Mesa County. Enforce public land boundaries in a future phase |

---

## Open Questions

<!-- New questions that come up during development -->

---

## Features

### Phase 1 - MVP

- **Google OAuth login** - Required to upload, optional to browse the map
- **Photo upload** - Mobile-friendly form with camera access; extract GPS from EXIF data; fallback to manual pin placement on map
- **User-selected categories** - Uploader picks from: household dumping, vehicle/tire debris, hazardous materials
- **Severity level** - User selects low / medium / high
- **Moderation queue** - New submissions are pending until a moderator approves or rejects (Django admin)
- **Interactive map** - Mapbox GL JS map centered on Mesa County BLM land, Outdoors/terrain style by default
- **BLM boundary overlay** - Visual layer showing BLM land boundaries on the map
- **Photo resize** - Server-side resize/compression of uploads (accept up to 20 MB, store at standard resolution)
- **Map markers** - Color-coded by category, clickable for detail popup
- **Marker clustering** - Clustered markers that expand on zoom
- **Filtering** - Filter by category, severity, cleanup status, date range
- **Submission detail view** - Full photo, location on map, metadata, category, status
- **Cleanup status tracking** - Moderators/admins can update status: reported -> in progress -> cleaned
- **Responsive design** - Mobile-first, usable for field uploads on phones

### Phase 2 - Enhancements

- Enforce public land boundaries (reject submissions outside public lands)
- Django REST Framework API for richer frontend interactions
- Gallery / list view (alternative to map browsing)
- Search by address or area
- Export/reporting tools for coordinating with agencies
- ML auto-categorization (suggestions based on photo content)
- Multiple photos per submission

### Phase 3 - Community

- User profiles with submission history and stats
- Comments on submissions
- Cleanup events (organized group cleanups)
- Leaderboards
- Notification preferences

### Phase 4 - Scale

- Migrate hosting to AWS (EC2/ECS, RDS, S3, CloudFront)
- Performance optimization and caching
- Public launch and outreach

---

## Architecture

### Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Django 5.x | Python, server-rendered templates |
| Frontend | Django templates + Mapbox GL JS | Minimal JS, map is the main interactive element |
| Database | PostgreSQL + PostGIS | Spatial queries for map data, filtering by location |
| File Storage | Local filesystem (Phase 1), S3 (Phase 4) | Photos stored on VPS disk initially |
| Map | Mapbox GL JS | Satellite/terrain views, clustering, popups |
| Auth | Google OAuth via django-allauth | "Sign in with Google" |
| Admin | Django admin | Moderation queue, user management, data management |
| Hosting | VPS (Phase 1), AWS (Phase 4) | DigitalOcean or Linode to start |

### Data Model

```
User (Django built-in + allauth)
  - id
  - email (from Google)
  - display_name
  - role (user | moderator | admin)
  - date_joined

Submission
  - id
  - user (FK -> User)
  - photo (image file)
  - latitude (decimal)
  - longitude (decimal)
  - location (PostGIS point, derived from lat/lng)
  - category (household_dumping | vehicle_tire | hazardous)
  - severity (low | medium | high)
  - status (pending | approved | rejected | in_progress | cleaned)
  - description (optional text from uploader)
  - exif_data (JSON, raw EXIF extracted from photo)
  - created_at
  - updated_at
  - moderated_by (FK -> User, nullable)
  - moderated_at (nullable)
  - cleaned_at (nullable)

Category
  - id
  - name
  - slug
  - icon
  - color (hex, for map markers)
  - description
```

---

## Pages / Views

1. **Map View** (home `/`) - Full-screen Mapbox map with filter sidebar, marker clustering, popups
2. **Login** (`/login/`) - Google OAuth sign-in
3. **Upload** (`/upload/`) - Mobile-friendly photo upload form (requires auth)
4. **Submission Detail** (`/submissions/<id>/`) - Photo, map pin, metadata, status, category
5. **My Submissions** (`/my-submissions/`) - User's own uploads and their statuses
6. **Admin / Moderation** (`/admin/`) - Django admin with moderation queue, status management
7. **About** (`/about/`) - Project info, how to report, how to help

---

## Notes

- **EXIF extraction**: Use `Pillow` or `exifread` to pull GPS coordinates from uploaded photos. If no GPS data, require manual pin placement on a Mapbox map widget in the upload form.
- **PostGIS**: Enables spatial queries like "find all submissions within X km" and efficient bounding-box queries for the map viewport.
- **django-allauth**: Handles Google OAuth flow, session management, and account linking. Well-maintained and widely used.
- **Django admin for moderation**: The built-in admin can be customized with list filters and actions (approve/reject) without writing a custom moderation UI.
- **Mapbox free tier**: 50,000 map loads/month. More than sufficient for initial use. Monitor usage as the project grows.
- **Photo resizing**: Use `Pillow` to resize uploaded photos server-side. A reasonable target is 1920px on the longest edge at 85% JPEG quality - good enough for detail while keeping file sizes around 200-500 KB.
- **BLM boundary data**: The BLM National Surface Management Agency dataset is available as GeoJSON/Shapefile from the BLM's GeoCommunicator or data.gov. Can be loaded as a Mapbox layer for the visual overlay.
