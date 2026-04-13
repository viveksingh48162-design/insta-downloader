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

# 🔥 CLEAN FILE NAME
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# 🔥 COOKIE ROTATION
def get_cookie():
    try:
        files = os.listdir("cookies")
        return os.path.join("cookies", random.choice(files))
    except:
        return None


# 🔥 SAFE EXTRACT (ANTI BLOCK)
def safe_extract(url):
    for i in range(5):
        try:
            ydl_opts = {
                "quiet": True,
                "cookiefile": get_cookie(),
                "noplaylist": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0"
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        except Exception as e:
            print("Retry:", e)
            time.sleep(2)

    return None


# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 📺 GET VIDEO (thumbnail + title)
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        info = safe_extract(url)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_insta": "instagram.com" in url
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎬 GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        info = safe_extract(url)

        video = []
        audio = []
        allowed = [360, 720, 1080, 2160]
        seen = set()

        # 🔥 INSTAGRAM SIMPLE
        if "instagram.com" in url:
            return jsonify({
                "video": [{"format_id": "best", "quality": "HD"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        # 🎥 YOUTUBE
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

    except Exception as e:
        return jsonify({"error": str(e)})


# 🚀 DOWNLOAD (FAST + TURBO)
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")
    mode = data.get("mode")

    try:
        info = safe_extract(url)
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
            "cookiefile": get_cookie(),
        }

        # AUDIO
        if type_ == "audio":
            ydl_opts.update({
                "format": "bestaudio",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            })

        # VIDEO
        else:
            if "instagram.com" in url:
                ydl_opts.update({
                    "format": "best",
                    "merge_output_format": "mp4"
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

    except Exception as e:
        return jsonify({"error": str(e)})


# 📂 SERVE FILE
@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
