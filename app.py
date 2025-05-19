from flask import Flask, render_template, request, jsonify, send_file
import os
from pathlib import Path
from youtube_playlist_scraper import main as scraper_main, get_playlist_info
import threading
import queue
import time
from dotenv import load_dotenv
import pandas as pd
import csv
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global state for tracking download progress
download_state = {
    "is_running": False,
    "progress": 0,
    "message": "",
    "status": "idle",
    "current_playlist": "",
    "total_playlists": 0,
    "processed_playlists": 0,
    "current_video": 0,
    "total_videos": 0
}

def run_scraper(channel, playlists, split, output_dir):
    """Run the scraper in a separate thread and update progress"""
    global download_state
    
    try:
        download_state["is_running"] = True
        download_state["progress"] = 0
        download_state["message"] = "Iniciando download..."
        download_state["status"] = "in_progress"
        download_state["current_playlist"] = ""
        download_state["total_playlists"] = 0
        download_state["processed_playlists"] = 0
        download_state["current_video"] = 0
        download_state["total_videos"] = 0
        
        all_data = []
        total_items = 0
        processed_items = 0
        
        # Initialize YouTube API
        youtube = build("youtube", "v3", developerKey=os.getenv('YOUTUBE_API_KEY'), cache_discovery=False)
        
        # Calculate total items to process
        if channel:
            total_items += 1
        if playlists:
            total_items += len(playlists)
            
        # Process channel if provided
        if channel:
            download_state["message"] = f"Processando canal: {channel}"
            if split:
                scraper_main(None, Path("playlists.csv"), True, channel=channel, progress_queue=None)
            else:
                # Get channel data without saving
                channel_data = scraper_main(None, Path("playlists.csv"), True, channel=channel, return_data=True, progress_queue=None)
                if channel_data:
                    all_data.extend(channel_data)
            processed_items += 1
            download_state["progress"] = (processed_items / total_items) * 100
        
        # Process individual playlists if provided
        if playlists:
            download_state["total_playlists"] = len(playlists)
            for i, playlist_url in enumerate(playlists, 1):
                # Get playlist info for better progress display
                playlist_id = playlist_url.split('list=')[-1]
                try:
                    playlist_info = get_playlist_info(youtube, playlist_id)
                    playlist_title = playlist_info["title"]
                except:
                    playlist_title = f"Playlist {i}"
                
                download_state["current_playlist"] = playlist_title
                download_state["processed_playlists"] = i - 1
                download_state["message"] = f"Processando playlist {i} de {len(playlists)}: {playlist_title}"
                
                if split:
                    scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist_url, progress_queue=None)
                else:
                    # Get playlist data without saving
                    playlist_data = scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist_url, return_data=True, progress_queue=None)
                    if playlist_data:
                        all_data.extend(playlist_data)
                processed_items += 1
                download_state["progress"] = (processed_items / total_items) * 100
        
        # If not splitting, save all data to a single CSV
        if not split and all_data:
            download_state["message"] = "Salvando dados em CSV..."
            df = pd.DataFrame(all_data, columns=["channel", "playlist", "videoTitle", "description", "duration"])
            output_file = Path("playlists") / "all_playlists.csv"
            output_file.parent.mkdir(exist_ok=True)
            df.to_csv(output_file, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
        
        # Update final state
        download_state["is_running"] = False
        download_state["progress"] = 100
        download_state["message"] = f"Download concluído com sucesso! {len(all_data) if not split else processed_items} itens processados."
        download_state["status"] = "completed"
        download_state["current_playlist"] = ""
        download_state["processed_playlists"] = download_state["total_playlists"]
        
    except Exception as e:
        download_state["is_running"] = False
        download_state["progress"] = 100
        download_state["message"] = f"Erro durante o download: {str(e)}"
        download_state["status"] = "error"
        download_state["current_playlist"] = ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    global download_state
    
    data = request.json
    channel = data.get('channel')
    playlists = data.get('playlists', [])
    split = data.get('split', False)
    
    if not channel and not playlists:
        return jsonify({"error": "Either channel or playlist(s) must be provided"}), 400
    
    # Reset download state
    download_state["is_running"] = False
    download_state["progress"] = 0
    download_state["message"] = ""
    download_state["status"] = "idle"
    download_state["current_playlist"] = ""
    download_state["total_playlists"] = 0
    download_state["processed_playlists"] = 0
    download_state["current_video"] = 0
    download_state["total_videos"] = 0
    
    # Start scraper in a separate thread
    thread = threading.Thread(
        target=run_scraper,
        args=(channel, playlists, split, "playlists")
    )
    thread.start()
    
    return jsonify({"message": "Download started"})

@app.route('/progress')
def get_progress():
    global download_state
    return jsonify(download_state)

@app.route('/download_file/<path:filename>')
def download_file(filename):
    return send_file(f"playlists/{filename}", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 