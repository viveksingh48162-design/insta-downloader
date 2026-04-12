from flask import Flask, render_template, request, jsonify, send_file
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


# 🔥 VIDEO INFO
@app.route("/info", methods=["POST"])
def info():
    url = request.json["url"]

    try:
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        formats = []

        if "youtu" in url:
            for f in data.get("formats", []):
                if f.get("height") and f.get("format_id"):
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
            "quiet": True,
            "noplaylist": True,
        }

        # 🔥 YouTube bot fix
        if "youtu" in url:
            ydl_opts["cookiesfrombrowser"] = ("chrome",)

        # 🔥 MP3
        if type_ == "mp3":
            ydl_opts.update({
                "format": "bestaudio",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3"
                }]
            })

        # 🔥 MP4
       # 🔥 MP4
    else: 
      if "instagram" in url:
        ydl_opts["format"] = "best"
        ydl_opts["cookiesfrombrowser"] = ("chrome",)
    else:
        ydl_opts["format"] = format_id if format_id else "best""

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if type_ == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        downloads[file_id] = filename

        return jsonify({"id": file_id})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/file")
def file():
    file_id = request.args.get("id")
    path = downloads.get(file_id)

    if not path or not os.path.exists(path):
        return "File not found", 404

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
