#!/usr/bin/env python3
"""
Automatic Tidal Playlist Generator
Migrates Spotify playlists to Tidal using ISRC codes
"""

import csv
import os
import sys
import webbrowser
import re
import unicodedata
from typing import List, Dict, Set, Tuple
import tidalapi
import pandas as pd


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching - lowercase, remove punctuation, handle common variations"""
    if not text:
        return ""
    
    # Normalize unicode characters (e.g., KUČKA -> KUCKA)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove content in parentheses
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Handle common variations
    text = re.sub(r'\b(feat|featuring|ft)\.?\s', '', text)  # Remove featuring variations
    text = re.sub(r'\b(remix|remaster|remastered)\b', '', text)  # Remove remix/remaster
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    
    return text


def clean_track_name(track_name: str) -> str:
    """Clean track name by removing parentheses content and normalizing unicode"""
    if not track_name:
        return ""
    
    # Remove content in parentheses
    cleaned = re.sub(r'\([^)]*\)', '', track_name)
    
    # Normalize unicode
    cleaned = unicodedata.normalize('NFD', cleaned)
    cleaned = ''.join(char for char in cleaned if unicodedata.category(char) != 'Mn')
    
    return cleaned.strip()


def get_primary_artist(artist_string: str) -> str:
    """Extract the primary artist from a string of multiple artists"""
    if not artist_string:
        return ""
    
    # Split by common separators and take the first artist
    separators = [', ', ' & ', ' and ', ' feat. ', ' feat ', ' featuring ', ' ft. ', ' ft ']
    
    primary_artist = artist_string
    for separator in separators:
        if separator in primary_artist.lower():
            primary_artist = primary_artist.split(separator)[0]
            break
    
    return primary_artist.strip()


def fuzzy_match_words(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """Check if two texts match based on word overlap percentage"""
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    
    if not words1 or not words2:
        return False
    
    # Find intersection of words
    common_words = words1.intersection(words2)
    
    # Calculate match percentage based on the longer text
    max_words = max(len(words1), len(words2))
    match_percentage = len(common_words) / max_words
    
    return match_percentage >= threshold


def search_track_in_album(session: tidalapi.Session, track: Dict, cleaned_track_name: str) -> tidalapi.Track:
    """Search for track within its album using cleaned track name"""
    if not track['album_name']:
        return None
    
    try:
        # Search for the album
        album_query = f"{track['album_name']} {track['artist_names']}"
        album_results = session.search(album_query, models=[tidalapi.Album])
        
        if album_results['albums']:
            # Check tracks in the first few albums
            for album in album_results['albums'][:3]:
                try:
                    album_tracks = album.tracks()
                    for album_track in album_tracks:
                        # Try fuzzy matching on cleaned track names
                        if fuzzy_match_words(album_track.name, cleaned_track_name):
                            return album_track
                except:
                    continue
    except:
        pass
    
    return None


def find_best_track_match(session: tidalapi.Session, track: Dict) -> tidalapi.Track:
    """Find the best matching track using improved 6-step strategy"""
    
    # Step 1: Search by original track name and artist
    search_query = f"{track['track_name']} {track['artist_names']}"
    search_results = session.search(search_query, models=[tidalapi.Track])
    
    if search_results['tracks']:
        # Step 1: ISRC matching if available
        for result_track in search_results['tracks'][:5]:
            try:
                if hasattr(result_track, 'isrc') and result_track.isrc == track['isrc']:
                    return result_track
            except:
                pass
        
        # Step 2: Exact name matching
        for result_track in search_results['tracks'][:5]:
            if result_track.name.lower().strip() == track['track_name'].lower().strip():
                return result_track
    
    # Step 3: Clean track name and search with modified name
    cleaned_track_name = clean_track_name(track['track_name'])
    if cleaned_track_name != track['track_name']:
        # Search again with cleaned name
        search_query = f"{cleaned_track_name} {track['artist_names']}"
        search_results = session.search(search_query, models=[tidalapi.Track])
    
    if search_results['tracks']:
        # Step 3: Fuzzy word match on search results (with cleaned names)
        for result_track in search_results['tracks'][:5]:
            if fuzzy_match_words(result_track.name, cleaned_track_name):
                return result_track
    
    # Step 4: Artist name simplification
    primary_artist = get_primary_artist(track['artist_names'])
    if primary_artist != track['artist_names']:
        # Search with primary artist only
        search_query = f"{cleaned_track_name} {primary_artist}"
        simplified_results = session.search(search_query, models=[tidalapi.Track])
        
        if simplified_results['tracks']:
            # Try fuzzy matching with simplified search
            for result_track in simplified_results['tracks'][:5]:
                if fuzzy_match_words(result_track.name, cleaned_track_name):
                    return result_track
    
    # Step 5: Album search + fuzzy match with cleaned names
    album_match = search_track_in_album(session, track, cleaned_track_name)
    if album_match:
        return album_match
    
    # Step 6: Mark as not found
    return None


def welcome_message():
    """Display welcome message and instructions"""
    print("Welcome to the automatic Tidal playlist generator.")
    print("This program will re-create your selected playlists, based on your data downloaded from Spotify.")
    print()
    print("If you haven't downloaded your Spotify data using spotify_scrub.py, please do that now.")
    print()


def authenticate_tidal():
    """Authenticate with Tidal using OAuth2"""
    print("Please follow the steps in your browser to authenticate with your Tidal profile.")
    print()
    
    session = tidalapi.Session()
    
    try:
        # Get login info and future from OAuth
        login, future = session.login_oauth()
        
        # Try multiple approaches to open browser
        login_url = "https://"+login.verification_uri_complete
        print(f"Opening browser to: {login_url}")
        
        try:
            webbrowser.open(login_url)
        except:
            # Fallback: try different browser opening methods
            try:
                import subprocess
                import platform
                if platform.system() == "Darwin":  # macOS
                    subprocess.call(["open", login_url])
                elif platform.system() == "Windows":
                    subprocess.call(["start", login_url], shell=True)
                else:  # Linux
                    subprocess.call(["xdg-open", login_url])
            except:
                print(f"Could not automatically open browser. Please manually visit: {login_url}")
        
        print("Waiting for you to complete authentication in your browser...")
        
        # Wait for authentication to complete
        future.result()
        
        # Check if login was successful
        if session.check_login():
            print("Authentication successful!")
            return session
        else:
            print("Authentication failed. Please try again.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        sys.exit(1)


def load_spotify_data(filename: str = "spotify csvs/playlist_tracks.csv") -> pd.DataFrame:
    """Load Spotify playlist data from CSV"""
    if not os.path.exists(filename):
        print(f"Error: {filename} not found in current directory.")
        print("Please ensure your Spotify data file is named 'playlist_tracks.csv' and located in directory 'spotify csvs'")
        sys.exit(1)
    
    try:
        df = pd.read_csv(filename)
        return df
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")
        sys.exit(1)


def get_unique_playlists(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Extract unique playlists from the dataframe"""
    # Get unique playlist_id and playlist_name combinations
    unique_playlists = df[['playlist_id', 'playlist_name']].drop_duplicates()
    # Sort by playlist name for consistent ordering
    unique_playlists = unique_playlists.sort_values('playlist_name')
    
    return [(row['playlist_id'], row['playlist_name']) for _, row in unique_playlists.iterrows()]


def display_playlists(playlists: List[Tuple[str, str]]) -> None:
    """Display numbered list of playlists"""
    print("Here's all the playlists I can auto-create:")
    for i, (playlist_id, playlist_name) in enumerate(playlists, 1):
        print(f"{i}. {playlist_name}")
    print()


def parse_playlist_selection(user_input: str, max_num: int) -> Set[int]:
    """Parse user's playlist selection input"""
    selected = set()
    
    # Clean input - remove spaces and split by comma
    parts = [part.strip() for part in user_input.split(',')]
    
    for part in parts:
        if '-' in part:
            # Handle range like "2-5"
            try:
                start, end = part.split('-')
                start, end = int(start.strip()), int(end.strip())
                if 1 <= start <= max_num and 1 <= end <= max_num and start <= end:
                    selected.update(range(start, end + 1))
                else:
                    print(f"Warning: Invalid range {part}, skipping")
            except ValueError:
                print(f"Warning: Invalid range format {part}, skipping")
        else:
            # Handle single number
            try:
                num = int(part.strip())
                if 1 <= num <= max_num:
                    selected.add(num)
                else:
                    print(f"Warning: Number {num} out of range, skipping")
            except ValueError:
                print(f"Warning: Invalid number {part}, skipping")
    
    return selected


def get_playlist_tracks(df: pd.DataFrame, playlist_id: str) -> List[Dict]:
    """Get all tracks for a specific playlist"""
    playlist_tracks = df[df['playlist_id'] == playlist_id].copy()
    
    # Convert to list of dictionaries for easier processing
    tracks = []
    for _, row in playlist_tracks.iterrows():
        tracks.append({
            'playlist_name': row['playlist_name'],
            'track_name': row['track_name'],
            'artist_names': row['artist_names'],
            'isrc': row['isrc'] if pd.notna(row['isrc']) else None,
            'album_name': row['album_name']
        })
    
    return tracks


def write_not_found_track(track: Dict, reason: str, filename: str = "not_found.csv"):
    """Append a not-found track to the CSV file"""
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['playlist_name', 'track_name', 'artist_names', 'album_name', 'isrc', 'reason']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'playlist_name': track['playlist_name'],
            'track_name': track['track_name'],
            'artist_names': track['artist_names'],
            'album_name': track['album_name'],
            'isrc': track['isrc'] if track['isrc'] else '',
            'reason': reason
        })


def get_unique_playlist_name(user, desired_name: str) -> str:
    """Get a unique playlist name, adding version numbers if needed"""
    existing_playlists = user.playlists()
    existing_names = {pl.name for pl in existing_playlists}
    
    # If the desired name doesn't exist, use it as-is
    if desired_name not in existing_names:
        return desired_name
    
    # Otherwise, find the next available version number
    version = 2
    while True:
        versioned_name = f"{desired_name} version {version}"
        if versioned_name not in existing_names:
            return versioned_name
        version += 1


def create_tidal_playlist(session: tidalapi.Session, playlist_name: str, tracks: List[Dict]) -> List[Dict]:
    """Create a Tidal playlist and add tracks, return list of not found tracks"""
    print(f"Generating playlist '{playlist_name}'!")
    
    not_found = []
    total_tracks = len(tracks)
    processed_count = 0
    
    try:
        user = session.user
        
        # Get a unique playlist name (add version numbers if needed)
        unique_playlist_name = get_unique_playlist_name(user, playlist_name)
        
        if unique_playlist_name != playlist_name:
            print(f"Playlist '{playlist_name}' already exists. Creating '{unique_playlist_name}' instead.")
        
        # Create the new playlist with unique name
        playlist = user.create_playlist(unique_playlist_name, "Migrated from Spotify")
        added_tracks = set()  # Track which songs we've successfully added
        
        for track_index, track in enumerate(tracks):
            processed_count += 1
            
            # Update progress in place (use the unique name for consistency)
            print(f"\rGenerating playlist '{unique_playlist_name}'! ({processed_count}/{total_tracks})", end='', flush=True)
            
            if not track['isrc']:
                # No ISRC available
                write_not_found_track(track, "isrc blank in input")
                not_found.append({
                    'name': track['track_name'],
                    'artist': track['artist_names'],
                    'reason': "isrc blank in input"
                })
                continue
            
            # Track identifier for resume functionality
            track_id_key = f"{track['track_name']}|{track['artist_names']}"
            
            # Skip if we already added this track (for resume functionality)
            if track_id_key in added_tracks:
                continue
            
            try:
                # Use improved fuzzy matching to find track
                found_track = find_best_track_match(session, track)
                
                if found_track:
                    # Found track, now try to add to playlist
                    retry_count = 0
                    max_retries = 1
                    
                    while retry_count <= max_retries:
                        try:
                            playlist.add([found_track.id])
                            added_tracks.add(track_id_key)  # Mark as successfully added
                            break  # Success, exit retry loop
                            
                        except Exception as add_error:
                            error_str = str(add_error)
                            
                            # Check if it's a 412 error
                            if "412" in error_str and "Client Error" in error_str:
                                print(f"\n\nRe-authentication required for track: {track['track_name']} by {track['artist_names']}")
                                print("Would you like to authenticate again? (y/n): ", end='')
                                
                                user_response = input().strip().lower()
                                
                                if 'y' in user_response:
                                    print("Re-authenticating...")
                                    
                                    # Step 1: Check and re-authenticate
                                    if not session.check_login():
                                        session = authenticate_tidal()
                                    
                                    # Update references after re-auth
                                    user = session.user
                                    
                                    # Find the playlist again (it might have a new reference)
                                    user_playlists = user.playlists()
                                    playlist = None
                                    for pl in user_playlists:
                                        if pl.name == unique_playlist_name:
                                            playlist = pl
                                            break
                                    
                                    if not playlist:
                                        raise Exception(f"Could not find playlist '{unique_playlist_name}' after re-authentication")
                                    
                                    retry_count += 1
                                    print(f"Retrying track: {track['track_name']}")
                                    continue  # Retry the add operation
                                else:
                                    print("Exiting program as requested.")
                                    sys.exit(0)
                            else:
                                # Not a 412 error, treat as regular error
                                raise add_error
                    
                    # If we exhausted retries without success
                    if track_id_key not in added_tracks:
                        write_not_found_track(track, f"error after retries: {str(add_error)}")
                        not_found.append({
                            'name': track['track_name'],
                            'artist': track['artist_names'],
                            'reason': f"error after retries: {str(add_error)}"
                        })
                else:
                    # Track not found on Tidal
                    write_not_found_track(track, "track not found on Tidal")
                    not_found.append({
                        'name': track['track_name'],
                        'artist': track['artist_names'],
                        'reason': "track not found on Tidal"
                    })
                    
            except Exception as e:
                # Error searching track (not adding to playlist)
                write_not_found_track(track, f"search error: {str(e)}")
                not_found.append({
                    'name': track['track_name'],
                    'artist': track['artist_names'],
                    'reason': f"search error: {str(e)}"
                })
        
        # Clear the progress line and move to next line
        print()
        
        return not_found
        
    except Exception as e:
        print(f"\nError creating playlist '{unique_playlist_name}': {str(e)}")
        return tracks  # Return all tracks as not found


def display_not_found_songs(not_found: List[Dict], playlist_name: str):
    """Display not found songs for a playlist"""
    print(f"Playlist '{playlist_name}' has been created.")
    
    if not_found:
        print("The following songs were not found on Tidal:")
        for song in not_found:
            print(f"  • {song['name']} by {song['artist']} ({song['reason']})")
    else:
        print("All songs were successfully added!")
    
    print()


def main():
    """Main function"""
    welcome_message()
    
    # Authenticate with Tidal
    session = authenticate_tidal()
    print()
    
    # Load Spotify data
    df = load_spotify_data()
    
    # Get unique playlists
    playlists = get_unique_playlists(df)
    
    if not playlists:
        print("No playlists found in the data file.")
        sys.exit(1)
    
    # Display playlists
    display_playlists(playlists)
    
    # Get user selection
    while True:
        user_input = input("Please select your playlist by number.\n Please try limit your selection to 5 playlists or less at a time.\nFor multiple playlists, separate by comma, or use the dash symbol (-) to indicate a range: ").strip()
        
        if not user_input:
            print("Please enter a valid selection.")
            continue
        
        selected_indices = parse_playlist_selection(user_input, len(playlists))
        
        if not selected_indices:
            print("No valid playlists selected. Please try again.")
            continue
        
        break
    
    print()
    
    # Process selected playlists
    selected_playlists = [playlists[i-1] for i in sorted(selected_indices)]
    
    for playlist_id, playlist_name in selected_playlists:
        # Get tracks for this playlist
        tracks = get_playlist_tracks(df, playlist_id)
        
        # Create playlist on Tidal
        not_found = create_tidal_playlist(session, playlist_name, tracks)
        
        # Display results
        display_not_found_songs(not_found, playlist_name)
    
    print("Playlist migration complete!")
    if os.path.exists("not_found.csv"):
        print("Check 'not_found.csv' for a complete list of songs that couldn't be migrated.")


if __name__ == "__main__":
    main()