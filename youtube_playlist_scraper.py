#!/usr/bin/env python3
"""
Baixa (playlist, título, descrição, duração) de playlists do YouTube
usando a YouTube Data API v3 e grava em arquivos CSV.
"""
from __future__ import annotations
import argparse, csv, re, sys, time
from datetime import timedelta
from pathlib import Path
from typing import Generator, List, Dict

import pandas as pd
from googleapiclient.discovery import build
from tqdm import tqdm
from dateutil import parser as dateparser   # só para converter ISO 8601

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

# ---------- main ----------
def main(api_key: str, out_file: Path, split_by_playlist: bool = False, channel: str = "@3blue1brown"):
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    channel_id = get_channel_id(youtube, channel)

    if split_by_playlist:
        # Create playlists directory and channel subdirectory
        playlists_dir = Path("playlists")
        channel_dir = playlists_dir / channel.lstrip("@")
        playlists_dir.mkdir(exist_ok=True)
        channel_dir.mkdir(exist_ok=True)
        
        # Process each playlist separately
        for pl in tqdm(iter_playlists(youtube, channel_id), desc="Playlists"):
            rows = []
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
                    "playlist": pl["title"],
                    "videoTitle": info["title"],
                    "description": info["description"],
                    "duration": info["duration"],
                })
            
            if skipped > 0:
                print(f"ℹ️  {skipped} vídeo(s) indisponível(is) na playlist '{pl['title']}'")
            
            if not rows:  # Skip if no valid data was collected
                print(f"⚠️  Nenhum dado válido encontrado para '{pl['title']}', pulando...")
                continue
                
            # Generate filename for this playlist (sanitize filename and ensure .csv extension)
            safe_title = "".join(c for c in pl['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
            playlist_filename = channel_dir / f"{safe_title}.csv"
            
            df = pd.DataFrame(rows, columns=["playlist", "videoTitle", "description", "duration"])
            df.to_csv(playlist_filename, index=False, encoding="utf-8")
            print(f"✅ CSV salvo em {playlist_filename.resolve()}  ({len(df)} linhas)")
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

        # Create playlists directory and channel subdirectory for single file mode too
        playlists_dir = Path("playlists")
        channel_dir = playlists_dir / channel.lstrip("@")
        playlists_dir.mkdir(exist_ok=True)
        channel_dir.mkdir(exist_ok=True)
        
        # Save the single CSV in the channel directory
        out_file = channel_dir / out_file.name
        df = pd.DataFrame(rows, columns=["playlist", "videoTitle", "description", "duration"])
        df.to_csv(out_file, index=False, encoding="utf-8")
        print(f"✅ CSV salvo em {out_file.resolve()}  ({len(df)} linhas)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api_key", required=True, help="YouTube Data API v3 key")
    ap.add_argument(
        "-o", "--out", default="playlists.csv",
        help="CSV de saída (padrão: %(default)s). Se --split for usado, será ignorado"
    )
    ap.add_argument(
        "--split", action="store_true",
        help="Gera um CSV separado para cada playlist na pasta 'playlists/<canal>'"
    )
    ap.add_argument(
        "-c", "--channel", default="@3blue1brown",
        help="Handle do canal (padrão: %(default)s)"
    )
    args = ap.parse_args()
    main(args.api_key, Path(args.out), args.split, args.channel)
