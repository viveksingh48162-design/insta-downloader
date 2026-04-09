from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)


# 🔥 HOME
@app.route("/")
def home():
    return render_template("index.html")


# 🔍 GET VIDEO INFO (thumbnail + platform detect)
@app.route("/info", methods=["POST"])
def info():
    url = request.json["url"]

    try:
        # 🔥 Thumbnail for YouTube
        if "youtube" in url or "youtu.be" in url:
            video_id = None

            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be" in url:
                video_id = url.split("/")[-1]
            elif "shorts" in url:
                video_id = url.split("/")[-1]

            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

            return jsonify({
                "title": "YouTube Video",
                "thumbnail": thumbnail,
                "is_youtube": True
            })

        # 🔥 Instagram thumbnail (basic)
        elif "instagram" in url:
            return jsonify({
                "title": "Instagram Reel",
                "thumbnail": "",
                "is_youtube": False
            })

        else:
            return jsonify({"error": "Unsupported URL"})

    except Exception as e:
        return jsonify({"error": str(e)})


# 🚀 MULTI API DOWNLOAD SYSTEM
@app.route("/download", methods=["POST"])
def download():
    url = request.json["url"]
    filetype = request.json.get("type", "mp4")

    # 🔥 MULTIPLE APIs (auto fallback)
    api_list = [

        # API 1 (fast)
        f"https://api.vevioz.com/api/button/{filetype}?url={url}",

        # API 2
        f"https://ytdownloaderapi.com/api?url={url}",

        # API 3
        f"https://api.y2mate.is/v1/download?url={url}"
    ]

    for api in api_list:
        try:
            res = requests.get(api, timeout=8)

            if res.status_code == 200 and len(res.text) > 50:
                return jsonify({
                    "success": True,
                    "api": api
                })

        except:
            continue

    return jsonify({"error": "All download servers busy ❌ Try again"})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
