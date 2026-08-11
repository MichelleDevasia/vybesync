import os
from flask import request, jsonify, send_file
from db import db
from models.song import Song
from services.processing_service import ProcessingService
from services.storage_service import StorageService
from config import Config

class SongController:
    @staticmethod
    def test_version():
        return jsonify({"version": "v10_debug_check"}), 200

    @staticmethod
    def test_process():
        import time, traceback
        t0 = time.time()
        logs = []
        try:
            logs.append(f"0.00s: Start test_process")
            res = ProcessingService.process_song_query("Madhu Pakaroo")
            logs.append(f"{time.time()-t0:.2f}s: ProcessingService finished: title={res.get('title')}")
            return jsonify({"status": "success", "logs": logs, "res": res}), 200
        except Exception as e:
            logs.append(f"{time.time()-t0:.2f}s: Error: {str(e)}")
            return jsonify({"status": "error", "logs": logs, "error": str(e), "traceback": traceback.format_exc()}), 500

    @staticmethod
    def test_ytdlp():
        q = request.args.get('q', 'Madhu Pakaroo')
        import scraper, traceback
        try:
            res = scraper.download_audio_ytdlp(q)
            import soundfile as sf
            data, sr = sf.read(res['mp3'])
            dur = len(data) / sr
            return jsonify({"status": "success", "res": res, "duration": dur}), 200
        except Exception as e:
            return jsonify({"status": "error", "error": str(e), "traceback": traceback.format_exc()}), 500

    @staticmethod
    def list_songs(current_user):
        include_deleted = request.args.get('deleted', 'false') == 'true'
        if include_deleted:
            songs = Song.query.filter_by(user_id=current_user.id, deleted=True).order_by(Song.created_at.desc()).all()
        else:
            songs = Song.query.filter_by(user_id=current_user.id, deleted=False).order_by(Song.pinned.desc(), Song.created_at.desc()).all()
        return jsonify([s.to_dict() for s in songs]), 200

    @staticmethod
    def process_song(current_user):
        data = request.get_json() or {}
        query = data.get('query')
        playlist_name = data.get('playlist')
        tags_str = data.get('tags')
        
        if not query:
            return jsonify({"message": "Query parameter missing."}), 400

        try:
            # We must prevent Render from terminating the connection via 502 Bad Gateway due to idle timeout.
            # We yield spaces every 2 seconds while processing in a background thread, then yield the JSON.
            def generate():
                import time, json, threading
                
                result_container = {}
                def run_processing():
                    try:
                        res = ProcessingService.process_song_query(query)
                        
                        # Save to DB
                        from app import app
                        with app.app_context():
                            song = Song(
                                user_id=current_user.id,
                                title=res["title"],
                                artist=res["artist"],
                                composer=res["composer"],
                                pitch=res["pitch"],
                                source=res["source"],
                                lyrics=res["lyrics"],
                                playlist=playlist_name,
                                tags=tags_str
                            )
                            db.session.add(song)
                            db.session.commit()
                            
                            audio_url = StorageService.save_original(res["local_mp3"], song.id)
                            karaoke_url = StorageService.save_instrumental(res["local_instrumental"], song.id)
                            cover_url = StorageService.save_cover(res["local_cover"], song.id)
                            
                            song.audio_file_url = audio_url
                            song.karaoke_file_url = karaoke_url
                            song.cover_image = cover_url
                            db.session.commit()
                            
                            try:
                                shutil_dir = os.path.join("karaoke_output", res["title"])
                                if os.path.exists(shutil_dir):
                                    import shutil
                                    shutil.rmtree(shutil_dir)
                            except Exception: pass
                            
                            result_container['data'] = song.to_dict()
                    except Exception as e:
                        result_container['error'] = str(e)

                t = threading.Thread(target=run_processing)
                t.start()
                
                # Keep connection alive while processing
                while t.is_alive():
                    yield b" "
                    time.sleep(2)
                    
                if 'error' in result_container:
                    yield json.dumps({"error": result_container['error']}).encode('utf-8')
                else:
                    yield json.dumps(result_container['data']).encode('utf-8')

            from flask import Response
            return Response(generate(), mimetype='application/json', status=201)

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Separation process failed: {str(e)}"}), 500

    @staticmethod
    def stream_storage_file(category, song_id, filename):
        # Serve stored files from local UPLOAD_FOLDER
        path = os.path.join(Config.UPLOAD_FOLDER, category, str(song_id), filename)
        if os.path.exists(path):
            mimetype = 'audio/mpeg' if category == 'originals' else ('audio/wav' if category == 'instrumentals' else 'image/jpeg')
            
            # Check if downloading
            as_attachment = request.args.get('download', 'false') == 'true'
            return send_file(path, mimetype=mimetype, as_attachment=as_attachment, download_name=filename)
            
        return "File not found", 404

    @staticmethod
    def toggle_favourite(current_user, song_id):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        song.favourite = not song.favourite
        db.session.commit()
        return jsonify(song.to_dict()), 200

    @staticmethod
    def toggle_pin(current_user, song_id):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        song.pinned = not song.pinned
        db.session.commit()
        return jsonify(song.to_dict()), 200

    @staticmethod
    def increment_play_count(current_user, song_id):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        song.play_count = (song.play_count or 0) + 1
        db.session.commit()
        return jsonify(song.to_dict()), 200

    @staticmethod
    def update_song_details(current_user, song_id):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        data = request.get_json() or {}
        if 'title' in data:
            song.title = data['title']
        if 'artist' in data:
            song.artist = data['artist']
        if 'playlist' in data:
            song.playlist = data['playlist']
        if 'tags' in data:
            song.tags = data['tags']
            
        db.session.commit()
        return jsonify(song.to_dict()), 200

    @staticmethod
    def delete_song(current_user, song_id):
        # Soft delete: mark deleted=True
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        song.deleted = True
        db.session.commit()
        return jsonify({"message": "Song moved to Trash Bin."}), 200

    @staticmethod
    def restore_song(current_user, song_id):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        song.deleted = False
        db.session.commit()
        return jsonify(song.to_dict()), 200

    @staticmethod
    def purge_song(current_user, song_id):
        # Permanent delete: delete file directories and record
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if not song:
            return jsonify({"message": "Song not found."}), 404
            
        try:
            # Delete files associated with this song
            dirs = ['originals', 'instrumentals', 'covers']
            for d in dirs:
                path = os.path.join(Config.UPLOAD_FOLDER, d, str(song_id))
                if os.path.exists(path):
                    import shutil
                    shutil.rmtree(path)
            
            db.session.delete(song)
            db.session.commit()
            return jsonify({"message": "Song permanently deleted."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Failed to purge song: {str(e)}"}), 500
