from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os
import uuid
import imageio_ffmpeg

app = Flask(__name__)

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def base_opts():
    return {
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'cookiefile': 'cookies.txt'
    }


@app.route("/")
def home():
    return render_template("index.html")


# 🔍 GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_short": "shorts" in url,
            "is_social": any(x in url for x in ["instagram","facebook"])
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎬 GET FORMATS (ONLY TURBO)
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get("formats", []):
            if f.get("vcodec") != "none" and f.get("height"):
                formats.append({
                    "format_id": f["format_id"],
                    "quality": f"{f['height']}p"
                })

        return jsonify({"video": formats[:8]})

    except Exception as e:
        return jsonify({"error": str(e)})


# 🚀 DOWNLOAD SYSTEM
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    type_ = data.get("type")
    mode = data.get("mode")  # fast / turbo

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        # ⚡ FAST MODE (ULTRA)
        if mode == "fast":

            # 🎧 AUDIO DIRECT
            if type_ == "audio":
                for f in info.get("formats", []):
                    if f.get("acodec") != "none" and f.get("vcodec") == "none":
                        return jsonify({
                            "type": "direct",
                            "url": f.get("url")
                        })

            # 🎬 VIDEO DIRECT
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("url"):
                    return jsonify({
                        "type": "direct",
                        "url": f.get("url")
                    })

        # ⚡ SHORTS / REELS
        if "shorts" in url or any(x in url for x in ["instagram","facebook"]):
            return jsonify({
                "type": "direct",
                "url": info.get("url")
            })

        # 🚀 TURBO MODE (FULL PROCESS)
        file_id = str(uuid.uuid4())

        # 🎬 VIDEO
        if type_ == "video":
            output = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

            ydl_opts = {
                'format': f"{format_id}+bestaudio/best",
                'outtmpl': output,
                'merge_output_format': 'mp4',
                'ffmpeg_location': ffmpeg_path,
                **base_opts()
            }

        # 🎧 AUDIO
        else:
            output = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': output,
                'ffmpeg_location': ffmpeg_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                **base_opts()
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({
            "type": "file",
            "file": file_id,
            "ext": "mp3" if type_ == "audio" else "mp4"
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/file/<file_id>/<ext>")
def serve_file(file_id, ext):
    path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.{ext}")

    if os.path.exists(path):
        return send_file(path, as_attachment=True)

    return "File not found"


if __name__ == "__main__":
    app.run(debug=True)
