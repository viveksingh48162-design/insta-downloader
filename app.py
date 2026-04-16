from flask import Flask, request, jsonify, render_template, redirect
import yt_dlp
import os

# 🔥 ffmpeg fallback (important for render)
import imageio_ffmpeg

# set ffmpeg path automatically
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)

# 🎯 GET VIDEO INFO
@app.route("/get_video", methods=["POST"])
def get_video():
    data = request.json
    url = data.get("url")

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'ffmpeg_location': ffmpeg_path
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "is_short": "shorts" in url,
            "is_social": any(x in url for x in ["instagram", "facebook"])
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎯 GET FORMATS (YT QUALITY)
@app.route("/get_formats", methods=["POST"])
def get_formats():
    data = request.json
    url = data.get("url")

    ydl_opts = {
        'quiet': True,
        'ffmpeg_location': ffmpeg_path
    }

    formats_list = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        for f in info.get("formats", []):
            if f.get("vcodec") != "none" and f.get("height"):
                formats_list.append({
                    "format_id": f["format_id"],
                    "quality": f"{f['height']}p"
                })

        return jsonify({
            "video": formats_list[:8]
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎯 DIRECT DOWNLOAD LINK (API)
@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")

    ydl_opts = {
        'format': format_id if format_id else 'best',
        'quiet': True,
        'ffmpeg_location': ffmpeg_path
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "download_url": info.get("url")
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# 🎯 VEGAS FUNNEL ROUTES

@app.route("/gate")
def gate():
    return render_template("gate.html")


@app.route("/adpage")
def adpage():
    return render_template("adpage.html")


# 🎯 FINAL DOWNLOAD (redirect based)
@app.route("/start-download")
def start_download():
    url = request.args.get("url")
    f = request.args.get("f")

    ydl_opts = {
        'format': f if f else 'best',
        'quiet': True,
        'ffmpeg_location': ffmpeg_path
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return redirect(info.get("url"))

    except Exception as e:
        return f"Error: {str(e)}"


# 🎯 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 🚀 RUN
if __name__ == "__main__":
    app.run(debug=True)
