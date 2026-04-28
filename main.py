from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import Optional
import httpx
from datetime import datetime, timedelta
import sqlite3
from contextlib import contextmanager

app = FastAPI(title="Music Share App")

# Serve static files
@app.get("/mzsa_small.png")
async def get_logo():
    return FileResponse("/app/mzsa_small.png")

# Database setup
DB_PATH = "/app/data/music_share.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.execute("PRAGMA table_info(songs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "apple_music_url" in existing_columns:
            conn.execute("""
                CREATE TABLE songs_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shared_by TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    spotify_url TEXT,
                    google_music_url TEXT,
                    title TEXT,
                    artist TEXT,
                    thumbnail_url TEXT,
                    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO songs_new (
                    id, shared_by, original_url, spotify_url, google_music_url,
                    title, artist, thumbnail_url, shared_at
                )
                SELECT id, shared_by, original_url, spotify_url, google_music_url,
                       title, artist, thumbnail_url, shared_at
                FROM songs
            """)
            conn.execute("DROP TABLE songs")
            conn.execute("ALTER TABLE songs_new RENAME TO songs")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_by TEXT NOT NULL,
                original_url TEXT NOT NULL,
                spotify_url TEXT,
                google_music_url TEXT,
                title TEXT,
                artist TEXT,
                thumbnail_url TEXT,
                shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# Initialize DB on startup
init_db()

class SongShare(BaseModel):
    shared_by: str
    url: HttpUrl

async def convert_song_link(url: str) -> dict:
    """Convert music link using song.link API"""
    api_url = f"https://api.song.link/v1-alpha.1/links?url={url}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract platform links
            links = data.get("linksByPlatform", {})
            entities = data.get("entitiesByUniqueId", {})
            
            # Get song metadata
            song_info = {}
            if entities:
                first_entity = list(entities.values())[0]
                song_info = {
                    "title": first_entity.get("title"),
                    "artist": first_entity.get("artistName"),
                    "thumbnail_url": first_entity.get("thumbnailUrl"),
                }
            
            return {
                "spotify_url": links.get("spotify", {}).get("url"),
                "google_music_url": links.get("youtubeMusic", {}).get("url"),
                **song_info
            }
        except httpx.HTTPError as e:
            print(f"Error converting link: {e}")
            return {}

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Muziekschaarapp</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { color: #333; margin-bottom: 10px; font-size: 2em; display: flex; align-items: center; justify-content: center; gap: 10px; }
            .logo { height: 40px; width: auto; }
            .subtitle { color: #666; margin-bottom: 30px; justify-content: center; display: flex; font-size: 12px; }
            .share-form {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .filters {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .filter-row {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
            .filter-row > div { flex: 1; min-width: 200px; }
            .filter-label {
                display: block;
                margin-bottom: 6px;
                color: #555;
                font-size: 13px;
                font-weight: 600;
            }
            input, select, button { 
                padding: 12px; 
                margin: 8px 0;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
            }
            input[type="text"] { width: 100%; }
            select { width: 100%; background: white; }
            button { 
                background: #667eea; 
                color: white; 
                border: none;
                cursor: pointer;
                width: 100%;
                font-weight: 600;
            }
            button:hover { background: #5568d3; }
            .song-item {
                background: #f8f9fa;
                padding: 20px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .song-header {
                display: flex;
                align-items: flex-start;
                margin-bottom: 12px;
                gap: 15px;
            }
            .song-thumbnail {
                width: 60px;
                height: 60px;
                border-radius: 6px;
                flex-shrink: 0;
            }
            .song-info { 
                flex: 1;
                min-width: 0;
            }
            .song-info h3 { color: #333; margin-bottom: 4px; }
            .song-info p { color: #666; font-size: 14px; }
            .song-meta { color: #bbb; font-size: 10px;  }
            .song-streaming-links {
                display: flex;
                flex-direction: column;
                gap: 8px;
                align-items: flex-end;
                min-width: 120px;
            }
            .song-streaming-links a {
                padding: 6px 12px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                text-decoration: none;
                color: #667eea;
                font-size: 12px;
                white-space: nowrap;
                text-align: center;
                min-width: 100px;
                transition: all 0.2s;
            }
            .song-streaming-links a:hover { background: #667eea; color: white; }
            .links { display: flex; gap: 10px; flex-wrap: wrap; }
            .links a {
                padding: 8px 16px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                text-decoration: none;
                color: #667eea;
                font-size: 13px;
            }
            .links a:hover { background: #667eea; color: white; }
            .song-actions {
                display: flex;
                justify-content: flex-end;
                align-items: center;
                margin-top: 5px;
            }
            .delete-btn {
                color: black;
                border: none;
                width: 18px;
                height: 18px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }
            .message {
                padding: 12px;
                margin: 10px 0;
                border-radius: 6px;
                display: none;
            }
            .message.success { background: #d4edda; color: #155724; }
            .message.error { background: #f8d7da; color: #721c24; }
            
            /* Mobile Responsive Styles */
            @media (max-width: 768px) {
                body {
                    padding: 10px;
                }
                .container {
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                h1 {
                    font-size: 1.5em;
                    text-align: center;
                    flex-direction: column;
                    gap: 5px;
                }
                .logo {
                    height: 32px;
                }
                .subtitle {
                    text-align: center;
                    font-size: 14px;
                }
                .filter-row {
                    flex-direction: column;
                    gap: 15px;
                }
                .filter-row > div {
                    min-width: auto;
                }
                .song-header {
                    flex-direction: column;
                    align-items: flex-start;
                    text-align: center;
                    gap: 10px;
                }
                .song-thumbnail {
                    width: 80px;
                    height: 80px;
                    margin: 0 auto 10px auto;
                }
                .song-info {
                    width: 100%;
                    text-align: center;
                }
                .song-streaming-links {
                    align-items: center;
                    width: 100%;
                }
                .song-streaming-links a {
                    min-width: 140px;
                }
                .song-info h3 {
                    font-size: 16px;
                }
                .song-info p {
                    font-size: 13px;
                }
                .links {
                    justify-content: center;
                    margin-top: 10px;
                }
                .links a {
                    flex: 1;
                    text-align: center;
                    min-width: 120px;
                }
                .delete-btn {
                    width: 36px;
                    height: 36px;
                    font-size: 18px;
                }
            }
            
            @media (max-width: 480px) {
                .container {
                    padding: 15px;
                    margin: 0;
                    border-radius: 0;
                }
                body {
                    padding: 0;
                }
                h1 {
                    font-size: 1.3em;
                }
                .logo {
                    height: 28px;
                }
                .share-form, .filters {
                    padding: 15px;
                }
                .song-item {
                    padding: 15px;
                }
                .song-thumbnail {
                    width: 60px;
                    height: 60px;
                }
                .song-streaming-links a {
                    font-size: 11px;
                    padding: 5px 10px;
                    min-width: 90px;
                }
                .links a {
                    padding: 6px 12px;
                    font-size: 12px;
                }
                input, select, button {
                    padding: 10px;
                    font-size: 16px; /* Prevents zoom on iOS */
                }
                .song-meta {
                    font-size: 8px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                <img src="/mzsa_small.png" alt="MZSA Logo" class="logo"> Muziekschaarapp <sup>TM</sup></h1> 
                <p class="subtitle">Share music between Spotify and Youtube Music</p>
            </h1>
            
            <div class="share-form">
                <h2 style="margin-bottom: 15px; color: #333;">Share a Song</h2>
                <form id="shareForm">
                    <select id="sharedBy" required>
                        <option value="">Who's sharing?</option>
                        <option value="You">You</option>
                        <option value="Suckel">Suckel</option>
                    </select>
                    <input type="text" id="url" placeholder="Paste music link" required>
                    <button type="submit">Share Song</button>
                </form>
                <div id="message" class="message"></div>
            </div>

            <div class="song-list">
                <h2 style="margin-bottom: 15px; color: #333;">Shared Songs</h2>
                <div class="filters">
                    <h3 style="margin-bottom: 10px; color: #333;">Filters</h3>
                    <div class="filter-row">
                        <div>
                            <label for="filterSharedBy" class="filter-label">Shared by</label>
                            <select id="filterSharedBy">
                                <option value="">All</option>
                                <option value="You">You</option>
                                <option value="Suckel">Suckel</option>
                            </select>
                        </div>
                        <div>
                            <label for="filterStartDate" class="filter-label">On or after</label>
                            <input type="date" id="filterStartDate">
                        </div>
                    </div>
                </div>
                <div id="songs"></div>
            </div>
        </div>

        <script>
            function formatLocalDate(date) {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            }

            async function loadSongs() {
                const filterSharedBy = document.getElementById('filterSharedBy').value;
                const filterStartDate = document.getElementById('filterStartDate').value;
                const params = new URLSearchParams();

                if (filterSharedBy) {
                    params.set('shared_by', filterSharedBy);
                }
                if (filterStartDate) {
                    params.set('start_date', filterStartDate);
                }

                const url = params.toString() ? `/songs?${params.toString()}` : '/songs';
                const response = await fetch(url);
                const songs = await response.json();
                const songsDiv = document.getElementById('songs');
                
                if (songs.length === 0) {
                    songsDiv.innerHTML = '<p style="color: #999; text-align: center;">No songs yet!</p>';
                    return;
                }
                
                songsDiv.innerHTML = songs.map(song => `
                    <div class="song-item">
                        <div class="song-header">
                            ${song.thumbnail_url ? `<img src="${song.thumbnail_url}" class="song-thumbnail">` : ''}
                            <div class="song-info">
                                <h3>${song.title || 'Unknown'}</h3>
                                <p>${song.artist || 'Unknown Artist'}</p>
                                <p class="song-meta">Shared by ${song.shared_by} on ${new Date(song.shared_at).toLocaleString()}</p>
                            </div>
                            <div class="song-streaming-links">
                                ${song.spotify_url ? `<a href="${song.spotify_url}" target="_blank">🎵 Spotify</a>` : ''}
                                ${song.google_music_url ? `<a href="${song.google_music_url}" target="_blank">🎵 Youtube Music</a>` : ''}
                                <p onclick="deleteSong(${song.id}, '${song.title || 'this song'}')" title="Delete song">
                                    🗑️
                                </p>
                            </div>
                        </div>
                    </div>
                `).join('');
            }

            document.getElementById('shareForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const messageDiv = document.getElementById('message');
                
                const data = {
                    shared_by: document.getElementById('sharedBy').value,
                    url: document.getElementById('url').value
                };

                try {
                    const response = await fetch('/share', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        if (result.status === 'duplicate') {
                            messageDiv.textContent = `⚠️ ${result.message}`;
                            messageDiv.className = 'message error';
                        } else {
                            messageDiv.textContent = '✓ Song shared!';
                            messageDiv.className = 'message success';
                            document.getElementById('shareForm').reset();
                            loadSongs();
                        }
                        messageDiv.style.display = 'block';
                        setTimeout(() => messageDiv.style.display = 'none', 4000);
                    } else {
                        throw new Error('Failed');
                    }
                } catch (error) {
                    messageDiv.textContent = '✗ Error sharing song';
                    messageDiv.className = 'message error';
                    messageDiv.style.display = 'block';
                }
            });

            const defaultStartDate = new Date();
            defaultStartDate.setDate(defaultStartDate.getDate() - 28);
            document.getElementById('filterStartDate').value = formatLocalDate(defaultStartDate);

            async function deleteSong(songId, songTitle) {
                if (!confirm(`Are you sure you want to delete "${songTitle}"?`)) {
                    return;
                }
                
                try {
                    const response = await fetch(`/songs/${songId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        loadSongs();
                    } else {
                        alert('Error deleting song');
                    }
                } catch (error) {
                    alert('Error deleting song');
                }
            }

            document.getElementById('filterSharedBy').addEventListener('change', loadSongs);
            document.getElementById('filterStartDate').addEventListener('change', loadSongs);

            loadSongs();
        </script>
    </body>
    </html>
    """

@app.post("/share")
async def share_song(song: SongShare):
    """Share a new song"""
    converted = await convert_song_link(str(song.url))
    
    # Check for duplicates if we have a Spotify URL
    spotify_url = converted.get("spotify_url")
    if spotify_url:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT id, title, artist, shared_by FROM songs WHERE spotify_url = ?", 
                (spotify_url,)
            )
            existing = cursor.fetchone()
            if existing:
                return {
                    "status": "duplicate", 
                    "message": f"This song ({existing[1]} by {existing[2]}) was already shared by {existing[3]}!"
                }
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO songs (shared_by, original_url, spotify_url, google_music_url, 
                             title, artist, thumbnail_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            song.shared_by,
            str(song.url),
            spotify_url,
            converted.get("google_music_url"),
            converted.get("title"),
            converted.get("artist"),
            converted.get("thumbnail_url")
        ))
        conn.commit()
    
    return {"status": "success"}

@app.get("/songs")
async def get_songs(shared_by: Optional[str] = None, start_date: Optional[str] = None):
    """Get all shared songs"""
    parsed_start = None
    if start_date:
        try:
            parsed_start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    else:
        parsed_start = datetime.utcnow() - timedelta(weeks=4)

    if parsed_start:
        parsed_start = parsed_start.replace(hour=0, minute=0, second=0, microsecond=0)
        start_value = parsed_start.strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        query = "SELECT * FROM songs"
        conditions = []
        params = []

        if shared_by:
            conditions.append("shared_by = ?")
            params.append(shared_by)
        if parsed_start:
            conditions.append("shared_at >= ?")
            params.append(start_value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY shared_at DESC"
        cursor = conn.execute(query, params)
        songs = [dict(row) for row in cursor.fetchall()]
    return songs

@app.delete("/songs/{song_id}")
async def delete_song(song_id: int):
    """Delete a song by ID"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM songs WHERE id = ?", (song_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Song not found")
        
        conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()
    
    return {"status": "success"}
