import os
import subprocess
import time

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
artifact_dir = r"C:\Users\arshr\.gemini\antigravity\brain\27961cc5-bd50-42d6-aba1-9d128879f790"
temp_user_data = r"C:\Users\arshr\AppData\Local\Temp\edge_screenshot_profile"

os.makedirs(artifact_dir, exist_ok=True)
os.makedirs(temp_user_data, exist_ok=True)

targets = [
    ("preview_desktop_home.png", "http://localhost:3000", "1280,850"),
    ("preview_artists.png", "http://localhost:3000/?view=artists", "1280,850"),
    ("preview_profile.png", "http://localhost:3000/?view=singer_profile&slug=diljit-dosanjh", "1280,850"),
    ("preview_mobile.png", "http://localhost:3000", "412,915")
]

for idx, (filename, url, size) in enumerate(targets):
    out_path = os.path.join(artifact_dir, filename)
    cmd = [
        edge_path,
        "--headless=new",
        f"--user-data-dir={temp_user_data}_{idx}",
        f"--window-size={size}",
        f"--screenshot={out_path}",
        url
    ]
    print(f"[*] Capturing {filename} from {url}...")
    subprocess.run(cmd, capture_output=True)
    time.sleep(1)
    if os.path.exists(out_path):
        print(f"  -> Successfully captured {filename} ({os.path.getsize(out_path)} bytes)")
    else:
        print(f"  [!] Failed to capture {filename}")
