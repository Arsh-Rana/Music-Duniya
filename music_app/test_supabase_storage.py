import os
import requests

url = os.environ.get('SUPABASE_URL', 'https://sosycnpbyrllrnnzapmn.supabase.co')
secret_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

headers = {
    'apikey': secret_key,
    'Authorization': f'Bearer {secret_key}',
    'Content-Type': 'application/json'
}

# 1. Upload test object
r = requests.post(f'{url}/storage/v1/object/music_cache/artists/diljit-dosanjh.json', headers=headers, json={'name': 'Diljit Dosanjh', 'status': 'cached'})
print('Upload status:', r.status_code, r.text)

# 2. Read public object
r2 = requests.get(f'{url}/storage/v1/object/public/music_cache/artists/diljit-dosanjh.json')
print('Read public status:', r2.status_code, r2.json())
