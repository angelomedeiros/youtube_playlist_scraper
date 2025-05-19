from flask import Flask, render_template, request, jsonify, send_file
import os
from pathlib import Path
from youtube_playlist_scraper import main as scraper_main, get_playlist_info, iter_playlists, get_channel_id
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

def process_channel_playlists(youtube, channel_handle, channel_name, split, progress_queue=None):
    """Processa todas as playlists de um canal"""
    all_data = []
    
    # Primeiro, obtém o ID do canal usando o handle
    try:
        channel_id = get_channel_id(youtube, channel_handle)
    except Exception as e:
        download_state["message"] = f"Erro ao encontrar o canal: {str(e)}"
        download_state["status"] = "error"
        return []
    
    # Agora obtém as playlists usando o ID do canal
    try:
        playlists = list(iter_playlists(youtube, channel_id))
    except Exception as e:
        download_state["message"] = f"Erro ao obter playlists do canal: {str(e)}"
        download_state["status"] = "error"
        return []
    
    if not playlists:
        download_state["message"] = "Nenhuma playlist encontrada neste canal"
        download_state["status"] = "error"
        return []
    
    total_playlists = len(playlists)
    
    download_state["total_playlists"] = total_playlists
    download_state["processed_playlists"] = 0
    
    for i, pl in enumerate(playlists, 1):
        download_state["current_playlist"] = pl["title"]
        download_state["processed_playlists"] = i - 1
        download_state["message"] = f"Processando playlist {i} de {total_playlists}: {pl['title']}"
        download_state["progress"] = (i - 1) / total_playlists * 100
        
        if split:
            scraper_main(None, Path("playlists.csv"), True, channel=channel_id, playlist_id=pl["id"], progress_queue=progress_queue)
        else:
            playlist_data = scraper_main(None, Path("playlists.csv"), True, channel=channel_id, playlist_id=pl["id"], return_data=True, progress_queue=progress_queue)
            if playlist_data:
                all_data.extend(playlist_data)
    
    return all_data

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
        failed_playlists = []
        
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
            try:
                if split:
                    process_channel_playlists(youtube, channel, channel, split)
                else:
                    # Get channel data without saving
                    channel_data = process_channel_playlists(youtube, channel, channel, split)
                    if channel_data:
                        all_data.extend(channel_data)
                processed_items += 1
                download_state["progress"] = (processed_items / total_items) * 100
            except Exception as e:
                failed_playlists.append(f"Canal {channel}: {str(e)}")
                download_state["message"] = f"Erro no canal {channel}, continuando com as playlists..."
        
        # Process individual playlists if provided
        if playlists:
            download_state["total_playlists"] = len(playlists)
            for i, playlist_url in enumerate(playlists, 1):
                # Get playlist info for better progress display
                try:
                    playlist_id = playlist_url.split('list=')[-1]
                    if not playlist_id:
                        raise Exception("URL da playlist inválida")
                    
                    playlist_info = get_playlist_info(youtube, playlist_id)
                    playlist_title = playlist_info["title"]
                except Exception as e:
                    failed_playlists.append(f"Playlist {i}/{len(playlists)}: {str(e)}")
                    download_state["message"] = f"Erro na playlist {i}/{len(playlists)}, continuando..."
                    processed_items += 1
                    download_state["progress"] = (processed_items / total_items) * 100
                    continue
                
                download_state["current_playlist"] = playlist_title
                download_state["processed_playlists"] = i - 1
                download_state["message"] = f"Processando playlist {i}/{len(playlists)}: {playlist_title}"
                
                try:
                    if split:
                        scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist_url, progress_queue=None)
                    else:
                        # Get playlist data without saving
                        playlist_data = scraper_main(None, Path("playlists.csv"), True, playlist_url=playlist_url, return_data=True, progress_queue=None)
                        if playlist_data:
                            all_data.extend(playlist_data)
                    processed_items += 1
                    download_state["progress"] = (processed_items / total_items) * 100
                except Exception as e:
                    failed_playlists.append(f"Playlist {i}/{len(playlists)} ({playlist_title}): {str(e)}")
                    download_state["message"] = f"Erro na playlist {i}/{len(playlists)} ({playlist_title}), continuando..."
                    processed_items += 1
                    download_state["progress"] = (processed_items / total_items) * 100
                    continue
        
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
        
        if failed_playlists:
            error_summary = "\n".join(failed_playlists)
            download_state["message"] = f"Download concluído com {len(failed_playlists)} erro(s):\n{error_summary}"
            download_state["status"] = "error"
        else:
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