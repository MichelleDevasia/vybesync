from flask import Blueprint
from controllers.auth_controller import AuthController
from controllers.song_controller import SongController
from services.auth_service import token_required

api_bp = Blueprint('api', __name__)

# Authentication Routes
api_bp.route('/auth/register', methods=['POST'])(AuthController.register)
api_bp.route('/auth/login', methods=['POST'])(AuthController.login)
api_bp.route('/auth/profile', methods=['GET'])(token_required(AuthController.get_profile))

# Song Management Routes
api_bp.route('/songs', methods=['GET'])(token_required(SongController.list_songs))
api_bp.route('/process', methods=['POST'])(token_required(SongController.process_song))
api_bp.route('/songs/<int:song_id>/favourite', methods=['POST'])(token_required(SongController.toggle_favourite))
api_bp.route('/songs/<int:song_id>/pin', methods=['POST'])(token_required(SongController.toggle_pin))
api_bp.route('/songs/<int:song_id>/play', methods=['POST'])(token_required(SongController.increment_play_count))
api_bp.route('/songs/<int:song_id>/details', methods=['PUT'])(token_required(SongController.update_song_details))
api_bp.route('/songs/<int:song_id>', methods=['DELETE'])(token_required(SongController.delete_song))
api_bp.route('/songs/<int:song_id>/restore', methods=['POST'])(token_required(SongController.restore_song))
api_bp.route('/songs/<int:song_id>/purge', methods=['DELETE'])(token_required(SongController.purge_song))

# Media Storage Streaming (Unprotected for simple HTML5 Audio tag streams)
api_bp.route('/storage/<category>/<int:song_id>/<filename>', methods=['GET'])(SongController.stream_storage_file)
api_bp.route('/test_ytdlp', methods=['GET'])(SongController.test_ytdlp)

@api_bp.route('/reload_gunicorn', methods=['GET'])
def reload_gunicorn():
    import os
    os._exit(0)

@api_bp.route('/test_version', methods=['GET'])
def test_version():
    from flask import jsonify
    return jsonify({"version": "v10_debug_check"}), 200
