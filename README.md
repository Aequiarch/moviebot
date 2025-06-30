# 🎬 MovieBot

**MovieBot** is a fully automated, headless movie streaming system that outputs video via a virtual webcam (`/dev/videoX`) using **FFmpeg**, `v4l2loopback`, and `Xvfb`. It plays local or YouTube videos into a **Discord voice channel**—all controlled via **Telegram** and **Discord** bots.

> ✨ Upload from Telegram, stream on Discord, control from anywhere. No “Go Live” required.

---

## 🌐 Architecture Overview

```plaintext
Telegram Bot   Discord Bot
     |              |
     v              v
+----------------+  +------------------+
| telegramcontrol|  |  discordbot      |
+----------------+  +------------------+
         \           /
          v         v
     +-------------------+
     |   control.json    | <--- User commands
     +-------------------+
                 |
                 v
        +----------------+
        |  controller.py |
        +----------------+
                 |
                 v
        +----------------+
        |  player.py     | ---+---> FFmpeg ----> v4l2loopback (/dev/video10)
        +----------------+    |
                              v
                       [now_playing.txt]

Uploader --> playlist.json --> Queue --> Player.
````
---
## 🚀 Features

  

* ✅ 24/7 autonomous video playback via simulated webcam

* 🧠 Headless rendering with `Xvfb`

* 🕹️ Telegram & Discord bot control

* 📄 JSON-based media queue with pinning support

* ⏯️ Supports pause/resume/skip/stop

* 💾 Crash-safe state persistence

* 🔐 POSIX-safe file I/O via advisory locks

* 🎥 FFmpeg + `v4l2loopback` integration

* ⚙️ Designed to run as a `systemd` service

  

---

  

## 📁 Project Structure
```plaintext
moviebot/
├── core/
│   ├── config.py
│   ├── controller.py
│   ├── player.py
│   ├── uploader.py
│   ├── discordbot.py
│   ├── telegramcontrol.py
│   ├── queue.py
│   ├── camera/
│   │   ├── virtual_cam.py
│   │   └── xvfb_manager.py
│   └── utils/
│       ├── logger.py
│       └── filelock.py
├── main.py
├── moviebot.service
├── .env
├── requirements.txt
└── README.md
```


---

  

## 💡 Requirements

  

* Python 3.10+

* Linux (Debian/Ubuntu recommended)

* `ffmpeg` with video4linux2 support

* `v4l2loopback` kernel module

* `Xvfb`

* `yt-dlp`

* `systemd` (for daemon mode)

  

---

  

## 📦 Installation

  

### 1. Clone & Set Up

  ```bash

git clone https://github.com/yourusername/moviebot.git

cd moviebot

```

### 2. Create `.env`

  

Rename `.env.example` or create manually:

```env
  # --- Telegram ---
TELEGRAM_CONTROL_BOT_TOKEN=your_token_here
TELEGRAM_UPLOAD_BOT_TOKEN=your_token_here
TELEGRAM_ADMIN_USER_ID=123456789
TELEGRAM_ALLOWED_USERS=123456789,987654321

# --- Discord ---
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id
DISCORD_VOICE_CHANNEL_ID=your_voice_channel_id
DISCORD_USER_TOKEN=your_discord_user_token  # optional

# --- Paths ---
FFMPEG_PATH=/usr/bin/ffmpeg
YTDLP_PATH=/usr/local/bin/yt-dlp

# --- Virtual Webcam ---
VIRTUAL_CAM_DEVICE=/dev/video10
XVFB_DISPLAY=:99

# --- Media Storage ---
MOVIE_DIR=./data/movies
YOUTUBE_DIR=./data/youtube

# --- Logs ---
LOG_DIR=./logs
```

---
### 3. Install Python Dependencies

 ```bash

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


``` 

---

### 4. Install System Dependencies

  ```bash

sudo apt update && sudo apt install -y \
  ffmpeg \
  v4l2loopback-dkms \
  v4l-utils \
  xvfb \
  yt-dlp \
  python3-venv \
  python3-pip

```

---
### 5. Load Virtual Webcam

  ```bash

sudo modprobe v4l2loopback video_nr=10 card_label="MovieBotCam" exclusive_caps=1

```

 

> ℹ️ MovieBot will auto-load this if not already active.

  

---

  

## ▶️ Running MovieBot

  

```bash

python3 main.py

```

  

To run as a background daemon:

  

```bash

sudo cp moviebot.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable --now moviebot

```

  

View logs:

  

```bash

sudo journalctl -u moviebot -f

```

  

---

  

## 🎛️ Control Commands

  

### Telegram Bot

  

```

/pause        ⏸️ Pause playback
/resume       ▶️ Resume playback
/skip         ⏭️ Skip current movie
/stop         ⏹️ Stop playback
/nowplaying   🎥 Show currently playing
/queue        🎞️ Show queue
/status       📊 Show current status

```

  

### Discord Buttons

  

* ⏸️ Pause
* ▶️ Resume
* ⏭️ Skip
* ⏹️ Stop

  

---

  

## 🛠️ Troubleshooting

  

| Problem                          | Fix                                                    |

| --------------------------------- | ------------------------------------------------------|
| ❌ `/dev/video10` not found      | Ensure `v4l2loopback` is loaded                        |
| 🚧 Xvfb fails to start           | Try `Xvfb :99 -screen 0 1280x720x24 &`                 |
| ⚠️ Bot won’t run                 | Check `.env` and paths, run `python3 main.py` manually |
| 🎥 Camera not visible in Discord | Check webcam permissions and virtual device            |

  

---

  

## 🔮 To-Do

  

* [ ] OBS Studio fallback mode

* [ ] Web dashboard with queue + status

* [ ] Web-based media uploader

* [ ] Auto-thumbnail in Discord messages

  

---

  

## 📄 License

  

**MIT License** — Free for personal or commercial use. Attribution appreciated.

  

---

  

## 👤 Author

  

# Made with ❤️ by [Aequiarch](https://github.com/Aequiarch)
