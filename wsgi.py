import os

try:
    # Prefer package version when running from server/ layout
    from server.app import create_app  # type: ignore
except Exception:
    from app import create_app  # type: ignore

app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    app.run()


