from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

progress_data = {"percent": 0, "speed": "", "status": "idle"}


@app.route("/")
def home():
    return render_template("index.html")


def progress_hook(d):
    if d['status'] == 'downloading':
        progress_data["percent"] = float(d.get('_percent_str', '0').replace('%', ''))
        progress_data["speed"] = d.get('_speed_str', '')
        progress_data["status"] = "downloading"

    elif d['status'] == 'finished':
        progress_data["percent"] = 100
        progress_data["status"] = "finished"


@app.route("/progress")
def progress():
    return jsonify(progress_data)


@app.route("/info", methods=["POST"])
def info():
    url = request.json["url"]

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            data = ydl.extract_info(url, download=False)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "platform": "instagram" if "instagram" in url else "youtube"
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/download", methods=["POST"])
def download():
    url = request.json["url"]
    quality = request.json.get("quality", "best")
    filetype = request.json.get("type", "mp4")

    progress_data.update({"percent": 0, "status": "starting"})

    try:
        # MP3 OPTION
        if filetype == "mp3":
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [progress_hook],
            }

        # MP4 OPTION
        else:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'progress_hooks': [progress_hook],
                'concurrent_fragment_downloads': 5
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        # fix extension
        if filetype == "mp3":
            path = path.rsplit(".", 1)[0] + ".mp3"
        else:
            path = path.rsplit(".", 1)[0] + ".mp4"

        return jsonify({"file": path})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/file")
def file():
    return send_file(request.args.get("path"), as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
