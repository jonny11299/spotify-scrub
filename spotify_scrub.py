#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Action steps -- 
# Prompt the user to input set_client_id, set_client_secret, and REDIRECT_URI
# Create a README that walks through Spotify's developer profile, and how to find
# one's associated email with Spotify

"""
Spotify Library Export (full):
- liked_songs.csv
- playlists.csv
- playlist_tracks.csv
- saved_albums.csv
- followed_artists.csv
- saved_shows.csv
- saved_episodes.csv
- top_artists_4w.csv, top_artists_6m.csv, top_artists_all.csv
- top_tracks_4w.csv,  top_tracks_6m.csv,  top_tracks_all.csv
- recently_played.csv

Auth: PKCE (no client secret), redirect to http://127.0.0.1:8888/callback/
"""

import os, sys
from typing import Dict, Any, Iterable, List, Optional
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ========= CONFIG =========
set_client_id = input("Please paste your CLIENT_ID and press 'enter' : ").strip()
set_client_secret = input("Please paste your CLIENT_SECRET and press 'enter' : ").strip()


REDIRECT_URI = "http://127.0.0.1:8888/callback/"

SCOPES = [
    "user-library-read",            # liked songs, saved albums/shows/episodes
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-follow-read",             # followed artists
    "user-top-read",                # top artists/tracks
    "user-read-recently-played"     # recently played (last 50)
]

OUT = {
    "liked_songs": "liked_songs.csv",
    "playlists": "playlists.csv",
    "playlist_tracks": "playlist_tracks.csv",
    "saved_albums": "saved_albums.csv",
    "followed_artists": "followed_artists.csv",
    "saved_shows": "saved_shows.csv",
    "saved_episodes": "saved_episodes.csv",
    "top_artists_4w": "top_artists_4w.csv",
    "top_artists_6m": "top_artists_6m.csv",
    "top_artists_all": "top_artists_all.csv",
    "top_tracks_4w": "top_tracks_4w.csv",
    "top_tracks_6m": "top_tracks_6m.csv",
    "top_tracks_all": "top_tracks_all.csv",
    "recently_played": "recently_played.csv",
}



# ========= AUTH =========
def auth_client() -> spotipy.Spotify:
    if not set_client_id or not set_client_secret:
        print("ERROR: Please set set_client_id and set_client_secret.")
        sys.exit(1)

    auth = SpotifyOAuth(
        client_id=set_client_id,
        client_secret=set_client_secret,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=".cache_spotify_export_full",
        show_dialog=True,  # force account chooser
    )
    token_info = auth.get_access_token()
    access_token = token_info["access_token"] if isinstance(token_info, dict) else token_info
    return spotipy.Spotify(auth=access_token)




def safe(obj: Optional[Dict], path: List[str], default=None):
    cur = obj
    for p in path:
        if cur is None: return default
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return default
    return default if cur is None else cur

def paginate(method, key: str, limit: int = 50, **kwargs) -> Iterable[Dict[str, Any]]:
    """Generic offset-based pagination (most endpoints)."""
    offset = 0
    while True:
        page = method(limit=limit, offset=offset, **kwargs)
        items = page.get(key, [])
        for it in items:
            yield it
        if page.get("next"):
            offset += limit
        else:
            break




# ===================== helpers + schema + counters + saving =====================

# Union schema so all outputs share column order; keep extras harmlessly blank.
COLUMNS_ALL = [
    # Playlist meta
    "playlist_id","playlist_name","owner_id","owner_display_name","public",
    "collaborative","snapshot_id","tracks_total","description",

    # Generic timing / attribution
    "added_at","added_by","played_at","rank",

    # Track/artist/album fields
    "is_local","track_name","artist_names","album_name","album_id","album_uri",
    "album_type","release_date","total_tracks","track_id","track_uri","isrc",
    "popularity","type","label","duration_ms","explicit",

    # Artist-only fields
    "artist_id","artist_uri","name","genres","followers",

    # Show/episode fields
    "show_name","show_id","show_uri","publisher","total_episodes","languages","media_type",
    "episode_name","episode_id","episode_uri",
]

# Per-export error counters
ERR = {
    "liked": {"count": 0},
    "playlists": {"count": 0},
    "pl_tracks": {"count": 0},
    "saved_albums": {"count": 0},
    "followed_artists": {"count": 0},
    "saved_shows": {"count": 0},
    "saved_episodes": {"count": 0},
    "top": {"count": 0},
    "recent": {"count": 0},
}

# Central error log (written to errors.csv at the end of main())
ERROR_LOG = []

def safe_join_names(items, key="name"):
    """
    Join values under `key` from a list of dicts into 'A, B, C'.
    Returns None if there are no valid names (CSV shows blank; JSON -> null).
    """
    try:
        names = [d.get(key) for d in (items or []) if isinstance(d, dict) and d.get(key)]
        return ", ".join(names) if names else None
    except Exception as e:
        ERROR_LOG.append({"where": "safe_join_names", "detail": str(e)})
        return None

def safe_row_append(rows, row_dict, expected_columns, ctx=None, errors_counter=None):
    """
    Append a standardized row:
    - Ensures all expected columns exist.
    - Missing/None -> keep as None (CSV blank, JSON null).
    - On exception, logs to ERROR_LOG, increments counter, and appends a blank row.
    """
    try:
        full_row = {col: (row_dict.get(col, None) if row_dict else None) for col in expected_columns}
        rows.append(full_row)
    except Exception as e:
        ERROR_LOG.append({
            "where": "safe_row_append",
            "context": ctx or "",
            "detail": f"{type(e).__name__}: {e}"
        })
        if isinstance(errors_counter, dict):
            errors_counter["count"] = errors_counter.get("count", 0) + 1
        rows.append({col: None for col in expected_columns})

def _basepath(key):
    """Turn OUT['liked_songs'] -> 'liked_songs' (strip extension for paired CSV/JSON writes)."""
    fn = OUT[key]
    return fn[:-4] if fn.lower().endswith(".csv") else fn

def save_csv_json(df, basepath, csv_missing=""):
    """
    Writes both CSV and JSON to 'spotify csvs' and 'spotify jsons' directories:
    - CSV with blanks (na_rep="") or a subtle placeholder if you set csv_missing (e.g., "-").
    - JSON with null for missing values.
    """
    # Ensure directories exist
    os.makedirs("spotify csvs", exist_ok=True)
    os.makedirs("spotify jsons", exist_ok=True)

    # Extract just the filename part (drop any directory from basepath)
    filename = os.path.basename(basepath)

    # Save CSV in 'spotify csvs'
    csv_path = os.path.join("spotify csvs", f"{filename}.csv")
    df.to_csv(csv_path, index=False, na_rep=csv_missing)

    # Save JSON in 'spotify jsons'
    json_path = os.path.join("spotify jsons", f"{filename}.json")
    df.to_json(json_path, orient="records", indent=2)

    print(f"Saved: {csv_path} and {json_path}")


def save_error_log():
    """Call once at end of main() to persist row-level issues."""
    if not ERROR_LOG:
        pd.DataFrame([{"status": "no row-level errors recorded"}]).to_csv("errors.csv", index=False)
        return
    # Normalize keys
    cols = sorted({k for d in ERROR_LOG for k in d.keys()})
    pd.DataFrame(ERROR_LOG, columns=cols).to_csv("errors.csv", index=False)

# ===================== EXPORTS (refactored; write CSV + JSON) =====================

def export_liked_songs(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    for item in paginate(sp.current_user_saved_tracks, key="items", limit=50):
        track = item.get("track") or {}
        album = track.get("album") or {}
        data = {
            "added_at": item.get("added_at"),
            "track_name": track.get("name"),
            "artist_names": safe_join_names(track.get("artists") or []),
            "album_name": album.get("name"),
            "release_date": album.get("release_date"),
            "track_id": track.get("id"),
            "track_uri": track.get("uri"),
            "isrc": (track.get("external_ids") or {}).get("isrc"),
            "album_id": album.get("id"),
            "popularity": track.get("popularity"),
            "is_local": track.get("is_local", False),
        }
        safe_row_append(rows, data, COLUMNS_ALL, ctx=f"liked:{track.get('id')}", errors_counter=ERR["liked"])
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("liked_songs"))
    return df

def export_playlists(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    for pl in paginate(sp.current_user_playlists, key="items", limit=50):
        owner = pl.get("owner") or {}
        data = {
            "playlist_id": pl.get("id"),
            "playlist_name": pl.get("name"),
            "owner_id": owner.get("id"),
            "owner_display_name": owner.get("display_name"),
            "public": pl.get("public"),
            "collaborative": pl.get("collaborative"),
            "snapshot_id": pl.get("snapshot_id"),
            "tracks_total": (pl.get("tracks") or {}).get("total"),
            "description": pl.get("description"),
        }
        safe_row_append(rows, data, COLUMNS_ALL, ctx=f"playlist:{pl.get('id')}", errors_counter=ERR["playlists"])
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("playlists"))
    return df

def export_playlist_tracks(sp: spotipy.Spotify, playlists_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, pl in playlists_df.iterrows():
        pl_id, pl_name = pl.get("playlist_id"), pl.get("playlist_name") or pl.get("name")
        for it in paginate(sp.playlist_items, key="items", playlist_id=pl_id, limit=100, additional_types=("track",)):
            track = it.get("track") or {}
            album = track.get("album") or {}
            data = {
                "playlist_id": pl_id,
                "playlist_name": pl_name,
                "added_at": it.get("added_at"),
                "added_by": (it.get("added_by") or {}).get("id"),
                "is_local": track.get("is_local", False),
                "track_name": track.get("name"),
                "artist_names": safe_join_names(track.get("artists") or []),
                "album_name": album.get("name"),
                "album_id": album.get("id"),
                "release_date": album.get("release_date"),
                "track_id": track.get("id"),
                "track_uri": track.get("uri"),
                "isrc": (track.get("external_ids") or {}).get("isrc"),
                "popularity": track.get("popularity"),
                "type": track.get("type"),
            }
            safe_row_append(rows, data, COLUMNS_ALL, ctx=f"pl:{pl_id}:{track.get('id')}", errors_counter=ERR["pl_tracks"])
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("playlist_tracks"))
    return df

def export_saved_albums(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    for item in paginate(sp.current_user_saved_albums, key="items", limit=50):
        album = item.get("album") or {}
        data = {
            "added_at": item.get("added_at"),
            "album_name": album.get("name"),
            "album_id": album.get("id"),
            "album_uri": album.get("uri"),
            "album_type": album.get("album_type"),
            "release_date": album.get("release_date"),
            "total_tracks": album.get("total_tracks"),
            "artist_names": safe_join_names(album.get("artists") or []),
            "label": album.get("label"),
            "popularity": album.get("popularity"),
        }
        safe_row_append(rows, data, COLUMNS_ALL, ctx=f"album:{album.get('id')}", errors_counter=ERR["saved_albums"])
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("saved_albums"))
    return df

def export_followed_artists(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    after = None
    while True:
        page = sp.current_user_followed_artists(limit=50, after=after)
        artists = (page.get("artists") or {}).get("items") or []
        for a in artists:
            data = {
                "artist_id": a.get("id"),
                "artist_uri": a.get("uri"),
                "name": a.get("name"),
                "genres": ", ".join(a.get("genres") or []),
                "followers": ((a.get("followers") or {}).get("total")),
                "popularity": a.get("popularity"),
            }
            safe_row_append(rows, data, COLUMNS_ALL, ctx=f"artist:{a.get('id')}", errors_counter=ERR["followed_artists"])
        next_url = (page.get("artists") or {}).get("next")
        after = ((page.get("artists") or {}).get("cursors") or {}).get("after")
        if not next_url:
            break
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("followed_artists"))
    return df

def export_saved_shows(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    try:
        for item in paginate(sp.current_user_saved_shows, key="items", limit=50):
            show = item.get("show") or {}
            data = {
                "added_at": item.get("added_at"),
                "show_name": show.get("name"),
                "show_id": show.get("id"),
                "show_uri": show.get("uri"),
                "publisher": show.get("publisher"),
                "total_episodes": show.get("total_episodes"),
                "languages": ", ".join(show.get("languages") or []),
                "media_type": show.get("media_type"),
            }
            safe_row_append(rows, data, COLUMNS_ALL, ctx=f"show:{show.get('id')}", errors_counter=ERR["saved_shows"])
    except Exception:
        pass  # region/account without podcast API access
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    if not df.empty:
        save_csv_json(df, _basepath("saved_shows"))
    return df

def export_saved_episodes(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    try:
        for item in paginate(sp.current_user_saved_episodes, key="items", limit=50):
            ep = item.get("episode") or {}
            show = ep.get("show") or {}
            data = {
                "added_at": item.get("added_at"),
                "episode_name": ep.get("name"),
                "episode_id": ep.get("id"),
                "episode_uri": ep.get("uri"),
                "release_date": ep.get("release_date"),
                "duration_ms": ep.get("duration_ms"),
                "explicit": ep.get("explicit"),
                "show_name": show.get("name"),
                "show_id": show.get("id"),
            }
            safe_row_append(rows, data, COLUMNS_ALL, ctx=f"episode:{ep.get('id')}", errors_counter=ERR["saved_episodes"])
    except Exception:
        pass
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    if not df.empty:
        save_csv_json(df, _basepath("saved_episodes"))
    return df

def export_top_items(sp: spotipy.Spotify) -> Dict[str, pd.DataFrame]:
    out = {}
    ranges = {"4w": "short_term", "6m": "medium_term", "all": "long_term"}

    for tag, time_range in ranges.items():
        # Top artists
        arts = []
        for offset in range(0, 100, 50):
            page = sp.current_user_top_artists(limit=50, offset=offset, time_range=time_range)
            for a in page.get("items", []):
                data = {
                    "rank": len(arts) + 1,
                    "artist_id": a.get("id"),
                    "artist_uri": a.get("uri"),
                    "name": a.get("name"),
                    "genres": ", ".join(a.get("genres") or []),
                    "followers": ((a.get("followers") or {}).get("total")),
                    "popularity": a.get("popularity"),
                }
                safe_row_append(arts, data, COLUMNS_ALL, ctx=f"top_artist:{time_range}:{a.get('id')}", errors_counter=ERR["top"])
            if not page.get("next"): break
        df_a = pd.DataFrame(arts, columns=COLUMNS_ALL)
        save_csv_json(df_a, _basepath(f"top_artists_{tag}"))
        out[f"top_artists_{tag}"] = df_a

        # Top tracks
        trks = []
        for offset in range(0, 100, 50):
            page = sp.current_user_top_tracks(limit=50, offset=offset, time_range=time_range)
            for t in page.get("items", []):
                album = t.get("album") or {}
                data = {
                    "rank": len(trks) + 1,
                    "track_id": t.get("id"),
                    "track_uri": t.get("uri"),
                    "track_name": t.get("name"),
                    "isrc": (t.get("external_ids") or {}).get("isrc"),
                    "artist_names": safe_join_names(t.get("artists") or []),
                    "album_name": album.get("name"),
                    "album_id": album.get("id"),
                    "release_date": album.get("release_date"),
                    "popularity": t.get("popularity"),
                    "duration_ms": t.get("duration_ms"),
                    "explicit": t.get("explicit"),
                }
                safe_row_append(trks, data, COLUMNS_ALL, ctx=f"top_track:{time_range}:{t.get('id')}", errors_counter=ERR["top"])
            if not page.get("next"): break
        df_t = pd.DataFrame(trks, columns=COLUMNS_ALL)
        save_csv_json(df_t, _basepath(f"top_tracks_{tag}"))
        out[f"top_tracks_{tag}"] = df_t

    return out

def export_recently_played(sp: spotipy.Spotify) -> pd.DataFrame:
    rows = []
    items = (sp.current_user_recently_played(limit=50).get("items", []))
    for it in items:
        t = it.get("track") or {}
        album = t.get("album") or {}
        data = {
            "played_at": it.get("played_at"),
            "track_name": t.get("name"),
            "artist_names": safe_join_names(t.get("artists") or []),
            "album_name": album.get("name"),
            "album_id": album.get("id"),
            "track_id": t.get("id"),
            "track_uri": t.get("uri"),
            "popularity": t.get("popularity"),
            "duration_ms": t.get("duration_ms"),
            "explicit": t.get("explicit"),
        }
        safe_row_append(rows, data, COLUMNS_ALL, ctx=f"recent:{t.get('id')}", errors_counter=ERR["recent"])
    df = pd.DataFrame(rows, columns=COLUMNS_ALL)
    save_csv_json(df, _basepath("recently_played"))
    return df



# ========= MAIN =========
def main():

    sp = auth_client()
    try:
        me = sp.me()
        print("DEBUG user id:", me["id"], "email:", me.get("email"))
    except Exception as e:
        print("DEBUG token seems invalid:", e)
        raise
    print(me)

    print(f"Hi, {me.get('display_name') or me.get('id')} — exporting your library…")

    print("→ Liked Songs")
    df1 = export_liked_songs(sp); print(f"   {len(df1)} rows → {OUT['liked_songs']}")

    print("→ Playlists & Tracks")
    dfp = export_playlists(sp); print(f"   {len(dfp)} playlists → {OUT['playlists']}")
    if not dfp.empty:
        dft = export_playlist_tracks(sp, dfp); print(f"   {len(dft)} rows → {OUT['playlist_tracks']}")

    print("→ Saved Albums")
    dfa = export_saved_albums(sp); print(f"   {len(dfa)} rows → {OUT['saved_albums']}")

    print("→ Followed Artists")
    dff = export_followed_artists(sp); print(f"   {len(dff)} rows → {OUT['followed_artists']}")

    print("→ Saved Shows / Episodes (if available)")
    dfs = export_saved_shows(sp); print(f"   {0 if dfs is None else len(dfs)} rows → {OUT['saved_shows'] if dfs is not None and not dfs.empty else '(skipped)'}")
    dfe = export_saved_episodes(sp); print(f"   {0 if dfe is None else len(dfe)} rows → {OUT['saved_episodes'] if dfe is not None and not dfe.empty else '(skipped)'}")

    print("→ Top Artists/Tracks (4w, 6m, all)")
    _ = export_top_items(sp)
    print(f"   wrote: top_* CSVs")

    # print("→ Recently Played")
    # dfr = export_recently_played(sp); print(f"   {len(dfr)} rows → {OUT['recently_played']}")

    print("Done ✨  All CSVs are in the current folder.")
    print("------------------------------------------------")
    save_error_log()
    print("Error counts:", {k: v["count"] for k, v in ERR.items()})



if __name__ == "__main__":
    try:
        main()
    except spotipy.SpotifyException as e:
        print(f"Spotify API error: {e}")
        if getattr(e, 'http_status', None) == 429:
            print("Hit a rate limit. Try again in a minute.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
