import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from db import db
from routes.api import api_bp
from services.storage_service import StorageService

# Explicitly import models to register with SQL Alchemy metadata
from models.user import User
from models.song import Song

app = Flask(__name__, static_folder='frontend')
app.config.from_object(Config)

CORS(app)  # Support cross-origin queries (important for Vercel/Render decoupling)

db.init_app(app)

# Initialize database tables and folders with automatic fallback
with app.app_context():
    try:
        db.create_all()  # Auto-creates schema if tables do not exist
        print("[+] Successfully connected to primary database.")
    except Exception as db_err:
        print(f"[!] Primary DB connection error: {db_err}")
        print("[*] Falling back to local SQLite database...")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///karaoke_studio.db'
        db.engine.dispose()
        db.init_app(app)
        db.create_all()
    StorageService.initialize()  # Create folders for local storage fallback

# Register Blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# ----------------- Static File Servings -----------------

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)