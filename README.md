# Spotify Scrub (Library Exporter) — Windows Guide

Export your Spotify library (playlists, liked tracks, top artists, recently played, etc.) to **CSV and JSON** files using Python + Spotipy.

## Features
- Exports data to **CSV and JSON** files in subfolders (`spotify csvs` and `spotify jsons`)  
- Works by interactively prompting for your **CLIENT_ID** and **CLIENT_SECRET**

---

## Requirements
- Windows 10/11  
- Python **3.9+** (from [python.org](https://www.python.org/downloads/))  
- Python packages: `pandas`, `spotipy`

---

## Quick Start (Windows)

1. **Download the script**  
   Put `spotify_scrub.py` in a new folder, e.g. `C:\Users\<YourName>\spotify-scrub`.

2. **Install Python**  
   - Download from [python.org](https://www.python.org/downloads/) and install.  
   - During installation, check **“Add Python to PATH”**.

3. **(Optional) Create a virtual environment**  
   Open **PowerShell** and run:
   ```powershell
   cd C:\Users\<YourName>\spotify-scrub
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. **Install dependencies**  
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install pandas spotipy
   ```

5. **Create a Spotify for Developers app**  
   - Go to https://developer.spotify.com/dashboard  
   - Log in with your Spotify account; click **Create app**  
   - **Which API/SDKs are you planning to use?** → *Web API*  
   - **Redirect URIs** → add:
     ```
     http://127.0.0.1:8888/callback/
     ```
   - Save your **Client ID** and **Client Secret**.

6. **Run the script**  
   From the project folder in PowerShell:
   ```powershell
   python spotify_scrub.py
   ```
   - You will be prompted:
     - “Please enter your CLIENT_ID”
     - “Please enter your CLIENT_SECRET”
   - A browser window will open for Spotify login/consent.

7. **Email access rules — important**  
   Your Spotify email must **either**:
   - Be the same email that owns the Spotify Developer app **or**  
   - Be added to the app’s **User Management** in the Developer Dashboard

---

## Scopes Requested
```python
"user-library-read",        # liked songs, saved albums/shows/episodes
"playlist-read-private",
"playlist-read-collaborative",
"user-follow-read",         # followed artists
"user-top-read",            # top artists/tracks
"user-read-recently-played" # recently played (last 50)
```

---

## Common Issues (Windows)

**Redirect URI mismatch**  
- Error: *INVALID_CLIENT: Invalid redirect URI*  
- Fix: Make sure `http://127.0.0.1:8888/callback/` is in your Spotify app settings.

**Bad token or changed scopes**  
- Delete the Spotipy cache file:
  ```powershell
  del .cache*
  ```
  Then re-run the script.

**Wrong Spotify account logging in**  
- If your browser auto-logs into the wrong account, open an **InPrivate/Incognito** window and re-run.

---

## Expected Outputs

After running, two directories will be created:

### `spotify csvs`
```
errors.csv            saved_albums.csv        top_artists_all.csv
followed_artists.csv  saved_episodes.csv      top_tracks_4w.csv
liked_songs.csv       saved_shows.csv         top_tracks_6m.csv
playlist_tracks.csv   top_artists_4w.csv      top_tracks_all.csv
playlists.csv         top_artists_6m.csv
```

### `spotify jsons`
```
followed_artists.json  saved_episodes.json     top_tracks_4w.json
liked_songs.json       saved_shows.json        top_tracks_6m.json
playlist_tracks.json   top_artists_4w.json     top_tracks_all.json
playlists.json         top_artists_6m.json
saved_albums.json      top_artists_all.json
```

---

## Development Notes

- Keep `CLIENT_ID` and `CLIENT_SECRET` **out of version control**.  
- Consider adding these to `.gitignore`:
  ```
  .venv/
  .cache*
  spotify csvs/
  spotify jsons/
  ```

---

## License

This is open-source. Anyone can use it. I don't care. Just get off Spotify. Sooner is better.

---

## Contributing

PRs welcome! Please open an issue first for discussion of major changes.

---

### Credits

Built with [Spotipy](https://spotipy.readthedocs.io/) and ❤️.
