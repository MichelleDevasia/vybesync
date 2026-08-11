from datetime import datetime
from db import db

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False)
    artist = db.Column(db.String(256), nullable=True)
    composer = db.Column(db.String(256), nullable=True)
    pitch = db.Column(db.String(10), nullable=True)
    source = db.Column(db.String(512), nullable=True)
    cover_image = db.Column(db.String(256), nullable=True)
    lyrics = db.Column(db.Text, nullable=True)
    audio_file_url = db.Column(db.String(512), nullable=True)     # Path or remote URL
    karaoke_file_url = db.Column(db.String(512), nullable=True)   # Path or remote URL
    play_count = db.Column(db.Integer, default=0)
    favourite = db.Column(db.Boolean, default=False)
    pinned = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)
    playlist = db.Column(db.String(256), nullable=True)
    tags = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "artist": self.artist,
            "composer": self.composer,
            "pitch": self.pitch,
            "source": self.source,
            "cover_image": self.cover_image,
            "lyrics": self.lyrics,
            "audio_file_url": self.audio_file_url,
            "karaoke_file_url": self.karaoke_file_url,
            "play_count": self.play_count,
            "favourite": self.favourite,
            "pinned": self.pinned,
            "deleted": self.deleted,
            "playlist": self.playlist,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
