from flask import Flask, render_template, request, jsonify, send_file
import os
from pathlib import Path
from youtube_playlist_scraper import main as scraper_main
import threading
import queue
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Queue for storing progress updates
progress_queue = queue.Queue()

def run_scraper(channel, playlists, split, output_dir):
    """Run the scraper in a separate thread and update progress"""
    try:
        # Process channel if provided
        if channel:
            scraper_main(None, Path("playlists.csv"), split, channel=channel)
        
        # Process individual playlists if provided
        if playlists:
            for playlist in playlists:
                scraper_main(None, Path("playlists.csv"), split, playlist_url=playlist)
        
        progress_queue.put({"status": "completed", "message": "Download completed successfully!"})
    except Exception as e:
        progress_queue.put({"status": "error", "message": str(e)})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    channel = data.get('channel')
    playlists = data.get('playlists', [])
    split = data.get('split', False)
    
    if not channel and not playlists:
        return jsonify({"error": "Either channel or playlist(s) must be provided"}), 400
    
    # Start scraper in a separate thread
    thread = threading.Thread(
        target=run_scraper,
        args=(channel, playlists, split, "playlists")
    )
    thread.start()
    
    return jsonify({"message": "Download started"})

@app.route('/progress')
def get_progress():
    try:
        progress = progress_queue.get_nowait()
        return jsonify(progress)
    except queue.Empty:
        return jsonify({"status": "in_progress"})

@app.route('/download_file/<path:filename>')
def download_file(filename):
    return send_file(f"playlists/{filename}", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 