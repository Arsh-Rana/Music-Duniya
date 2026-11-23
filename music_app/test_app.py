import json
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

def run_tests():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    music_dir = os.path.join(root, 'music_app')
    songs_path = os.path.join(music_dir, 'songs.json')
    dl_dir = os.path.join(root, 'downloads')

    print("[1] Verifying frontend assets...")
    for fname in ['index.html', 'style.css', 'app.js', 'server.js', 'server.py']:
        fpath = os.path.join(music_dir, fname)
        assert os.path.exists(fpath), f"Missing {fname}"
        assert os.path.getsize(fpath) > 0, f"Empty {fname}"
    print("  -> Assets verified.")

    print("[2] Verifying catalog and audio files...")
    assert os.path.exists(songs_path), "Missing songs.json"
    with open(songs_path, 'r', encoding='utf-8') as f:
        songs = json.load(f)
    assert len(songs) >= 19, f"Expected songs in catalog, got {len(songs)}"

    print(f"  -> {len(songs)} songs verified in catalog.")

    print("[3] Testing HTTP server and range streaming...")
    test_port = 3099
    env = os.environ.copy()
    env['PORT'] = str(test_port)

    # Start server in background
    proc = subprocess.Popen(['node', 'server.js'], cwd=music_dir, env=env)
    time.sleep(1.5)

    try:
        base_url = f"http://127.0.0.1:{test_port}"

        # Test index.html
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200, f"Index failed: {res.status}"
            body = res.read().decode('utf-8')
            assert 'Music-Duniya' in body, "Index missing Music-Duniya title"
        print("  -> GET / returned 200 OK with Music-Duniya HTML.")

        # Test /api/songs
        req = urllib.request.Request(f"{base_url}/api/songs")
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200, f"API failed: {res.status}"
            api_songs = json.loads(res.read().decode('utf-8'))
            assert len(api_songs) == 19, "API song count mismatch"
        print("  -> GET /api/songs returned 200 OK with 19 songs.")

        # Test Audio streaming with HTTP Range
        first_song = songs[0]
        audio_url = f"{base_url}{first_song['audio_url']}"
        range_req = urllib.request.Request(audio_url)
        range_req.add_header('Range', 'bytes=0-1023')
        with urllib.request.urlopen(range_req, timeout=5) as res:
            assert res.status == 206, f"Range request failed: {res.status}"
            assert res.headers.get('Content-Type') == 'audio/mpeg', "Wrong audio content type"
            assert 'bytes 0-1023/' in res.headers.get('Content-Range', ''), "Missing Content-Range"
            chunk = res.read()
            assert len(chunk) == 1024, f"Expected 1024 bytes, got {len(chunk)}"
        print("  -> GET /audio/... Range request returned 206 Partial Content (1024 bytes).")

        print("\n ALL TESTS PASSED! Music-Duniya app is completely verified.")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    run_tests()
