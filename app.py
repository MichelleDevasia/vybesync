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
        try:
            db.engine.dispose()
            from sqlalchemy import create_engine
            db.engine = create_engine('sqlite:///karaoke_studio.db')
            db.create_all()
            print("[+] Successfully initialized local SQLite fallback database.")
        except Exception as fallback_err:
            print(f"[!] SQLite fallback error: {fallback_err}")
    try:
        StorageService.initialize()  # Create folders for local storage fallback
    except Exception as st_err:
        print(f"[!] Storage initialization warning: {st_err}")

# Register Blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# ----------------- Static File Servings -----------------

@app.route('/')
def serve_index():
    resp = send_from_directory('frontend', 'index.html')
    resp.headers['X-App-Version'] = 'v11_deploy_check'
    return resp

@app.route('/api/status/<task_id>', methods=['GET'])
@jwt_required()
def get_task_status(task_id):
    return SongController.get_task_status(task_id)

@app.route('/api/process', methods=['POST'])
@jwt_required()
def process_song():
    current_user = User.query.get(get_jwt_identity())
    return SongController.process_song(current_user)

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)