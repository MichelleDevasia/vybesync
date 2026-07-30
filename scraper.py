import yt_dlp
import os
import re
import urllib.parse
import requests

def clean_title(text):
    # Removes everything after | - ( [ and special characters like '歌'
    text = re.split(r'[|\-\(\[歌]', text)[0]
    # Remove any symbols, keeping only letters, numbers, and spaces
    clean = re.sub(r'[^\w\s]', '', text).strip()
    return clean if clean else "Unknown_Song"

def resolve_youtube_url(query):
    if query.startswith(('http://', 'https://')):
        return query
    try:
        query_encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={query_encoded}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        video_ids = re.findall(r"watch\?v=(\w{11})", resp.text)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        print("URL resolution fallback error:", e)
    return f"ytsearch5:{query}"

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
        'ignoreerrors': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'writethumbnail': True,
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }

    search_target = resolve_youtube_url(song_name)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_target, download=True)
        if info is None:
            return {
                "mp3": None,
                "title": "Error",
                "artist": "Unknown"
            }
        # ----------------------------

        video_info = None
        if 'entries' in info and info['entries']:
            valid_entries = [e for e in info['entries'] if e is not None]
            if valid_entries:
                video_info = valid_entries[0]
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