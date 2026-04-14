from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp, os, uuid
import imageio_ffmpeg as ffmpeg

app = Flask(__name__)

FFMPEG_PATH = ffmpeg.get_ffmpeg_exe()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def base_opts():
    return {
        "quiet": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "geo_bypass": True,
        "ffmpeg_location": FFMPEG_PATH,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        }
    }

# 🔍 VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_short": info.get("duration", 0) < 60,
            "is_social": any(x in url for x in ["instagram.com","facebook.com"])
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 📦 FORMATS (ONLY YT LONG)
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        video, seen = [], set()

        for f in info.get("formats", []):
            h = f.get("height")

            if f.get("vcodec") != "none" and h:
                if h not in seen:
                    seen.add(h)
                    video.append({
                        "format_id": f.get("format_id"),
                        "quality": f"{h}p"
                    })

        return jsonify({"video": video})

    except Exception as e:
        return jsonify({"error": str(e)})

# ⬇️ DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    mode = data.get("mode")
    format_id = data.get("format_id")
    type_ = data.get("type")
    bitrate = data.get("bitrate", "192")

    try:
        filename = str(uuid.uuid4())
        path = os.path.join(DOWNLOAD_FOLDER, filename + ".%(ext)s")

        ydl_opts = base_opts()
        ydl_opts["outtmpl"] = path

        # ⚡ FAST
        if mode == "fast":
            if type_ == "audio":
                ydl_opts["format"] = "bestaudio"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate
                }]
            else:
                ydl_opts["format"] = "best"

        # 🚀 TURBO
        else:
            if type_ == "audio":
                ydl_opts["format"] = "bestaudio"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate
                }]
            else:
                ydl_opts["format"] = format_id or "best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({"download_url": f"/file/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/file/<filename>")
def file(filename):
    for ext in ["mp4","mp3","webm","mkv"]:
        path = os.path.join(DOWNLOAD_FOLDER, f"{filename}.{ext}")
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    return "File not found"

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
