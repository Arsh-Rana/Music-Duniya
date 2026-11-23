import subprocess
import os
import time
import json
import urllib.request
import base64
import websocket

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
artifact_dir = r"C:\Users\arshr\.gemini\antigravity\brain\27961cc5-bd50-42d6-aba1-9d128879f790"
user_data = os.path.abspath("edge_preview_profile")

screens = [
    ("preview_mobile_home.png", "http://localhost:3000/?view=home", 390, 844, True),
    ("preview_mobile_search.png", "http://localhost:3000/?view=search", 390, 844, True),
    ("preview_mobile_library.png", "http://localhost:3000/?view=library", 390, 844, True),
    ("preview_mobile_artist.png", "http://localhost:3000/?view=singer_profile&param=diljit-dosanjh", 390, 844, True),
    ("preview_mobile_playlist.png", "http://localhost:3000/?view=playlist&param=Kitab", 390, 844, True),
    ("preview_mobile_auth.png", "http://localhost:3000/?modal=auth", 390, 844, True),
    ("preview_mobile_jam.png", "http://localhost:3000/?modal=jam", 390, 844, True),
    ("preview_mobile_settings.png", "http://localhost:3000/?modal=settings", 390, 844, True),
    ("preview_desktop_home.png", "http://localhost:3000/?view=home", 1280, 820, False)
]

for idx, (name, url, width, height, is_mobile) in enumerate(screens):
    out_path = os.path.join(artifact_dir, name)
    profile_dir = f"{user_data}_{idx}"
    cmd = [
        edge_path,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--disable-gpu",
        f"--user-data-dir={profile_dir}",
        url
    ]
    p = subprocess.Popen(cmd)
    time.sleep(2.5)
    try:
        tabs = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
        target_tab = None
        for t in tabs:
            if "3000" in t.get("url", ""):
                target_tab = t
                break
        if not target_tab and tabs:
            target_tab = tabs[0]
        
        ws = websocket.create_connection(target_tab["webSocketDebuggerUrl"])
        # Device metrics override
        metrics_msg = {
            "id": 1,
            "method": "Emulation.setDeviceMetricsOverride",
            "params": {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": is_mobile
            }
        }
        ws.send(json.dumps(metrics_msg))
        ws.recv()
        time.sleep(1.0)

        # Capture screenshot
        shot_msg = {
            "id": 2,
            "method": "Page.captureScreenshot",
            "params": {
                "format": "png",
                "clip": {
                    "x": 0,
                    "y": 0,
                    "width": width,
                    "height": height,
                    "scale": 1
                }
            }
        }
        ws.send(json.dumps(shot_msg))
        res = json.loads(ws.recv())
        img_b64 = res.get("result", {}).get("data")
        if img_b64:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(img_b64))
            print(f"Captured {name}: {os.path.exists(out_path)} ({os.path.getsize(out_path)} bytes)")
        else:
            print(f"Failed to capture {name}: empty screenshot data")
        ws.close()
    except Exception as e:
        print(f"Error {name}: {e}")
    finally:
        p.terminate()
        time.sleep(0.5)
