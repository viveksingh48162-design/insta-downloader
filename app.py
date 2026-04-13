from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔹 clean filename
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name or "video")

# 🔹 fix shorts → watch URL
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url

# 🔹 detect short content
def is_short(url):
    return (
        "instagram.com" in url or
        "youtu.be" in url or
        "shorts" in url
    )

# 🔹 base yt-dlp options (ANTI BLOCK 🔥)
def base_opts():
    return {
        "quiet": True,
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    }

# 🔹 HOME
@app.route("/")
def home():
    return render_template("index.html")

# 🔹 GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = fix_url(request.json.get("url"))

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔹 GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = fix_url(request.json.get("url"))

    try:
        # 🔥 SHORT → no quality, direct options
        if is_short(url):
            return jsonify({"short": True})

        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

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
            "short": False,
            "video": video
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔹 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = fix_url(data.get("url"))
    format_id = data.get("format_id")
    type_ = data.get("type")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        title = clean_filename(info.get("title"))

        # 🔥 AUDIO (MP3)
        if type_ == "audio":
            ydl_opts = {
                **base_opts(),
                "outtmpl": f"{DOWNLOAD_FOLDER}/{title}.%(ext)s",
                "format": "bestaudio",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            }

        # 🔥 VIDEO
        else:
            if is_short(url):
                ydl_opts = {
                    **base_opts(),
                    "outtmpl": f"{DOWNLOAD_FOLDER}/{title}.%(ext)s",
                    "format": "best",
                    "merge_output_format": "mp4"
                }
            else:
                ydl_opts = {
                    **base_opts(),
                    "outtmpl": f"{DOWNLOAD_FOLDER}/{title}.%(ext)s",
                    "format": f"{format_id}+bestaudio/best",
                    "merge_output_format": "mp4"
                }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        ext = "mp3" if type_ == "audio" else "mp4"

        return jsonify({
            "download_url": f"/file/{title}.{ext}"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔹 SERVE FILE
@app.route("/file/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
