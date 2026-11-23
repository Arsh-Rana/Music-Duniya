import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json

def test_full_pipeline():
    music_app_dir = os.path.dirname(os.path.abspath(__file__))
    port = 3097
    env = os.environ.copy()
    env['PORT'] = str(port)

    print("[1] Starting backend server...")
    proc = subprocess.Popen([sys.executable, 'server.py'], cwd=music_app_dir, env=env)
    time.sleep(2)

    try:
        base_url = f"http://127.0.0.1:{port}"

        # 1. Test frontend
        with urllib.request.urlopen(f"{base_url}/") as res:
            assert res.status == 200
            html = res.read().decode('utf-8')
            assert 'Music-Duniya' in html
        print("  -> GET / returned 200 OK")

        # 2. Test online search across DJJohal & Mr-Jatt
        search_url = f"{base_url}/api/search-online?q=sidhu"
        print(f"  -> Testing online search: {search_url}")
        with urllib.request.urlopen(search_url, timeout=12) as res:
            assert res.status == 200
            data = json.loads(res.read().decode('utf-8'))
            assert isinstance(data, list)
            assert len(data) > 0, "No search results returned from scraper!"
            sources = set(item['source'] for item in data)
            print(f"  -> Found {len(data)} search results across sources: {sources}")
            assert 'djjohal' in sources or 'mrjatt' in sources, "Expected djjohal or mrjatt sources"

        # 3. Test on-demand stream/download
        first_song = data[0]
        stream_api = f"{base_url}/api/stream-or-download?id={first_song['id']}&source={first_song['source']}&page_url={urllib.parse.quote(first_song.get('page_url', ''))}"
        print(f"  -> Testing stream API: {stream_api}")

        req = urllib.request.Request(stream_api)
        req.add_header('Range', 'bytes=0-2047')
        with urllib.request.urlopen(req, timeout=15) as res:
            assert res.status in (200, 206)
            assert res.headers.get('Content-Type') == 'audio/mpeg'
            chunk = res.read()
            assert len(chunk) > 0
            print(f"  -> Streamed {len(chunk)} bytes of audio successfully!")

        # 4. Test cached songs list
        with urllib.request.urlopen(f"{base_url}/api/cached-songs") as res:
            assert res.status == 200
            cached = json.loads(res.read().decode('utf-8'))
            print(f"  -> /api/cached-songs shows {len(cached)} songs currently cached.")
            assert len(cached) > 0

        print("\n🎉 ALL TESTS PASSED! Multi-source scraper, caching, and Music-Duniya player verified!")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    test_full_pipeline()
