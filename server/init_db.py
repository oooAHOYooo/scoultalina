#!/usr/bin/env python
"""Initialize ScoutAlina database."""

import os
import sys
from sqlalchemy import text

from app import create_app, db
from models import User


def install_postgis() -> None:
    """Install PostGIS extension."""
    print("Installing PostGIS extension...")
    try:
        db.session.execute(text('CREATE EXTENSION IF NOT EXISTS postgis;'))
        db.session.commit()
        print("✓ PostGIS installed")
    except Exception as e:  # noqa: BLE001
        print(f"✗ PostGIS installation failed: {e}")
        sys.exit(1)


def create_tables() -> None:
    """Create all database tables."""
    print("Creating database tables...")
    try:
        db.create_all()
        print("✓ Tables created")
    except Exception as e:  # noqa: BLE001
        print(f"✗ Table creation failed: {e}")
        sys.exit(1)


def create_admin() -> User:
    """Create admin user if none exists."""
    print("Checking for admin user...")

    admin = User.query.filter_by(username='admin').first()
    if admin:
        print("✓ Admin user already exists")
        print(f"  Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  API Key: {admin.api_key}")
        return admin

    admin = User(
        username='admin',
        email=os.environ.get('ADMIN_EMAIL', 'admin@scoutalina.com'),
    )
    admin.set_password(os.environ.get('ADMIN_PASSWORD', 'changeme123'))
    admin.generate_api_key()

    db.session.add(admin)
    db.session.commit()

    print("✓ Admin user created")
    print(f"  Username: {admin.username}")
    print(f"  Email: {admin.email}")
    print(f"  API Key: {admin.api_key}")
    print("\n⚠️  Save this API key! You'll need it for the Android app.")

    return admin


def main() -> None:
    """Run initialization."""
    print("=== ScoutAlina Database Initialization ===\n")

    if not os.environ.get('DATABASE_URL'):
        print("✗ DATABASE_URL environment variable not set")
        sys.exit(1)

    app = create_app('production')

    with app.app_context():
        install_postgis()
        create_tables()
        create_admin()

    print("\n=== Initialization Complete ===")
    print("Next steps:")
    print("1. Copy the API key above")
    print("2. Configure Android app with server URL and API key")
    print("3. Start the server: gunicorn wsgi:app")


if __name__ == '__main__':
    main()

"""Initialize database.

TODO:
- Implement Alembic migrations and actual schema creation
"""

if __name__ == "__main__":
    print("[init_db] Placeholder: implement DB initialization logic.")


