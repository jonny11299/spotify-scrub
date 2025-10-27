# Spotify Scrub (Library Exporter)

Migrate your heartfelt playlists from Spotify to Tidal.
Save all of your precious listening data from years on Spotify.

Exports your Spotify library (playlists, liked tracks, top artists, recently played, etc.) to **CSV and JSON** files using Python + Spotipy.

## Features
- Exports data to **CSV and JSON** files in subfolders (`spotify csvs` and `spotify jsons`)  
- Works by interactively prompting for your **CLIENT_ID** and **CLIENT_SECRET**

---

## Requirements
- macOS (tested), Python **3.9+** recommended  
- Python packages: `pandas`, `spotipy`

---

## Quick Start (Mac)

1. **Download** this repository and put `spotify_scrub.py` in a new folder.

2. **Install Python** (if you don’t already have it):  
   - macOS: `brew install python` (or download from [python.org](https://www.python.org/downloads/))

3. **Create a virtual environment (optional but recommended):**
   ```bash
   cd /path/to/your/folder
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install pandas spotipy
   ```

   Or with a `requirements.txt`:
   ```
   pandas
   spotipy
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

6. **Run the script:**
   ```bash
   python3 spotify_scrub.py
   ```
   - You will be prompted:
     - “Please enter your CLIENT_ID”
     - “Please enter your CLIENT_SECRET”
   - Then a browser window will open for Spotify login/consent.

7. **Email access rules — important**  
   Your Spotify email must **either**:
   - Be the same email that owns the Spotify Developer app **or**
   - Be added to the app’s **User Management** in the Developer Dashboard

---

## The following scopes will be granted to the script:
```python
"user-library-read",        # liked songs, saved albums/shows/episodes
"playlist-read-private",
"playlist-read-collaborative",
"user-follow-read",         # followed artists
"user-top-read",            # top artists/tracks
"user-read-recently-played" # recently played (last 50)
```

---

## Common Issues & Fixes

**Redirect URI mismatch**  
- Error: *INVALID_CLIENT: Invalid redirect URI*  
- Fix: Make sure the **exact** URI `http://127.0.0.1:8888/callback/` is added in your Spotify app settings.

**Stuck with a bad token / changed scopes**  
- Delete the local Spotipy cache file:
  ```bash
  rm .cache*
  ```
  Then re-run the script to re-login.

**403 / some playlists missing**  
- Private or collaborative playlists require `playlist-read-private` and `playlist-read-collaborative`.  
- Also verify the user is allowed in **User Management** for the app.

**Wrong account logging in**  
- If the browser auto-logs into a different Spotify account, open a private window and re-run so you can choose the correct account.

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

## 👾Uploading to TIDAL👾:

You can use "autotidal.py" to automatically re-create your Spotify playlists on TIDAL.

To do this, simply run "python3 autotidal.py" in terminal, and follow the steps.

You may have to first run a quick "pip install tidalapi" if the package isn't installed, though.

Once the app is running, you'll be prompted to select specific playlists to upload to TIDAL.



## License

This is open-source. Anyone can use it. I don't care. Just get off Spotify. Sooner is better.

---

## Contributing

PRs welcome! Please open an issue first for discussion of major changes.

---

### Credits

Built with [Spotipy](https://spotipy.readthedocs.io/) and ❤️.
