from flask import Blueprint, render_template
from flask import current_app, redirect, url_for, request, send_from_directory

import os
import hashlib
from datetime import datetime
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
    apk_dir = os.path.join(current_app.static_folder, "apk")
    os.makedirs(apk_dir, exist_ok=True)

    apks = []
    for entry in sorted(os.listdir(apk_dir)):
        if not entry.lower().endswith(".apk"):
            continue
        file_path = os.path.join(apk_dir, entry)
        try:
            stat = os.stat(file_path)
            size_bytes = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            # Compute SHA256 for integrity (ok for small number of files)
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            checksum = sha256.hexdigest()
        except Exception:
            size_bytes = 0
            mtime = None
            checksum = None

        # Tracked download URL
        tracked_url = url_for("web.download_apk", filename=entry)
        absolute_url = url_for("web.download_apk", filename=entry, _external=True)
        apks.append(
            dict(
                filename=entry,
                tracked_url=tracked_url,
                absolute_url=absolute_url,
                size_bytes=size_bytes,
                modified_at=mtime.isoformat() if mtime else None,
                sha256=checksum,
            )
        )

    # Compute latest file metadata for hero section
    latest = None
    try:
        candidates = [
            os.path.join(apk_dir, f) for f in os.listdir(apk_dir) if f.lower().endswith(".apk")
        ]
        if candidates:
            newest_path = max(candidates, key=lambda p: os.path.getmtime(p))
            newest_name = os.path.basename(newest_path)
            newest_stat = os.stat(newest_path)
            newest_size = newest_stat.st_size
            newest_mtime = datetime.fromtimestamp(newest_stat.st_mtime).isoformat()
            latest = dict(
                filename=newest_name,
                tracked_url=url_for("web.download_apk", filename=newest_name),
                absolute_url=url_for("web.download_apk", filename=newest_name, _external=True),
                size_bytes=newest_size,
                modified_at=newest_mtime,
            )
    except Exception:
        latest = None

    return render_template("downloads.html", title="Downloads", apks=apks, latest=latest)


@web_bp.get("/downloads/apk/<path:filename>")
def download_apk(filename: str):
    # Serve APK via tracked endpoint and log download event
    apk_dir = os.path.join(current_app.static_folder, "apk")
    file_path = os.path.join(apk_dir, filename)
    if not filename.lower().endswith(".apk") or not os.path.isfile(file_path):
        return redirect(url_for("web.downloads"))

    # Gather request metadata
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent")
    size_bytes = os.path.getsize(file_path)
    ts = datetime.utcnow().isoformat()

    # Log to main app logger
    try:
        current_app.logger.info(
            f"[apk_download] ts={ts} ip={ip} ua={user_agent!r} file={filename} size={size_bytes}"
        )
    except Exception:
        pass

    # Append CSV-style line to dedicated download log
    try:
        logs_dir = os.path.join(current_app.root_path, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, "apk_downloads.csv"), "a", encoding="utf-8") as f:
            f.write(f"{ts},{ip},\"{(user_agent or '').replace('\\', '\\\\').replace('"', '\\"')}\",{filename},{size_bytes}\n")
    except Exception:
        pass

    return send_from_directory(apk_dir, filename, as_attachment=True)


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


