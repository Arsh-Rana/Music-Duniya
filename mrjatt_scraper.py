#!/usr/bin/env python3
"""
Mr-Jatt Song Scraper
Scrapes songs, albums, and download links from https://www.mr-jatt.im/punjabi-music/
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import requests

BASE_URL = "https://www.mr-jatt.im"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.mr-jatt.im/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_html(url: str, retries: int = 3, timeout: int = 15) -> str:
    """Fetch HTML content with retry logic."""
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 404:
                return ""
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"[!] Failed to fetch {url}: {e}", file=sys.stderr)
            time.sleep(1)
    return ""


def clean_text(text: str) -> str:
    """Strip HTML tags and clean up whitespace."""
    clean = re.sub(r'<[^>]+>', '', text)
    return ' '.join(clean.split()).strip()


def parse_song_page(song_url: str, default_title: str = "", default_artist: str = "") -> dict:
    """Parse a single song/album detail page to extract 320k, 128k, 48k download links."""
    html = fetch_html(song_url)
    if not html:
        return {}

    # Extract ID from URL
    id_m = re.search(r'/(?:song|album)/(\d+)/', song_url)
    song_id = id_m.group(1) if id_m else ""

    # Title & Artist
    title = default_title
    artist = default_artist
    h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if h1_m and not title:
        raw_h1 = clean_text(h1_m.group(1))
        # Often "Song Name (Artist Name) Mp3 Song Download"
        raw_h1 = re.sub(r'(?i)\s*(?:mp3|song|download|latest).*$', '', raw_h1).strip()
        parts = re.split(r'\((.*?)\)', raw_h1)
        if len(parts) >= 2:
            title = parts[0].strip()
            artist = parts[1].strip()
        else:
            title = raw_h1

    # Cover Image
    cover_m = re.search(r'<img[^>]+src=["\']([^"\']*(?:thumb|cover)[^"\']*)["\']', html)
    cover_url = urljoin(BASE_URL, cover_m.group(1)) if cover_m else ""

    # Download Links (48k, 128k, 320k)
    downloads = {"320k": "", "128k": "", "48k": "", "size_320k": "", "size_128k": "", "size_48k": ""}
    dl_links = re.findall(r'<a[^>]+href=["\']([^"\']*\.mp3[^"\']*)["\'][^>]*>(.*?)</a>', html, re.S)
    for href, label in dl_links:
        full_href = urljoin(BASE_URL, href)
        clean_label = clean_text(label)
        # Size inside [ ... ]
        size_m = re.search(r'\[(.*?)\]', clean_label)
        size_str = size_m.group(1) if size_m else ""

        if "320" in clean_label or "/320/" in full_href:
            downloads["320k"] = full_href
            downloads["size_320k"] = size_str
        elif "128" in clean_label or "/128/" in full_href:
            downloads["128k"] = full_href
            downloads["size_128k"] = size_str
        elif "48" in clean_label or "/48/" in full_href:
            downloads["48k"] = full_href
            downloads["size_48k"] = size_str

    return {
        "id": song_id,
        "title": title or "Unknown",
        "artist": artist or "Unknown",
        "cover_url": cover_url,
        "page_url": song_url,
        "download_320k": downloads["320k"],
        "size_320k": downloads["size_320k"],
        "download_128k": downloads["128k"],
        "size_128k": downloads["size_128k"],
        "download_48k": downloads["48k"],
        "size_48k": downloads["size_48k"],
    }


def parse_album_page(album_url: str, default_title: str = "", default_artist: str = "") -> list[dict]:
    """Parse an album page: if it has multi-track songs, return each song, else parse as single."""
    html = fetch_html(album_url)
    if not html:
        return []

    # Check if there are individual song links
    song_links = re.findall(r'<a[^>]+href=["\'](/punjabi-music/song/\d+/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.S)
    if song_links:
        songs = []
        for href, label in song_links:
            clean_l = clean_text(label)
            # Remove leading bullet
            clean_l = re.sub(r'^[»\s\d\.]+', '', clean_l).strip()
            # Split title and artist if "(Artist)"
            s_title = clean_l
            s_artist = default_artist
            m = re.search(r'^(.*?)\s*\((.*?)\)', clean_l)
            if m:
                s_title = m.group(1).strip()
                s_artist = m.group(2).strip()

            song_data = parse_song_page(urljoin(BASE_URL, href), default_title=s_title, default_artist=s_artist)
            if song_data:
                songs.append(song_data)
        return songs
    else:
        # Single track album page
        s = parse_song_page(album_url, default_title=default_title, default_artist=default_artist)
        return [s] if s else []


def scrape_top20(timeframe: str = "24hours", category: str = "Single-Track") -> list[dict]:
    """Scrape top 20 songs from mr-jatt."""
    url = f"{BASE_URL}/top20-{category}-songs-{timeframe}.html"
    print(f"[*] Scraping Top 20 Songs ({category} - {timeframe}): {url}")
    html = fetch_html(url)
    if not html:
        return []

    links = re.findall(r'<a[^>]+href=["\'](/punjabi-music/(?:song|album)/\d+/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.S)
    songs = []
    print(f"[*] Found {len(links)} top songs. Fetching download links...")
    for href, label in links:
        clean_l = clean_text(label)
        clean_l = re.sub(r'^[»\s\d\.]+', '', clean_l).strip()
        s_title = clean_l
        s_artist = ""
        m = re.search(r'^(.*?)\s*\((.*?)\)', clean_l)
        if m:
            s_title = m.group(1).strip()
            s_artist = m.group(2).strip()

        full_url = urljoin(BASE_URL, href)
        if "/song/" in href:
            data = parse_song_page(full_url, default_title=s_title, default_artist=s_artist)
            if data:
                songs.append(data)
        else:
            alb_songs = parse_album_page(full_url, default_title=s_title, default_artist=s_artist)
            songs.extend(alb_songs)

    return songs


def scrape_category(category_name: str = "Single-Track", max_pages: int = 1) -> list[dict]:
    """Scrape songs/albums from a category up to max_pages."""
    print(f"[*] Scraping Category: {category_name} (Up to {max_pages} pages)...")
    all_songs = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/punjabi-music/cat/a/{page}/{category_name}.html"
        print(f"  [-] Fetching page {page}: {url}")
        html = fetch_html(url)
        if not html:
            break

        album_links = re.findall(r'<a[^>]+href=["\'](/punjabi-music/album/\d+/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.S)
        if not album_links:
            break

        print(f"    Found {len(album_links)} releases on page {page}. Extracting download links...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_album = {}
            for href, label in album_links:
                clean_l = clean_text(label)
                clean_l = re.sub(r'^[»\s\d\.]+', '', clean_l).strip()
                s_title = clean_l
                s_artist = ""
                m = re.search(r'^(.*?)\s*\((.*?)\)', clean_l)
                if m:
                    s_title = m.group(1).strip()
                    s_artist = m.group(2).strip()

                full_url = urljoin(BASE_URL, href)
                future_to_album[executor.submit(parse_album_page, full_url, s_title, s_artist)] = full_url

            for future in as_completed(future_to_album):
                try:
                    res = future.result()
                    for s in res:
                        if s.get("id") and s["id"] not in seen_ids:
                            seen_ids.add(s["id"])
                            all_songs.append(s)
                except Exception as e:
                    print(f"[!] Error parsing album: {e}", file=sys.stderr)

        if f"/punjabi-music/cat/a/{page + 1}/" not in html:
            break

        time.sleep(0.5)

    return all_songs


def download_mp3(song: dict, dest_dir: str = "downloads_mrjatt", quality: str = "128") -> str:
    """Download an MP3 file to disk."""
    os.makedirs(dest_dir, exist_ok=True)
    clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{song['artist']} - {song['title']}").strip()
    filename = f"{clean_title} ({quality}k).mp3"
    filepath = os.path.join(dest_dir, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
        return filepath

    url = song.get(f"download_{quality}k") or song.get("download_128k") or song.get("download_320k") or song.get("download_48k")
    if not url:
        return ""

    try:
        r = SESSION.get(url, stream=True, timeout=25)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return filepath
    except Exception as e:
        print(f"[!] Error downloading {filename}: {e}", file=sys.stderr)

    return ""


def save_results(songs: list[dict], base_name: str = "mrjatt_songs"):
    """Save scraped songs to CSV and JSON files."""
    json_path = f"{base_name}.json"
    csv_path = f"{base_name}.csv"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)

    # Save CSV
    if songs:
        keys = list(songs[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(songs)

    print(f"\n[+] Saved {len(songs)} songs to:")
    print(f"    - JSON: {os.path.abspath(json_path)}")
    print(f"    - CSV:  {os.path.abspath(csv_path)}")


def main():
    parser = argparse.ArgumentParser(description="Mr-Jatt Song Scraper")
    parser.add_argument("--mode", choices=["top20", "category", "album", "all"], default="top20",
                        help="Mode: top20, category, album, all (default: top20)")
    parser.add_argument("--cat", default="Single-Track",
                        help="Category name (e.g. Single-Track, Punjabi, Haryanvi, Hindi, Sad-Songs)")
    parser.add_argument("--timeframe", choices=["24hours", "7days", "30days"], default="24hours",
                        help="Top 20 timeframe (default: 24hours)")
    parser.add_argument("--pages", type=int, default=1, help="Max pages to scrape per category (default: 1)")
    parser.add_argument("--album-url", default="", help="Specific album/song URL to scrape")
    parser.add_argument("--download", action="store_true", help="Download MP3 files to downloads_mrjatt/ folder")
    parser.add_argument("--quality", choices=["320", "128", "48"], default="128", help="Audio quality (default: 128)")
    parser.add_argument("--out", default="mrjatt_songs", help="Base output filename for .json and .csv")
    parser.add_argument("--threads", type=int, default=5, help="Concurrent download threads (default: 5)")
    args = parser.parse_args()

    songs = []
    if args.mode == "top20":
        songs = scrape_top20(timeframe=args.timeframe, category=args.cat)
    elif args.mode == "category":
        songs = scrape_category(category_name=args.cat, max_pages=args.pages)
    elif args.mode == "album":
        if not args.album_url:
            print("[!] Please provide --album-url", file=sys.stderr)
            return
        songs = parse_album_page(args.album_url)
    elif args.mode == "all":
        categories = ["Single-Track", "Punjabi", "Haryanvi", "Hindi", "Sad-Songs"]
        for cat in categories:
            cat_songs = scrape_category(category_name=cat, max_pages=args.pages)
            songs.extend(cat_songs)
        # Deduplicate
        seen = set()
        dedup = []
        for s in songs:
            if s["id"] not in seen:
                seen.add(s["id"])
                dedup.append(s)
        songs = dedup

    print(f"\n[*] Total unique songs found: {len(songs)}")

    # Save metadata
    save_results(songs, base_name=args.out)

    # Download MP3s if requested
    if args.download:
        print(f"\n[*] Downloading {len(songs)} songs ({args.quality}kbps) using {args.threads} threads...")
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(download_mp3, s, "downloads_mrjatt", args.quality) for s in songs]
            for i, future in enumerate(as_completed(futures), start=1):
                p = future.result()
                if p:
                    print(f"  [{i}/{len(songs)}] Downloaded: {os.path.basename(p)}")
        print("[+] All downloads complete! Check the downloads_mrjatt/ folder.")


if __name__ == "__main__":
    main()
