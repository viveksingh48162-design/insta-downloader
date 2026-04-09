from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import threading

app = Flask(__name__)

progress_data = {
    "percent": 0,
    "speed": "0 KB/s",
    "status": "idle"
}

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/info", methods=["POST"])
def info():
    url = request.json.get("url")

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'cookiefile': None
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


# 🎯 PROGRESS HOOK
def hook(d):
    if d['status'] == 'downloading':
        progress_data["percent"] = int(float(d['_percent_str'].replace('%','')))
        progress_data["speed"] = d.get("_speed_str", "0 KB/s")
        progress_data["status"] = "downloading"

    elif d['status'] == 'finished':
        progress_data["percent"] = 100
        progress_data["status"] = "finished"


@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    format_id = request.json.get("format_id")
    filetype = request.json.get("type")

    progress_data["percent"] = 0
    progress_data["status"] = "starting"

    try:
        ydl_opts = {
            'progress_hooks': [hook],
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

        def run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        threading.Thread(target=run).start()

        return jsonify({"status": "started"})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/progress")
def progress():
    return jsonify(progress_data)


@app.route("/file")
def file():
    if os.path.exists("video.mp4"):
        return send_file("video.mp4", as_attachment=True)
    if os.path.exists("video.mp3"):
        return send_file("video.mp3", as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
