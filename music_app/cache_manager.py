"""
Cache Manager supporting Supabase Storage / REST and embedded SQLite fallback.
Caches artists, songs metadata, and audio stream links for temporary storage.
"""

import os
import json
import time
import sqlite3
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, 'cache.db')

# Load Supabase credentials from .env if present
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://sosycnpbyrllrnnzapmn.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_fazLLChwcEY4CclhVccMIg_H6ejZt4i")
BUCKET_NAME = "music_cache"

env_file = os.path.join(ROOT_DIR, '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('SUPABASE_URL='):
                SUPABASE_URL = line.split('=', 1)[1].strip()
            elif line.startswith('SUPABASE_SERVICE_ROLE_KEY='):
                SUPABASE_KEY = line.split('=', 1)[1].strip()
            elif line.startswith('SUPABASE_ANON_KEY=') and not SUPABASE_ANON:
                SUPABASE_ANON = line.split('=', 1)[1].strip()


def init_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cached_artists (
            slug TEXT PRIMARY KEY,
            name TEXT,
            avatar_url TEXT,
            source TEXT,
            song_count INTEGER,
            songs_json TEXT,
            updated_at INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cached_songs (
            id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            album TEXT,
            cover_url TEXT,
            stream_url TEXT,
            page_url TEXT,
            source TEXT,
            duration TEXT,
            updated_at INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_sqlite()


def save_artist_cache(slug: str, name: str, avatar_url: str, source: str, songs: list):
    """Save artist and their songs into cache (Supabase Storage + SQLite)."""
    now = int(time.time())
    data = {
        'slug': slug,
        'name': name,
        'avatar_url': avatar_url,
        'source': source,
        'song_count': len(songs),
        'songs': songs,
        'updated_at': now
    }

    # 1. Save to Supabase Storage (Cloud)
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/artists/{slug}.json"
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'x-upsert': 'true'
            }
            requests.post(url, headers=headers, json=data, timeout=3)
        except Exception as e:
            pass

    # 2. SQLite local cache (always keeps a fast local copy)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO cached_artists 
            (slug, name, avatar_url, source, song_count, songs_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (slug, name, avatar_url, source, len(songs), json.dumps(songs), now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] SQLite save artist error: {e}")


def get_artist_cache(slug: str, max_age_seconds: int = 86400) -> dict:
    """Retrieve artist and songs from cache if fresh (within max_age_seconds)."""
    now = int(time.time())

    # 1. Try SQLite first (fastest local hit)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT name, avatar_url, source, song_count, songs_json, updated_at FROM cached_artists WHERE slug = ?', (slug,))
        row = cur.fetchone()
        conn.close()

        if row:
            name, avatar_url, source, song_count, songs_json, updated_at = row
            if now - updated_at < max_age_seconds:
                return {
                    'slug': slug,
                    'name': name,
                    'avatar_url': avatar_url,
                    'source': source,
                    'song_count': song_count,
                    'songs': json.loads(songs_json),
                    'from_cache': True
                }
    except Exception as e:
        print(f"[!] SQLite get artist error: {e}")

    # 2. Try Supabase Storage (Cloud cache)
    if SUPABASE_URL:
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{BUCKET_NAME}/artists/{slug}.json"
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                item = res.json()
                if item and 'songs' in item:
                    item['from_cache'] = True
                    # Sync down to local SQLite
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute('''
                            INSERT OR REPLACE INTO cached_artists 
                            (slug, name, avatar_url, source, song_count, songs_json, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (slug, item.get('name'), item.get('avatar_url'), item.get('source'), item.get('song_count', len(item['songs'])), json.dumps(item['songs']), item.get('updated_at', now)))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                    return item
        except Exception:
            pass

    return None


def get_all_cached_artists(limit: int = 50) -> list:
    """Return all cached artists for browsing."""
    artists = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT slug, name, avatar_url, source, song_count FROM cached_artists ORDER BY updated_at DESC LIMIT ?', (limit,))
        for r in cur.fetchall():
            artists.append({
                'slug': r[0],
                'name': r[1],
                'avatar_url': r[2],
                'source': r[3],
                'song_count': r[4]
            })
        conn.close()
    except Exception as e:
        print(f"[!] SQLite get all artists error: {e}")
    return artists
