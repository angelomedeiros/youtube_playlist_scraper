#!/usr/bin/env python3
"""
Baixa (playlist, título, descrição, duração) de playlists do YouTube
usando a YouTube Data API v3 e grava em arquivos CSV.
"""
from __future__ import annotations
import argparse, csv, re, sys, time
from datetime import timedelta
from pathlib import Path
from typing import Generator, List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import pandas as pd
from googleapiclient.discovery import build
from tqdm import tqdm
from dateutil import parser as dateparser   # só para converter ISO 8601
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# ---------- helpers ----------
ISO_DUR_RE = re.compile(
    r'P(?:(?P<d>\d+)D)?T?(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?'
)

def iso_to_hms(iso: str) -> str:
    """PT1H2M3S -> 01:02:03   /   PT15M -> 00:15:00"""
    m = ISO_DUR_RE.fullmatch(iso)
    if not m:
        return ""
    h = int(m.group("h") or 0)
    m_ = int(m.group("m") or 0)
    s = int(m.group("s") or 0)
    d = int(m.group("d") or 0)
    total = timedelta(days=d, hours=h, minutes=m_, seconds=s)
    hh, rem = divmod(total.seconds, 3600)
    mm, ss = divmod(rem, 60)
    hh += total.days * 24
    return f"{hh:02}:{mm:02}:{ss:02}"

def extract_playlist_id(url: str) -> Optional[str]:
    """Extrai o ID da playlist de uma URL do YouTube."""
    if not url.startswith(('http://', 'https://')):
        return None
        
    parsed = urlparse(url)
    if parsed.netloc not in ('www.youtube.com', 'youtube.com'):
        return None
        
    if '/playlist' in parsed.path:
        query = parse_qs(parsed.query)
        return query.get('list', [None])[0]
    return None

# ---------- API wrappers ----------
def get_channel_id(youtube, handle: str) -> str:
    """Pesquisa o handle e devolve o channelId."""
    resp = youtube.search().list(
        q=handle, type="channel", part="snippet", maxResults=1
    ).execute()
    items = resp.get("items", [])
    if not items:
        sys.exit("Handle não encontrado.")
    return items[0]["snippet"]["channelId"]

def get_playlist_info(youtube, playlist_id: str) -> Dict:
    """Obtém informações básicas de uma playlist."""
    resp = youtube.playlists().list(
        id=playlist_id,
        part="snippet"
    ).execute()
    items = resp.get("items", [])
    if not items:
        sys.exit("Playlist não encontrada.")
    return {
        "id": playlist_id,
        "title": items[0]["snippet"]["title"]
    }

def iter_playlists(youtube, channel_id: str) -> Generator[Dict, None, None]:
    """Itera sobre todas as playlists públicas do canal."""
    next_token = None
    while True:
        resp = youtube.playlists().list(
            channelId=channel_id,
            part="id,snippet",
            maxResults=50,
            pageToken=next_token,
        ).execute()
        for pl in resp["items"]:
            yield {"id": pl["id"], "title": pl["snippet"]["title"]}
        next_token = resp.get("nextPageToken")
        if not next_token:
            break

def iter_videos_in_playlist(youtube, playlist_id: str) -> List[str]:
    """Retorna todos os videoIds de uma playlist."""
    ids = []
    next_token = None
    while True:
        resp = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_token,
        ).execute()
        ids.extend(item["contentDetails"]["videoId"] for item in resp["items"])
        next_token = resp.get("nextPageToken")
        if not next_token:
            break
    return ids

def get_videos_metadata(youtube, video_ids: List[str]) -> Dict[str, Dict]:
    """Chama videos.list em lotes (máx 50 por requisição)."""
    meta = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        resp = youtube.videos().list(
            id=",".join(chunk), part="snippet,contentDetails,status"
        ).execute()
        for item in resp["items"]:
            vid = item["id"]
            # Skip if video is unavailable or private
            if item.get("status", {}).get("privacyStatus") != "public":
                continue
            meta[vid] = {
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"].replace("\n", " ").strip(),
                "duration": iso_to_hms(item["contentDetails"]["duration"]),
            }
    return meta

def get_channel_info(youtube, channel_id: str) -> Dict:
    """Obtém informações do canal."""
    resp = youtube.channels().list(
        id=channel_id,
        part="snippet"
    ).execute()
    items = resp.get("items", [])
    if not items:
        return {"title": "Unknown Channel"}
    return {
        "title": items[0]["snippet"]["title"]
    }

def process_playlist(youtube, playlist: Dict, split_by_playlist: bool, channel_dir: Path, channel_name: str = None) -> None:
    """Processa uma única playlist e salva os dados."""
    rows = []
    video_ids = iter_videos_in_playlist(youtube, playlist["id"])
    if not video_ids:  # Skip if no videos found
        print(f"⚠️  Playlist '{playlist['title']}' está vazia, pulando...")
        return
        
    meta = get_videos_metadata(youtube, video_ids)
    skipped = 0
    for vid in video_ids:            # preserva a ordem da playlist
        info = meta.get(vid)
        if not info:  # Skip if video is unavailable
            skipped += 1
            continue
        rows.append({
            "channel": channel_name or "Unknown Channel",
            "playlist": playlist["title"],
            "videoTitle": info["title"],
            "description": info["description"],
            "duration": info["duration"],
        })
    
    if skipped > 0:
        print(f"ℹ️  {skipped} vídeo(s) indisponível(is) na playlist '{playlist['title']}'")
    
    if not rows:  # Skip if no valid data was collected
        print(f"⚠️  Nenhum dado válido encontrado para '{playlist['title']}', pulando...")
        return
        
    # Generate filename for this playlist (sanitize filename and ensure .csv extension)
    safe_title = "".join(c for c in playlist['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
    playlist_filename = channel_dir / f"{safe_title}.csv"
    
    df = pd.DataFrame(rows, columns=["channel", "playlist", "videoTitle", "description", "duration"])
    df.to_csv(playlist_filename, index=False, encoding="utf-8")
    print(f"✅ CSV salvo em {playlist_filename.resolve()}  ({len(df)} linhas)")

# ---------- main ----------
def main(api_key: str = None, out_file: Path = None, split_by_playlist: bool = False, channel: str = None, playlist_url: str = None):
    # Get API key from environment if not provided
    api_key = api_key or os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        sys.exit("Error: YouTube API key not found. Please set YOUTUBE_API_KEY in .env file or provide it via --api_key")
    
    # Set default output file if not provided
    out_file = out_file or Path("playlists.csv")
    
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    
    # Create playlists directory
    playlists_dir = Path("playlists")
    playlists_dir.mkdir(exist_ok=True)
    
    if playlist_url:
        # Process single playlist
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            sys.exit("URL da playlist inválida.")
            
        playlist = get_playlist_info(youtube, playlist_id)
        channel_dir = playlists_dir / "single_playlists"
        channel_dir.mkdir(exist_ok=True)
        process_playlist(youtube, playlist, True, channel_dir)
    else:
        # Process all playlists from channel
        channel_id = get_channel_id(youtube, channel)
        channel_info = get_channel_info(youtube, channel_id)
        channel_name = channel_info["title"]
        channel_dir = playlists_dir / channel.lstrip("@")
        channel_dir.mkdir(exist_ok=True)
        
        if split_by_playlist:
            # Process each playlist separately
            for pl in tqdm(iter_playlists(youtube, channel_id), desc="Playlists"):
                process_playlist(youtube, pl, True, channel_dir, channel_name)
        else:
            # Original behavior - single CSV with all playlists
            rows = []
            total_skipped = 0
            for pl in tqdm(iter_playlists(youtube, channel_id), desc="Playlists"):
                video_ids = iter_videos_in_playlist(youtube, pl["id"])
                if not video_ids:  # Skip if no videos found
                    print(f"⚠️  Playlist '{pl['title']}' está vazia, pulando...")
                    continue
                    
                meta = get_videos_metadata(youtube, video_ids)
                skipped = 0
                for vid in video_ids:            # preserva a ordem da playlist
                    info = meta.get(vid)
                    if not info:  # Skip if video is unavailable
                        skipped += 1
                        continue
                    rows.append({
                        "channel": channel_name,
                        "playlist": pl["title"],
                        "videoTitle": info["title"],
                        "description": info["description"],
                        "duration": info["duration"],
                    })
                
                if skipped > 0:
                    print(f"ℹ️  {skipped} vídeo(s) indisponível(is) na playlist '{pl['title']}'")
                    total_skipped += skipped

            if total_skipped > 0:
                print(f"ℹ️  Total de {total_skipped} vídeo(s) indisponível(is) em todas as playlists")

            if not rows:  # Check if we have any data at all
                print("⚠️  Nenhum dado válido encontrado em nenhuma playlist!")
                return

            # Save the single CSV in the channel directory
            out_file = channel_dir / out_file.name
            df = pd.DataFrame(rows, columns=["channel", "playlist", "videoTitle", "description", "duration"])
            df.to_csv(out_file, index=False, encoding="utf-8")
            print(f"✅ CSV salvo em {out_file.resolve()}  ({len(df)} linhas)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api_key", help="YouTube Data API v3 key (optional if set in .env file)")
    ap.add_argument(
        "-o", "--out", default="playlists.csv",
        help="CSV de saída (padrão: %(default)s). Se --split for usado, será ignorado"
    )
    ap.add_argument(
        "--split", action="store_true",
        help="Gera um CSV separado para cada playlist na pasta 'playlists/<canal>'"
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c", "--channel",
        help="Handle do canal (ex: @NomeDoCanal)"
    )
    group.add_argument(
        "-p", "--playlist",
        help="URL da playlist do YouTube"
    )
    args = ap.parse_args()
    main(args.api_key, Path(args.out), args.split, args.channel, args.playlist)
