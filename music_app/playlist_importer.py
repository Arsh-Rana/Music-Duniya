import requests
import json
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

playlist_ids = [
    ('1FOX9nddvQSTd5V4u3Q9n5', 'Playlist 1'),
    ('3gtSfF5tgY0qhH6YGr1Zz6', 'Playlist 2'),
    ('4Ur1b92oHD4kiKHRs0DbvV', 'Playlist 3'),
    ('5m6F2T6fKtmZiJtrzkwp52', 'Playlist 4'),
    ('25L3vOJXpQBaoA3HSwolqK', 'Playlist 5')
]

all_playlists = {}

for pid, default_name in playlist_ids:
    source_domain = os.environ.get("SOURCE_DOMAIN", "open.audio-stream.com")
    url = f"https://{source_domain}/embed/playlist/{pid}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        s = soup.find('script', id='__NEXT_DATA__')
        if s:
            data = json.loads(s.string)
            entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
            name = entity.get('name') or default_name
            tracks = []
            for t in entity.get('trackList', []):
                tracks.append({
                    'title': t.get('title', '').strip(),
                    'artist': t.get('subtitle', '').strip(),
                    'duration_ms': t.get('duration', 0),
                    'uri': t.get('uri', '')
                })
            all_playlists[name] = {
                'id': pid,
                'name': name,
                'tracks': tracks
            }
            print(f"[+] Loaded '{name}' ({len(tracks)} tracks)")
        else:
            print(f"[-] No __NEXT_DATA__ for {pid}")
    except Exception as e:
        print(f"[!] Error fetching {pid}: {e}")

with open('music_app/playlist_import.json', 'w', encoding='utf-8') as f:
    json.dump(all_playlists, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(all_playlists)} playlists to music_app/playlist_import.json")
