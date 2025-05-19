from flask import Flask, render_template, request, jsonify, send_file
import os
from pathlib import Path
from youtube_playlist_scraper import main as scraper_main
import threading
import queue
import time
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Queue for storing progress updates
progress_queue = queue.Queue()

def run_scraper(channel, playlists, split, output_dir):
    """Run the scraper in a separate thread and update progress"""
    try:
        all_data = []
        
        # Process channel if provided
        if channel:
            if split:
                scraper_main(None, Path("playlists.csv"), True, channel=channel)
            else:
                # Get channel data without saving
                channel_data = scraper_main(None, Path("playlists.csv"), True, channel=channel, return_data=True)
                all_data.extend(channel_data)
        
        # Process individual playlists if provided
        if playlists:
            if split:
                for playlist in playlists:
                    scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist)
            else:
                for playlist in playlists:
                    # Get playlist data without saving
                    playlist_data = scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist, return_data=True)
                    all_data.extend(playlist_data)
        
        # If not splitting, save all data to a single CSV
        if not split and all_data:
            df = pd.DataFrame(all_data, columns=["channel", "playlist", "videoTitle", "description", "duration"])
            output_file = Path("playlists") / "all_playlists.csv"
            output_file.parent.mkdir(exist_ok=True)
            df.to_csv(output_file, index=False, encoding="utf-8")
        
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