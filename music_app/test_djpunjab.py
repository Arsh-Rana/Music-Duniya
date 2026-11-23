import requests
import re

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://djpunjab.is/single-track/dealer-diljit-dosanjh-album-59149.html'
r = requests.get(url, headers=headers)
print('Track page status:', r.status_code)

# Find song page link or mp3 link
song_links = re.findall(r'<a[^>]*href=["\'](/single-track/[^"\']+-mp3-song-(\d+)\.html)["\'][^>]*>(.*?)</a>', r.text)
print('Song links:', song_links)
if song_links:
    song_url = 'https://djpunjab.is' + song_links[0][0]
    sr = requests.get(song_url, headers=headers)
    mp3s = re.findall(r'href=["\'](https://s320\.djpunjab\.is/data/[^"\']+\.mp3)["\']', sr.text)
    print('MP3s on song page:', mp3s)
