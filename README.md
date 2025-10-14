ScoutAlina
===========

Every drive is a discovery.

ScoutAlina is a GPS-based real estate discovery app that helps drivers discover nearby properties of interest in real time. It consists of a Flask backend (Render-deployable) and a Kivy-based Android client, with simple docs to get started.

Goal & Name
-----------
- Scout (explore) + Alina (short, memorable): your real estate discovery companion.
- Goal: Turn everyday drives into property scouting sessions with a fun, Pokedex-inspired dashboard.

Architecture
------------
```
scoutalina/
├── server/                    # Flask backend (Render)
│   ├── app.py                 # Flask app factory / entrypoint
│   ├── config.py              # Config (env-driven)
│   ├── models.py              # ORM models
│   ├── requirements.txt       # Python server deps
│   ├── render.yaml            # Render service definition
│   ├── runtime.txt            # Python runtime pin
│   ├── wsgi.py                # WSGI entry for Render
│   ├── init_db.py             # One-time DB bootstrap
│   ├── routes/                # Flask blueprints (api, web)
│   ├── services/              # Domain services (auth, enrichment)
│   ├── static/                # Static assets (css, js, images)
│   ├── templates/             # Jinja templates (dashboard, downloads)
│   └── migrations/            # Alembic migrations
│
├── android/                   # Kivy Android app
│   ├── main.py                # App entrypoint
│   ├── buildozer.spec         # Build config for Android
│   ├── scoutalina.kv          # Kivy UI
│   ├── database.py            # Local storage
│   ├── gps_service.py         # GPS integration
│   ├── sync_manager.py        # Sync with backend
│   └── requirements.txt       # Python client deps
│
└── docs/
    ├── API.md
    ├── DEPLOYMENT.md
    └── USER_GUIDE.md
```

Current Status (MVP)
--------------------
- Backend
  - App factory with CORS, SQLAlchemy, Migrate, Login, logging, error handlers
  - PostGIS-ready models: `User`, `Route`, `RoutePoint`, `Property`, `RouteProperty`, `Watchlist`
  - DB init script `server/init_db.py` installs PostGIS, creates tables, seeds admin, prints API key
  - Auth decorators: API key header/body; web auth via Flask-Login
  - API endpoints:
    - `POST /api/register`, `POST /api/login`
    - `POST /api/upload_route` (bulk insert points, make LineString, distance)
    - `GET /api/routes`, `GET /api/properties?route_id=...`
    - `POST /api/watchlist`, `DELETE /api/watchlist/<id>`, `GET /api/watchlist`
    - `GET /api/stats`, `GET /api/health`
  - Enrichment service scaffold for ATTOM with Estated fallback
- Web UI
  - Pokedex-inspired dashboard (`templates/base.html`, `dashboard.html`, `static/css/main.css`)
  - Downloads page (`/downloads`) to host APKs
- Android
  - Kivy app scaffold with placeholder sync action
- Deployment
  - `render.yaml`, `wsgi.py`, pinned `runtime.txt`

What’s Next (Planned Prompts)
-----------------------------
- Enrichment service
  - ATTOM integration with retries, backoff, rate limiting, detailed parsing
  - Estated fallback path and normalization
  - Background job/queue for enrichment
- Android client
  - GPS tracking service and route batching
  - Config screen for API key + server URL
  - Upload routes with retries
- Web dashboard
  - Map rendering with Leaflet + date picker
  - Watchlist management UX
  - Auth flows (sessions), profile page, API key regeneration
- Data layer
  - Alembic migrations, indexes, performance tuning
  - Spatial queries optimizations and caching

Quick Start
-----------

Server (Flask)
1. Create and activate a virtualenv
   - macOS/Linux:
     - `python3 -m venv .venv && source .venv/bin/activate`
   - Windows (PowerShell):
     - `py -m venv .venv; .venv\\Scripts\\Activate.ps1`
2. Install dependencies: `pip install -r server/requirements.txt`
3. Export env vars (example):
   - `export DATABASE_URL="postgresql://user:pass@host:5432/db"`
   - `export FLASK_ENV=development`
   - `export SECRET_KEY=change-me`
4. Initialize the database: `python server/init_db.py`
5. Run locally: `python -m flask run --app server/app.py --port 5000`

Android (Kivy)
1. Ensure Python 3.10+ and buildozer prerequisites
2. Install Kivy and requirements: `pip install -r android/requirements.txt`
3. Run locally (desktop dev): `python android/main.py`
4. Build APK (Android): `cd android && buildozer android debug`

Downloads Page
--------------
- Place built APKs into `server/static/apk/` as `scoutalina-debug.apk` or `scoutalina-release.apk`
- Visit `/downloads` to get links. On Android, tapping the link will download the APK.

Documentation
-------------
- See `docs/API.md` for REST endpoints
- See `docs/DEPLOYMENT.md` for Render setup and environment configuration
- See `docs/USER_GUIDE.md` for app usage

Licensing
---------
Licensed under the MIT License. See `LICENSE`.

Contributing
------------
Issues and PRs welcome. Please keep code readable and documented.


