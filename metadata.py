import typing
import re
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self
    typing.Self = Self

import librosa
import numpy as np
import lyricsgenius
import wikipedia
import musicbrainzngs
import os

# Load Genius Token from environment, fallback to hardcoded value
GENIUS_TOKEN = os.getenv('GENIUS_TOKEN', 'LZQYig_IDcBO4i8yBiSykKKmUKPQmbKlMef-2GHRUL1cvjRXvIE3Vg_zVrWhko1b')
musicbrainzngs.set_useragent("VibeSync-AI-Project", "1.0", "mich@example.com")

def get_theory_data(audio_path):
    """Calculates the musical pitch/key of the track."""
    try:
        y, sr = librosa.load(audio_path, sr=None, duration=10) 
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_index = np.argmax(np.mean(chroma, axis=1))
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        return {"pitch": keys[key_index]}
    except Exception as e:
        print(f"DEBUG: Pitch Error -> {e}")
        return {"pitch": "Unknown"}

def get_lyrics_and_metadata(title, vocal_path=None): # Added vocal_path
    print("\n" + "="*30)
    print(f"DEBUG: Initial YouTube Title -> {title}")
    
    try:
        genius = lyricsgenius.Genius(GENIUS_TOKEN, verbose=False, timeout=3, retries=1)
        
        # Cleaning the title
        clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title)
        junk = ["official", "video", "audio", "lyric", "full song", "hd", "4k", "topic", "vevo"]
        for word in junk:
            clean_title = re.compile(re.escape(word), re.IGNORECASE).sub("", clean_title)
        clean_title = clean_title.replace("-", " ").strip()

        print(f"DEBUG: Cleaned Search Query -> '{clean_title}'")
        
        song = genius.search_song(clean_title)
        
        if song:
            print(f"DEBUG: Found Match on Genius: {song.title} by {song.artist}")
            lyrics_raw = song.lyrics
            lyrics_clean = re.sub(r'\d*Embed$', '', lyrics_raw.split("Lyrics", 1)[-1]).strip() if "Lyrics" in lyrics_raw else lyrics_raw
            
            def get_name(data):
                if hasattr(data, 'name'): return data.name
                if isinstance(data, dict): return data.get('name', 'Unknown')
                return "Unknown"

            singer = get_name(song.primary_artist) if hasattr(song, 'primary_artist') else song.artist
            
            composer = "Unknown"
            producers = getattr(song, 'producer_artists', [])
            writers = getattr(song, 'writer_artists', [])
            
            if producers and len(producers) > 0:
                composer = get_name(producers[0])
            elif writers and len(writers) > 0:
                composer = get_name(writers[0])
            
            return {
                "lyrics": lyrics_clean,
                "singer": singer,
                "composer": composer,
                "source": "Genius API" # Added source tracking
            }
        
        # Fast fallback when Genius has no text match
        else:
            print(f"DEBUG: Genius lookup completed for '{clean_title}'")
            return {
                "lyrics": f"Instrumental track for {title}. Lyrics not found in database.",
                "singer": "Unknown Artist",
                "composer": "Unknown Composer",
                "source": "Catalog Lookup"
            }
            
    except Exception as e:
        print(f"DEBUG: API Error occurred: {e}")
        return None

def get_artist_info(artist_name):
    """Fetches a 3-sentence biography from Wikipedia."""
    clean_artist = artist_name.replace("- Topic", "").replace("VEVO", "").strip()
    try:
        summary = wikipedia.summary(clean_artist, sentences=3)
        return summary
    except Exception:
        return f"Could not find a detailed bio for {clean_artist}. They are a prominent artist in the music industry."