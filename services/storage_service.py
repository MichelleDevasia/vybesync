import os
import shutil
from werkzeug.utils import secure_filename
from config import Config

class StorageService:
    @staticmethod
    def initialize():
        # Setup base storage folders
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'originals'), exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'instrumentals'), exist_ok=True)
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'covers'), exist_ok=True)

    @staticmethod
    def save_original(local_path, song_id):
        """Save original audio file to persistent storage, returning its URL."""
        if not local_path or not os.path.exists(local_path):
            return None
        
        filename = secure_filename(os.path.basename(local_path))
        dest_dir = os.path.join(Config.UPLOAD_FOLDER, 'originals', str(song_id))
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_path = os.path.join(dest_dir, filename)
        shutil.copy2(local_path, dest_path)
        
        # Returns relative url path for web client access
        return f"/api/storage/originals/{song_id}/{filename}"

    @staticmethod
    def save_instrumental(local_path, song_id):
        """Save separated accompaniment track to storage, returning its URL."""
        if not local_path or not os.path.exists(local_path):
            return None
            
        filename = secure_filename(os.path.basename(local_path))
        dest_dir = os.path.join(Config.UPLOAD_FOLDER, 'instrumentals', str(song_id))
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_path = os.path.join(dest_dir, filename)
        shutil.copy2(local_path, dest_path)
        
        return f"/api/storage/instrumentals/{song_id}/{filename}"

    @staticmethod
    def save_cover(local_path, song_id):
        """Save album cover artwork image, returning its URL."""
        if not local_path or not os.path.exists(local_path):
            return None
            
        filename = secure_filename(os.path.basename(local_path))
        dest_dir = os.path.join(Config.UPLOAD_FOLDER, 'covers', str(song_id))
        os.makedirs(dest_dir, exist_ok=True)
        
        dest_path = os.path.join(dest_dir, filename)
        shutil.copy2(local_path, dest_path)
        
        return f"/api/storage/covers/{song_id}/{filename}"

    # NOTE: To connect Supabase storage bucket, developers can swap the body of these methods to:
    # client = supabase.create_client(url, key)
    # client.storage.from_('bucket').upload(path, file)
    # and return the public URL.
