from flask import Blueprint, jsonify, request


api_bp = Blueprint("api", __name__)


@api_bp.get("/v1/ping")
def ping():
    return jsonify({"message": "pong"})


@api_bp.post("/v1/events")
def record_event():
    # TODO: validate and persist event payload
    payload = request.get_json(silent=True) or {}
    return jsonify({"received": payload}), 201


