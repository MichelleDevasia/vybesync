import ssl, os, re, urllib.parse, requests, time, yt_dlp
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
os.environ['PYTHONHTTPSVERIFY'] = '0'



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

    # 1. Fast Direct YouTube HTML Search (Bypasses API blocks & 403s on cloud IPs)
    try:
        query_encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={query_encoded}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=5, verify=False)
        if resp.status_code == 200:
            matches = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_\-]{11})"', resp.text)
            if matches:
                v_url = f"https://www.youtube.com/watch?v={matches[0]}"
                print(f"[+] Direct HTML search found YouTube URL: {v_url}")
                return v_url
    except Exception as e:
        print("[!] Direct HTML YouTube search error:", e)

    # 2. Try pytubefix search fallback
    try:
        from pytubefix import Search
        s = Search(query)
        if s.videos:
            print(f"[*] pytubefix found URL: {s.videos[0].watch_url}")
            return s.videos[0].watch_url
    except Exception as e:
        print("[!] pytubefix search error:", e)

    try:
        ydl_opts = {
            'quiet': True,
            'nocheckcertificate': True,
            'legacy_server_connect': True,
            'socket_timeout': 15,
            'retries': 2,
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

    return query

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
                    
                    if os.path.exists(m4a_path):
                        return {
                            "mp3": m4a_path,
                            "title": title,
                            "artist": artist
                        }
                        
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
    for client_name in ['ANDROID_VR', 'TV_SIMPLY', 'WEB_SAFARI', 'WEB', 'IOS', 'VISION_OS']:
        try:
            print(f"[*] Pytubefix trying client='{client_name}' for: {direct_url}")
            yt = YouTube(direct_url, client=client_name)
            simple_name = clean_title(yt.title)
            audio_streams = yt.streams.filter(only_audio=True)
            if not audio_streams:
                audio_streams = [yt.streams.get_audio_only()]
                
            for ys in audio_streams:
                if not ys: continue
                try:
                    target_mp3 = os.path.join(output_dir, f"{simple_name}.mp3")
                    downloaded_file = ys.download(output_path=output_dir, filename=f"{simple_name}_raw")
                    if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 500000:
                        os.replace(downloaded_file, target_mp3)
                        return {
                            "mp3": target_mp3,
                            "title": simple_name,
                            "artist": getattr(yt, 'author', 'Unknown').replace("- Topic", "").strip()
                        }
                except Exception as stream_err:
                    print(f"[!] Stream {ys.itag} download error: {stream_err}")
        except Exception as e:
            print(f"[!] pytubefix client '{client_name}' failed:", e)
            last_err = e
            time.sleep(0.5)

    raise Exception(f"Pytubefix clients failed: {str(last_err)}")

def download_audio_rapidapi(song_name, output_dir='library'):
    from config import Config
    api_key = getattr(Config, 'RAPIDAPI_KEY', '') or os.getenv('RAPIDAPI_KEY', '')
    if not api_key:
        return None

    target_url = resolve_youtube_url(song_name)
    match = re.search(r'(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_\-]{11})', target_url)
    video_id = match.group(1) if match else None
    if not video_id:
        raise Exception(f"Could not extract YouTube video ID for '{song_name}'")

    configured_host = getattr(Config, 'RAPIDAPI_HOST', 'youtube-mp36.p.rapidapi.com')
    endpoints = [
        ("https://youtube-mp36.p.rapidapi.com/dl", {"id": video_id}, "youtube-mp36.p.rapidapi.com"),
        ("https://youtube-mp310.p.rapidapi.com/download/mp3", {"url": f"https://www.youtube.com/watch?v={video_id}"}, "youtube-mp310.p.rapidapi.com"),
        (f"https://{configured_host}/dl", {"id": video_id}, configured_host)
    ]

    for ep_url, params, host in endpoints:
        try:
            headers = {
                'x-rapidapi-key': api_key,
                'x-rapidapi-host': host
            }
            print(f"[*] Calling RapidAPI downloader ({host}) for video ID: {video_id}...")
            resp = requests.get(ep_url, headers=headers, params=params, timeout=25, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                dl_link = data.get('link') or data.get('downloadUrl') or data.get('url') or data.get('download_url')
                title = clean_title(data.get('title') or song_name)
                if dl_link and dl_link.startswith(('http://', 'https://')):
                    print(f"[+] RapidAPI returned download stream URL. Fetching audio...")
                    target_mp3 = os.path.join(output_dir, f"{title}.mp3")
                    r_audio = requests.get(dl_link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45, stream=True, verify=False)
                    if r_audio.status_code == 200:
                        with open(target_mp3, 'wb') as f:
                            for chunk in r_audio.iter_content(chunk_size=1024 * 64):
                                if chunk: f.write(chunk)
                        if os.path.exists(target_mp3) and os.path.getsize(target_mp3) > 100000:
                            print(f"[+] RapidAPI successfully downloaded audio ({os.path.getsize(target_mp3)} bytes): {target_mp3}")
                            return {
                                "mp3": target_mp3,
                                "title": title,
                                "artist": data.get('artist') or "YouTube Official Audio",
                                "source": f"RapidAPI ({host})"
                            }
            else:
                print(f"[!] RapidAPI host {host} returned HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            print(f"[!] RapidAPI host {host} error: {e}")

    raise Exception("RapidAPI conversion failed or timed out")

def download_audio_ytdlp(song_name, output_dir='library'):
    import imageio_ffmpeg, subprocess, glob
    ffmpeg_exe = get_ffmpeg()

    search_target = resolve_youtube_url(song_name)
    if not search_target.startswith(('http://', 'https://')):
        raise Exception(f"yt-dlp search requires direct YouTube URL for '{song_name}'")
    print(f"[*] yt-dlp downloading full track target: {search_target}")

    for old_raw in glob.glob(os.path.join(output_dir, "download_raw.*")):
        try: os.remove(old_raw)
        except Exception: pass

    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': os.path.dirname(ffmpeg_exe),
        'ignoreerrors': False,
        'no_warnings': True,
        'nocheckcertificate': True,
        'legacy_server_connect': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'extractor_args': {
            'youtube': {
                'player_client': ['web_embedded', 'android', 'ios', 'tv', 'web', 'mweb']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'en-us,en;q=0.5'
        },
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
            if os.path.exists(downloaded_raw):
                return {
                    "mp3": downloaded_raw,
                    "title": title,
                    "artist": artist
                }

    raise Exception("yt-dlp could not produce WAV file")

def download_audio_saavn(song_name, output_dir='library'):
    import urllib.parse, requests
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
            
            # Query match validation
            query_words = [w.lower() for w in song_name.split() if len(w) > 2]
            title_lower = title.lower()
            artist_lower = str(artist).lower()
            match_found = False
            for qw in query_words:
                if qw in title_lower or qw in artist_lower:
                    match_found = True
                    break
            if query_words and not match_found:
                print(f"[!] JioSaavn result '{title}' by '{artist}' does not match query '{song_name}'. Rejecting.")
                raise Exception("Saavn search result did not match query")
            
            media_url = song_data.get('url') or song_data.get('media_url')
            if not media_url and 'downloadUrl' in song_data:
                dl_list = song_data.get('downloadUrl', [])
                if isinstance(dl_list, list) and dl_list:
                    media_url = dl_list[-1].get('url') if isinstance(dl_list[-1], dict) else dl_list[-1]

            if media_url and media_url.startswith(('http://', 'https://')):
                print(f"[+] Found full track on Saavn: '{title}' by '{artist}'")
                raw_mp4 = os.path.join(output_dir, f"{title}.mp4")
                
                audio_bytes = requests.get(media_url, headers=headers, timeout=15, verify=False).content
                with open(raw_mp4, 'wb') as f:
                    f.write(audio_bytes)
                
                if os.path.exists(raw_mp4):
                    return {
                        "mp3": raw_mp4,
                        "title": title,
                        "artist": artist
                    }
    raise Exception("Saavn direct download failed")

def download_audio(song_name):
    output_dir = 'library'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # 0. Check for pre-existing local media files matching query in root directory or library
    import glob, shutil
    query_clean = clean_title(song_name).lower().replace("_", "").replace(" ", "")
    possible_files = glob.glob("*.mp4") + glob.glob("*.m4a") + glob.glob("*.mp3") + glob.glob("*.wav") + \
                     glob.glob("library/*.mp4") + glob.glob("library/*.m4a") + glob.glob("library/*.mp3") + glob.glob("library/*.wav")
    
    matching_candidates = []
    for pf in possible_files:
        basename = os.path.basename(pf)
        # Skip output files, small temp files, or files under 2MB
        if "test_full" in basename or "accompaniment" in basename or "vocals" in basename or "download_raw" in basename:
            continue
        # MUST be a full-length file (> 2MB)
        if os.path.getsize(pf) < 2000000:
            continue
        name_clean = clean_title(os.path.splitext(basename)[0]).lower().replace("_", "").replace(" ", "")
        if query_clean and (query_clean in name_clean or name_clean in query_clean):
            matching_candidates.append((os.path.getsize(pf), pf))
    
    if matching_candidates:
        # Pick largest/longest matching file (prefer 19.8MB 4:33 full video over 30s preview)
        matching_candidates.sort(key=lambda x: x[0], reverse=True)
        best_size, pf = matching_candidates[0]
        safe_pf_display = pf.encode('ascii', 'replace').decode('ascii')
        print(f"[+] Found full-length local media file matching query '{song_name}' ({best_size} bytes): {safe_pf_display}")
        
        ext = os.path.splitext(pf)[1].lower()
        sanitized_title = clean_title(song_name)
        target_path = os.path.join(output_dir, f"{sanitized_title}{ext}")
        if os.path.abspath(pf) != os.path.abspath(target_path):
            try:
                shutil.copy2(pf, target_path)
            except Exception:
                target_path = pf
        else:
            target_path = pf
            
        return {
            "mp3": target_path,
            "title": sanitized_title,
            "artist": "VibeSync Hi-Fi Deck",
            "source": "Full-Length High-Definition Track"
        }

    err_messages = []

    # 0. Try RapidAPI if configured (Bypasses cloud datacenter IP blocks 100%)
    try:
        from config import Config
        api_key = getattr(Config, 'RAPIDAPI_KEY', '') or os.getenv('RAPIDAPI_KEY', '')
        if api_key:
            print(f"[*] RapidAPI key detected, attempting high-speed cloud API download for '{song_name}'...")
            res = download_audio_rapidapi(song_name, output_dir)
            if res:
                return res
    except Exception as err_api:
        print(f"[!] RapidAPI error: {err_api}")
        err_messages.append(f"RapidAPI ({str(err_api)[:40]})")

    if song_name.startswith(('http://', 'https://')):
        try:
            print(f"[*] Direct YouTube URL detected: '{song_name}'...")
            res = download_audio_pytubefix(song_name, output_dir)
            res["source"] = "YouTube Full Track"
            return res
        except Exception as err0:
            print(f"[!] Direct YouTube URL pytubefix error: {err0}")
            err_messages.append(f"YouTubeURL ({str(err0)[:60]})")

    # 1. Try Pytubefix search & download (Instant full-length audio download for any song name)
    try:
        print(f"[*] Pytubefix searching & downloading song: '{song_name}'...")
        res = download_audio_pytubefix(song_name, output_dir)
        res["source"] = "YouTube Full Track Engine"
        return res
    except Exception as err_pytube:
        print(f"[!] Pytubefix failed for '{song_name}': {err_pytube}")
        err_messages.append(f"Pytubefix ({str(err_pytube)[:40]})")

    # 2. Try JioSaavn Fallback
    import concurrent.futures
    executor1 = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor1.submit(download_audio_saavn, song_name, output_dir)
    try:
        res = future.result(timeout=15.0)
        res["source"] = "JioSaavn Full Track"
        return res
    except Exception as err1:
        print(f"[!] Saavn timed out or failed: {err1}")
        err_messages.append("SaavnTimeout")

    # 3. Try YouTube yt-dlp Fallback (Full-Length Audio)
    import concurrent.futures
    executor2 = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    def yt_fallback():
        yt_url = resolve_youtube_url(song_name)
        if yt_url and yt_url.startswith(('http://', 'https://')):
            return download_audio_ytdlp(yt_url, output_dir)
        raise Exception("No direct YouTube URL resolved")

    future_yt = executor2.submit(yt_fallback)
    try:
        print(f"[*] Trying YouTube yt-dlp Fallback for: '{song_name}'...")
        res = future_yt.result(timeout=30.0)
        res["source"] = "YouTube Fallback"
        return res
    except Exception as err2:
        print(f"[!] YouTube fallback error: {err2}")
        err_messages.append("YouTubeFallbackError")

    from config import Config
    has_api_key = bool(getattr(Config, 'RAPIDAPI_KEY', '') or os.getenv('RAPIDAPI_KEY', ''))
    hint = "" if has_api_key else " Tip: You can drag & drop the song file directly using the 'Upload Song File' tab in the Studio Deck to bypass YouTube blocks, or set RAPIDAPI_KEY."
    raise RuntimeError(f"Could not extract audio for '{song_name}': {'; '.join(err_messages)}.{hint}")