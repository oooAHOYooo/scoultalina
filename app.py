import os
import socket
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path


def _open_browser(url: str) -> None:
    time.sleep(1.0)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _in_venv() -> bool:
    return getattr(sys, 'base_prefix', sys.prefix) != sys.prefix or bool(os.environ.get('VIRTUAL_ENV'))


def _venv_python() -> Path:
    base = Path(__file__).resolve().parent
    # macOS/Linux path
    return base / '.venv' / 'bin' / 'python'


def _ensure_venv_and_requirements() -> None:
    base = Path(__file__).resolve().parent
    venv_python = _venv_python()
    # Prefer root requirements.txt, fallback to server/requirements.txt
    req_root = base / 'requirements.txt'
    req_server = base / 'server' / 'requirements.txt'
    req = req_root if req_root.exists() else req_server
    stamp = base / '.venv' / '.installed'

    if not _in_venv():
        # Create venv if missing, then re-exec within it
        if not venv_python.exists():
            print('[bootstrap] Creating virtualenv at .venv ...')
            subprocess.check_call([sys.executable, '-m', 'venv', str(base / '.venv')])
        # Install only if not installed before or requirements changed
        need_install = True
        try:
            if stamp.exists() and req.exists() and stamp.stat().st_mtime >= req.stat().st_mtime:
                need_install = False
        except Exception:
            need_install = True
        if need_install:
            print('[bootstrap] Installing requirements ...')
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'])
            subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '-r', str(req)])
            try:
                stamp.touch()
            except Exception:
                pass
        # Re-exec into venv python
        os.execv(str(venv_python), [str(venv_python), __file__])

    # Already in venv: ensure critical deps are present (e.g., geoalchemy2)
    try:
        import geoalchemy2  # noqa: F401
    except Exception:
        # Install once inside venv if missing
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(req)])

    # Ensure APK folder exists for downloads (support both layouts)
    apk_dir = (base / 'static' / 'apk') if (base / 'static').exists() else (base / 'server' / 'static' / 'apk')
    apk_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    _ensure_venv_and_requirements()

    # Import after ensuring deps are installed and venv active
    try:
        from server.app import create_app  # type: ignore
    except Exception:
        from app import create_app  # type: ignore

    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env if env in ("development", "production", "testing") else "development")

    # Prefer explicit PORT; otherwise pick a free one
    port_env = os.environ.get("PORT")
    port = int(port_env) if port_env else _find_free_port()
    url = f"http://localhost:{port}"

    try:
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
        app.run(host="0.0.0.0", port=port, debug=app.debug)
    except OSError:
        # Retry once on a new free port
        port = _find_free_port()
        url = f"http://localhost:{port}"
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
        app.run(host="0.0.0.0", port=port, debug=app.debug)


if __name__ == "__main__":
    main()


