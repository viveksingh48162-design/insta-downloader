from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import uuid

app = Flask(__name__)

# 🔥 folder create
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 storage
downloads = {}
progress_data = {"percent": 0, "speed": "0 KB/s", "status": "idle"}

# -------------------------
# 🔥 PROGRESS HOOK
# -------------------------
def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            percent = float(d.get('_percent_str', '0').replace('%', '').strip())
            speed = d.get('_speed_str', '0 KB/s')

            progress_data["percent"] = percent
            progress_data["speed"] = speed
            progress_data["status"] = "downloading"
        except:
            pass

    elif d['status'] == 'finished':
        progress_data["percent"] = 100
        progress_data["status"] = "finished"


# -------------------------
# 🔥 HOME
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------------
# 🔥 GET VIDEO INFO
# -------------------------
@app.route("/info", methods=["POST"])
def info():

    url = request.json["url"]

    try:
        ydl_opts = {'quiet': True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        formats = []

        # 🔥 only for youtube
        if "youtube" in url or "youtu" in url:
            for f in data.get("formats", []):
                if f.get("height"):
                    formats.append({
                        "format_id": f["format_id"],
                        "quality": f"{f['height']}p"
                    })

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "platform": "youtube" if "youtu" in url else "instagram",
            "formats": formats
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# -------------------------
# 🔥 DOWNLOAD
# -------------------------
@app.route("/download", methods=["POST"])
def download():

    data = request.json
    url = data["url"]
    type_ = data["type"]
    format_id = data.get("format_id", "best")

    file_id = str(uuid.uuid4())

    try:
        progress_data["percent"] = 0
        progress_data["speed"] = "0 KB/s"

        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/{file_id}.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True
        }

        # 🔥 MP3
        if type_ == "mp3":
            ydl_opts.update({
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }]
            })
        else:
            ydl_opts['format'] = format_id if format_id else "best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # 🔥 fix extension
        if type_ == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        downloads[file_id] = filename

        return jsonify({"id": file_id})

    except Exception as e:
        return jsonify({"error": str(e)})


# -------------------------
# 🔥 PROGRESS API
# -------------------------
@app.route("/progress")
def progress():
    return jsonify(progress_data)


# -------------------------
# 🔥 FILE DOWNLOAD
# -------------------------
@app.route("/file")
def file():

    file_id = request.args.get("id")

    if file_id not in downloads:
        return "File not found", 404

    path = downloads[file_id]

    if not os.path.exists(path):
        return "File missing", 404

    return send_file(path, as_attachment=True)


# -------------------------
# 🔥 RUN (RENDER FIX)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
