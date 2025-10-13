from flask import Blueprint, render_template


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def dashboard():
    # TODO: provide real data to dashboard
    return render_template("dashboard.html", title="ScoutAlina Dashboard")


@web_bp.get("/login")
def login():
    return render_template("login.html", title="Login")


@web_bp.get("/register")
def register():
    return render_template("register.html", title="Register")


