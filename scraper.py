import yt_dlp
import os
import re

def clean_title(text):
    # Removes everything after | - ( [ and special characters like '歌'
    text = re.split(r'[|\-\(\[歌]', text)[0]
    # Remove any symbols, keeping only letters, numbers, and spaces
    clean = re.sub(r'[^\w\s]', '', text).strip()
    return clean if clean else "Unknown_Song"

def download_audio(song_name):
    output_dir = 'library'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ignoreerrors': True,           # Don't crash if one video is blocked
        'no_warnings': True,
        'nocheckcertificate': True,     # Helps with some network blocks
        'default_search': 'ytsearch3',
        'writethumbnail': True,
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(song_name, download=True)
        if info is None:
            return {
                "mp3": None,
                "title": "Error",
                "artist": "Unknown"
            }
        # ----------------------------

        entries = info.get('entries')
        if entries:
            video_info = entries[0]
        else:
            video_info = info

        if not video_info:
            raise Exception(f"No audio tracks found on YouTube for '{song_name}'. Please try another search term or full title.")

        # Get the initial path yt-dlp created
        raw_path = ydl.prepare_filename(video_info)
        # yt-dlp might use different extensions before converting to mp3
        for ext in ['.webm', '.m4a', '.mp4']:
            raw_path = raw_path.replace(ext, '.mp3')
            
        # Create the NEW clean name
        simple_name = clean_title(video_info.get('title', 'Song'))
        new_mp3_path = os.path.join(output_dir, f"{simple_name}.mp3")
        new_jpg_path = os.path.join(output_dir, f"{simple_name}.jpg")

        # Rename the MP3
        if os.path.exists(raw_path):
            os.replace(raw_path, new_mp3_path)
            
        # Rename the Poster/Thumbnail
        raw_poster = raw_path.replace(".mp3", ".jpg")
        if os.path.exists(raw_poster):
            os.replace(raw_poster, new_jpg_path)

        return {
            "mp3": new_mp3_path,
            "title": simple_name,
            "artist": video_info.get('uploader', '').replace("- Topic", "").strip()
        }