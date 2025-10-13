"""Authentication helpers and decorators for ScoutAlina.

Provides API key enforcement for API routes and integrates with Flask-Login
for web session protection.
"""

from functools import wraps
from typing import Any, Callable, Optional, Tuple, TypeVar, cast

from flask import g, jsonify, request
from flask_login import login_required

from ..app import db
from ..models import User

F = TypeVar("F", bound=Callable[..., Any])


def _extract_api_key() -> Optional[str]:
    # Prefer header, fallback to JSON body
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key.strip()
    if request.is_json:
        data = request.get_json(silent=True) or {}
        key = data.get("api_key")
        if isinstance(key, str) and key:
            return key.strip()
    return None


def require_api_key(func: F) -> F:
    """Decorator to enforce API key authentication on API endpoints."""

    @wraps(func)
    def wrapper(*args: Tuple[Any, ...], **kwargs: Any):  # type: ignore[misc]
        api_key = _extract_api_key()
        if not api_key:
            return jsonify({"error": "Invalid API key"}), 401

        user = db.session.query(User).filter_by(api_key=api_key).first()
        if not user or not user.is_active:
            return jsonify({"error": "Invalid API key"}), 401

        g.current_user = user
        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_auth() -> Callable[[F], F]:
    """Alias for Flask-Login's login_required for web routes."""

    def decorator(func: F) -> F:
        return cast(F, login_required(func))

    return decorator



