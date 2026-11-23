#!/usr/bin/env python3
"""
DJJohal Song Scraper
Scrapes songs, albums, and download links from https://www.djjohal.com/
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

BASE_URL = "https://www.djjohal.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.djjohal.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_html(url: str, retries: int = 3, timeout: int = 15) -> str:
    """Fetch HTML content from a URL with retry logic."""
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


def parse_song_buttons(html: str) -> list[dict]:
    """Extract songs from HTML containing .play-song button elements."""
    songs = []
    # Pattern to match the play-song button and its data attributes
    buttons = re.findall(r'<button[^>]*class=["\'][^"\']*play-song[^"\']*["\'][^>]*>', html)
    for b in buttons:
        tid_m = re.search(r'data-tid=["\']([^"\']*)["\']', b)
        title_m = re.search(r'data-title=["\']([^"\']*)["\']', b)
        artist_m = re.search(r'data-artist=["\']([^"\']*)["\']', b)
        audio_m = re.search(r'data-audio=["\']([^"\']*)["\']', b)
        category_m = re.search(r'data-category=["\']([^"\']*)["\']', b)
        cover_m = re.search(r'data-cover=["\']([^"\']*)["\']', b)
        url_m = re.search(r'data-url=["\']([^"\']*)["\']', b)

        tid = tid_m.group(1).strip() if tid_m else ""
        if not tid:
            continue

        detail_url = urljoin(BASE_URL, url_m.group(1).strip()) if url_m else ""
        songs.append({
            "id": tid,
            "title": title_m.group(1).strip() if title_m else "Unknown",
            "artist": artist_m.group(1).strip() if artist_m else "Unknown",
            "category": category_m.group(1).strip() if category_m else "",
            "stream_128k": audio_m.group(1).strip() if audio_m else f"https://sd2.djjohal.com/128/{tid}.mp3",
            "cover_url": cover_m.group(1).strip() if cover_m else "",
            "page_url": detail_url,
            "download_320k": "",
            "download_128k": "",
            "download_48k": ""
        })
    return songs


def get_detail_downloads(song: dict) -> dict:
    """Fetch high quality (320k, 128k, 48k) download links from the song's page."""
    page_url = song.get("page_url")
    if not page_url:
        return song

    html = fetch_html(page_url)
    if not html:
        return song

    # Find .mp3 download links
    links = re.findall(r'href=["\']([^"\']*\.mp3[^"\']*)["\']', html)
    for l in links:
        full_l = urljoin(BASE_URL, l)
        if "/320/" in full_l:
            song["download_320k"] = full_l
        elif "/128/" in full_l:
            song["download_128k"] = full_l
        elif "/48/" in full_l:
            song["download_48k"] = full_l

    # Fallback to direct stream url if download_128k wasn't in page
    if not song["download_128k"]:
        song["download_128k"] = song["stream_128k"]

    return song


def scrape_album_tracks(album_url: str) -> list[dict]:
    """Scrape all tracks inside an album page."""
    html = fetch_html(album_url)
    if not html:
        return []
    return parse_song_buttons(html)


def scrape_section(section_name: str, max_pages: int = 1) -> list[dict]:
    """Scrape a specific section (trending, recently, or a category)."""
    all_songs = []
    seen_ids = set()

    if section_name == "trending":
        print("[*] Scraping Trending Songs...")
        html = fetch_html(f"{BASE_URL}/trending.html")
        songs = parse_song_buttons(html)
        for s in songs:
            if s["id"] not in seen_ids:
                seen_ids.add(s["id"])
                all_songs.append(s)

    elif section_name == "recently":
        print("[*] Scraping Recently Added Songs...")
        html = fetch_html(f"{BASE_URL}/recently.html")
        songs = parse_song_buttons(html)
        for s in songs:
            if s["id"] not in seen_ids:
                seen_ids.add(s["id"])
                all_songs.append(s)

    else:
        # Category scraping (e.g. single-track, punjabi, haryanvi)
        print(f"[*] Scraping Category: {section_name} (Up to {max_pages} pages)...")
        for page in range(1, max_pages + 1):
            if page == 1:
                page_url = f"{BASE_URL}/category/{section_name}.html"
            else:
                page_url = f"{BASE_URL}/category/{section_name}/{page}.html"

            print(f"  [-] Fetching page {page}: {page_url}")
            html = fetch_html(page_url)
            if not html:
                break

            # Check direct songs on page
            songs = parse_song_buttons(html)
            for s in songs:
                if s["id"] not in seen_ids:
                    seen_ids.add(s["id"])
                    all_songs.append(s)

            # Check if this category has album links (e.g. /album/...)
            album_links = set(re.findall(r'href=["\'](/album/[^"\']+)["\']', html))
            if album_links:
                print(f"    Found {len(album_links)} albums on page {page}. Extracting tracks...")
                for alb in album_links:
                    alb_url = urljoin(BASE_URL, alb)
                    alb_songs = scrape_album_tracks(alb_url)
                    for s in alb_songs:
                        if s["id"] not in seen_ids:
                            seen_ids.add(s["id"])
                            all_songs.append(s)

            # Check if there is next page
            if f"/category/{section_name}/{page + 1}.html" not in html and page > 1:
                break

            time.sleep(0.5)

    return all_songs


def scrape_search(query: str) -> list[dict]:
    """Search for songs or albums by query."""
    print(f"[*] Searching for '{query}'...")
    url = f"{BASE_URL}/search.php?q={requests.utils.quote(query)}"
    html = fetch_html(url)
    if not html:
        return []

    songs = parse_song_buttons(html)
    # Also check albums in search results
    album_links = set(re.findall(r'href=["\'](/album/[^"\']+)["\']', html))
    for alb in album_links:
        alb_songs = scrape_album_tracks(urljoin(BASE_URL, alb))
        songs.extend(alb_songs)

    # Deduplicate
    unique = []
    seen = set()
    for s in songs:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def download_mp3(song: dict, dest_dir: str = "downloads", quality: str = "128") -> str:
    """Download an MP3 file to disk."""
    os.makedirs(dest_dir, exist_ok=True)
    clean_title = re.sub(r'[\\/*?:"<>|]', "", f"{song['artist']} - {song['title']}").strip()
    filename = f"{clean_title} ({quality}k).mp3"
    filepath = os.path.join(dest_dir, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
        return filepath

    url = song.get(f"download_{quality}k") or song.get("stream_128k")
    if not url:
        return ""

    try:
        r = SESSION.get(url, stream=True, timeout=20)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return filepath
    except Exception as e:
        print(f"[!] Error downloading {filename}: {e}", file=sys.stderr)

    return ""


def save_results(songs: list[dict], base_name: str = "djjohal_songs"):
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
    parser = argparse.ArgumentParser(description="DJJohal Song Scraper")
    parser.add_argument("--mode", choices=["trending", "recently", "category", "search", "all"], default="trending",
                        help="Mode: trending, recently, category, search, all")
    parser.add_argument("--cat", default="single-track", help="Category slug (e.g. single-track, punjabi, haryanvi)")
    parser.add_argument("--pages", type=int, default=1, help="Max pages to scrape per category (default: 1)")
    parser.add_argument("--query", default="", help="Search query for search mode")
    parser.add_argument("--fetch-details", action="store_true", help="Fetch 320k HQ links from each song page")
    parser.add_argument("--download", action="store_true", help="Download MP3 files to downloads/ folder")
    parser.add_argument("--quality", choices=["320", "128", "48"], default="128", help="Audio quality (default: 128)")
    parser.add_argument("--out", default="djjohal_songs", help="Base output filename for .json and .csv")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent threads (default: 5)")
    args = parser.parse_args()

    songs = []
    if args.mode == "trending":
        songs = scrape_section("trending")
    elif args.mode == "recently":
        songs = scrape_section("recently")
    elif args.mode == "category":
        songs = scrape_section(args.cat, max_pages=args.pages)
    elif args.mode == "search":
        if not args.query:
            print("[!] Please provide a search query with --query", file=sys.stderr)
            return
        songs = scrape_search(args.query)
    elif args.mode == "all":
        categories = ["single-track", "punjabi", "haryanvi", "hindi-movies", "hindi-single"]
        for cat in categories:
            cat_songs = scrape_section(cat, max_pages=args.pages)
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

    # Fetch 320k download links if requested or downloading
    if args.fetch_details or (args.download and args.quality == "320"):
        print(f"[*] Fetching high-quality download links using {args.threads} threads...")
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            future_to_song = {executor.submit(get_detail_downloads, s): s for s in songs}
            for i, future in enumerate(as_completed(future_to_song), start=1):
                res = future.result()
                if i % 10 == 0 or i == len(songs):
                    print(f"  Processed {i}/{len(songs)} song details...", end="\r")
        print()

    # Save metadata
    save_results(songs, base_name=args.out)

    # Download MP3s if requested
    if args.download:
        print(f"\n[*] Downloading {len(songs)} songs ({args.quality}kbps) using {args.threads} threads...")
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(download_mp3, s, "downloads", args.quality) for s in songs]
            for i, future in enumerate(as_completed(futures), start=1):
                p = future.result()
                if p:
                    print(f"  [{i}/{len(songs)}] Downloaded: {os.path.basename(p)}")
        print("[+] All downloads complete! Check the downloads/ folder.")


if __name__ == "__main__":
    main()
