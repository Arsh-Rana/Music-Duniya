import os
from dual_scraper import search_all_sources, get_cached_or_download_song

print("[1] Searching 'sidhu' on DJJohal & Mr-Jatt...")
results = search_all_sources('sidhu')
print(f"Total results: {len(results)}")

dj_song = next((r for r in results if r['source'] == 'djjohal'), None)
mj_song = next((r for r in results if r['source'] == 'mrjatt'), None)

print(f"DJJohal song: {dj_song['title']} ({dj_song['page_url']})")
print(f"MrJatt song: {mj_song['title']} ({mj_song['page_url']})")

print("\n[2] Testing DJJohal caching...")
path1 = get_cached_or_download_song(
    song_id=dj_song['id'],
    source='djjohal',
    page_url=dj_song.get('page_url', '')
)
print(f"DJJohal cached at: {path1} (size: {os.path.getsize(path1)} bytes)")
assert os.path.exists(path1) and os.path.getsize(path1) > 50000

print("\n[3] Testing Mr-Jatt caching...")
path2 = get_cached_or_download_song(
    song_id=mj_song['id'],
    source='mrjatt',
    page_url=mj_song.get('page_url', '')
)
print(f"Mr-Jatt cached at: {path2} (size: {os.path.getsize(path2)} bytes)")
assert os.path.exists(path2) and os.path.getsize(path2) > 50000

print("\n🎉 BOTH DJJOHAL AND MR-JATT CAN BE SEARCHED, TEMPORARILY CACHED, AND PLAYED!")
