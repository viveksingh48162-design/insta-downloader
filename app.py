from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp, os, uuid, threading, time, requests

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

progress_data = {"percent":0,"speed":"0 KB/s","status":"idle"}

# 🔥 AUTO DELETE
def auto_delete(path):
    time.sleep(60)
    if os.path.exists(path):
        os.remove(path)

# 🔥 PROGRESS
def hook(d):
    if d['status'] == 'downloading':
        try:
            progress_data["percent"] = int(float(d['_percent_str'].replace('%','')))
        except:
            pass
        progress_data["speed"] = d.get("_speed_str","0 KB/s")
    elif d['status'] == 'finished':
        progress_data["percent"] = 100

@app.route("/")
def home():
    return render_template("index.html")

# 🔥 INFO (YT + INSTA + FALLBACK)
@app.route("/info", methods=["POST"])
def info():
    url = request.json.get("url")

    try:
        ydl_opts = {'quiet':True,'noplaylist':True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        is_youtube = "youtube" in url or "youtu.be" in url

        formats = []
        if is_youtube:
            for f in data.get("formats",[]):
                if f.get("height"):
                    formats.append({
                        "quality": str(f["height"])+"p",
                        "format_id": f["format_id"]
                    })

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats[:6],
            "platform": "youtube" if is_youtube else "instagram"
        })

    except:
        # 🔥 FALLBACK API (NO BLOCK)
        try:
            api = f"https://yt-api.p.rapidapi.com/dl?id={url.split('v=')[-1]}"
            r = requests.get(api)
            d = r.json()

            return jsonify({
                "title": d.get("title"),
                "thumbnail": d.get("thumbnail"),
                "formats": [
                    {"quality":"360p","format_id":"18"},
                    {"quality":"720p","format_id":"22"},
                    {"quality":"1080p","format_id":"137"},
                    {"quality":"4K","format_id":"313"}
                ],
                "platform":"youtube"
            })
        except Exception as e:
            return jsonify({"error":str(e)})

# 🔥 DOWNLOAD
@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    format_id = request.json.get("format_id")
    filetype = request.json.get("type")

    progress_data["percent"]=0

    uid = str(uuid.uuid4())[:8]
    filename = f"{DOWNLOAD_FOLDER}/video_{uid}.%(ext)s"

    try:
        ydl_opts = {
            'outtmpl': filename,
            'progress_hooks':[hook]
        }

        if filetype=="mp3":
            ydl_opts.update({
                'format':'bestaudio',
                'postprocessors':[{
                    'key':'FFmpegExtractAudio',
                    'preferredcodec':'mp3'
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

        return jsonify({"id":uid})

    except Exception as e:
        return jsonify({"error":str(e)})

@app.route("/progress")
def progress():
    return jsonify(progress_data)

@app.route("/file")
def file():
    fid = request.args.get("id")

    for ext in ["mp4","mp3"]:
        path = f"{DOWNLOAD_FOLDER}/video_{fid}.{ext}"
        if os.path.exists(path):
            threading.Thread(target=auto_delete,args=(path,)).start()
            return send_file(path, as_attachment=True)

    return "File not found"
