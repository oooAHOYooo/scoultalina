import os

try:
    # Prefer package version when running within the repository
    from server.app import create_app  # type: ignore
except Exception:  # noqa: BLE001
    # Fallback if running from a flat layout
    from app import create_app  # type: ignore


app = create_app(os.environ.get('FLASK_ENV', 'production'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))


