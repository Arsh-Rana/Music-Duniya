import subprocess
import os

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
artifact_dir = r"C:\Users\arshr\.gemini\antigravity\brain\27961cc5-bd50-42d6-aba1-9d128879f790"
user_data = os.path.abspath("edge_preview_profile")

out_path = os.path.join(artifact_dir, "preview_search.png")
cmd = [
    edge_path,
    "--headless=new",
    "--disable-gpu",
    f"--user-data-dir={user_data}",
    f"--screenshot={out_path}",
    "--window-size=1280,820",
    "--virtual-time-budget=4000",
    "http://localhost:3000/?q=Sidhu"
]
subprocess.run(cmd, capture_output=True, text=True, timeout=20)
print(f"Captured preview_search.png -> {os.path.exists(out_path)} ({os.path.getsize(out_path) if os.path.exists(out_path) else 0} bytes)")
