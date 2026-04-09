from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/info", methods=["POST"])
def info():
    url = request.json.get("url")

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        is_youtube = "youtube" in url or "youtu.be" in url

        formats = []
        if is_youtube:
            for f in data.get("formats", []):
                if f.get("height"):
                    formats.append({
                        "quality": str(f["height"]) + "p",
                        "format_id": f["format_id"]
                    })

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats[:6],
            "platform": "youtube" if is_youtube else "instagram"
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    format_id = request.json.get("format_id")
    filetype = request.json.get("type")

    try:
        ydl_opts = {
            'outtmpl': 'video.%(ext)s'
        }

        if filetype == "mp3":
            ydl_opts.update({
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }]
            })
        else:
            ydl_opts.update({
                'format': format_id if format_id else 'best'
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        file_path = "video.mp3" if filetype == "mp3" else "video.mp4"
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
