from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp, os

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

progress_data = {"percent": 0, "speed": "", "status": "idle"}


@app.route("/")
def home():
    return render_template("index.html")


def progress_hook(d):
    if d['status'] == 'downloading':
        progress_data["percent"] = float(d.get('_percent_str','0').replace('%',''))
        progress_data["speed"] = d.get('_speed_str','')
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

    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        data = ydl.extract_info(url, download=False)

    return jsonify({
        "title": data.get("title"),
        "thumbnail": data.get("thumbnail"),
        "platform": "instagram" if "instagram" in url else "youtube"
    })


@app.route("/download", methods=["POST"])
def download():
    url = request.json["url"]
    quality = request.json["quality"]
    filetype = request.json["type"]

    progress_data.update({"percent":0,"status":"starting"})

    quality_map = {
        "360": "bestvideo[height=360]+bestaudio/best",
        "720": "bestvideo[height=720]+bestaudio/best",
        "1080": "bestvideo[height=1080]+bestaudio/best",
        "2160": "bestvideo[height=2160]+bestaudio/best",
    }

    if filetype == "mp3":
        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors':[{
                'key':'FFmpegExtractAudio',
                'preferredcodec':'mp3'
            }],
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'progress_hooks':[progress_hook]
        }
    else:
        format_code = "best" if "instagram" in url else quality_map.get(quality,"best")

        ydl_opts = {
            'format': format_code,
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'merge_output_format':'mp4',
            'progress_hooks':[progress_hook],
            'concurrent_fragment_downloads':5
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)

        if filetype=="mp3":
            path = path.rsplit(".",1)[0]+".mp3"
        else:
            path = path.rsplit(".",1)[0]+".mp4"

    return jsonify({"file": path})


@app.route("/file")
def file():
    return send_file(request.args.get("path"), as_attachment=True)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
