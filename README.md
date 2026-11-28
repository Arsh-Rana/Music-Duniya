# Music 🎵

> **Ultra Lossless Music Streaming Web Application & Android App**  
> Built with a luxury visionOS dark UI inspired by **YouTube Music Premium**, **Apple Music**, and **ViaMusic**, featuring Long-Distance Jam co-listening, verified studio artwork, and native Android foreground media playback.

---

## 📱 Screenshots & Previews

- **Mobile Home & Luxury Glass Interface:** Verified dark aesthetic with frosted cards and floating navigation.
- **Search & High-Resolution Track Art:** Studio artwork with Enter-triggered precision search.
- **Long-Distance Jam Sessions:** Synchronous room audio playback across devices worldwide.
- **Android Foreground Notification:** Persistent status bar and lock screen player with full OS Force Stop capability.

---

## ✨ Features

- **🎧 Hi-Fi Ultra Lossless Audio:** 320kbps MP3 / AAC direct streaming engine with preloading for `< 50ms` playback startup.
- **🎨 Luxury Dark UI/UX:** Inspired by YouTube Music, Apple Music, and ViaMusic with pitch-black OLED background (`#07070b`), glassmorphism cards, and floating docked mini-player.
- **🔍 Non-Blocking Precision Search:** Type freely without aggressive timeouts; search triggers smoothly on **Enter** or tapping the Search button.
- **🖼️ 100% Unique Verified Track Covers:** Every single track and album features genuine, high-resolution artwork from Apple Music & JioSaavn CDNs.
- **📻 Long-Distance Jam (Listen Together):** Real-time synchronized co-listening. When the host plays, pauses, or seeks, listener devices stay in sync automatically.
- **📲 Native Android APK with Foreground Service:** Includes `MusicPlaybackService` for persistent background playback, lock screen media controls, and full OS process management (**Force Stop** support).
- **🔒 Mandatory Gmail Account Gate:** Protects user sessions with Gmail-based authentication and synchronized personal libraries.

---

## 🏗️ Project Architecture

```
Music-Duniya/
├── android_app/                  # Native Android Application Source
│   ├── src/com/musicduniya/app/  # Java Native Bridge & Services
│   │   ├── MainActivity.java     # Fullscreen WebView activity & notification channels
│   │   ├── MusicPlaybackService.java # Android Foreground Service for media & Force Stop
│   │   └── ScraperBridge.java    # JavaScript to Java interface for native playback
│   ├── assets/                   # Bundled offline web assets & initial song catalog
│   ├── res/                      # Android drawables, mipmaps, and XML themes
│   ├── AndroidManifest.xml       # Permissions (POST_NOTIFICATIONS, FOREGROUND_SERVICE)
│   └── build_apk.py              # Automated AAPT2 + D8 + apksigner build pipeline
│
├── music_app/                    # Core Web Application
│   ├── index.html                # Single Page Application structure
│   ├── style.css                 # Executive luxury CSS with visionOS glassmorphism
│   ├── app.js                    # Audio engine, Jam sync, search, and Gmail gate
│   ├── server.py                 # Lightweight Python backend & Jam room relay
│   ├── songs.json                # Curated studio track database
│   ├── playlists_resolved.json   # Pre-resolved playlist catalog
│   └── logo.png                  # Music-Duniya brand emblem
│
├── Music-Duniya.apk              # Pre-built & signed release Android APK (0.15 MB)
├── requirements.txt              # Python server dependencies
├── render.yaml                   # 1-Click Render cloud deployment configuration
├── Procfile                      # Web process launcher for PaaS hosting
├── Dockerfile                    # Container definition for containerized deployment
└── README.md                     # Documentation
```

---

## 🚀 Getting Started

### 1. Run the Web Application Locally

```bash
# Clone the repository
git clone https://github.com/Arsh-Rana/Music-Duniya.git
cd Music-Duniya

# Start the Music server (Python 3.8+)
python music_app/server.py
```

Open your browser and visit:
👉 **`http://localhost:3000`**

---

### 2. Install on Android

1. Download the signed APK file: [`Music.apk`](Music.apk) or [`Music-Duniya.apk`](Music-Duniya.apk)
2. Transfer it to your Android device via USB, WhatsApp, or Google Drive.
3. Open the file on your device and tap **Install**.
4. Grant notification permission when prompted to enable background media playback and status-bar controls.

---

### 3. Rebuild the Android APK from Source

```bash
python android_app/build_apk.py
```
This automatically compiles resources with AAPT2, compiles Java sources, converts classes to DEX with D8, aligns the APK, and signs it with `apksigner`.

---

## 🌐 Cloud Deployment (Render / Railway / Docker)

The project includes ready-to-use cloud configuration files:
- **Render:** Deploy with 1-click using [`render.yaml`](render.yaml).
- **Heroku / Railway:** Configured with [`Procfile`](Procfile).
- **Docker:** Build and run container with [`Dockerfile`](Dockerfile).

```bash
docker build -t music-duniya .
docker run -p 3000:3000 music-duniya
```

---

## 📄 License

Developed for **Music-Duniya**. All rights reserved.
