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


# 🔥 CLEAN NAME
def clean_filename(name):
    if not name:
        return "video"
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# 🔥 FIX SHORTS
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


# 🔥 SAFE EXTRACT
def safe_extract(url):
    url = fix_url(url)

    for i in range(3):
        try:
            ydl_opts = {
                "quiet": True,
                "noplaylist": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10)"
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info:
                    return info

        except Exception as e:
            print("Retry:", e)
            time.sleep(1)

    return None


# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 🎬 GET VIDEO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        info = safe_extract(url)

        if not info:
            return jsonify({"error": "Video not found"})

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail")
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎚️ GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        info = safe_extract(url)

        if not info:
            return jsonify({"error": "Formats not found"})

        video = []
        audio = []
        seen = set()

        # 🔥 Instagram simple
        if "instagram.com" in url:
            return jsonify({
                "video": [{"format_id": "best", "quality": "HD"}],
                "audio": []
            })

        for f in info.get("formats", []):
            h = f.get("height")

            # 🎥 VIDEO
            if f.get("vcodec") != "none" and h:
                if h not in seen:
                    seen.add(h)
                    video.append({
                        "format_id": f.get("format_id"),
                        "quality": f"{h}p"
                    })

            # 🎧 AUDIO
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                audio.append({
                    "format_id": f.get("format_id"),
                    "quality": f"{int(f.get('abr') or 128)} kbps"
                })

        return jsonify({"video": video, "audio": audio})

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

        if not info:
            return jsonify({"error": "Download failed"})

        safe_title = clean_filename(info.get("title"))

        # ⚡ FAST MODE (DIRECT LINK)
        if mode == "fast":
            for f in info.get("formats", []):
                if f.get("format_id") == format_id:
                    return jsonify({
                        "download_url": f.get("url")
                    })

            return jsonify({"error": "Fast link not found"})

        # 🔥 TURBO MODE (DOWNLOAD FILE)
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
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            })

        # 🎥 VIDEO
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


# 📥 SERVE FILE
@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
