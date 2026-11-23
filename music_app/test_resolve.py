import requests
import re

url = 'https://www.djjohal.com/song/sidhu-son-slowed-reverb-sidhu-moose-wala.html'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
print('Status:', r.status_code)
# look for play-song buttons or mp3 links
buttons = re.findall(r'<button[^>]*class=["\'][^"\']*play-song[^"\']*["\'][^>]*>', r.text)
print('Buttons on page:', len(buttons))
for b in buttons[:2]:
    print(' ', b)

links = re.findall(r'href=["\']([^"\']+\.mp3[^"\']*)["\']', r.text)
print('MP3 links:', links)
