import os
import sys
import json
import time
import base64
import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(BASE_DIR)

from cache_manager import SUPABASE_URL, SUPABASE_KEY, BUCKET_NAME

DES_KEY = b"38346591"

def decrypt_saavn_url(enc_url: str) -> str:
    if not enc_url:
        return ""
    try:
        k24 = DES_KEY * 3
        cipher = Cipher(TripleDES(k24), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(base64.b64decode(enc_url.strip())) + decryptor.finalize()
        unpadder = padding.PKCS7(64).unpadder()
        data = unpadder.update(padded) + unpadder.finalize()
        raw_url = data.decode('utf-8')
        # Try 320k quality
        url320 = raw_url.replace('_96.mp4', '_320.mp4').replace('_160.mp4', '_320.mp4')
        return url320
    except Exception as e:
        return ""

def search_saavn(query: str):
    url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=5&p=1&q={requests.utils.quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data.get('results', [])
    except Exception as e:
        pass
    return []

def clean_title(title: str) -> str:
    # remove (From "...", feat, etc for search)
    t = re.sub(r'\(From [^\)]+\)', '', title)
    t = re.sub(r'\(Duet Version\)', '', t)
    t = re.sub(r'\(feat[^\)]+\)', '', t)
    t = re.sub(r'- From [^\-]+', '', t)
    t = re.sub(r'- Lofi Mix', '', t)
    t = re.sub(r'- Coke Studio [^\-]+', '', t)
    t = re.sub(r'- Acoustic', '', t)
    t = re.sub(r'- Unplugged', '', t)
    return t.strip()

import re

# Load imported playlists
playlist_import_path = os.path.join(BASE_DIR, 'playlist_import.json')
if not os.path.exists(playlist_import_path):
    print("Error: playlist_import.json not found")
    sys.exit(1)

with open(playlist_import_path, 'r', encoding='utf-8') as f:
    imported_playlists = json.load(f)

# Load existing songs to check if already present
songs_json_path = os.path.join(BASE_DIR, 'songs.json')
existing_songs = []
if os.path.exists(songs_json_path):
    with open(songs_json_path, 'r', encoding='utf-8') as f:
        existing_songs = json.load(f)

existing_map = {}
for s in existing_songs:
    k = s.get('title', '').strip().lower()
    existing_map[k] = s

resolved_playlists = {}
all_new_songs = []

print("=== STARTING RESOLUTION FOR ALL PLAYLISTS ===")

for p_name, p_data in imported_playlists.items():
    print(f"\n---> Processing Playlist: {p_name} ({len(p_data['tracks'])} songs)")
    resolved_tracks = []

    for t in p_data['tracks']:
        orig_title = t['title']
        orig_artist = t['artist']
        primary_artist = orig_artist.split(',')[0].strip()
        cleaned_t = clean_title(orig_title)
        
        # 1. Check if already present in app
        matched_song = None
        for k in (orig_title.lower(), cleaned_t.lower()):
            if k in existing_map:
                matched_song = existing_map[k]
                break

        if matched_song and matched_song.get('audio_url'):
            print(f"  [✓ LOCAL HIT] {orig_title} -> {matched_song['id']}")
            resolved_tracks.append(matched_song)
            continue

        # 2. Search Saavn
        search_q = f"{cleaned_t} {primary_artist}"
        saavn_hits = search_saavn(search_q)
        if not saavn_hits:
            saavn_hits = search_saavn(cleaned_t)

        resolved_track = None
        if saavn_hits:
            for hit in saavn_hits:
                enc_url = hit.get('more_info', {}).get('encrypted_media_url')
                stream_url = decrypt_saavn_url(enc_url)
                if stream_url:
                    dur_sec = int(hit.get('more_info', {}).get('duration', 0) or 200)
                    m = dur_sec // 60
                    s = dur_sec % 60
                    duration_str = f"{m}:{s:02d}"
                    img = hit.get('image', '').replace('150x150', '500x500')

                    resolved_track = {
                        'id': f"sp_{hit.get('id', str(int(time.time()*1000)))}",
                        'title': hit.get('title', orig_title).replace('&quot;', '"').replace('&amp;', '&'),
                        'artist': hit.get('subtitle', orig_artist).replace('&amp;', '&'),
                        'album': hit.get('more_info', {}).get('album', p_name).replace('&amp;', '&'),
                        'cover_url': img or 'https://lq.djjohal.com/covers_webp/48718/1.webp',
                        'audio_url': stream_url,
                        'duration': duration_str,
                        'source': 'jiosaavn',
                        'playlist': p_name
                    }
                    break

        if resolved_track:
            print(f"  [✓ RESOLVED] {orig_title} by {primary_artist}")
            resolved_tracks.append(resolved_track)
            all_new_songs.append(resolved_track)
        else:
            print(f"  [?] Fallback stream for: {orig_title} by {orig_artist}")
            # Add with high quality preview or placeholder
            dummy_id = f"sp_miss_{abs(hash(orig_title)) % 100000}"
            dummy_track = {
                'id': dummy_id,
                'title': orig_title,
                'artist': orig_artist,
                'album': p_name,
                'cover_url': 'https://lq.djjohal.com/covers_webp/48718/1.webp',
                'audio_url': f"http://localhost:3000/api/stream-or-download?song_id={dummy_id}&title={requests.utils.quote(orig_title)}&artist={requests.utils.quote(orig_artist)}",
                'duration': "3:20",
                'source': 'music_scraped',
                'playlist': p_name
            }
            resolved_tracks.append(dummy_track)
            all_new_songs.append(dummy_track)

    resolved_playlists[p_name] = {
        'id': p_data['id'],
        'name': p_name,
        'song_count': len(resolved_tracks),
        'cover_url': resolved_tracks[0]['cover_url'] if resolved_tracks else 'https://lq.djjohal.com/covers_webp/48718/1.webp',
        'tracks': resolved_tracks
    }

# Save resolved playlists
with open(os.path.join(BASE_DIR, 'playlists_resolved.json'), 'w', encoding='utf-8') as f:
    json.dump(resolved_playlists, f, indent=2, ensure_ascii=False)

# Merge all new songs into songs.json (avoiding duplicate IDs)
seen_ids = set()
merged_songs = []
for s in existing_songs + all_new_songs:
    if s['id'] not in seen_ids:
        seen_ids.add(s['id'])
        merged_songs.append(s)

with open(songs_json_path, 'w', encoding='utf-8') as f:
    json.dump(merged_songs, f, indent=2, ensure_ascii=False)

print(f"\n==========================================")
print(f"Total songs in app songs.json: {len(merged_songs)} (added {len(all_new_songs)} from playlists)")
print(f"Playlists created: {list(resolved_playlists.keys())}")
print(f"==========================================")
