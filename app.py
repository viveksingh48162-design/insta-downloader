from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os
import uuid
import imageio_ffmpeg
import random

app = Flask(__name__)

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 ADD YOUR PROXIES HERE
PROXIES = [
    "http://username:password@ip:port",
    # add more proxies
]

def get_proxy():
    if PROXIES:
        return random.choice(PROXIES)
    return None


# 🔥 UNIVERSAL EXTRACT FUNCTION
def extract_info_ultra(url):
    configs = [
        # 1️⃣ Normal
        {'quiet': True},

        # 2️⃣ Android client
        {
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android']}}
        },

        # 3️⃣ Proxy
        {
            'quiet': True,
            'proxy': get_proxy()
        },

        # 4️⃣ Proxy + Android
        {
            'quiet': True,
            'proxy': get_proxy(),
            'extractor_args': {'youtube': {'player_client': ['android']}}
        },

        # 5️⃣ Proxy + Cookies (BEST)
        {
            'quiet': True,
            'proxy': get_proxy(),
            'cookiefile': 'cookies.txt',
            'extractor_args': {'youtube': {'player_client': ['android']}}
        }
    ]

    for cfg in configs:
        try:
            with yt_dlp.YoutubeDL(cfg) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            print("Retrying with next config...")

    return None


@app.route("/")
def home():
    return render_template("index.html")


# 🎯 VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    info = extract_info_ultra(url)

    if not info:
        return jsonify({"error": "Failed to fetch video (blocked by YouTube)"})

    return jsonify({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "is_short": "shorts" in url,
        "is_social": any(x in url for x in ["instagram","facebook"])
    })


# 🎯 FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    info = extract_info_ultra(url)

    if not info:
        return jsonify({"error": "Failed to fetch formats"})

    formats = []
    for f in info.get("formats", []):
        if f.get("vcodec") != "none" and f.get("height"):
            formats.append({
                "format_id": f["format_id"],
                "quality": f"{f['height']}p"
            })

    return jsonify({"video": formats[:8]})


# 🚀 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")

    try:
        # ⚡ SHORTS / REELS (FAST)
        if "shorts" in url or any(x in url for x in ["instagram","facebook"]):
            info = extract_info_ultra(url)
            return jsonify({
                "type": "direct",
                "url": info.get("url")
            })

        # 🎬 YOUTUBE LONG
        file_id = str(uuid.uuid4())
        output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

        ydl_opts = {
            'format': format_id if format_id else 'bestvideo+bestaudio/best',
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_path,
            'proxy': get_proxy(),
            'cookiefile': 'cookies.txt',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({
            "type": "file",
            "file": file_id
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 📁 FILE SERVE
@app.route("/file/<file_id>")
def serve_file(file_id):
    path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found"


if __name__ == "__main__":
    app.run(debug=True)
