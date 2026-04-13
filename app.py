from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# ✅ HOME
@app.route("/")
def home():
    return render_template("index.html")


# ✅ GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "geo_bypass": True,
            "extract_flat": False
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"error": "❌ Video fetch failed"})

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_insta": "instagram.com" in url
        })

    except Exception as e:
        return jsonify({"error": f"❌ Error: {str(e)}"})


# ✅ GET FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "geo_bypass": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({"error": "❌ Cannot fetch formats"})

        # 🔥 INSTAGRAM SIMPLE
        if "instagram.com" in url:
            return jsonify({
                "short": True,
                "video": [{"format_id": "best", "quality": "HD"}],
                "audio": [{"format_id": "bestaudio", "quality": "MP3"}]
            })

        video = []
        audio = []

        seen = set()
        allowed = [360, 480, 720, 1080]

        for f in info.get("formats", []):
            h = f.get("height")

            # 🎬 VIDEO
            if f.get("vcodec") != "none" and h in allowed:
                if h not in seen:
                    seen.add(h)
                    video.append({
                        "format_id": f.get("format_id"),
                        "quality": f"{h}p"
                    })

            # 🎧 AUDIO
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
            "short": False,
            "video": video,
            "audio": audio
        })

    except Exception as e:
        return jsonify({"error": f"❌ Format error: {str(e)}"})


# ✅ DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")

    try:
        filename = str(uuid.uuid4()) + ".mp4"

        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, filename),
            "quiet": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "geo_bypass": True
        }

        # 🎧 AUDIO FIX (IMPORTANT)
        if type_ == "audio":
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            ydl_opts["format"] = format_id

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({
            "download_url": f"/file/{filename}"
        })

    except Exception as e:
        return jsonify({"error": f"❌ Download failed: {str(e)}"})


# ✅ SERVE FILE
@app.route("/file/<filename>")
def serve_file(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    return send_file(path, as_attachment=True)


# ✅ RUN
if __name__ == "__main__":
    app.run(debug=True)
