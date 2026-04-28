# Muziekschaarapp

A small FastAPI web app for sharing music links and quickly opening the same song in Spotify or YouTube Music.

## What This Project Does

Muziekschaarapp lets users paste a music URL, converts it through the song.link API, and stores a shared song list in SQLite.

Current behavior:
- Provides a simple web UI at `/` for sharing and browsing songs.
- Converts links to platform-specific links (Spotify and YouTube Music when available).
- Stores song metadata (title, artist, thumbnail, sharer, timestamp).
- Detects duplicates based on `spotify_url` and returns a duplicate message.
- Supports filtering by sharer and start date (default: last 4 weeks).
- Supports deleting songs.

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn
- SQLite
- httpx
- Docker and Docker Compose

## Project Structure

- `main.py`: FastAPI app, HTML UI, API routes, and DB logic
- `requirements.txt`: Python dependencies
- `Dockerfile`: Container image definition
- `docker-compose.yml`: Local container orchestration
- `run`: Convenience script to run Docker Compose
- `mzsa_small.png`: Logo served by the app

## Run With Docker (Recommended)

From the project root:

```bash
docker-compose up --build
```

Then open:
- http://localhost:8000

Data is stored in `./data` (mounted to `/app/data` in the container).

## Run Locally (Without Docker)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a data directory (for SQLite DB):

```bash
mkdir data
```

4. Start the app:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

5. Open http://localhost:8000

Note: `main.py` currently uses `/app/data/music_share.db` as DB path, which is ideal in Docker. For local runs, update `DB_PATH` or make it environment-driven.

## API Endpoints

- `GET /`: Main HTML page
- `GET /mzsa_small.png`: Logo image
- `POST /share`: Share a song URL
- `GET /songs`: List songs (optional query params: `shared_by`, `start_date`)
- `DELETE /songs/{song_id}`: Delete a song

## Simple Improvements To Make Next

1. Make DB path configurable through environment variable.
2. Add basic tests for `POST /share`, duplicate handling, filters, and delete flow.
3. Validate allowed domains for submitted music URLs (e.g., Spotify, YouTube Music).
4. Move HTML/CSS/JS from inline string to template and static files for maintainability.
5. Add pagination or result limits for `/songs` as data grows.
6. Improve duplicate detection fallback when Spotify URL is missing.
7. Add structured logging and better error responses for external API failures.
8. Add a simple CI workflow (lint + tests) for safer changes.

## License

No license is defined yet. Add a `LICENSE` file if you plan to share or distribute this project.