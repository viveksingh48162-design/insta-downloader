from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

downloads = {}

@app.route("/")
def home():
    return render_template("index.html")

# 🔥 GET VIDEO INFO
@app.route("/info", methods=["POST"])
def info():
    url = request.json["url"]

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            data = ydl.extract_info(url, download=False)

        formats = []

        if "youtube" in url:
            for f in data.get("formats", []):
                if f.get("height"):
                    formats.append({
                        "format_id": f["format_id"],
                        "quality": f"{f['height']}p"
                    })

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats,
            "platform": "youtube" if "youtu" in url else "instagram"
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔥 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data["url"]
    type_ = data["type"]
    format_id = data.get("format_id")

    file_id = str(uuid.uuid4())

    try:
        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s",
            "quiet": True
        }

        # 🎵 MP3
        if type_ == "mp3":
            ydl_opts.update({
                "format": "bestaudio",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3"
                }]
            })

        # 🎥 MP4
        else:
            if "instagram" in url:
                ydl_opts["format"] = "best"
            else:
                ydl_opts["format"] = format_id if format_id else "best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if type_ == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        downloads[file_id] = filename

        return jsonify({"id": file_id})

    except Exception as e:
        return jsonify({"error": str(e)})

# 🔥 FILE DOWNLOAD
@app.route("/file")
def file():
    file_id = request.args.get("id")

    if file_id not in downloads:
        return "File not found", 404

    return send_file(downloads[file_id], as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
