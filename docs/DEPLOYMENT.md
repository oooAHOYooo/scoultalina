# Deployment (Render)

This project includes a `server/render.yaml` suitable for deploying the Flask backend on Render.

## Prerequisites
- Render account
- GitHub repository containing this project

## Steps
1. Push the repository to GitHub.
2. In Render, create a new Web Service and connect the repo.
3. Render will detect Python from `runtime.txt` and use the `render.yaml` settings.
4. Ensure environment variables:
   - `SECRET_KEY` (auto-generated if using `render.yaml`)
   - `FLASK_ENV=production`
   - `DATABASE_URL` (optional; configure if using Postgres)
5. Deploy. Render will run:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn wsgi:application --workers=2 --threads=4 --timeout=120`

## Database
- TODO: Configure Postgres on Render and set `DATABASE_URL`
- TODO: Add Alembic migrations and run on release

## Static Files
- Flask serves `server/static/` directly. For heavy assets, consider a CDN.


