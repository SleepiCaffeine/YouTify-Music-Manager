import os
import json
import sqlite3
import hashlib
import threading
import atexit
import utility as util
from typing import Dict, Any, Optional, Tuple, List

class DatabaseConnection:
  def __init__(self, path_to_db : str = os.path.join(util.DATA_LOCATION, 'schema.db')):
    self.db_path = path_to_db
    self._lock = threading.Lock()  # Thread safety
    self._connection = self._create_connection() 
    
    # Ensure connection closes when app shuts down
    atexit.register(self.close)
  

  def _create_connection(self) -> sqlite3.Connection:
    """Initialize the persistent connection"""
    connection = sqlite3.connect(
      self.db_path,
      check_same_thread=False,  # Allow use from multiple threads
      timeout=20.0              # Wait up to 20 seconds for locks
    )
    
    # Configure connection
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection
  

  def get_connection(self) -> sqlite3.Connection:
    """Get the persistent connection"""
    if self._connection is None:
       self._connection = self._create_connection()
    return self._connection


  def close(self):
    if self.get_connection():
      self.get_connection().close()
      self._connection = None


  def create_song(
      self,
      path_to_song   : str,
      original_title : str = "",
      user_title     : str = "",
      duration       : int = 0,
      note           : str = "") -> Optional[int]:
    """Add a new song to the database. Returns song ID."""
    with self._lock:
      if not os.path.exists(path_to_song):
        raise FileNotFoundError(f"File not found: {path_to_song}")

      file_size = os.path.getsize(path_to_song)
      file_hash = self._get_song_hash(path_to_song)

      cursor = self.get_connection().cursor()


      cursor.execute(
      "INSERT INTO songs (file_path, original_title, user_title," \
      "duration, file_size, file_hash, user_note, date_added, date_modified)" \
      "VALUES"
      "(?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (
        path_to_song,
        original_title if len(original_title) > 0 else os.path.basename(path_to_song),
        user_title if len(user_title) > 0 else os.path.basename(path_to_song),
        duration,
        file_size,
        file_hash,
        note
        )
    )
      
    self.get_connection().commit()
    return cursor.lastrowid


  def get_song(
    self,
    song_id : int) -> Optional[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()

    if row:
      columns = [desc[0] for desc in cursor.description]
      return dict(zip(columns, row))
    return None


  def get_songs_by_title(
    self,
    title : str,
    exact_match : bool = False
  ) -> List[Dict[str, Any]]:
   """Search songs by title (user_title or original_title)"""
   cursor = self.get_connection().cursor()
   statement = f"""
      SELECT * FROM songs
      WHERE user_title {"=" if exact_match else "LIKE"} ? OR original_title {"=" if exact_match else "LIKE"} ?
    """
   if exact_match:
     title = f"%{title}%"
    
   cursor.execute(statement, (title, title))
   columns = [desc[0] for desc in cursor.description]
   return [dict(zip(columns, row)) for row in cursor.fetchall()]


  def get_songs_by_playlist_title(
      self,
      playlist_title : str 
  ):
    cursor = self.get_connection().cursor()
    cursor.execute("""
        SELECT s.*
        FROM songs s
        JOIN playlists_songs ps on s.id = ps.song_id
        JOIN playlists p on ps.playlist_id = p.id
        WHERE p.name = ?
      """, (playlist_title,))
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


  def get_songs_by_playlist_id(
      self,
      playlist_id : int
  ) -> List[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("""
        SELECT s.*
        FROM songs s
        JOIN playlists_songs ps on s.id = ps.song_id
        JOIN playlists p on ps.playlist_id = p.id
        WHERE p.id = ?
      """, (playlist_id,))
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

  def get_songs_NOT_in_playlist_by_id(
      self,
      playlist_id : int
  ) -> List[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("""
        SELECT s.*
        FROM songs s
        WHERE NOT EXISTS (
          SELECT 1
          FROM playlists_songs ps
          WHERE ps.song_id = s.id
          AND ps.playlist_id = ?
        )
      """, (playlist_id,))
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


  def get_all_songs(self) -> List[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("SELECT * from songs ORDER BY user_title")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


  def update_song(self, song_id: int, **kwargs) -> bool:
    """Update song fields. Returns True if updated, False if song not found."""
    allowed_fields = {'original_title', 'user_title', 'duration', 'user_note', 'play_count'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
      return False
        
    with self._lock:
      set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
      cursor = self.get_connection().cursor()
      cursor.execute(f"UPDATE songs SET {set_clause} WHERE id = ?", 
                     list(updates.values()) + [song_id])
      self.get_connection().commit()
      return cursor.rowcount > 0
  

  def delete_song(
      self,
      song_id : int) -> bool:
     """Delete a song and remove from all playlists. Returns True if deleted."""
     with self._lock:
      cursor = self.get_connection().cursor()
      cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
      self.get_connection().commit()
      return cursor.rowcount > 0
    
  # Since this will be one of the more often update operations,
  # I decided to put it in its own function
  def increment_play_count(self, song_id: int) -> bool:
    """Increment the play count for a song"""
    with self._lock:
      cursor = self.get_connection().cursor()
      cursor.execute("UPDATE songs SET play_count = play_count + 1 WHERE id = ?", (song_id,))
      self.get_connection().commit()
      return cursor.rowcount > 0


  # To be used later with self.delete_song()
  def find_duplicates(self) -> List[List[Dict[str, Any]]]:
    """Find songs with the same file hash (potential duplicates)"""
    cursor = self.get_connection().cursor()
    cursor.execute("""
        SELECT file_hash, COUNT(*) as count 
        FROM songs 
        WHERE file_hash IS NOT NULL 
        GROUP BY file_hash 
        HAVING COUNT(*) > 1
    """)
    
    duplicate_groups = []
    for hash_value, _ in cursor.fetchall():
      cursor.execute("SELECT * FROM songs WHERE file_hash = ?", (hash_value,))
      columns = [desc[0] for desc in cursor.description]
      group = [dict(zip(columns, row)) for row in cursor.fetchall()]
      duplicate_groups.append(group)
  
    return duplicate_groups


  def update_songs_to_new_folder(
    self,
    new_path : str,
    old_path : str | None = None):
    if not os.path.exists(new_path):
      print(f"New path ({new_path}) doesn't exist")
      return
    
    cursor = self.get_connection().cursor()

    # Assume to change all paths:
    if old_path is None:
      cursor.execute("UPDATE songs SET file_path = ?", (new_path))
    
    else:
      cursor.execute("UPDATE songs SET file_path = ? WHERE file_path = ?", (new_path, old_path))


  def create_playlist(
      self,
      name : str,
      description : str = ""
  ) -> Optional[int]:
    """Create a new playlist. Returns playlist ID."""
    with self._lock:
      cursor = self.get_connection().cursor()
      cursor.execute("INSERT INTO playlists (name, description) VALUES (?, ?)", (name, description))
      self.get_connection().commit()
      return cursor.lastrowid


  def get_playlist(
    self,
    playlist_id : int
  ) -> Optional[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
    row = cursor.fetchone()

    if row:
      columns = [desc[0] for desc in cursor.description]
      return dict(zip(columns, row))
    return None


  def get_all_playlists(self) -> List[Dict[str, Any]]:
    cursor = self.get_connection().cursor()
    cursor.execute("SELECT * from playlists ORDER BY name")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

  
  def update_playlist(self, playlist_id: int, **kwargs) -> bool:
    """Update playlist fields. Returns True if updated, False if playlist not found."""
    allowed_fields = {'name', 'description', 'total_duration', 'song_count'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
      return False
        
    with self._lock:
      set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
      cursor = self.get_connection().cursor()
      cursor.execute(f"UPDATE songs SET {set_clause} WHERE id = ?", 
                     list(updates.values()) + [playlist_id])
      self.get_connection().commit()
      return cursor.rowcount > 0


  def add_song_to_playlist(
      self,
      playlist_id : int,
      song_id     : int,
      position    : int = -1
  ) -> bool:
    """Add song to playlist at specified position (or end if -1). Returns True if added."""
    with self._lock:
      cursor = self.get_connection().cursor()
      
      # Verify playlist and song exist
      cursor.execute("SELECT id FROM playlists WHERE id = ?", (playlist_id,))
      if not cursor.fetchone():
        return False
      cursor.execute("SELECT id FROM songs WHERE id = ?", (song_id,))
      if not cursor.fetchone():
        return False
      
      # Get current max position if no position specified
      if position == -1:
        cursor.execute("SELECT COALESCE(MAX(position), 0) FROM playlists_songs WHERE playlist_id = ?", 
                      (playlist_id,))
        position = cursor.fetchone()[0] + 1
      else:
        # Shift existing songs down to make room
        cursor.execute("""
            UPDATE playlists_songs 
            SET position = position + 1 
            WHERE playlist_id = ? AND position >= ?
        """, (playlist_id, position))
      
      try:
        cursor.execute("""
            INSERT INTO playlists_songs (playlist_id, song_id, position) 
            VALUES (?, ?, ?)
        """, (playlist_id, song_id, position))
        self.get_connection().commit()
        return True
      
      except sqlite3.IntegrityError:
        self.get_connection().rollback()
        return False  # Duplicate song in playlist

  def remove_song_from_playlist(
      self,
      song_id : int,
  ) -> bool:
    with self._lock:
      cursor = self.get_connection().cursor()
      cursor.execute("DELETE FROM playlists_songs WHERE song_id = ?", (song_id,))
      self.get_connection().commit()
      
      if cursor.lastrowid:
        return cursor.lastrowid > 0
      return False

  def delete_playlist(
    self,
    playlist_id : int
  ) -> bool:
    with self._lock:
      cursor = self.get_connection().cursor()
      cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
      self.get_connection().commit()
      
      if cursor.lastrowid:
        return cursor.lastrowid > 0
      return False


  def create_tables(self):
    with self._lock:
      try:
        cursor = self.get_connection().cursor()
        with open(os.path.join(util.DATA_LOCATION, 'table_init.sql')) as f:
          cursor.execute(f.read())
          self.get_connection().commit()
          f.close()
      except Exception as e:
        raise e


  def clear_all(self):
    with self._lock:
      try:
        cursor = self.get_connection().cursor()
        cursor.execute("DELETE FROM songs")
        cursor.execute("DELETE FROM playlists")
        cursor.execute("DELETE FROM playlists_songs")
        self.get_connection().commit()
      except Exception as e:
        raise e


  def _get_song_hash(self, path_to_song : str) -> str | None:
    if not os.path.exists(path_to_song):
        print(f"Cannot locate {path_to_song}!")
        return
    md5_hash = hashlib.md5()
    try:
      with open(path_to_song, "rb") as f:
        # Read first and last 8 KB
        md5_hash.update(f.read(8192))
        f.seek(-8192, 2)
        md5_hash.update(f.read(8192))
        
    except (OSError, IOError):
      # Try to open regardless, no limitations
      try:  
        md5_hash.update(f.read())
      except (OSError, IOError) as e:
        # welp, we tried
        print(f"Could not read {path_to_song}!\nError: {e}")
        return
      
    return md5_hash.hexdigest() 
          