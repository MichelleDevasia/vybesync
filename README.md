# VibeSync AI Studio: Premium Interactive Karaoke Deck

A retro-futuristic single-page interactive music box and karaoke separation deck. It simulates a vintage cassette/CD player dashboard with glowing LEDs, analog knobs, animated tape reels, and tactile CD loaders.

---

## 🕹️ Interactive Features

1. **Vintage Cassette Slot**: Loading and generating songs animates a cassette tape sliding in, rotating, and processing with glowing lights and rotating gears.
2. **CD Eject Mechanism**: On complete processing, a custom-designed CD with the song's artwork and title slides out from the tray.
3. **Immersive Karaoke Studio**: Clicking the CD triggers a transition loading it into a spinning vinyl record player with volume mixer tracks for Vocals and Instrumental stems.
4. **Interactive CD Shelf**: Hovering over shelf CDs pulls them out of the cabinet with 3D shadow and glow elements.
5. **Canvas Visualizer**: Draws a real-time glowing audio spectrum waveform dynamically during playback.
6. **Animated Lyric Tracking**: Synchronizes and auto-scrolls lyrics matching playback time.

---

## 🚀 Quick Start (Local Setup)

1. Make sure you have **FFmpeg** installed on your system.
2. Setup the virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   python app.py
   ```
4. Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🌎 Production Deployment

### Backend (Render)
1. Link your repository to **Render.com**.
2. Deploy a **Web Service** using `render.yaml` configurations:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
3. Add the `GENIUS_TOKEN` key in settings.

### Frontend (Vercel)
1. Import your repository in **Vercel**.
2. Vercel will auto-detect `vercel.json` and deploy `frontend/` as a high-speed static frontend.
3. Modify the proxy target domain in `vercel.json` to map to your live Render endpoint.
