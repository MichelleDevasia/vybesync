import os
import scraper
import metadata
from processor import separate_vocals

class ProcessingService:
    @staticmethod
    def process_song_query(query):
        """Downloads audio, splits vocals, scrapes metadata, and returns details with local paths."""
        # 1. Download
        data = scraper.download_audio(query)
        if not data or not data.get("mp3"):
            raise ValueError("Could not download audio from query.")
            
        title = data['title']
        mp3_path = data['mp3']
        
        # Determine image
        cover_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            test_img = mp3_path.replace(".mp3", ext)
            if os.path.exists(test_img):
                cover_path = test_img
                break
        
        # 2. Separate Vocals
        success = separate_vocals(mp3_path)
        if not success:
            raise ValueError("AI stem vocal separation failed.")

        # 3. Lyrics & Metadata
        song_folder_name = os.path.splitext(os.path.basename(mp3_path))[0]
        vocal_path = os.path.join("karaoke_output", song_folder_name, "vocals.wav")
        instrumental_path = os.path.join("karaoke_output", song_folder_name, "accompaniment.wav")
        
        meta = metadata.get_lyrics_and_metadata(title, vocal_path)
        
        singer = meta['singer'] if meta else data['artist']
        composer = meta['composer'] if meta else "Unknown Composer"
        source = data.get('source', 'VibeSync Full Track Engine')
        lyrics = meta['lyrics'] if meta else "Lyrics not found."
        
        # Key/scale detection
        theory = metadata.get_theory_data(mp3_path)
        pitch = theory.get("pitch", "Unknown")
        
        return {
            "title": title,
            "artist": singer,
            "composer": composer,
            "source": source,
            "lyrics": lyrics,
            "pitch": pitch,
            "local_mp3": vocal_path,
            "local_instrumental": instrumental_path,
            "local_cover": cover_path
        }

    @staticmethod
    def process_audio_file(audio_path, original_filename=None, title=None, artist=None):
        """Processes an already provided/uploaded audio file: separates vocals, extracts metadata/key."""
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        base_name = os.path.splitext(os.path.basename(original_filename or audio_path))[0]
        cleaned_title = scraper.clean_title(title or base_name)
        if not cleaned_title:
            cleaned_title = "Uploaded_Track"
            
        # Determine image if any
        cover_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            test_img = os.path.splitext(audio_path)[0] + ext
            if os.path.exists(test_img):
                cover_path = test_img
                break
                
        # 1. Separate Vocals
        success = separate_vocals(audio_path)
        if not success:
            raise ValueError("AI stem vocal separation failed on uploaded file.")
            
        # 2. Stems paths
        song_folder_name = os.path.splitext(os.path.basename(audio_path))[0]
        vocal_path = os.path.join("karaoke_output", song_folder_name, "vocals.wav")
        instrumental_path = os.path.join("karaoke_output", song_folder_name, "accompaniment.wav")
        
        meta = metadata.get_lyrics_and_metadata(cleaned_title, vocal_path)
        singer = artist or (meta['singer'] if meta else "Studio Master")
        composer = meta['composer'] if meta else "Studio Production"
        source = "Direct Audio Upload (Hi-Fi)"
        lyrics = meta['lyrics'] if meta else "Lyrics not found."
        
        theory = metadata.get_theory_data(audio_path)
        pitch = theory.get("pitch", "C Major")
        
        return {
            "title": cleaned_title,
            "artist": singer,
            "composer": composer,
            "source": source,
            "lyrics": lyrics,
            "pitch": pitch,
            "local_mp3": vocal_path,
            "local_instrumental": instrumental_path,
            "local_cover": cover_path
        }
