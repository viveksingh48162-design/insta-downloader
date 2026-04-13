from flask import Flask, request, jsonify, render_template, send_from_directory
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
    if not name:
        return "video"
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


def is_short(url):
    return (
        "instagram.com" in url
        or "youtube.com/shorts/" in url
        or "youtu.be/" in url
    )


def safe_extract(url):
    url = fix_url(url)

    for i in range(3):
        try:
            ydl_opts = {
                "quiet": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Android)"
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        except:
            time.sleep(1)

    return None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "Video not found"})

    return jsonify({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "is_short": is_short(url)
    })


@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "Formats not found"})

    # 🔥 SHORT MODE → no quality
    if is_short(url):
        return jsonify({
            "short": True
        })

    allowed = [360, 720, 1080, 2160]
    video = []
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


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")

    info = safe_extract(url)

    if not info:
        return jsonify({"error": "Download failed"})

    safe_title = clean_filename(info.get("title"))

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/{safe_title}.%(ext)s",
        "quiet": True
    }

    # 🎧 AUDIO
    if type_ == "audio":
        ydl_opts.update({
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3"
            }]
        })

    # 🎥 VIDEO
    else:
        if is_short(url):
            ydl_opts.update({
                "format": "best"
            })
        else:
            ydl_opts.update({
                "format": f"{format_id}+bestaudio/best"
            })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    filename = safe_title + (".mp3" if type_ == "audio" else ".mp4")

    return jsonify({
        "download_url": f"/downloads/{filename}"
    })


@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
