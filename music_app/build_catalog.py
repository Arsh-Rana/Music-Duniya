import json
import os
import urllib.parse

def build_catalog():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(root, 'djjohal_songs.json')
    dl_dir = os.path.join(root, 'downloads')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        songs = json.load(f)
        
    dl_files = os.listdir(dl_dir) if os.path.exists(dl_dir) else []
    catalog = []
    
    for idx, s in enumerate(songs):
        title = s.get('title', '').strip()
        artist = s.get('artist', '').strip()
        
        match = None
        for f in dl_files:
            if title.lower() in f.lower() and artist.lower() in f.lower():
                match = f
                break
        if not match:
            for f in dl_files:
                if title.lower() in f.lower():
                    match = f
                    break
                    
        file_path = os.path.join(dl_dir, match) if match else None
        duration_sec = 195
        if file_path and os.path.exists(file_path):
            size = os.path.getsize(file_path)
            duration_sec = max(30, int(size / 16000))
            
        mins = duration_sec // 60
        secs = duration_sec % 60
        duration_str = f"{mins}:{secs:02d}"
        
        # Album name groupings
        album = f"{artist} Special"
        if "Kulbir" in artist:
            album = "Sardarni & Classics"
        elif "Babbar" in artist:
            album = "Desi Vibes"
            
        catalog.append({
            "id": str(s.get('id', idx + 1)),
            "title": title,
            "artist": artist,
            "album": album,
            "category": s.get('category', 'Punjabi'),
            "duration": duration_str,
            "duration_sec": duration_sec,
            "cover_url": s.get('cover_url', ''),
            "filename": match,
            "audio_url": f"/audio/{urllib.parse.quote(match)}" if match else s.get('stream_128k', ''),
            "stream_url": s.get('stream_128k', '')
        })
        
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'songs.json')
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump(catalog, out, indent=2, ensure_ascii=False)
        
    print(f"Catalog created: {len(catalog)} songs at {out_path}")

if __name__ == '__main__':
    build_catalog()
