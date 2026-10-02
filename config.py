import os

class Config:
    # Use PostgreSQL if available, otherwise fallback to SQLite locally
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///karaoke_studio.db'
    )
    # Fix for newer SQLAlchemy versions with Render's postgresql:// schema
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Connect args depending on DB engine
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"connect_timeout": 3} if "sqlite" not in SQLALCHEMY_DATABASE_URI else {}
    }
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'vibesync-super-secret-key-999')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'storage')
    GENIUS_TOKEN = os.getenv('GENIUS_TOKEN', 'LZQYig_IDcBO4i8yBiSykKKmUKPQmbKlMef-2GHRUL1cvjRXvIE3Vg_zVrWhko1b')
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'c971be4d6dmsh03dc87a0c6c7025p1c8720jsnf043a8f04b07')
    RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'youtube-mp36.p.rapidapi.com')
