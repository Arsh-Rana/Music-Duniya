import requests
import json

base_url = "http://localhost:3000"

print("[1] Testing /api/songs...")
try:
    r = requests.get(f"{base_url}/api/songs", timeout=5)
    print(f"  Status: {r.status_code}, Songs count: {len(r.json())}")
except Exception as e:
    print(f"  Error: {e}")

print("\n[2] Testing /api/singers (Popular Punjabi Artists with Avatars)...")
try:
    r = requests.get(f"{base_url}/api/singers", timeout=5)
    print(f"  Status: {r.status_code}")
    singers = r.json()
    for s in singers[:3]:
        print(f"  - {s['name']} | Tag: {s.get('tag')} | Avatar: {s['avatar_url'][:50]}...")
except Exception as e:
    print(f"  Error: {e}")

print("\n[3] Testing /api/all-singers?letter=d (DJPunjab A-Z catalog)...")
try:
    r = requests.get(f"{base_url}/api/all-singers?letter=d", timeout=8)
    print(f"  Status: {r.status_code}")
    d_singers = r.json()
    print(f"  Found {len(d_singers)} singers starting with 'D'. First 3:")
    for s in d_singers[:3]:
        print(f"  - {s['name']} (slug: {s['slug']})")
except Exception as e:
    print(f"  Error: {e}")

print("\n[4] Testing /api/singer-profile?slug=diljit-dosanjh (Profile & Caching)...")
try:
    r = requests.get(f"{base_url}/api/singer-profile?slug=diljit-dosanjh", timeout=10)
    print(f"  Status: {r.status_code}")
    prof = r.json()
    print(f"  Singer: {prof['name']}")
    print(f"  Avatar: {prof['avatar_url']}")
    print(f"  Total Tracks: {len(prof.get('songs', []))}")
    print(f"  From Cache: {prof.get('from_cache', False)}")
except Exception as e:
    print(f"  Error: {e}")

print("\nVERIFICATION COMPLETE!")
