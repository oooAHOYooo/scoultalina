from __future__ import annotations

"""API routes for ScoutAlina.

Includes authentication, user endpoints, routes upload/listing, properties,
watchlist, stats, and health checks.
"""

import re
from datetime import date, datetime, timedelta
import secrets
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload

from ..app import db
from ..models import Property, Route, RoutePoint, RouteProperty, User, Watchlist, DeviceLinkCode
from ..services.auth import require_api_key


api_bp = Blueprint("api", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@api_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "")

    if not (3 <= len(username) <= 50):
        return _json_error("Invalid username length (3-50)")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""):
        return _json_error("Invalid email")
    if len(password) < 8:
        return _json_error("Password must be at least 8 characters")

    if db.session.query(User).filter((User.username == username) | (User.email == email)).first():
        return _json_error("Username or email already exists")

    user = User(username=username, email=email)
    user.set_password(password)
    user.generate_api_key()
    db.session.add(user)
    db.session.commit()
    return (
        jsonify({
            "status": "success",
            "user_id": str(user.id),
            "api_key": user.api_key,
            "message": "User registered",
        }),
        201,
    )


@api_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "")

    user: Optional[User] = db.session.query(User).filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.api_key:
        user.generate_api_key()
        db.session.commit()

    return jsonify({
        "status": "success",
        "api_key": user.api_key,
        "user": {"username": user.username, "email": user.email},
    })


@api_bp.post("/upload_route")
@require_api_key
def upload_route():
    data = request.get_json(silent=True) or {}
    recorded_date_str = data.get("recorded_date")
    points = data.get("points") or []

    if not recorded_date_str:
        return _json_error("recorded_date is required")
    try:
        recorded_dt = datetime.strptime(recorded_date_str, "%Y-%m-%d").date()
    except ValueError:
        return _json_error("Invalid recorded_date format, expected YYYY-MM-DD")

    if not isinstance(points, list) or not points:
        return _json_error("points must be a non-empty array")

    route = Route(
        user_id=g.current_user.id,
        recorded_date=recorded_dt,
        uploaded_at=datetime.utcnow(),
        point_count=len(points),
    )
    db.session.add(route)
    db.session.flush()  # get route.id

    # Bulk insert route points
    point_rows: List[Dict[str, Any]] = []
    for p in points:
        try:
            ts = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
        except Exception:
            return _json_error("Invalid timestamp in points")
        lat = p.get("lat")
        lon = p.get("lon")
        if lat is None or lon is None:
            return _json_error("Each point requires lat and lon")
        point_rows.append({
            "route_id": route.id,
            "timestamp": ts,
            "latitude": lat,
            "longitude": lon,
            "accuracy_meters": p.get("accuracy"),
            "speed_mps": p.get("speed"),
        })

    db.session.bulk_insert_mappings(RoutePoint, point_rows)
    db.session.flush()

    # Build LineString in DB and compute distance
    db.session.execute(text(
        """
        UPDATE routes r
        SET geom = sub.line::geography,
            total_distance_km = ST_Length(sub.line::geography) / 1000.0
        FROM (
          SELECT ST_MakeLine(
                   ARRAY(
                     SELECT ST_SetSRID(ST_MakePoint(rp.longitude, rp.latitude), 4326)::geometry
                     FROM route_points rp
                     WHERE rp.route_id = :rid
                     ORDER BY rp.timestamp
                   )
                 ) AS line
        ) AS sub
        WHERE r.id = :rid
        """
    ), {"rid": route.id})

    db.session.commit()

    # TODO: Trigger enrichment asynchronously

    return jsonify({
        "status": "success",
        "route_id": route.id,
        "message": "Route uploaded. Enrichment queued.",
    })


@api_bp.get("/routes")
@require_api_key
def list_routes():
    date_param = request.args.get("date")
    q = db.session.query(Route).filter(Route.user_id == g.current_user.id)
    if date_param:
        try:
            d = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            return _json_error("Invalid date format, expected YYYY-MM-DD")
        q = q.filter(Route.recorded_date == d)
    else:
        q = q.filter(Route.recorded_date >= date.today() - timedelta(days=30))

    routes = (
        q.options(joinedload(Route.points))
        .order_by(Route.recorded_date.desc(), Route.id.desc())
        .all()
    )

    payload = []
    for r in routes:
        geojson = r.to_geojson()
        # Property count via association
        property_count = db.session.query(RouteProperty).filter_by(route_id=r.id).count()
        payload.append({
            "id": r.id,
            "date": r.recorded_date.isoformat(),
            "distance_km": float(r.total_distance_km or 0.0),
            "point_count": r.point_count or len(r.points),
            "property_count": property_count,
            "geojson": geojson["geometry"],
        })

    return jsonify({"routes": payload})


@api_bp.get("/properties")
@require_api_key
def list_properties():
    try:
        route_id = int(request.args.get("route_id", "0"))
    except ValueError:
        return _json_error("route_id must be an integer")
    if route_id <= 0:
        return _json_error("Invalid route_id")

    # Ensure route belongs to user
    route = db.session.get(Route, route_id)
    if not route or route.user_id != g.current_user.id:
        return _json_error("Route not found", 404)

    # Join association and properties
    rows = (
        db.session.query(RouteProperty, Property)
        .join(Property, Property.id == RouteProperty.property_id)
        .filter(RouteProperty.route_id == route_id)
        .order_by(RouteProperty.distance_meters.asc())
        .all()
    )

    # Watchlist set for quick containment test
    watch_ids = set(
        rid for (rid,) in db.session.query(Watchlist.property_id).filter(Watchlist.user_id == g.current_user.id).all()
    )

    props = []
    for assoc, prop in rows:
        item = prop.to_dict()
        item.update({
            "lat": float(prop.latitude) if prop.latitude is not None else None,
            "lon": float(prop.longitude) if prop.longitude is not None else None,
            "distance_meters": float(assoc.distance_meters or 0.0),
            "rarity": prop.get_rarity(),
            "is_in_watchlist": prop.id in watch_ids,
        })
        props.append(item)

    return jsonify({"properties": props})


@api_bp.post("/watchlist")
@require_api_key
def add_watchlist():
    data = request.get_json(silent=True) or {}
    property_id = data.get("property_id")
    notes = (data.get("notes") or "").strip()
    if not property_id:
        return _json_error("property_id is required")

    prop = db.session.get(Property, int(property_id))
    if not prop:
        return _json_error("Property not found", 404)

    existing = db.session.query(Watchlist).filter_by(user_id=g.current_user.id, property_id=prop.id).first()
    if existing:
        existing.notes = notes or existing.notes
        db.session.commit()
        return jsonify({"status": "success", "message": "Watchlist updated"})

    wl = Watchlist(user_id=g.current_user.id, property_id=prop.id, notes=notes)
    db.session.add(wl)
    db.session.commit()
    return jsonify({"status": "success", "message": "Added to watchlist"})


@api_bp.delete("/watchlist/<int:property_id>")
@require_api_key
def remove_watchlist(property_id: int):
    row = db.session.query(Watchlist).filter_by(user_id=g.current_user.id, property_id=property_id).first()
    if not row:
        return _json_error("Not in watchlist", 404)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "success", "message": "Removed from watchlist"})


@api_bp.get("/watchlist")
@require_api_key
def list_watchlist():
    rows = (
        db.session.query(Watchlist, Property)
        .join(Property, Property.id == Watchlist.property_id)
        .filter(Watchlist.user_id == g.current_user.id)
        .order_by(Watchlist.added_at.desc())
        .all()
    )
    payload = []
    for wl, prop in rows:
        item = prop.to_dict()
        item.update({"added_at": wl.added_at.isoformat(), "notes": wl.notes})
        payload.append(item)
    return jsonify({"watchlist": payload})


@api_bp.get("/stats")
@require_api_key
def stats():
    uid = g.current_user.id
    total_routes = db.session.query(func.count(Route.id)).filter(Route.user_id == uid).scalar() or 0
    total_distance_km = db.session.query(func.coalesce(func.sum(Route.total_distance_km), 0)).filter(Route.user_id == uid).scalar() or 0

    # Properties discovered via association
    total_properties = db.session.query(func.count(RouteProperty.property_id)).join(Route, Route.id == RouteProperty.route_id).filter(Route.user_id == uid).scalar() or 0

    # Rarity breakdown by price
    def rarity_case():
        return func.case(
            (Property.price >= 2_000_000, 'legendary'),
            (Property.price >= 1_000_000, 'epic'),
            (Property.price >= 500_000, 'rare'),
            else_='common',
        )

    rarity_counts = dict(
        db.session.query(rarity_case().label('rar'), func.count(Property.id))
        .join(RouteProperty, RouteProperty.property_id == Property.id)
        .join(Route, Route.id == RouteProperty.route_id)
        .filter(Route.user_id == uid)
        .group_by('rar')
        .all()
    )

    # Week stats
    week_start = date.today() - timedelta(days=7)
    week_routes = db.session.query(func.count(Route.id)).filter(Route.user_id == uid, Route.recorded_date >= week_start).scalar() or 0
    week_distance = db.session.query(func.coalesce(func.sum(Route.total_distance_km), 0)).filter(Route.user_id == uid, Route.recorded_date >= week_start).scalar() or 0
    week_properties = db.session.query(func.count(RouteProperty.property_id)).join(Route, Route.id == RouteProperty.route_id).filter(Route.user_id == uid, Route.recorded_date >= week_start).scalar() or 0

    return jsonify({
        "total_properties": int(total_properties),
        "total_distance_km": float(total_distance_km),
        "total_routes": int(total_routes),
        "neighborhoods_covered": 0,
        "rarity_breakdown": {
            "legendary": int(rarity_counts.get('legendary', 0)),
            "epic": int(rarity_counts.get('epic', 0)),
            "rare": int(rarity_counts.get('rare', 0)),
            "common": int(rarity_counts.get('common', 0)),
        },
        "this_week": {
            "routes": int(week_routes),
            "properties": int(week_properties),
            "distance_km": float(week_distance),
        },
    })


@api_bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        "status": "ok",
        "db": "connected" if db_ok else "unavailable",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }), (200 if db_ok else 503)



# -----------------------------
# Device Link Endpoints
# -----------------------------

def _generate_link_code(length: int = 8) -> str:
    # URL-safe, uppercase without confusing chars (no I/O/1/0)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(alphabet[secrets.randbelow(len(alphabet))] for _ in range(length))


@api_bp.post("/device_link/create")
@require_api_key
def create_device_link():
    code = _generate_link_code(8)
    expires = datetime.utcnow() + timedelta(minutes=5)
    row = DeviceLinkCode(user_id=g.current_user.id, code=code, expires_at=expires)
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": code, "expires_at": expires.isoformat() + "Z"}), 201


@api_bp.post("/device_link/exchange")
def exchange_device_link():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return _json_error("code is required")

    row: DeviceLinkCode | None = db.session.query(DeviceLinkCode).filter_by(code=code).first()
    if not row or not row.is_valid():
        return _json_error("Invalid or expired code", 401)

    row.used = True
    row.used_at = datetime.utcnow()

    user = db.session.get(User, row.user_id)
    if not user:
        return _json_error("User not found", 404)
    if not user.api_key:
        user.generate_api_key()

    db.session.commit()
    return jsonify({
        "status": "success",
        "api_key": user.api_key,
        "user": {"username": user.username, "email": user.email},
    })

