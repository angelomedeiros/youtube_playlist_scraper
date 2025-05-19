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
- python-dotenv

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

4. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

5. Edit the `.env` file and add your YouTube API key:

```
YOUTUBE_API_KEY=your_api_key_here
```

## Usage

### Basic Command

```bash
python youtube_playlist_scraper.py
```

### Available Options

- `--api_key`: (Optional) Your YouTube Data API v3 key (if not set in .env file)
- `-c, --channel`: Channel handle (e.g., "@ChannelName")
- `-p, --playlist`: YouTube playlist URL
- `-o, --out`: Output CSV filename (default: "playlists.csv")
- `--split`: Generate a separate CSV file for each playlist

Note: You must provide either `-c/--channel` or `-p/--playlist`, but not both.

### Examples

1. Download all playlists from a channel:

```bash
python youtube_playlist_scraper.py -c "@ChannelName"
```

2. Download a single playlist:

```bash
python youtube_playlist_scraper.py -p "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

3. Generate a separate CSV file for each playlist in a channel:

```bash
python youtube_playlist_scraper.py -c "@ChannelName" --split
```

## File Structure

Files are organized as follows:

```
playlists/
  channel-name/           # When using -c/--channel
    playlist1.csv
    playlist2.csv
    ...
  single_playlists/      # When using -p/--playlist
    playlist1.csv
    ...
```

## CSV Format

The generated CSV files contain the following columns:

- `channel`: Channel name
- `playlist`: Playlist name
- `videoTitle`: Video title
- `description`: Video description
- `duration`: Video duration (HH:MM:SS format)

## Notes

- The script automatically skips unavailable or private videos
- Empty playlists are skipped
- The script shows informative messages about unavailable videos
- Filenames are sanitized to remove invalid characters
- API key can be set in `.env` file or passed via command line

## Limitations

- Requires a YouTube API key
- Subject to YouTube Data API v3 quotas
- Can only access public playlists

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
