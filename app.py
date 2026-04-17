from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os, uuid, threading
import imageio_ffmpeg

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

# 📊 progress store
progress_data = {}

# 🔧 base config
def base_opts():
    return {
        'quiet': True,
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }

# 🏠 HOME
@app.route("/")
def home():
    return render_template("index.html")

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
            "is_short": "shorts" in url,
            "is_social": any(x in url for x in ["instagram","facebook"])
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🎬 GET FORMATS (QUALITY)
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

        return jsonify({"video": formats[:10]})

    except Exception as e:
        return jsonify({"error": str(e)})

# 📥 DOWNLOAD THREAD (TURBO)
def download_thread(url, format_id, type_, file_id):

    def hook(d):
        if d['status'] == 'downloading':
            percent = d.get("_percent_str","0%").replace("%","").strip()
            try:
                progress_data[file_id] = int(float(percent))
            except:
                progress_data[file_id] = 0
        elif d['status'] == 'finished':
            progress_data[file_id] = 100

    try:
        if type_ == "video":
            path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

            ydl_opts = {
                'format': f"{format_id}+bestaudio/best",
                'outtmpl': path,
                'merge_output_format': 'mp4',
                'ffmpeg_location': ffmpeg_path,
                'progress_hooks': [hook],
                **base_opts()
            }

        else:
            path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': path,
                'ffmpeg_location': ffmpeg_path,
                'progress_hooks': [hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                **base_opts()
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        progress_data[file_id] = -1


# 🚀 DOWNLOAD API
@app.route("/download", methods=["POST"])
def download():
    data = request.json

    url = data.get("url")
    type_ = data.get("type")      # video / audio
    mode = data.get("mode")      # fast / turbo
    format_id = data.get("format_id")

    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        # ⚡ FAST MODE (DIRECT)
        if mode == "fast":

            # 🎧 MP3 direct
            if type_ == "audio":
                for f in info.get("formats", []):
                    if f.get("vcodec") == "none" and f.get("acodec") != "none":
                        return jsonify({"type":"direct","url":f.get("url")})

            # 🎬 MP4 direct
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("url"):
                    return jsonify({"type":"direct","url":f.get("url")})

        # 📱 SHORTS / REELS DIRECT
        if "shorts" in url or any(x in url for x in ["instagram","facebook"]):
            return jsonify({"type":"direct","url":info.get("url")})

        # 🚀 TURBO MODE (DOWNLOAD + PROCESS)
        file_id = str(uuid.uuid4())
        progress_data[file_id] = 0

        threading.Thread(
            target=download_thread,
            args=(url, format_id, type_, file_id)
        ).start()

        return jsonify({
            "type": "progress",
            "file": file_id,
            "ext": "mp3" if type_=="audio" else "mp4"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 📊 PROGRESS
@app.route("/progress/<file_id>")
def progress(file_id):
    return jsonify({"progress": progress_data.get(file_id, 0)})

# 📁 FILE SERVE
@app.route("/file/<file_id>/<ext>")
def serve_file(file_id, ext):
    path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.{ext}")

    if os.path.exists(path):
        return send_file(path, as_attachment=True)

    return "File not found"


# ▶ RUN
if __name__ == "__main__":
    app.run(debug=True)
