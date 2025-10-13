from flask import Flask


def create_app() -> Flask:
    """Application factory for Flask.

    TODO:
    - Configure database and ORM
    - Register blueprints (api, web)
    - Set up logging, CORS, auth
    """
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object("config.Config")

    # Blueprint registration deferred to avoid circulars
    from routes.api import api_bp  # type: ignore
    from routes.web import web_bp  # type: ignore
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


