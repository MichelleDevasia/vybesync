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

def download_audio_pytubefix(song_name, output_dir='library'):
    from pytubefix import YouTube
    direct_url = resolve_youtube_url(song_name)
    if not direct_url.startswith(('http://', 'https://')):
        raise Exception(f"Could not resolve YouTube URL for '{song_name}'")
    
    print(f"[*] Pytubefix attempting download for: {direct_url}")
    yt = YouTube(direct_url)
    simple_name = clean_title(yt.title)
    ys = yt.streams.get_audio_only()
    
    target_mp3 = os.path.join(output_dir, f"{simple_name}.mp3")
    temp_filename = f"{simple_name}_raw"
    downloaded_file = ys.download(output_path=output_dir, filename=temp_filename)
    
    if os.path.exists(downloaded_file):
        os.replace(downloaded_file, target_mp3)
        
    return {
        "mp3": target_mp3,
        "title": simple_name,
        "artist": getattr(yt, 'author', 'Unknown').replace("- Topic", "").strip()
    }

def download_audio(song_name):
    output_dir = 'library'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_bin = None

    ydl_opts = {
        'format': 'ba/b/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ignoreerrors': False,
        'no_warnings': True,
        'nocheckcertificate': True,
        'writethumbnail': False,
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': False,
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

    if ffmpeg_bin:
        ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_bin)

    search_target = resolve_youtube_url(song_name)
    print(f"[*] Downloading audio target: {search_target} using FFmpeg at {ffmpeg_bin}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_target, download=True)
        except Exception as err:
            print("[!] yt-dlp error, attempting pytubefix fallback:", err)
            try:
                return download_audio_pytubefix(song_name, output_dir)
            except Exception as pyerr:
                print("[!] pytubefix error:", pyerr)
                raise Exception(f"Audio download failed. Primary error: {str(err)}")

        if info is None:
            return download_audio_pytubefix(song_name, output_dir)

        # Handle search results vs direct video info
        if 'entries' in info and info['entries']:
            valid_entries = [e for e in info['entries'] if e is not None]
            video_info = valid_entries[0] if valid_entries else info
        else:
            video_info = info

        if not video_info:
            return download_audio_pytubefix(song_name, output_dir)

        raw_path = ydl.prepare_filename(video_info)
        base_path = os.path.splitext(raw_path)[0]
        actual_mp3_path = base_path + ".mp3"

        simple_name = clean_title(video_info.get('title', 'Song'))
        new_mp3_path = os.path.join(output_dir, f"{simple_name}.mp3")
        new_jpg_path = os.path.join(output_dir, f"{simple_name}.jpg")

        # Find and move the created MP3 file
        if os.path.exists(actual_mp3_path):
            os.replace(actual_mp3_path, new_mp3_path)
        elif os.path.exists(raw_path):
            os.replace(raw_path, new_mp3_path)
        else:
            # Fallback: find any file in library matching the base name
            for f in os.listdir(output_dir):
                if f.endswith('.mp3') and not f.startswith('karaoke_'):
                    new_mp3_path = os.path.join(output_dir, f)
                    break

        return {
            "mp3": new_mp3_path,
            "title": simple_name,
            "artist": video_info.get('uploader', '').replace("- Topic", "").strip()
        }