"""Database models for ScoutAlina with PostGIS support.

This module defines the SQLAlchemy ORM models for users, routes, route points,
properties, associations, and watchlists. Geography columns use PostGIS via
GeoAlchemy2. Models include helpful serialization methods and convenience
functions for initialization and bootstrapping an admin user.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from flask_login import UserMixin
from geoalchemy2 import Geography, Geometry  # noqa: F401  (Geometry reserved for future use)
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


# -----------------------------
# User Model
# -----------------------------
class User(db.Model, UserMixin):
    """Application user.

    Attributes store authentication and profile metadata. API keys are generated
    as needed to allow non-interactive client access.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    routes: Mapped[List["Route"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    watchlists: Mapped[List["Watchlist"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self) -> str:
        """Generate a unique 64-hex API key and assign it to the user."""
        # Attempt a few times to avoid rare collisions
        for _ in range(5):
            candidate = secrets.token_hex(32)
            if not db.session.query(User).filter_by(api_key=candidate).first():
                self.api_key = candidate
                return candidate
        # Fallback if collision persists (extremely unlikely)
        candidate = secrets.token_hex(32)
        self.api_key = candidate
        return candidate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
        }


# -----------------------------
# Route Model
# -----------------------------
class Route(db.Model):
    """A recorded driving route consisting of ordered GPS points.

    The `geom` column stores the LineString geography representation, while
    `points` holds the high-resolution time series.
    """

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recorded_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    total_distance_km: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    point_count: Mapped[Optional[int]] = mapped_column(Integer)
    geom = mapped_column(Geography(geometry_type="LINESTRING", srid=4326))

    user: Mapped[User] = relationship(back_populates="routes")
    points: Mapped[List["RoutePoint"]] = relationship(
        back_populates="route",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RoutePoint.timestamp",
    )
    route_properties: Mapped[List["RouteProperty"]] = relationship(
        back_populates="route", cascade="all, delete-orphan", passive_deletes=True
    )
    properties: Mapped[List["Property"]] = relationship(
        "Property",
        secondary="route_properties",
        viewonly=True,
    )

    def to_geojson(self) -> Dict[str, Any]:
        """Return a GeoJSON LineString representation using ordered points.

        Note: This builds from `points` to avoid database-specific ST_AsGeoJSON.
        """
        coordinates = [
            (float(p.longitude), float(p.latitude))
            for p in self.points
            if p.longitude is not None and p.latitude is not None
        ]
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {"id": self.id, "user_id": str(self.user_id)},
        }


# -----------------------------
# RoutePoint Model
# -----------------------------
class RoutePoint(db.Model):
    """A single GPS sample from a recorded route."""

    __tablename__ = "route_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    accuracy_meters: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    speed_mps: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    geom = mapped_column(Geography(geometry_type="POINT", srid=4326))

    route: Mapped[Route] = relationship(back_populates="points")


# -----------------------------
# Property Model
# -----------------------------
class Property(db.Model):
    """A real estate property from external sources (ATTOM/Estated)."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(2))
    zip: Mapped[Optional[str]] = mapped_column(String(10))
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    lot_sqft: Mapped[Optional[int]] = mapped_column(Integer)
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    property_type: Mapped[Optional[str]] = mapped_column(String(50))
    listing_date: Mapped[Optional[date]] = mapped_column(Date)
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(20))  # ATTOM or Estated
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    geom = mapped_column(Geography(geometry_type="POINT", srid=4326))

    route_properties: Mapped[List["RouteProperty"]] = relationship(
        back_populates="property", cascade="all, delete-orphan", passive_deletes=True
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip": self.zip,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "price": float(self.price) if self.price is not None else None,
            "bedrooms": self.bedrooms,
            "bathrooms": float(self.bathrooms) if self.bathrooms is not None else None,
            "sqft": self.sqft,
            "lot_sqft": self.lot_sqft,
            "year_built": self.year_built,
            "property_type": self.property_type,
            "listing_date": self.listing_date.isoformat() if self.listing_date else None,
            "photo_url": self.photo_url,
            "source": self.source,
            "last_updated": self.last_updated.isoformat(),
        }

    def get_rarity(self) -> str:
        """Return a rarity label for gamification.

        This is a placeholder heuristic and should be replaced with a data-driven
        approach combining supply, price percentile, and user preferences.
        """
        price = float(self.price) if self.price is not None else 0.0
        if price >= 2_000_000:
            return "legendary"
        if price >= 1_000_000:
            return "epic"
        if price >= 500_000:
            return "rare"
        return "common"


# -----------------------------
# RouteProperty Association
# -----------------------------
class RouteProperty(db.Model):
    """Association between a Route and a Property with proximity metadata."""

    __tablename__ = "route_properties"

    route_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routes.id", ondelete="CASCADE"), primary_key=True
    )
    property_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True
    )
    distance_meters: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    route: Mapped[Route] = relationship(back_populates="route_properties")
    property: Mapped[Property] = relationship(back_populates="route_properties")


# -----------------------------
# Watchlist Model
# -----------------------------
class Watchlist(db.Model):
    """User-specific tracked properties with optional notes and favorite flag."""

    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "property_id", name="uq_watchlist_user_property"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="watchlists")
    property: Mapped[Property] = relationship()


# -----------------------------
# Indexes
# -----------------------------
# Composite and spatial indexes to optimize typical queries
Index("idx_routes_user_date", Route.user_id, Route.recorded_date)
Index("idx_route_points_route_time", RoutePoint.route_id, RoutePoint.timestamp)
Index("idx_properties_geom", Property.geom, postgresql_using="gist")
Index("idx_routes_geom", Route.geom, postgresql_using="gist")
Index("idx_properties_city_price", Property.city, Property.price)
Index("idx_route_properties_distance", RouteProperty.distance_meters)


# -----------------------------
# Helpers
# -----------------------------
def init_db(app) -> None:
    """Initialize database tables.

    Creates all tables based on the current metadata. In production, prefer
    Alembic migrations to manage schema evolution.
    """
    with app.app_context():
        db.create_all()


def create_admin_user(username: str, email: str, password: str) -> User:
    """Create an initial admin user if not present.

    Returns the existing or newly created user. The password is hashed and an
    API key is generated if absent.
    """
    user: Optional[User] = db.session.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if not user:
        user = User(username=username, email=email)
        user.set_password(password)
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()
        return user

    # Ensure API key exists for existing user
    if not user.api_key:
        user.generate_api_key()
        db.session.commit()
    return user

# TODO: Configure ORM (e.g., SQLAlchemy) models here.
# Suggested models:
# - User
# - Property
# - DiscoveryEvent (user x property x timestamp, gps position)


