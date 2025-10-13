"""Property enrichment service integrating ATTOM with Estated fallback.

This module provides functions to enrich a Route with nearby properties within
the configured buffer distance. It queries third-party APIs, projects results
to the database, and associates properties with routes including precise
distances.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import text

from app import db
from models import Property, Route, RouteProperty


logger = logging.getLogger(__name__)


def enrich_route(route_id: int) -> int:
    """Enrich a route with properties from ATTOM (fallback to Estated).

    Steps:
    - Load route, buffer its geometry, compute bbox
    - Query ATTOM snapshot within bbox
    - For each candidate, ensure inside buffer via ST_DWithin
    - Upsert property and create association with exact distance
    - Return count of associated properties
    """
    logger.info("Enriching route %s", route_id)

    route: Optional[Route] = db.session.get(Route, route_id)
    if not route or not route.geom:
        logger.warning("Route %s not found or has no geometry", route_id)
        return 0

    from flask import current_app

    buffer_meters = int(current_app.config.get("ROUTE_BUFFER_METERS", 100))

    # Compute buffered geometry and bbox using SQL
    bbox_row = db.session.execute(text(
        """
        WITH buf AS (
          SELECT ST_Buffer(:geom::geography, :buf)::geometry AS g
        )
        SELECT ST_XMin(ST_Envelope(g)) AS minlon,
               ST_YMin(ST_Envelope(g)) AS minlat,
               ST_XMax(ST_Envelope(g)) AS maxlon,
               ST_YMax(ST_Envelope(g)) AS maxlat
        FROM buf
        """
    ), {"geom": route.geom.desc, "buf": buffer_meters}).mappings().first()

    if not bbox_row:
        return 0

    logger.info("Querying ATTOM for bbox (%s, %s, %s, %s)", bbox_row["minlat"], bbox_row["maxlat"], bbox_row["minlon"], bbox_row["maxlon"])

    attom_props = _query_attom_bbox(
        minlat=bbox_row["minlat"], maxlat=bbox_row["maxlat"],
        minlon=bbox_row["minlon"], maxlon=bbox_row["maxlon"],
    )

    if attom_props is None:
        logger.warning("ATTOM failed; attempting Estated fallback")
        return enrich_with_estated(route_id)

    count = _upsert_and_associate(route_id, attom_props, buffer_meters)
    logger.info("Found %s properties", count)
    return count


def parse_attom_property(data: dict) -> dict:
    """Extract and normalize ATTOM property data into Property fields."""
    identifier = (data.get("identifier") or {})
    address = (data.get("address") or {})
    location = (data.get("location") or {})
    sale = (data.get("sale") or {})
    amount = (sale.get("amount") or {})
    building = (data.get("building") or {})
    rooms = (building.get("rooms") or {})
    size = (building.get("size") or {})
    vintage = (data.get("vintage") or {})

    attom_id = str(identifier.get("attomId") or "")
    lat = float(location.get("latitude") or 0) or None
    lon = float(location.get("longitude") or 0) or None

    listing_date = None
    if sale.get("saleTransDate"):
        try:
            listing_date = datetime.strptime(sale["saleTransDate"], "%Y-%m-%d").date()
        except Exception:
            listing_date = None

    return {
        "external_id": attom_id or None,
        "address": address.get("line1"),
        "city": address.get("locality"),
        "state": address.get("countrySubd"),
        "zip": address.get("postal1"),
        "latitude": lat,
        "longitude": lon,
        "price": (amount.get("saleamt") if amount.get("saleamt") is not None else None),
        "bedrooms": rooms.get("beds"),
        "bathrooms": rooms.get("bathstotal"),
        "sqft": size.get("livingsize"),
        "lot_sqft": None,
        "year_built": (vintage.get("yearbuilt") if vintage else None),
        "property_type": "SFR",
        "listing_date": listing_date,
        "photo_url": None,
        "source": "ATTOM",
        "last_updated": datetime.utcnow(),
    }


def get_property_photo_url(address: str, attom_id: str) -> Optional[str]:
    """Fetch a photo URL from ATTOM detail API if available (placeholder)."""
    return None


def _query_attom_bbox(*, minlat: float, maxlat: float, minlon: float, maxlon: float) -> Optional[List[dict]]:
    api_key = os.environ.get("ATTOM_API_KEY")
    if not api_key:
        return None
    url = "https://api.gateway.attomdata.com/property/v1/sale/snapshot"
    params = {
        "minlat": minlat,
        "maxlat": maxlat,
        "minlon": minlon,
        "maxlon": maxlon,
        "propertytype": "SFR,CND,MFR",
        "salesearchtype": "listingonly",
    }
    headers = {"apikey": api_key, "accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 429:
            logger.warning("ATTOM rate limited")
            return None
        resp.raise_for_status()
        data = resp.json()
        return data.get("property") or []
    except requests.RequestException:
        return None


def _upsert_and_associate(route_id: int, attom_props: List[dict], buffer_meters: int) -> int:
    count = 0
    for rec in attom_props:
        props = parse_attom_property(rec)
        ext_id = props.get("external_id")
        if not ext_id:
            continue

        existing: Optional[Property] = db.session.query(Property).filter_by(external_id=ext_id).first()
        if existing:
            if existing.last_updated <= datetime.utcnow() - timedelta(hours=24):
                for k, v in props.items():
                    setattr(existing, k, v)
            prop = existing
        else:
            prop = Property(**props)
            db.session.add(prop)
            db.session.flush()

        # Precise distance check and association
        dist_row = db.session.execute(text(
            """
            SELECT ST_Distance(
                     r.geom::geometry,
                     ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry
                   ) AS d
            FROM routes r WHERE r.id = :rid
            """
        ), {"rid": route_id, "lon": props.get("longitude"), "lat": props.get("latitude")}).mappings().first()

        if not dist_row:
            continue
        dist_m = float(dist_row["d"] or 0.0)
        if dist_m > float(buffer_meters):
            continue

        assoc = db.session.query(RouteProperty).filter_by(route_id=route_id, property_id=prop.id).first()
        if not assoc:
            assoc = RouteProperty(route_id=route_id, property_id=prop.id, distance_meters=dist_m)
            db.session.add(assoc)
        else:
            assoc.distance_meters = dist_m
        count += 1

    db.session.commit()
    return count


def enrich_with_estated(route_id: int) -> int:
    """Fallback enrichment using Estated API (placeholder)."""
    return 0


