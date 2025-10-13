import os
import threading
import time
import webbrowser

from server.app import create_app


def _open_browser(url: str) -> None:
    time.sleep(1.0)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env if env in ("development", "production", "testing") else "development")
    port = int(os.environ.get("PORT", 5000))
    url = f"http://localhost:{port}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=app.debug)


if __name__ == "__main__":
    main()


