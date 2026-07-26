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
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'vibesync-super-secret-key-999')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'storage')
    GENIUS_TOKEN = os.getenv('GENIUS_TOKEN', 'LZQYig_IDcBO4i8yBiSykKKmUKPQmbKlMef-2GHRUL1cvjRXvIE3Vg_zVrWhko1b')
