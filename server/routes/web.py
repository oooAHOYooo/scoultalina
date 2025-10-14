from flask import Blueprint, render_template
from flask import current_app, redirect, url_for
from flask_login import logout_user


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


@web_bp.get("/downloads")
def downloads():
    return render_template("downloads.html", title="Downloads")


@web_bp.get("/logout")
def logout():
    logout_user()
    return render_template("login.html", title="Login")


@web_bp.post("/dev/build-apk")
def dev_build_apk():
    # Dev-only: trigger buildozer debug build and place APK under static/apk
    if not current_app.debug:
        return redirect(url_for("web.downloads"))
    import os
    import subprocess
    apk_dir = os.path.join(current_app.static_folder, "apk")
    os.makedirs(apk_dir, exist_ok=True)
    try:
        subprocess.run(["bash", "-lc", "cd android && buildozer android debug"], check=True)
        # Copy typical buildozer output path if exists
        cand = os.path.join(current_app.root_path, "..", "android", "bin")
        for name in ("scoutalina-0.1.0-debug.apk", "*.apk"):
            src = os.path.join(cand, name)
            subprocess.run(["bash", "-lc", f"cp {src} {apk_dir}/scoutalina-debug.apk || true"], check=False)
    except Exception:
        pass
    return redirect(url_for("web.downloads"))


