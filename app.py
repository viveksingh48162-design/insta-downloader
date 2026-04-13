from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# CLEAN FILE NAME
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


# FIX YOUTUBE SHORTS URL
def fix_url(url):
    if "youtube.com/shorts/" in url:
        vid = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url


@app.route("/")
def home():
    return render_template("index.html")


# GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")
    url = fix_url(url)

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0"
            },
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_insta": "instagram.com" in url
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")
    url = fix_url(url)

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0"
            },
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            }
        }) as ydl:
            info = ydl.extract_info(url, download=False)

        # INSTAGRAM SIMPLE
        if "instagram.com" in url:
            return jsonify({
                "video": [{"format_id": "best", "quality": "HD"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        video = []
        audio = []

        allowed = [360, 720, 1080, 2160]
        seen = set()

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
                    "quality": "MP3"
                })

        return jsonify({
            "video": video,
            "audio": audio
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    format_id = request.json.get("format_id")

    url = fix_url(url)

    try:
        ydl_opts = {
            "format": format_id if format_id else "best[ext=mp4]",
            "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            "quiet": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0"
            },
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
