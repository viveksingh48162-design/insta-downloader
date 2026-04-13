from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# CLEAN NAME
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# FIX SHORTS
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


# 🔥 COMMON YTDLP OPTIONS (NO COOKIES BEST FIX)
def get_opts():
    return {
        "quiet": True,
        "noplaylist": True,
        "format": "best[ext=mp4]/best",
        "geo_bypass": True,
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": "com.google.android.youtube/17.31.35 (Linux; Android 11)"
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "skip": ["dash", "hls"]
            }
        }
    }


@app.route("/")
def home():
    return render_template("index.html")


# 📌 GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = fix_url(request.json.get("url"))

    try:
        with yt_dlp.YoutubeDL(get_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_insta": "instagram.com" in url,
            "is_short": "shorts" in url or info.get("duration", 0) < 60
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 📌 GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = fix_url(request.json.get("url"))

    try:
        with yt_dlp.YoutubeDL(get_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        # 🔥 INSTAGRAM (NO QUALITY)
        if "instagram.com" in url:
            return jsonify({
                "video": [{"format_id": "best", "quality": "MP4"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        # 🔥 YOUTUBE SHORTS (NO QUALITY)
        if "shorts" in url or info.get("duration", 0) < 60:
            return jsonify({
                "video": [{"format_id": "best", "quality": "MP4"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        # 🔥 YOUTUBE LONG VIDEO (LIMITED QUALITY)
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

    except Exception as e:
        return jsonify({"error": str(e)})


# 📌 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    url = fix_url(request.json.get("url"))
    format_id = request.json.get("format_id")

    try:
        opts = get_opts()
        opts["outtmpl"] = f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s"

        # 🔥 FAST MODE (NO FFMPEG)
        if format_id == "best" or format_id is None:
            opts["format"] = "best[ext=mp4]/best"
        else:
            opts["format"] = format_id

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
