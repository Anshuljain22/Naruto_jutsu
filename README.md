# 🍃 Jutsu Vision — Naruto AR Engine

A real-time Augmented Reality app that detects Naruto hand signs via your webcam and overlays jutsu effects using MediaPipe + OpenCV, served through a browser UI.

## ✨ Jutsus Supported

| Gesture | Jutsu |
|---|---|
| Form a **Plus Sign (+)** with your index fingers | 👥 Shadow Clone |
| Hold open palms **close together** facing each other | 🌀 Rasengan |
| Hold one hand up like a **Claw** facing the camera | ⚡ Chidori |
| Bring index & middle fingers to your **lips** | 🔥 Fireball |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A webcam

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/Jutsu-try.git
cd Jutsu-try

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download MediaPipe models
python download_models.py

# 5. Run the app
python app.py
```

Then open **http://localhost:5000** in your browser and click **Start Camera**.

## 🌐 Share with Others (ngrok)

Since this app needs your local webcam, use [ngrok](https://ngrok.com) to expose it publicly:

```bash
# While app.py is running in another terminal:
ngrok http 5000
```

Share the generated `https://xxxx.ngrok.io` URL — anyone with the link can use your camera feed in real time.

## 📁 Project Structure

```
Jutsu-try/
├── app.py                  # Flask server + AR engine
├── main.py                 # Standalone (no browser) version
├── index.html / script.js  # Web UI
├── effects/                # Jutsu visual effects
├── gesture_engine/         # Hand sign recognition
├── pose_detection/         # MediaPipe pose + hand tracking
├── segmentation/           # Person segmentation (Shadow Clone)
├── input/                  # Webcam capture
├── utils/                  # Image + math helpers
├── assets/                 # Sprite images
└── models/                 # MediaPipe .task files (auto-downloaded)
```

## ⚙️ Tech Stack

- **MediaPipe** — Pose & hand landmark detection
- **OpenCV** — Webcam capture & image compositing
- **Flask** — Backend server + MJPEG video streaming
- **Vanilla JS + HTML/CSS** — Frontend UI
