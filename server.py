from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Cobalt API - Free, no key needed
COBALT_API = "https://api.cobalt.tools"

HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}

@app.route('/')
def home():
    return jsonify({"status": "Khushiverse API running! 🌸"})


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        # Get video info from Cobalt
        res = requests.post(
            f"{COBALT_API}",
            json={
                "url": url,
                "videoQuality": "720",
                "audioFormat": "mp3",
                "downloadMode": "auto",
            },
            headers=HEADERS,
            timeout=30
        )
        data_resp = res.json()

        if data_resp.get('status') in ['error', 'rate-limit']:
            return jsonify({"error": data_resp.get('error', {}).get('code', 'Unknown error')}), 500

        # Extract video ID for thumbnail (YouTube)
        vid_id = extract_yt_id(url)
        thumbnail = f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg" if vid_id else ""

        # Return available formats
        formats = [
            {"label": "MP3", "ext": "mp3", "quality": "mp3", "type": "audio"},
            {"label": "360p", "ext": "mp4", "quality": "360", "type": "video"},
            {"label": "720p", "ext": "mp4", "quality": "720", "type": "video"},
            {"label": "1080p", "ext": "mp4", "quality": "1080", "type": "video"},
        ]

        return jsonify({
            "title": extract_title(url),
            "thumbnail": thumbnail,
            "channel": "Video",
            "duration": "--:--",
            "view_count": "",
            "formats": formats,
            "cobalt_url": data_resp.get('url', ''),
            "status": data_resp.get('status', '')
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url', '').strip()
    quality = data.get('quality', '720')
    fmt_type = data.get('type', 'video')
    label = data.get('label', '720p')

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        if fmt_type == 'audio':
            payload = {
                "url": url,
                "downloadMode": "audio",
                "audioFormat": "mp3",
                "audioQuality": "128",
            }
        else:
            payload = {
                "url": url,
                "downloadMode": "auto",
                "videoQuality": quality,
            }

        res = requests.post(
            COBALT_API,
            json=payload,
            headers=HEADERS,
            timeout=30
        )
        data_resp = res.json()

        status = data_resp.get('status')

        if status == 'error':
            code = data_resp.get('error', {}).get('code', 'Unknown')
            return jsonify({"error": code}), 500

        if status == 'redirect' or status == 'tunnel':
            download_url = data_resp.get('url')
            filename = data_resp.get('filename', f'video.{"mp3" if fmt_type=="audio" else "mp4"}')
            return jsonify({
                "download_url": download_url,
                "filename": filename,
                "status": "ok"
            })

        if status == 'picker':
            # Multiple options - take first
            picker = data_resp.get('picker', [])
            if picker:
                return jsonify({
                    "download_url": picker[0].get('url'),
                    "filename": f'video.{"mp3" if fmt_type=="audio" else "mp4"}',
                    "status": "ok"
                })

        return jsonify({"error": "Could not get download link"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/playlist', methods=['POST'])
def get_playlist():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "URL required"}), 400

    # Extract playlist ID
    import re
    match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
    if not match:
        return jsonify({"error": "Invalid playlist URL"}), 400

    playlist_id = match.group(1)

    try:
        # Use YouTube oEmbed for basic info
        videos = []
        return jsonify({
            "title": "YouTube Playlist",
            "thumbnail": "",
            "count": 0,
            "videos": videos,
            "message": "Playlist feature coming soon"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_yt_id(url):
    import re
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None


def extract_title(url):
    try:
        vid_id = extract_yt_id(url)
        if vid_id:
            res = requests.get(
                f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={vid_id}&format=json",
                timeout=10
            )
            if res.ok:
                return res.json().get('title', 'Video')
    except:
        pass
    return 'Video'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)