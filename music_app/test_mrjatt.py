import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.mr-jatt.im/'
}
url = 'https://cdnsongs.com/dren/music/data/Single_Track/202611/Aukaat/128/Aukaat_1.mp3/Aukaat.mp3'
r = requests.get(url, headers=headers, stream=True, timeout=10)
print('Status:', r.status_code, 'Content-Type:', r.headers.get('Content-Type'))
if r.status_code == 200:
    chunk = next(r.iter_content(chunk_size=10240))
    print('Success! Received bytes:', len(chunk))
