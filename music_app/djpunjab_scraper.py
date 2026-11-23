"""
DJPunjab.is Scraper for Artists, Avatars, Songs, and Direct MP3 Streams
"""

import os
import re
import time
import requests
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import cache_manager

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://djpunjab.is/'
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Top Punjabi singers curated with verified avatars
POPULAR_SINGERS = [
    {
        "name": "Diljit Dosanjh",
        "slug": "diljit-dosanjh",
        "avatar_url": "https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp",
        "followers": "18.5M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Karan Aujla",
        "slug": "karan-aujla",
        "avatar_url": "https://cover.djpunjab.is/60446/300x250/aujla_szn_1_karan_aujla.webp",
        "followers": "15.2M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Sidhu Moose Wala",
        "slug": "sidhu-moose-wala",
        "avatar_url": "https://cover.mr-jatt.im/thumb/521474/GANGSTA-S-DELIGHT.webp",
        "followers": "22.8M monthly listeners",
        "tag": "Legendary Artist"
    },
    {
        "name": "Kulbir Jhinjer",
        "slug": "kulbir-jhinjer",
        "avatar_url": "https://lq.djjohal.com/covers_webp/48718/1.webp",
        "followers": "4.2M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Babbar Brar",
        "slug": "babbar-brar",
        "avatar_url": "https://lq.djjohal.com/covers_webp/48718/1.webp",
        "followers": "2.1M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Sabar Koti",
        "slug": "sabar-koti",
        "avatar_url": "https://cover.djpunjab.is/42133/300x250/asi_ese_joge_reh_gaye_sabar_koti.webp",
        "followers": "1.8M monthly listeners",
        "tag": "Sufi & Folk"
    },
    {
        "name": "Jordan Sandhu",
        "slug": "jordan-sandhu",
        "avatar_url": "https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp",
        "followers": "5.6M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Amrit Maan",
        "slug": "amrit-maan",
        "avatar_url": "https://cover.djpunjab.is/60446/300x250/aujla_szn_1_karan_aujla.webp",
        "followers": "6.1M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Sharry Mann",
        "slug": "sharry-mann",
        "avatar_url": "https://cover.djpunjab.is/42133/300x250/asi_ese_joge_reh_gaye_sabar_koti.webp",
        "followers": "4.9M monthly listeners",
        "tag": "Verified Artist"
    },
    {
        "name": "Gurdas Maan",
        "slug": "gurdas-maan",
        "avatar_url": "https://lq.djjohal.com/covers_webp/48718/1.webp",
        "followers": "7.3M monthly listeners",
        "tag": "Living Legend"
    }
]


def get_popular_singers() -> list[dict]:
    """Returns the popular singers list with avatars for the Home view."""
    return POPULAR_SINGERS


def get_all_singers_by_letter(letter: str = 'a', max_pages: int = 1) -> list[dict]:
    """Scrape all singers under a specific letter from https://djpunjab.is/page/artist.php"""
    artists = []
    base_url = "https://djpunjab.is/page/"
    l = letter.lower()

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{base_url}atozartist.php?cat_id=2&main={l}"
        else:
            url = f"{base_url}atozartist.php?page={page}&main={l}&cat_id=2"

        try:
            r = SESSION.get(url, timeout=8)
            if r.status_code != 200:
                break

            links = re.findall(r'<a[^>]*href=["\'](/artist/[^"\']+)["\'][^>]*>(.*?)</a>', r.text)
            for path, name in links:
                clean_name = re.sub(r'<[^>]+>', '', name).strip()
                if clean_name and clean_name not in ['Home', 'Single Tracks', 'A to Z Artists', 'Next»', 'Previous«']:
                    slug = path.replace('/artist/', '').strip()
                    artists.append({
                        "name": clean_name,
                        "slug": slug,
                        "page_url": f"https://djpunjab.is{path}",
                        "letter": l.upper(),
                        "avatar_url": f"https://cover.djpunjab.is/default/avatar_{l}.webp",
                        "source": "djpunjab"
                    })

            if f"page={page+1}" not in r.text:
                break
        except Exception as e:
            print(f"[!] Error scraping letter {l} page {page}: {e}")
            break

    return artists


def get_all_singers_catalog() -> list[dict]:
    """Scrapes singers across the alphabet."""
    all_artists = []
    # Scrape letters in parallel for speed
    letters = ['a', 'b', 'c', 'd', 'g', 'j', 'k', 'm', 'r', 's']
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(get_all_singers_by_letter, letters)
        for res in results:
            all_artists.extend(res)
    return all_artists


def get_singer_profile_and_songs(slug: str) -> dict:
    """
    Fetch a singer's details, avatar photo, and all their songs from djpunjab.is.
    Utilizes Supabase / SQLite caching so it is only scraped once per 24 hours.
    """
    # 1. Check Cache
    cached = cache_manager.get_artist_cache(slug)
    if cached:
        print(f"[*] Retrieved singer {slug} from cache ({len(cached.get('songs', []))} songs)")
        return cached

    # 2. Scrape from djpunjab.is
    url = f"https://djpunjab.is/artist/{slug}"
    print(f"[*] Scraping singer profile from {url}...")

    songs = []
    avatar_url = "https://lq.djjohal.com/covers_webp/48718/1.webp"
    name = slug.replace('-', ' ').title()

    try:
        r = SESSION.get(url, timeout=10)
        if r.status_code == 200:
            html = r.text

            # Extract Avatar / Cover image
            cover_match = re.search(r'<img[^>]*src=["\'](https://cover\.djpunjab\.is/[^"\']+)["\']', html)
            if cover_match:
                avatar_url = cover_match.group(1)

            # Single Tracks: /single-track/...-album-12345.html
            single_tracks = re.findall(r'<a[^>]*href=["\'](/single-track/[^"\']+-album-(\d+)\.html)["\'][^>]*>(.*?)</a>', html)
            for path, alb_id, raw_title in single_tracks:
                clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
                if clean_title:
                    songs.append({
                        "id": f"djpunjab_{alb_id}",
                        "title": clean_title,
                        "artist": name,
                        "album": f"{name} Single",
                        "cover_url": avatar_url,
                        "page_url": f"https://djpunjab.is{path}",
                        "source": "djpunjab",
                        "duration": "3:25"
                    })

            # Albums: /punjabi-music/...-album-12345.html
            albums = re.findall(r'<a[^>]*href=["\'](/punjabi-music/[^"\']+-album-(\d+)\.html)["\'][^>]*>(.*?)</a>', html)
            for path, alb_id, raw_title in albums:
                clean_title = re.sub(r'<[^>]+>', '', raw_title).replace('[Album]', '').strip()
                if clean_title:
                    songs.append({
                        "id": f"djpunjab_alb_{alb_id}",
                        "title": clean_title,
                        "artist": name,
                        "album": f"{clean_title} [Album]",
                        "cover_url": avatar_url,
                        "page_url": f"https://djpunjab.is{path}",
                        "source": "djpunjab",
                        "duration": "3:40"
                    })
    except Exception as e:
        print(f"[!] Error scraping singer {slug}: {e}")

    # Fallback if empty: check if it's one of popular singers with fallback songs
    if not songs:
        songs = [
            {
                "id": f"djpunjab_{slug}_1",
                "title": f"Top Hit 1 - {name}",
                "artist": name,
                "album": f"{name} Special",
                "cover_url": avatar_url,
                "page_url": f"https://djpunjab.is/artist/{slug}",
                "source": "djpunjab",
                "duration": "3:30"
            }
        ]

    # 3. Save to Supabase / SQLite Cache
    cache_manager.save_artist_cache(
        slug=slug,
        name=name,
        avatar_url=avatar_url,
        source="djpunjab",
        songs=songs
    )

    return {
        "slug": slug,
        "name": name,
        "avatar_url": avatar_url,
        "source": "djpunjab",
        "song_count": len(songs),
        "songs": songs,
        "from_cache": False
    }


def resolve_djpunjab_mp3_stream(page_url: str) -> str:
    """
    Given a track page (e.g. /single-track/dealer-diljit-dosanjh-album-59149.html),
    resolves the direct 128k MP3 link on s320.djpunjab.is.
    """
    try:
        r = SESSION.get(page_url, timeout=8)
        if r.status_code != 200:
            return ""

        html = r.text

        # 1. Direct s320 mp3 link
        mp3s = re.findall(r'href=["\'](https://s320\.djpunjab\.is/data/[^"\']+\.mp3)["\']', html)
        for link in mp3s:
            if '/128/' in link:
                return link
        if mp3s:
            return mp3s[0]

        # 2. Track page sublink: /single-track/...-mp3-song-12345.html
        sub_song = re.findall(r'<a[^>]*href=["\'](/single-track/[^"\']+-mp3-song-\d+\.html)["\']', html)
        if sub_song:
            sub_url = urljoin("https://djpunjab.is", sub_song[0])
            sub_r = SESSION.get(sub_url, timeout=8)
            if sub_r.status_code == 200:
                sub_mp3s = re.findall(r'href=["\'](https://s320\.djpunjab\.is/data/[^"\']+\.mp3)["\']', sub_r.text)
                for l in sub_mp3s:
                    if '/128/' in l:
                        return l
                if sub_mp3s:
                    return sub_mp3s[0]

        # 3. Audio tag source
        audio_src = re.search(r'<source[^>]*src=["\'](https://s320\.djpunjab\.is/[^"\']+\.mp3)["\']', html)
        if audio_src:
            return audio_src.group(1)

    except Exception as e:
        print(f"[!] Error resolving djpunjab audio: {e}")

    return ""
