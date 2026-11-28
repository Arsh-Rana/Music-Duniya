#!/usr/bin/env python3
"""
Music-Duniya Backend Server with Ultra-Fast Streaming, Multi-Source Search (DJJohal + Mr-Jatt + DJPunjab),
Artist Avatars, Supabase Cloud Caching, Long-Distance Jam Sync, and Update Verification.
"""
import os
import sys
import json
import time
import mimetypes
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import dual_scraper
import djpunjab_scraper
import cache_manager

PORT = int(os.environ.get("PORT", 3000))
MUSIC_APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(MUSIC_APP_DIR)
DOWNLOADS_DIR = os.path.join(ROOT_DIR, "downloads")
TEMP_CACHE_DIR = os.path.join(MUSIC_APP_DIR, "temp_cache")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TEMP_CACHE_DIR, exist_ok=True)

# Memory Cache for Direct Stream URLs (for <100ms ultra-fast playback)
STREAM_URL_CACHE = {}

# Active Jam Rooms for Long-Distance Listen Together
JAM_ROOMS = {}


class MusicDuniyaHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Range, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        pathname = urllib.parse.unquote(parsed.path)
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API: Local / Curated songs
        if pathname == "/api/songs":
            songs_file = os.path.join(MUSIC_APP_DIR, "songs.json")
            if os.path.exists(songs_file):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                with open(songs_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "songs.json not found")
            return

        # 1b. API: Curated Playlists
        if pathname in ("/api/playlists", "/api/curated-playlists"):
            playlists_file = os.path.join(MUSIC_APP_DIR, "playlists_resolved.json")
            if os.path.exists(playlists_file):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                with open(playlists_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_json_response({})
            return

        # 2. API: Popular Singers with Avatars
        if pathname == "/api/singers":
            singers = djpunjab_scraper.get_popular_singers()
            self.send_json_response(singers)
            return

        # 3. API: All Singers from djpunjab.is A-Z
        if pathname == "/api/all-singers":
            letter = query_params.get("letter", ["a"])[0].strip()
            singers = djpunjab_scraper.get_all_singers_by_letter(letter)
            self.send_json_response(singers)
            return

        # 4. API: Singer Profile and Songs from djpunjab.is
        if pathname == "/api/singer-profile":
            slug = query_params.get("slug", [""])[0].strip()
            if not slug:
                self.send_error(400, "Missing slug parameter")
                return
            profile = djpunjab_scraper.get_singer_profile_and_songs(slug)
            self.send_json_response(profile)
            return

        # 5. API: Multi-Source Search (DJJohal + Mr-Jatt + DJPunjab)
        if pathname == "/api/search-online":
            q = query_params.get("q", [""])[0].strip()
            if not q:
                self.send_json_response([])
                return

            try:
                online_results = dual_scraper.search_all_sources(q)
                self.send_json_response(online_results)
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=500)
            return

        # 6. API: Instant Stream Resolution (< 100ms Ultra-Fast Playback)
        if pathname == "/api/stream-or-download":
            song_id = query_params.get("id", [""])[0]
            source = query_params.get("source", [""])[0]
            page_url = query_params.get("page_url", [""])[0]
            stream_url = query_params.get("stream_url", [""])[0]

            if not song_id or not source:
                self.send_error(400, "Missing id or source parameter")
                return

            # Check if already cached locally on disk
            clean_id = song_id.replace('djpunjab_', '').replace('djjohal_', '').replace('mrjatt_', '')
            local_cached = os.path.join(TEMP_CACHE_DIR, f"{clean_id}.mp3")
            if os.path.exists(local_cached) and os.path.getsize(local_cached) > 50000:
                self.stream_audio_file(local_cached)
                return

            # 1. Resolve direct CDN URL with in-memory caching for zero latency
            cache_key = f"{source}_{song_id}"
            direct_cdn_url = STREAM_URL_CACHE.get(cache_key)

            if not direct_cdn_url:
                if source == "djpunjab":
                    direct_cdn_url = djpunjab_scraper.resolve_djpunjab_mp3_stream(page_url)
                elif source == "djjohal":
                    direct_cdn_url = dual_scraper.resolve_djjohal_direct_url(page_url)
                elif source == "mrjatt":
                    direct_cdn_url = dual_scraper.resolve_mrjatt_direct_url(page_url)
                elif stream_url:
                    direct_cdn_url = stream_url

                if direct_cdn_url:
                    STREAM_URL_CACHE[cache_key] = direct_cdn_url

            if direct_cdn_url:
                # Launch background caching thread so audio plays immediately without downloading first
                threading.Thread(target=self.background_cache_file, args=(direct_cdn_url, source, local_cached), daemon=True).start()

                # Redirect client directly to CDN stream for immediate playback (<100ms)
                self.send_response(302)
                self.send_header("Location", direct_cdn_url)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                return

            # Fallback to local streaming
            self.send_error(404, "Stream URL could not be resolved")
            return

        # 7. API: Jam / Listen Together Sync (Get State)
        if pathname == "/api/jam/sync":
            room_id = query_params.get("room", [""])[0].strip().upper()
            if not room_id or room_id not in JAM_ROOMS:
                self.send_json_response({"active": False, "message": "Room not found"})
                return
            room = JAM_ROOMS[room_id]
            self.send_json_response({"active": True, "room": room})
            return

        # 8. API: Check for Updates in Settings & Background OTA Broadcast
        if pathname == "/api/check-update":
            apk_path = os.path.join(ROOT_DIR, "Music.apk")
            if not os.path.exists(apk_path):
                apk_path = os.path.join(ROOT_DIR, "Music-Duniya.apk")
            apk_size_mb = f"{os.path.getsize(apk_path) / (1024 * 1024):.2f} MB" if os.path.exists(apk_path) else "0.15 MB"
            update_info = {
                "app_name": "Music",
                "current_version": "v2.0.0",
                "latest_version": "v2.0.0",
                "update_available": True,
                "is_latest": False,
                "release_date": "2026-11-28",
                "apk_filename": "Music.apk",
                "apk_download_url": "/Music.apk",
                "apk_url": "/Music.apk",
                "apk_size": apk_size_mb,
                "title": "Haute Hi-Fi Studio & Background Playback Release",
                "changelog": "• Haute Hi-Fi Studio Master Soundstage with 3D Turntable Deck & Tonearm<br>• Native Android Foreground Media Notification with lockscreen controls<br>• Full Android OS Force Stop capability enabled during background playback<br>• Heavyweight Master Crates & Royal Punjabi Maestros catalog<br>• Mandatory Gmail authentication gate & long-distance Jam sync"
            }
            self.send_json_response(update_info)
            return

        # 9. Serve APK File Directly (support both /Music.apk and /Music-Duniya.apk)
        if pathname in ("/Music.apk", "/Music-Duniya.apk", "/download/apk"):
            apk_file = os.path.join(ROOT_DIR, "Music.apk")
            if not os.path.exists(apk_file):
                apk_file = os.path.join(ROOT_DIR, "Music-Duniya.apk")
            if not os.path.exists(apk_file):
                apk_file = os.path.join(MUSIC_APP_DIR, "Music.apk")
            if not os.path.exists(apk_file):
                apk_file = os.path.join(MUSIC_APP_DIR, "Music-Duniya.apk")

            if os.path.exists(apk_file):
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.android.package-archive")
                self.send_header("Content-Disposition", 'attachment; filename="Music.apk"')
                self.send_header("Content-Length", str(os.path.getsize(apk_file)))
                self.end_headers()
                with open(apk_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "APK not found")
            return

        # 10. API: List temporarily cached songs
        if pathname == "/api/cached-songs":
            cached_files = []
            for f in os.listdir(TEMP_CACHE_DIR):
                if f.endswith('.mp3'):
                    p = os.path.join(TEMP_CACHE_DIR, f)
                    cached_files.append({
                        "id": f.replace('.mp3', ''),
                        "filename": f,
                        "size": os.path.getsize(p),
                        "mtime": os.path.getmtime(p),
                        "audio_url": f"/audio/cache/{urllib.parse.quote(f)}"
                    })
            self.send_json_response(cached_files)
            return

        # 11. Audio Range Streaming for local / downloads / cache
        if pathname.startswith("/audio/"):
            subpath = pathname[len("/audio/"):]
            if subpath.startswith("cache/"):
                actual_file = os.path.join(TEMP_CACHE_DIR, subpath[len("cache/"):])
            else:
                actual_file = os.path.join(DOWNLOADS_DIR, subpath)

            if not os.path.exists(actual_file):
                cache_cand = os.path.join(TEMP_CACHE_DIR, subpath)
                if os.path.exists(cache_cand):
                    actual_file = cache_cand
                else:
                    self.send_error(404, "Audio file not found")
                    return

            self.stream_audio_file(actual_file)
            return

        # 12. Static files serving
        if pathname in ("/", ""):
            pathname = "/index.html"

        file_path = os.path.join(MUSIC_APP_DIR, pathname.lstrip("/"))
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.send_header("Content-Length", str(os.path.getsize(file_path)))
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            # SPA fallback
            index_path = os.path.join(MUSIC_APP_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(os.path.getsize(index_path)))
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        pathname = urllib.parse.unquote(parsed.path)

        # 1. API: Jam / Listen Together Create Room
        if pathname == "/api/jam/create":
            import random
            room_code = f"DUNIYA-{random.randint(1000, 9999)}"
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                data = {}

            JAM_ROOMS[room_code] = {
                "room_id": room_code,
                "host_name": data.get("host_name", "Arsh Rana"),
                "song": data.get("song"),
                "is_playing": data.get("is_playing", True),
                "position": data.get("position", 0.0),
                "updated_at": time.time()
            }
            self.send_json_response({"success": True, "room_id": room_code})
            return

        # 2. API: Jam Update from Host
        if pathname == "/api/jam/update":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                room_id = (data.get("room_id") or data.get("room") or "").strip().upper()
                if room_id:
                    if room_id not in JAM_ROOMS:
                        JAM_ROOMS[room_id] = {
                            "room_id": room_id,
                            "host_name": data.get("host_name", "Arsh Rana"),
                            "song": data.get("song"),
                            "is_playing": data.get("is_playing", True),
                            "position": data.get("position", 0.0),
                            "updated_at": time.time()
                        }
                    else:
                        JAM_ROOMS[room_id].update({
                            "song": data.get("song", JAM_ROOMS[room_id].get("song")),
                            "is_playing": data.get("is_playing", JAM_ROOMS[room_id].get("is_playing")),
                            "position": data.get("position", JAM_ROOMS[room_id].get("position")),
                            "updated_at": time.time()
                        })
                self.send_json_response({"success": True})
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)
            return

        # 3. Clear cache
        if pathname == "/api/clear-cache":
            for f in os.listdir(TEMP_CACHE_DIR):
                if f.endswith('.mp3'):
                    try:
                        os.remove(os.path.join(TEMP_CACHE_DIR, f))
                    except OSError:
                        pass
            self.send_json_response({"success": True, "message": "Temporary cache cleared"})
            return

        self.send_error(404, "Not Found")

    def background_cache_file(self, direct_url: str, source: str, target_file: str):
        """Asynchronously cache audio stream without delaying client playback."""
        if os.path.exists(target_file) and os.path.getsize(target_file) > 50000:
            return
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'
            }
            if source == "djpunjab":
                headers['Referer'] = 'https://djpunjab.is/'
            elif source == "djjohal":
                headers['Referer'] = 'https://www.djjohal.com/'
            elif source == "mrjatt":
                headers['Referer'] = 'https://www.mr-jatt.im/'

            r = requests.get(direct_url, headers=headers, stream=True, timeout=15)
            if r.status_code == 200:
                temp_file = f"{target_file}.tmp"
                with open(temp_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(target_file):
                    os.remove(target_file)
                os.rename(temp_file, target_file)
        except Exception:
            pass

    def stream_audio_file(self, file_path: str):
        file_size = os.path.getsize(file_path)
        range_header = self.headers.get("Range")

        if range_header:
            range_match = range_header.strip().lower()
            if range_match.startswith("bytes="):
                parts = range_match[6:].split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
                end = min(end, file_size - 1)
                content_length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(content_length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    bytes_remaining = content_length
                    while bytes_remaining > 0:
                        chunk_size = min(bytes_remaining, 65536)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        self.wfile.write(data)
                        bytes_remaining -= len(data)
                return

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                self.wfile.write(data)

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MusicDuniyaHandler)
    print(f"[*] Music Server running on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    run()
