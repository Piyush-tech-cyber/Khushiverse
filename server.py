from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import re

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = tempfile.gettempdir()

@app.route('/')
def home():
    return jsonify({"status": "Khushiverse API running! 🌸"})

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "URL required"}), 400
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen = set()
            formats.append({"label": "MP3", "ext": "mp3", "format_id": "bestaudio", "type": "audio"})
            for f in (info.get('formats') or []):
                height = f.get('height')
                ext = f.get('ext', 'mp4')
                fid = f.get('format_id')
                if height and height not in seen and ext in ['mp4', 'webm']:
                    seen.add(height)
                    formats.append({"label": f"{height}p", "ext": "mp4", "format_id": fid, "type": "video"})
            video_fmts = sorted([f for f in formats if f['type']=='video'], key=lambda x: int(x['label'].replace('p','')))
            audio_fmts = [f for f in formats if f['type']=='audio']
            return jsonify({
                "title": info.get('title', 'Unknown'),
                "thumbnail": info.get('thumbnail', ''),
                "channel": info.get('uploader', 'Unknown'),
                "duration": info.get('duration_string', '--:--'),
                "view_count": f"{info.get('view_count', 0):,} views" if info.get('view_count') else '',
                "formats": audio_fmts + video_fmts
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url', '').strip()
    format_id = data.get('format_id', 'best')
    fmt_type = data.get('type', 'video')
    label = data.get('label', 'video')
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        out_path = os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')
        if fmt_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': out_path,
                'quiet': True,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            }
        else:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best[height<={label.replace("p","")}]/best',
                'outtmpl': out_path,
                'quiet': True,
                'merge_output_format': 'mp4',
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt_type == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))
            else:
                return jsonify({"error": "File not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/playlist', methods=['POST'])
def get_playlist():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({"error": "URL required"}), 400
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            videos = []
            for e in entries[:50]:
                videos.append({
                    "id": e.get('id', ''),
                    "title": e.get('title', 'Unknown'),
                    "url": e.get('url') or f"https://youtube.com/watch?v={e.get('id','')}",
                    "duration": e.get('duration_string', '--:--'),
                    "thumbnail": f"https://i.ytimg.com/vi/{e.get('id','')}/default.jpg"
                })
            return jsonify({
                "title": info.get('title', 'Playlist'),
                "thumbnail": info.get('thumbnail') or (videos[0]['thumbnail'] if videos else ''),
                "count": len(videos),
                "videos": videos
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
