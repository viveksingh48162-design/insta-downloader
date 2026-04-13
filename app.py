from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import re
import random
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 CLEAN NAME
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# 🔥 FIX SHORTS
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


# 🔥 COOKIE ROTATION
def get_cookie():
    try:
        files = os.listdir("cookies")
        if not files:
            return None
        return os.path.join("cookies", random.choice(files))
    except:
        return None


# 🔥 USER AGENT ROTATION
def get_headers():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0",
            "Chrome/120.0",
            "Safari/537.36"
        ])
    }


# 🔥 SAFE EXTRACT (CORE)
def safe_extract(url):
    url = fix_url(url)

    for i in range(5):
        try:
            ydl_opts = {
                "quiet": True,
                "cookiefile": get_cookie(),
                "noplaylist": True,
                "http_headers": get_headers()
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info:
                    return info

        except Exception as e:
            print("Retry:", e)
            time.sleep(random.uniform(1, 3))

    return None


# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 📺 VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "❌ Failed (blocked or cookies needed)"})

    return jsonify({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "is_insta": "instagram.com" in url
    })


# 🎬 FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "❌ Cannot fetch formats"})

    video = []
    audio = []
    seen = set()
    allowed = [360, 720, 1080, 2160]

    if "instagram.com" in url:
        return jsonify({
            "video": [{"format_id": "best", "quality": "HD"}],
            "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
        })

    for f in info.get("formats", []):
        h = f.get("height")

        # VIDEO
        if f.get("vcodec") != "none" and h in allowed:
            if h not in seen:
                seen.add(h)
                video.append({
                    "format_id": f.get("format_id"),
                    "quality": f"{h}p"
                })

        # AUDIO
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            audio.append({
                "format_id": f.get("format_id"),
                "quality": f"{int(f.get('abr') or 128)} kbps"
            })

    return jsonify({
        "video": video,
        "audio": audio
    })


# 🚀 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json

    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")
    mode = data.get("mode")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "❌ Download failed"})

    safe_title = clean_filename(info.get("title"))

    # ⚡ FAST MODE
    if mode == "fast":
        for f in info.get("formats"):
            if f.get("format_id") == format_id:
                return jsonify({
                    "download_url": f.get("url")
                })

        return jsonify({"error": "Fast link not found"})

    # 🔥 TURBO MODE
    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/{safe_title}.%(ext)s",
        "quiet": True,
        "cookiefile": get_cookie()
    }

    if type_ == "audio":
        ydl_opts.update({
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3"
            }]
        })

    else:
        ydl_opts.update({
            "format": f"{format_id}+bestaudio/best",
            "merge_output_format": "mp4"
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    filename = safe_title + (".mp3" if type_ == "audio" else ".mp4")

    return jsonify({
        "download_url": f"/downloads/{filename}"
    })


# 📂 SERVE
@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
