```

## 📜 `README.md`

```markdown
# 🎬 Stargold Proxy (SOCKS5 Reverse Proxy for .m3u8)

This project is a lightweight **reverse proxy** that fetches `.m3u8` video playlists through a **SOCKS5 proxy** and re-serves them via a Rails/Heroku‑style app URL for media players. Perfect for hosting on **Railway.app**.

---

## 🚀 Features
- Fetches playlists via SOCKS5 proxy
- Routes through Railway’s HTTPS endpoint
- Supports channel switching by changing the `{channel_id}`
- .m3u8‑friendly URLs so IPTV players accept them
- Simple, lightweight (no heavy frameworks)

---

## 📂 Project Structure
```
├── server.py         # Main aiohttp reverse proxy app
├── requirements.txt  # Dependencies
├── Procfile          # Start command for Railway/Heroku
├── .gitignore        # Ignore local cruft
└── README.md         # Documentation (this file)
```

---

## ⚡️ Deployment on Railway

### 1. Push to GitHub
Create a new repo and push this folder:

```bash
git init
git add .
git commit -m "Initial commit: add Stargold Proxy"
git branch -M main
git remote add origin https://github.com/yourname/stargold-proxy.git
git push -u origin main
```

### 2. Create Railway Project
- Go to [Railway](https://railway.app)
- Create new project → Deploy from GitHub
- Select your repo

### 3. Add Environment Variable
- In Railway dashboard → Variables → Add:
  - `SOCKS_PROXY=socks5://USER:PASS@HOST:PORT`

Example from your notes:
```
socks5://bdiix_bypass:bdiix_bypass@circle.bypassempire.com:1080
```

### 4. Done! 🎉
Railway builds & starts your project. It’ll give you a URL like:

```
https://your-app-name.up.railway.app
```

---

## 🔧 Usage
To fetch a channel’s playlist:

```
https://your-app-name.up.railway.app/stream/stargoldhd.m3u8
```

Swap `stargoldhd` with the desired channel ID:
```
https://your-app-name.up.railway.app/stream/{channel_id}.m3u8
```

Your favorite IPTV player (VLC, ffmpeg, Kodi, OTT Navigator, etc.) will happily accept this.

---

## 🧩 Next Steps
- Add segment proxying so `.ts` files also route through SOCKS5 (currently only index `.m3u8` is proxied).
- Add caching or error handling for long-term use.
- Monitor Railway usage: free tier bandwidth is limited.

---

💡 Think of this as your “m3u8 costume shop” — whatever channel you dress up, your IPTV player politely accepts, none the wiser.
```

---

That’s a **complete GitHub repo snapshot** with a friendly `README.md` explaining everything.  

Would you like me to extend this so that *TS segment files* (`.ts`) are also proxied, instead of just the main `.m3u8` playlist? Right now, playlists go through the proxy but players still fetch segments from the origin directly.
