import os


class Config:
    """Base configuration loaded from environment variables.

    TODO:
    - Add DB connection URL and secrets management
    - Add feature flags as needed
    """

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///scoutalina.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


