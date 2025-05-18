# YouTube Playlist Scraper

English | [Portuguese version](README_PT.md)

A Python script to download metadata from YouTube playlists using the YouTube Data API v3. The script can generate either a single CSV file with all playlists or separate files for each playlist.

## Features

- Downloads metadata from all public playlists of a YouTube channel
- Supports multiple channels
- Organizes files in channel-specific directories
- Skips unavailable videos
- Generates CSV files with:
  - Playlist name
  - Video title
  - Description
  - Duration

## Requirements

- Python 3.6+
- Google API Python Client
- pandas
- tqdm
- dateutil

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-username/youtube-playlist-scraper.git
cd youtube-playlist-scraper
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Get a YouTube API key:
   - Visit the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the YouTube Data API v3
   - Create an API key

## Usage

### Basic Command

```bash
python youtube_playlist_scraper.py --api_key YOUR_API_KEY
```

### Available Options

- `--api_key`: (Required) Your YouTube Data API v3 key
- `-c, --channel`: (Required) Channel handle (e.g., "@ChannelName")
- `-o, --out`: Output CSV filename (default: "playlists.csv")
- `--split`: Generate a separate CSV file for each playlist

### Examples

1. Download playlists from a channel:

```bash
python youtube_playlist_scraper.py --api_key YOUR_API_KEY -c "@ChannelName"
```

2. Generate a separate CSV file for each playlist:

```bash
python youtube_playlist_scraper.py --api_key YOUR_API_KEY -c "@ChannelName" --split
```

## File Structure

Files are organized as follows:

```
playlists/
  channel-name/
    playlist1.csv
    playlist2.csv
    ...
```

## CSV Format

The generated CSV files contain the following columns:

- `playlist`: Playlist name
- `videoTitle`: Video title
- `description`: Video description
- `duration`: Video duration (HH:MM:SS format)

## Notes

- The script automatically skips unavailable or private videos
- Empty playlists are skipped
- The script shows informative messages about unavailable videos
- Filenames are sanitized to remove invalid characters

## Limitations

- Requires a YouTube API key
- Subject to YouTube Data API v3 quotas
- Can only access public playlists

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
