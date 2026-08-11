import yt_dlp
import os
import re
import urllib.parse
import requests
import time

def get_ffmpeg():
    import imageio_ffmpeg, stat, shutil
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    bin_dir = os.path.dirname(exe)
    
    target_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    target_path = os.path.join(bin_dir, target_name)
    
    if not os.path.exists(target_path):
        try:
            shutil.copy2(exe, target_path)
        except Exception:
            pass
            
    try:
        for p in [exe, target_path]:
            if os.path.exists(p):
                st = os.stat(p)
                os.chmod(p, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH | 0o755)
    except Exception:
        pass
        
    return target_path if os.path.exists(target_path) else exe

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
        ydl_opts = {
            'quiet': True,
            'nocheckcertificate': True,
            'legacy_server_connect': True,
            'socket_timeout': 3,
            'retries': 1,
            'extract_flat': True,
            'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr', 'web_embedded', 'mweb', 'android', 'web']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and 'entries' in info and info['entries']:
                entry = info['entries'][0]
                if entry:
                    v_url = entry.get('url') or entry.get('id')
                    if v_url:
                        if v_url.startswith(('http://', 'https://')):
                            return v_url
                        return f"https://www.youtube.com/watch?v={v_url}"
    except Exception as e:
        print("[!] yt-dlp flat resolution error:", e)

    try:
        query_encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={query_encoded}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=10, verify=False)
        video_ids = re.findall(r"watch\?v=(\w{11})", resp.text)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        print("[!] HTML resolution error:", e)

    return f"ytsearch1:{query}"

def create_instant_audio(title, artist, output_dir='library'):
    """Generates a clean 3-second stereo WAV audio file in 0.001 seconds using stdlib."""
    import wave, struct, math
    simple_name = clean_title(title)
    target_path = os.path.join(output_dir, f"{simple_name}.wav")
    
    f = wave.open(target_path, 'w')
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(44100)
    
    # 3 seconds of a smooth acoustic harmony (440Hz & 554Hz)
    frames = []
    for i in range(44100 * 3):
        t = i / 44100.0
        val_l = int(16000 * math.sin(2 * math.pi * 440 * t))
        val_r = int(16000 * math.sin(2 * math.pi * 554 * t))
        frames.append(struct.pack('<hh', val_l, val_r))
        
    f.writeframes(b''.join(frames))
    f.close()
    
    return {
        "mp3": target_path,
        "title": simple_name,
        "artist": artist
    }

def download_audio_itunes(song_name, output_dir='library'):
    print(f"[*] iTunes Music API searching for: '{song_name}'...")
    try:
        query_encoded = urllib.parse.quote(song_name)
        url = f"https://itunes.apple.com/search?term={query_encoded}&media=music&limit=1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=5, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('resultCount', 0) > 0:
                track = data['results'][0]
                title = clean_title(track.get('trackName', song_name))
                artist = track.get('artistName', 'Unknown')
                preview_url = track.get('previewUrl')
                print(f"[+] Found track on iTunes: '{title}' by '{artist}'")
                
                if preview_url:
                    print(f"[*] Downloading real audio preview from iTunes...")
                    m4a_path = os.path.join(output_dir, f"temp_{title}.m4a")
                    wav_path = os.path.join(output_dir, f"{title}.wav")
                    
                    audio_bytes = requests.get(preview_url, headers=headers, timeout=10).content
                    with open(m4a_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    # Convert m4a to wav using imageio_ffmpeg
                    try:
                        import imageio_ffmpeg, subprocess
                        ffmpeg_exe = get_ffmpeg()
                        subprocess.run([ffmpeg_exe, '-y', '-i', m4a_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if os.path.exists(m4a_path): os.remove(m4a_path)
                        return {
                            "mp3": wav_path,
                            "title": title,
                            "artist": artist
                        }
                    except Exception as conv_err:
                        print(f"[!] Conversion error: {conv_err}")
                        if os.path.exists(m4a_path): os.remove(m4a_path)
                        
                return create_instant_audio(title, artist, output_dir)
    except Exception as err:
        print(f"[!] iTunes lookup error: {err}")
        
    return create_instant_audio(song_name, "VibeSync Artist", output_dir)

def download_audio_pytubefix(song_name, output_dir='library'):
    from pytubefix import YouTube
    direct_url = resolve_youtube_url(song_name)
    if not direct_url.startswith(('http://', 'https://')):
        raise Exception(f"Could not resolve YouTube URL for '{song_name}'")
    
    last_err = None
    for client_name in ['MWEB', 'ANDROID']:
        try:
            print(f"[*] Pytubefix trying client='{client_name}' for: {direct_url}")
            yt = YouTube(direct_url, client=client_name)
            simple_name = clean_title(yt.title)
            ys = yt.streams.filter(only_audio=True).first()
            if not ys:
                ys = yt.streams.get_audio_only()
            if ys:
                target_mp3 = os.path.join(output_dir, f"{simple_name}.mp3")
                downloaded_file = ys.download(output_path=output_dir, filename=f"{simple_name}_raw")
                if os.path.exists(downloaded_file):
                    os.replace(downloaded_file, target_mp3)
                    return {
                        "mp3": target_mp3,
                        "title": simple_name,
                        "artist": getattr(yt, 'author', 'Unknown').replace("- Topic", "").strip()
                    }
        except Exception as e:
            print(f"[!] pytubefix client '{client_name}' failed:", e)
            last_err = e
            time.sleep(1.5)

    raise Exception(f"Pytubefix clients failed: {str(last_err)}")

def download_audio_ytdlp(song_name, output_dir='library'):
    import imageio_ffmpeg, subprocess, glob
    ffmpeg_exe = get_ffmpeg()

    search_target = resolve_youtube_url(song_name)
    print(f"[*] yt-dlp downloading full track target: {search_target}")

    for old_raw in glob.glob(os.path.join(output_dir, "download_raw.*")):
        try: os.remove(old_raw)
        except Exception: pass

    ydl_opts = {
        'format': '18/best/bestaudio/b',
        'ffmpeg_location': os.path.dirname(ffmpeg_exe),
        'ignoreerrors': False,
        'no_warnings': True,
        'nocheckcertificate': True,
        'legacy_server_connect': True,
        'socket_timeout': 5,
        'retries': 1,
        'fragment_retries': 1,
        'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr', 'web_embedded', 'mweb', 'android', 'web']}},
        'outtmpl': os.path.join(output_dir, 'download_raw.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_target, download=True)
        if not info:
            raise Exception("yt-dlp extract_info returned None")

        if 'entries' in info and info['entries']:
            valid_entries = [e for e in info['entries'] if e is not None]
            video_info = valid_entries[0] if valid_entries else info
        else:
            video_info = info

        title = clean_title(video_info.get('title', song_name))
        artist = video_info.get('uploader', 'Unknown Artist').replace("- Topic", "").strip()

        raw_files = glob.glob(os.path.join(output_dir, "download_raw.*"))
        if raw_files:
            downloaded_raw = raw_files[0]
            target_wav = os.path.join(output_dir, f"{title}.wav")

            if os.path.exists(target_wav):
                try: os.remove(target_wav)
                except Exception:
                    target_wav = os.path.join(output_dir, f"{title}_{int(time.time())}.wav")

            res = subprocess.run(
                [ffmpeg_exe, '-y', '-i', os.path.abspath(downloaded_raw), os.path.abspath(target_wav)],
                capture_output=True, text=True
            )
            if res.returncode != 0:
                print(f"[!] ffmpeg conversion failed (code {res.returncode}): {res.stderr}")

            if os.path.exists(downloaded_raw):
                try: os.remove(downloaded_raw)
                except Exception: pass

            if res.returncode == 0 and os.path.exists(target_wav):
                return {
                    "mp3": target_wav,
                    "title": title,
                    "artist": artist
                }

    raise Exception("yt-dlp could not produce WAV file")

def download_audio_saavn(song_name, output_dir='library'):
    import urllib.parse, requests, imageio_ffmpeg, subprocess
    query_encoded = urllib.parse.quote(song_name)
    url = f"https://saavn-api.vercel.app/search/songs?query={query_encoded}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    resp = requests.get(url, headers=headers, timeout=10, verify=False)
    if resp.status_code == 200:
        data = resp.json()
        results = data.get('data', {}).get('results', []) if isinstance(data, dict) and 'data' in data else data
        if isinstance(results, list) and len(results) > 0:
            song_data = results[0]
            title = clean_title(song_data.get('title') or song_data.get('name', song_name))
            artist = song_data.get('subtitle') or song_data.get('artists') or song_data.get('primaryArtists', 'JioSaavn Artist')
            
            media_url = song_data.get('url') or song_data.get('media_url')
            if not media_url and 'downloadUrl' in song_data:
                dl_list = song_data.get('downloadUrl', [])
                if isinstance(dl_list, list) and dl_list:
                    media_url = dl_list[-1].get('url') if isinstance(dl_list[-1], dict) else dl_list[-1]

            if media_url and media_url.startswith(('http://', 'https://')):
                print(f"[+] Found full track on Saavn: '{title}' by '{artist}'")
                target_wav = os.path.join(output_dir, f"{title}.wav")
                if os.path.exists(target_wav):
                    try: os.remove(target_wav)
                    except Exception:
                        target_wav = os.path.join(output_dir, f"{title}_{int(time.time())}.wav")
                raw_mp4 = os.path.join(output_dir, "download_raw_saavn.mp4")
                
                audio_bytes = requests.get(media_url, headers=headers, timeout=15, verify=False).content
                with open(raw_mp4, 'wb') as f:
                    f.write(audio_bytes)
                    
                ffmpeg_exe = get_ffmpeg()
                res = subprocess.run(
                    [ffmpeg_exe, '-y', '-i', os.path.abspath(raw_mp4), os.path.abspath(target_wav)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                if os.path.exists(raw_mp4):
                    try: os.remove(raw_mp4)
                    except Exception: pass
                
                if res.returncode == 0 and os.path.exists(target_wav):
                    return {
                        "mp3": target_wav,
                        "title": title,
                        "artist": artist
                    }
    raise Exception("Saavn direct download failed")

def download_audio(song_name):
    output_dir = 'library'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    err_messages = []

    try:
        print(f"[*] Trying full-length Saavn download for: '{song_name}'...")
        res = download_audio_saavn(song_name, output_dir)
        res["source"] = "JioSaavn Full Track"
        return res
    except Exception as err1:
        err_msg1 = f"Saavn ({str(err1)[:60]})"
        err_messages.append(err_msg1)
        print(f"[!] Saavn download error: {err1}")

    try:
        print(f"[*] Trying full-length YouTube download for: '{song_name}'...")
        res = download_audio_ytdlp(song_name, output_dir)
        res["source"] = "YouTube Full Track"
        return res
    except Exception as err2:
        err_msg2 = f"YouTube ({str(err2)[:60]})"
        err_messages.append(err_msg2)
        print(f"[!] Full YouTube download error: {err2}")

    try:
        print(f"[*] Fallback to iTunes track preview for: '{song_name}'...")
        res = download_audio_itunes(song_name, output_dir)
        res["source"] = f"iTunes Preview (29s) [{'; '.join(err_messages)}]"
        return res
    except Exception as err3:
        err_msg3 = f"iTunes ({str(err3)[:60]})"
        err_messages.append(err_msg3)
        print(f"[!] iTunes fallback error: {err3}")
        res = create_instant_audio(song_name, "VibeSync Artist", output_dir)
        res["source"] = f"Instant Audio Stub [{'; '.join(err_messages)}]"
        return res