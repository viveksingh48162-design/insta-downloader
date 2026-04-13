from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


# 🔥 ADVANCED CONFIG
def get_opts(format_id=None):
    opts = {
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },

        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios"]
            }
        },

        "age_limit": 99
    }

    # 🔥 FORMAT LOGIC
    if format_id == "bestaudio":
        opts["format"] = "bestaudio"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    elif format_id:
        opts["format"] = format_id
    else:
        opts["format"] = "best[ext=mp4]/best"

    return opts


# 🔁 SAFE RETRY SYSTEM
def safe_extract(url, download=False, format_id=None, outtmpl=None):
    url = fix_url(url)

    for _ in range(3):
        try:
            opts = get_opts(format_id)

            if download:
                opts["outtmpl"] = outtmpl

            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=download)

        except Exception as e:
            print("Retry:", e)
            time.sleep(1)

    return None


@app.route("/")
def home():
    return render_template("index.html")


# 🎬 VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "❌ YouTube blocked / Try another video"})

    return jsonify({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "is_short": info.get("duration", 0) < 60,
        "is_insta": "instagram.com" in url
    })


# 🎯 FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "❌ Failed to fetch formats"})

    # INSTAGRAM + SHORTS
    if "instagram.com" in url or info.get("duration", 0) < 60:
        return jsonify({
            "video": [{"format_id": "best", "quality": "MP4"}],
            "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
        })

    # YOUTUBE LONG
    video = []
    allowed = [360, 720, 1080, 2160]
    seen = set()

    for f in info.get("formats", []):
        h = f.get("height")

        if f.get("vcodec") != "none" and h in allowed:
            if h not in seen:
                seen.add(h)
                video.append({
                    "format_id": f.get("format_id"),
                    "quality": f"{h}p"
                })

    return jsonify({
        "video": video,
        "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
    })


# 🚀 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")

    filename = clean_filename(str(os.urandom(6).hex()))

    info = safe_extract(
        url,
        download=True,
        format_id=format_id,
        outtmpl=f"{DOWNLOAD_FOLDER}/{filename}.%(ext)s"
    )

    if not info:
        return jsonify({"error": "❌ Download failed"})

    ext = "mp3" if format_id == "bestaudio" else "mp4"

    return send_file(f"{DOWNLOAD_FOLDER}/{filename}.{ext}", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
