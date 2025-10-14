import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'scoutalina.log')

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')

    file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    if app.debug or app.env == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)


def _register_error_handlers(app: Flask) -> None:
    def api_error(status_code: int, message: str):
        return jsonify({"error": message, "status": status_code}), status_code

    @app.errorhandler(400)
    def bad_request(error):  # type: ignore
        if request.path.startswith('/api'):
            return api_error(400, 'Bad Request')
        return render_template('error.html', code=400, message='Bad Request'), 400

    @app.errorhandler(401)
    def unauthorized(error):  # type: ignore
        if request.path.startswith('/api'):
            return api_error(401, 'Unauthorized')
        return render_template('error.html', code=401, message='Unauthorized'), 401

    @app.errorhandler(404)
    def not_found(error):  # type: ignore
        if request.path.startswith('/api'):
            return api_error(404, 'Not Found')
        return render_template('error.html', code=404, message='Not Found'), 404

    @app.errorhandler(500)
    def server_error(error):  # type: ignore
        if request.path.startswith('/api'):
            return api_error(500, 'Internal Server Error')
        return render_template('error.html', code=500, message='Something went wrong'), 500


def create_app(config_name: str = 'development') -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Load config
    from .config import config as config_map  # type: ignore
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'web.login'
    CORS(app, resources={r"/*": {"origins": ["http://localhost:5000", r"*.onrender.com", "https://scoutalina.com", "http://scoutalina.com"]}})

    # Blueprints
    from .routes.api import api_bp  # type: ignore
    from .routes.web import web_bp  # type: ignore
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(web_bp, url_prefix='/')

    # Flask-Login user loader
    from .models import User  # late import to avoid circulars

    @login_manager.user_loader
    def load_user(user_id: str):  # type: ignore
        try:
            from uuid import UUID as _UUID
            return db.session.get(User, _UUID(user_id))
        except Exception:  # noqa: BLE001
            return None

    # Health
    @app.get('/health')
    def health_check():
        return {"status": "ok"}

    # Logging and errors
    _configure_logging(app)
    _register_error_handlers(app)

    # Expose config to templates
    @app.context_processor
    def inject_config():  # type: ignore
        return dict(config=app.config)

    return app


if __name__ == '__main__':
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env if env in ('development', 'production', 'testing') else 'development')
    app.run(host='0.0.0.0', port=5000, debug=app.debug)


