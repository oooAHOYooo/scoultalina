ScoutAlina
===========

Every drive is a discovery.

ScoutAlina is a GPS-based real estate discovery app that helps drivers discover nearby properties of interest in real time. It consists of a Flask backend (Render-deployable) and a Kivy-based Android client, with simple docs to get started.

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
│   ├── routes/                # Flask blueprints
│   ├── services/              # Domain services
│   ├── static/                # Static assets
│   ├── templates/             # Jinja templates
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
   - `export FLASK_APP=server/app.py`
   - `export FLASK_ENV=development`
4. Initialize the database (optional placeholder): `python server/init_db.py`
5. Run locally: `python -m flask run --port 5000`

Android (Kivy)
1. Ensure Python 3.10+ and buildozer prerequisites
2. Install Kivy and requirements: `pip install -r android/requirements.txt`
3. Run locally (desktop dev): `python android/main.py`
4. Build APK (Android): `cd android && buildozer android debug`

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


