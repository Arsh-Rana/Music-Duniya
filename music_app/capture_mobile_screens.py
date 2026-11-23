import os
import subprocess
import time

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
artifact_dir = r"C:\Users\arshr\.gemini\antigravity\brain\27961cc5-bd50-42d6-aba1-9d128879f790"
temp_profile = r"C:\Users\arshr\AppData\Local\Temp\edge_mobile_p"

os.makedirs(artifact_dir, exist_ok=True)

targets = [
    ("preview_mobile_home.png", "http://localhost:3000"),
    ("preview_mobile_search.png", "http://localhost:3000/?view=search"),
    ("preview_mobile_library.png", "http://localhost:3000/?view=library"),
    ("preview_mobile_artists.png", "http://localhost:3000/?view=artists")
]

for idx, (filename, url) in enumerate(targets):
    out_path = os.path.join(artifact_dir, filename)
    cmd = [
        edge_path,
        "--headless=new",
        f"--user-data-dir={temp_profile}_{idx}",
        "--window-size=500,915",
        f"--screenshot={out_path}",
        url
    ]
    print(f"[*] Capturing {filename} from {url}...")
    subprocess.run(cmd, capture_output=True)
    time.sleep(1)
    if os.path.exists(out_path):
        print(f"  -> Captured {filename} ({os.path.getsize(out_path)} bytes)")
