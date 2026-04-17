from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os
import uuid
import imageio_ffmpeg

app = Flask(__name__)

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 yt_dlp base config
def get_ydl_opts():
    return {
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'cookiefile': 'cookies.txt'
    }


@app.route("/")
def home():
    return render_template("index.html")


# 🎯 VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_short": "shorts" in url,
            "is_social": any(x in url for x in ["instagram","facebook"])
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎯 FORMATS
@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.json.get("url")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
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


# 🚀 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        # ⚡ SHORTS / REELS (DIRECT)
        if "shorts" in url or any(x in url for x in ["instagram","facebook"]):
            
            video_url = info.get("url")

            # 🔥 fallback
            if not video_url:
                for f in info.get("formats", []):
                    if f.get("url"):
                        video_url = f.get("url")
                        break

            if not video_url:
                return jsonify({"error": "No direct video URL found"})

            return jsonify({
                "type": "direct",
                "url": video_url
            })

        # 🎬 YOUTUBE LONG DOWNLOAD
        file_id = str(uuid.uuid4())
        output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

        ydl_opts = {
            'format': format_id if format_id else 'bestvideo+bestaudio/best',
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_path,
            **get_ydl_opts()
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
