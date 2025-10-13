import os


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    _db_url = (os.environ.get('DATABASE_URL') or '').replace('postgres://', 'postgresql://')
    # Safe local fallback to SQLite if DATABASE_URL is not set (for design/preview)
    SQLALCHEMY_DATABASE_URI = _db_url if _db_url else 'sqlite:///scoutalina.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ATTOM_API_KEY = os.environ.get('ATTOM_API_KEY')
    ESTATED_API_KEY = os.environ.get('ESTATED_API_KEY')

    # Property enrichment settings
    ROUTE_BUFFER_METERS = 100
    PROPERTY_CACHE_HOURS = 24
    ENRICHMENT_BATCH_SIZE = 50


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


