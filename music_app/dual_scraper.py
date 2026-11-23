"""
Dual Scraper and On-Demand Audio Streamer for DJJohal.com and Mr-Jatt.im
"""

import os
import re
import time
import json
import requests
from urllib.parse import quote, urljoin
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DOWNLOADS_DIR = os.path.join(ROOT_DIR, 'downloads')
TEMP_CACHE_DIR = os.path.join(BASE_DIR, 'temp_cache')

os.makedirs(TEMP_CACHE_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# =====================================================================
# RESOLVERS
# =====================================================================
def resolve_djjohal_audio(page_url: str) -> str:
    """Resolve direct audio streaming URL from DJJohal song page."""
    if not page_url:
        return ''
    try:
        r = SESSION.get(page_url, timeout=8)
        if r.status_code == 200:
            html = r.text
            # Look for 128k or 320k direct mp3 links
            mp3_links = re.findall(r'href=["\'](https?://[^"\']+\.mp3[^"\']*)["\']', html)
            for l in mp3_links:
                if '/128/' in l:
                    return l
            for l in mp3_links:
                if '/320/' in l:
                    return l
            if mp3_links:
                return mp3_links[0]

            # Look for data-audio in button
            data_audio = re.findall(r'data-audio=["\'](https?://[^"\']+\.mp3)["\']', html)
            if data_audio:
                return data_audio[0]
    except Exception as e:
        print(f"[!] Error resolving DJJohal audio: {e}")
    return ''


def resolve_mrjatt_audio(page_url: str) -> str:
    """Resolve direct audio streaming URL from Mr-Jatt song/album page."""
    if not page_url:
        return ''
    try:
        headers = {**HEADERS, 'Referer': 'https://www.mr-jatt.im/'}
        r = SESSION.get(page_url, headers=headers, timeout=8)
        if r.status_code == 200:
            html = r.text
            # 1. cdnsongs direct download link
            cdnsongs_links = re.findall(r'href=["\'](https?://cdnsongs\.com/[^"\']+\.mp3[^"\']*)["\']', html)
            for link in cdnsongs_links:
                if '/128/' in link:
                    return link
            for link in cdnsongs_links:
                if '/320/' in link:
                    return link
            if cdnsongs_links:
                return cdnsongs_links[0]

            # 2. Look for <source src="...mp3"> in <audio> tag
            audio_src = re.search(r'<source[^>]*src=["\']([^"\']+\.mp3)["\']', html)
            if audio_src:
                return audio_src.group(1)

            # 3. If it is an album page listing songs, fetch the first song page
            song_hrefs = re.findall(r'<a[^>]*href=["\'](/punjabi-music/song/[^"\']+)["\']', html)
            if song_hrefs:
                first_song_url = urljoin('https://www.mr-jatt.im', song_hrefs[0])
                return resolve_mrjatt_audio(first_song_url)
    except Exception as e:
        print(f"[!] Error resolving Mr-Jatt audio: {e}")
    return ''

resolve_djjohal_direct_url = resolve_djjohal_audio
resolve_mrjatt_direct_url = resolve_mrjatt_audio


# =====================================================================
# DJJOHAL SEARCH
# =====================================================================
def search_djjohal(query: str, limit: int = 15) -> list[dict]:
    """Search djjohal.com for songs matching query."""
    results = []
    url = f"https://www.djjohal.com/search.php?q={quote(query)}"
    try:
        resp = SESSION.get(url, timeout=8)
        if resp.status_code != 200:
            return results

        html = resp.text

        # 1. Check direct play-song buttons
        buttons = re.findall(r'<button[^>]*class=["\'][^"\']*play-song[^"\']*["\'][^>]*>', html)
        for b in buttons:
            tid = re.search(r'data-tid=["\']([^"\']*)["\']', b)
            title = re.search(r'data-title=["\']([^"\']*)["\']', b)
            artist = re.search(r'data-artist=["\']([^"\']*)["\']', b)
            audio = re.search(r'data-audio=["\']([^"\']*)["\']', b)
            cover = re.search(r'data-cover=["\']([^"\']*)["\']', b)
            page = re.search(r'data-url=["\']([^"\']*)["\']', b)

            if tid and title:
                tid_val = tid.group(1).strip()
                results.append({
                    'id': f"djjohal_{tid_val}",
                    'raw_id': tid_val,
                    'source': 'djjohal',
                    'title': title.group(1).strip(),
                    'artist': artist.group(1).strip() if artist else 'Unknown',
                    'stream_url': audio.group(1).strip() if audio else f"https://sd2.djjohal.com/128/{tid_val}.mp3",
                    'cover_url': cover.group(1).strip() if cover else 'https://lq.djjohal.com/covers_webp/48718/1.webp',
                    'page_url': urljoin('https://www.djjohal.com', page.group(1)) if page else '',
                    'album': 'DJJohal Music'
                })

        # 2. Check glass-card search song links: /song/{slug}.html
        cards = re.findall(
            r'<a[^>]*class=["\'][^"\']*glass-card[^"\']*["\'][^>]*href=["\'](/song/[^"\']+)["\'][^>]*>.*?<img[^>]*src=["\']([^"\']+)["\'].*?<h3[^>]*>([^<]+)</h3>.*?<small[^>]*>([^<]+)</small>',
            html,
            re.DOTALL
        )

        for song_path, cover_path, raw_title, raw_artist in cards:
            clean_artist = re.sub(r'·.*$', '', raw_artist).strip()
            song_url = urljoin('https://www.djjohal.com', song_path)
            cover_full = urljoin('https://www.djjohal.com', cover_path)

            m_id = re.search(r'-(\d+)\.html$', song_path)
            song_id = m_id.group(1) if m_id else str(abs(hash(song_path)) % 1000000)

            if not any(r['title'].lower() == raw_title.strip().lower() for r in results):
                results.append({
                    'id': f"djjohal_{song_id}",
                    'raw_id': song_id,
                    'source': 'djjohal',
                    'title': raw_title.strip(),
                    'artist': clean_artist or 'DJJohal Artist',
                    'stream_url': '',  # Resolved on-demand
                    'cover_url': cover_full,
                    'page_url': song_url,
                    'album': 'DJJohal Single'
                })

        # 3. Fallback: check /song/ links
        if not results:
            song_links = re.findall(r'<a[^>]*href=["\'](/song/[^"\']+\.html)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
            for path, text in song_links[:limit]:
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                if clean_text and clean_text.lower() != 'song':
                    m_id = re.search(r'-(\d+)\.html$', path)
                    sid = m_id.group(1) if m_id else str(abs(hash(path)) % 1000000)
                    results.append({
                        'id': f"djjohal_{sid}",
                        'raw_id': sid,
                        'source': 'djjohal',
                        'title': clean_text,
                        'artist': 'DJJohal Punjabi',
                        'stream_url': '',
                        'cover_url': 'https://lq.djjohal.com/covers_webp/48718/1.webp',
                        'page_url': urljoin('https://www.djjohal.com', path),
                        'album': 'DJJohal'
                    })

    except Exception as e:
        print(f"[!] DJJohal search error for '{query}': {e}")

    return results[:limit]


# =====================================================================
# MR-JATT SEARCH
# =====================================================================
def search_mrjatt(query: str, limit: int = 15) -> list[dict]:
    """Search mr-jatt.im for songs matching query."""
    results = []
    q_norm = query.strip().replace(' ', '-').title()

    # 1. Try artist top songs direct URL: https://www.mr-jatt.im/{Artist}-top-songs.html
    artist_urls = [
        f"https://www.mr-jatt.im/{q_norm}-top-songs.html",
        f"https://www.mr-jatt.im/{query.strip().replace(' ', '-')}-top-songs.html"
    ]

    for a_url in artist_urls:
        try:
            r = SESSION.get(a_url, timeout=5)
            if r.status_code == 200:
                song_links = re.findall(r'<a[^>]*href=["\']([^"\']+/song/[^"\']+)["\'][^>]*>(.*?)</a>', r.text)
                for h, t in song_links:
                    t_clean = re.sub(r'<[^>]+>', '', t).replace('&raquo;', '').strip()
                    t_clean = re.sub(r'^\d+\.\s*', '', t_clean)
                    t_clean = re.sub(r'\s*\[R\]\s*$', '', t_clean)

                    m_art = re.search(r'\((.*?)\)', t_clean)
                    artist = m_art.group(1) if m_art else query.title()
                    title = re.sub(r'\(.*?\)', '', t_clean).strip()

                    full_url = urljoin('https://www.mr-jatt.im', h.split('?')[0])
                    sid = re.search(r'/song/(\d+)/', full_url)
                    song_id = sid.group(1) if sid else str(abs(hash(full_url)) % 1000000)

                    results.append({
                        'id': f"mrjatt_{song_id}",
                        'raw_id': song_id,
                        'source': 'mrjatt',
                        'title': title,
                        'artist': artist,
                        'page_url': full_url,
                        'cover_url': f"https://cover.mr-jatt.im/thumb/{song_id}/thumb.webp",
                        'album': 'Mr-Jatt Punjabi',
                        'stream_url': ''
                    })
                if results:
                    break
        except Exception:
            pass

    # 2. Browse Single Track catalog if few results
    if len(results) < 5:
        try:
            for page in range(1, 3):
                cat_url = f"https://www.mr-jatt.im/punjabi-music/cat/a/{page}/Single-Track.html"
                r = SESSION.get(cat_url, timeout=5)
                if r.status_code != 200:
                    break

                albums = re.findall(r'<a[^>]*href=["\'](/punjabi-music/album/[^"\']+)["\'][^>]*>(.*?)</a>', r.text)
                for alb_href, alb_text in albums:
                    text_clean = re.sub(r'<[^>]+>', '', alb_text).strip()
                    if query.lower() in text_clean.lower():
                        alb_full = urljoin('https://www.mr-jatt.im', alb_href)
                        sid = re.search(r'/album/(\d+)/', alb_href)
                        song_id = sid.group(1) if sid else str(abs(hash(alb_href)) % 1000000)

                        artist = 'Punjabi'
                        m_art = re.search(r'\[(.*?)\]', text_clean)
                        if m_art:
                            artist = m_art.group(1)
                            title = re.sub(r'\[.*?\]', '', text_clean).strip()
                        else:
                            title = text_clean

                        results.append({
                            'id': f"mrjatt_{song_id}",
                            'raw_id': song_id,
                            'source': 'mrjatt',
                            'title': title,
                            'artist': artist,
                            'page_url': alb_full,
                            'cover_url': f"https://cover.mr-jatt.im/thumb/{song_id}/thumb.webp",
                            'album': 'Mr-Jatt Single',
                            'stream_url': ''
                        })
        except Exception as e:
            print(f"[!] Mr-Jatt browse error: {e}")

    return results[:limit]


# =====================================================================
# UNIFIED MULTI-SOURCE SEARCH & CACHING
# =====================================================================
def search_all_sources(query: str) -> list[dict]:
    """Search both DJJohal and Mr-Jatt in parallel, returning merged results."""
    combined = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_dj = executor.submit(search_djjohal, query, 12)
        f_mj = executor.submit(search_mrjatt, query, 12)

        dj_results = f_dj.result()
        mj_results = f_mj.result()

    # Interleave results
    max_len = max(len(dj_results), len(mj_results))
    for i in range(max_len):
        if i < len(dj_results):
            combined.append(dj_results[i])
        if i < len(mj_results):
            combined.append(mj_results[i])

    return combined


def get_cached_or_download_song(song_id: str, source: str, stream_url: str = '', page_url: str = '') -> str:
    """
    Check if song is locally cached; if not, download into TEMP_CACHE_DIR.
    Returns the absolute path to the local mp3 file.
    """
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', song_id)
    cache_path = os.path.join(TEMP_CACHE_DIR, f"{clean_id}.mp3")

    # If already cached and valid size (> 50KB), return path
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 50000:
        return cache_path

    # Check downloads folder
    for fname in os.listdir(DOWNLOADS_DIR):
        if clean_id in fname:
            return os.path.join(DOWNLOADS_DIR, fname)

    # Resolve direct stream URL via page_url
    direct_url = ''
    if source == 'djjohal':
        if page_url:
            direct_url = resolve_djjohal_audio(page_url)
        if not direct_url and stream_url:
            direct_url = stream_url
    elif source == 'mrjatt':
        if page_url:
            direct_url = resolve_mrjatt_audio(page_url)
        if not direct_url and stream_url:
            direct_url = stream_url

    if not direct_url:
        raise ValueError(f"Could not resolve direct stream URL for {song_id} from {source}")

    # Download into temporary cache
    referer = 'https://www.djjohal.com/' if source == 'djjohal' else 'https://www.mr-jatt.im/'
    headers = {**HEADERS, 'Referer': referer}

    print(f"[*] Downloading {song_id} from {source} into temporary cache: {direct_url}")
    resp = requests.get(direct_url, headers=headers, stream=True, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to download audio from {direct_url}, status {resp.status_code}")

    temp_partial = f"{cache_path}.part"
    with open(temp_partial, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                f.write(chunk)

    if os.path.exists(cache_path):
        os.remove(cache_path)
    os.rename(temp_partial, cache_path)

    print(f"[+] Successfully cached {song_id} ({os.path.getsize(cache_path)} bytes) at {cache_path}")
    return cache_path


def cleanup_old_temp_cache(max_files: int = 50, max_age_seconds: int = 86400):
    """Prunes temporary cached songs older than max_age_seconds or beyond max_files."""
    try:
        now = time.time()
        files = []
        for f in os.listdir(TEMP_CACHE_DIR):
            if f.endswith('.mp3'):
                p = os.path.join(TEMP_CACHE_DIR, f)
                files.append((p, os.path.getmtime(p), os.path.getsize(p)))

        for p, mtime, size in files:
            if now - mtime > max_age_seconds:
                try:
                    os.remove(p)
                except OSError:
                    pass

        remaining = [f for f in os.listdir(TEMP_CACHE_DIR) if f.endswith('.mp3')]
        if len(remaining) > max_files:
            remaining_paths = [os.path.join(TEMP_CACHE_DIR, f) for f in remaining]
            remaining_paths.sort(key=lambda p: os.path.getmtime(p))
            for p in remaining_paths[:len(remaining_paths) - max_files]:
                try:
                    os.remove(p)
                except OSError:
                    pass
    except Exception as e:
        print(f"[!] Temp cache cleanup error: {e}")
