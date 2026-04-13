from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import re
import subprocess

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# 🔥 CLEAN FILE NAME
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# 🔥 FIX YOUTUBE SHORTS
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


# 🔥 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 🔥 CHECK FFMPEG
@app.route("/check_ffmpeg")
def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return "<pre>" + result.stdout + "</pre>"
    except Exception as e:
        return str(e)


# 🎬 GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")
    url = fix_url(url)

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_short": info.get("duration", 0) < 60,
            "is_insta": "instagram.com" in url
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎯 GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")
    url = fix_url(url)

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        # 🔥 SHORT / REEL / INSTA = SIMPLE
        if info.get("duration", 0) < 60 or "instagram.com" in url:
            return jsonify({
                "video": [{"format_id": "best", "quality": "MP4"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        # 🔥 LONG VIDEO = LIMITED QUALITY
        video = []
        audio = [{"format_id": "bestaudio", "quality": "MP3"}]

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
            "video": sorted(video, key=lambda x: int(x["quality"].replace("p", ""))),
            "audio": audio
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🚀 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = fix_url(data.get("url"))
    format_id = data.get("format_id")
    type_ = data.get("type")
    mode = data.get("mode")

    try:
        filename = clean_filename(str(os.urandom(6).hex()))

        # ⚡ FAST MODE
        if mode == "fast":
            ydl_opts = {
                "format": format_id,
                "quiet": True
            }

        # 🔥 TURBO MODE (ffmpeg use)
        else:
            if type_ == "audio":
                ydl_opts = {
                    "format": "bestaudio",
                    "outtmpl": f"{DOWNLOAD_FOLDER}/{filename}.%(ext)s",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3"
                    }],
                    "quiet": True
                }
            else:
                ydl_opts = {
                    "format": f"{format_id}+bestaudio/best",
                    "outtmpl": f"{DOWNLOAD_FOLDER}/{filename}.%(ext)s",
                    "merge_output_format": "mp4",
                    "quiet": True
                }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # ⚡ FAST MODE → direct URL
        if mode == "fast":
            return jsonify({
                "download_url": info.get("url")
            })

        # 🔥 TURBO MODE → file download
        ext = "mp3" if type_ == "audio" else "mp4"
        return jsonify({
            "download_url": f"/downloads/{filename}.{ext}"
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 📁 SERVE FILE
@app.route("/downloads/<path:filename>")
def serve_file(filename):
    from flask import send_from_directory
    return send_from_directory(DOWNLOAD_FOLDER, filename)


# 🔥 RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
