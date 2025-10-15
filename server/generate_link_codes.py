#!/usr/bin/env python3
"""Generate device link codes for testing without interactive login.

Usage examples:
  # Generate 3 codes tied to auto-created users (tester-1..3), valid for 7 days
  python server/generate_link_codes.py --count 3 --ttl-days 7

  # Generate codes for specific labels (become usernames/email prefixes)
  python server/generate_link_codes.py --labels alice,bob --ttl-days 3

The mobile app can then enter a code via "Link Device"; the server will
exchange the code for an API key on /api/device_link/exchange.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List

from .app import create_app, db
from .models import DeviceLinkCode, User


def ensure_tables() -> None:
    # Create only the device link table to avoid PostGIS requirements on SQLite
    try:
        DeviceLinkCode.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        # Fallback to create_all if the engine supports all types
        db.create_all()


def get_or_create_user(label: str) -> User:
    # Use label as username/email prefix
    username = label
    email = f"{label}@example.test"
    user = db.session.query(User).filter((User.username == username) | (User.email == email)).first()
    if user:
        # Ensure API key exists
        if not user.api_key:
            user.generate_api_key()
            db.session.commit()
        return user

    user = User(username=username, email=email)
    # Set a random password; not used by device link flow
    user.set_password(os.environ.get("TEST_USER_DEFAULT_PASSWORD", "not-used-123"))
    user.generate_api_key()
    db.session.add(user)
    db.session.commit()
    return user


def generate_codes(labels: List[str], ttl_minutes: int) -> None:
    expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    rows = []
    for label in labels:
        user = get_or_create_user(label)
        # Create a short-lived code; the API generates the random code on create,
        # but here we can reuse the same generator by importing the endpoint or
        # simply let DB pick a row and have API handle code generation. For
        # simplicity, we let API handle generation in routes; here we just create
        # an empty row would not work. So we replicate minimal code generation.
        from secrets import randbelow

        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = "".join(alphabet[randbelow(len(alphabet))] for _ in range(8))

        dlc = DeviceLinkCode(user_id=user.id, code=code, expires_at=expires_at)
        db.session.add(dlc)
        rows.append((label, code))
    db.session.commit()

    print("Generated device link codes:\n")
    for label, code in rows:
        print(f"  {label:>12}: {code}")
    print(f"\nExpires at (UTC): {expires_at.isoformat()}Z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate device link codes for testers")
    parser.add_argument("--count", type=int, default=1, help="Number of codes to generate (when --labels not used)")
    parser.add_argument("--labels", type=str, default="", help="Comma-separated labels (e.g., alice,bob)")
    parser.add_argument("--ttl-minutes", type=int, default=7 * 24 * 60, help="Minutes until code expiration (default 7 days)")
    parser.add_argument("--ttl-days", type=int, default=None, help="Days until code expiration (overrides --ttl-minutes)")
    parser.add_argument("--env", type=str, default=os.environ.get("FLASK_ENV", "development"), help="Flask config name")
    args = parser.parse_args()

    if args.ttl_days is not None:
        ttl_minutes = int(args.ttl_days) * 24 * 60
    else:
        ttl_minutes = int(args.ttl_minutes)

    if args.labels:
        labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    else:
        labels = [f"tester-{i+1}" for i in range(int(args.count))]

    app = create_app(args.env)
    with app.app_context():
        ensure_tables()
        generate_codes(labels, ttl_minutes)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        sys.exit(1)


