from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid
import imageio_ffmpeg as ffmpeg

app = Flask(__name__)

# ✅ FFmpeg auto path
FFMPEG_PATH = ffmpeg.get_ffmpeg_exe()

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🚀 FAST TURBO CONFIG
def get_ydl_opts():
    return {
        "quiet": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "geo_bypass": True,
        "ffmpeg_location": FFMPEG_PATH,
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    }

# 🔍 AUTO FETCH INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    if not url:
        return jsonify({"error": "No URL"})

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"error": "Fetch failed"})

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "is_insta": "instagram.com" in url
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🎯 GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        video = []
        audio = []
        seen = set()

        for f in info.get("formats", []):
            h = f.get("height")

            if f.get("vcodec") != "none" and h:
                if h not in seen:
                    seen.add(h)
                    video.append({
                        "format_id": f.get("format_id"),
                        "quality": f"{h}p"
                    })

            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                audio.append({
                    "format_id": f.get("format_id"),
                    "quality": "MP3"
                })

        if not video:
            video = [{"format_id": "best", "quality": "Auto"}]

        if not audio:
            audio = [{"format_id": "bestaudio", "quality": "MP3"}]

        return jsonify({
            "video": video,
            "audio": audio
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# ⬇️ DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")

    try:
        filename = str(uuid.uuid4())

        ydl_opts = get_ydl_opts()
        ydl_opts["outtmpl"] = os.path.join(DOWNLOAD_FOLDER, filename + ".%(ext)s")

        # 🎵 AUDIO FIX (FFmpeg required)
        if type_ == "audio":
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        else:
            ydl_opts["format"] = format_id or "best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({
            "download_url": f"/file/{filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 📂 SERVE FILE
@app.route("/file/<filename>")
def serve_file(filename):
    for ext in ["mp4", "mp3", "mkv", "webm"]:
        path = os.path.join(DOWNLOAD_FOLDER, f"{filename}.{ext}")
        if os.path.exists(path):
            return send_file(path, as_attachment=True)

    return "File not found"

# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
