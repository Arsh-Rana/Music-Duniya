import djpunjab_scraper

print("[1] Testing get_popular_singers...")
singers = djpunjab_scraper.get_popular_singers()
print(f"Total popular singers: {len(singers)}")
for s in singers[:3]:
    print(f"  {s['name']} -> {s['avatar_url']}")

print("\n[2] Testing get_singer_profile_and_songs for diljit-dosanjh...")
profile = djpunjab_scraper.get_singer_profile_and_songs('diljit-dosanjh')
print(f"Singer: {profile['name']}")
print(f"Avatar URL: {profile['avatar_url']}")
print(f"Songs count: {len(profile['songs'])}")
for song in profile['songs'][:3]:
    print(f"  - {song['title']} ({song['page_url']})")

print("\n[3] Testing resolve_djpunjab_mp3_stream...")
first_song = profile['songs'][0]
direct_stream = djpunjab_scraper.resolve_djpunjab_mp3_stream(first_song['page_url'])
print(f"Direct MP3 URL: {direct_stream}")
assert direct_stream.endswith('.mp3'), "Direct stream should be an MP3 link!"

print("\n[4] Testing cache retrieval...")
cached_profile = djpunjab_scraper.get_singer_profile_and_songs('diljit-dosanjh')
assert cached_profile['from_cache'] is True, "Profile should be served from cache on 2nd hit!"
print(f"Cache hit verified: {cached_profile['name']} with {cached_profile['song_count']} songs.")

print("\nALL DJPUNJAB SCRAPER & CACHE TESTS PASSED!")
