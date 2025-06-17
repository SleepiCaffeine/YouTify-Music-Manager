import os, json, sqlite3, hashlib
import utility as util

class DatabaseConnection:
  def __init__(self, path_to_db : str = os.path.join(util.DATA_LOCATION, 'schema.db')):
    self._connection = sqlite3.connect(path_to_db)
    self._connection.execute("PRAGMA foreign_keys = ON;")
  
  def add_song(
      self,
      path_to_song   : str,
      original_title : str | None = None,
      user_title     : str | None = None):
    

    if not os.path.exists(path_to_song):
      print(f"Cannot locate {path_to_song}!")
      return

    file_size = os.path.getsize(path_to_song)
    file_hash = self._get_song_hash(path_to_song)

    cursor = self._connection.cursor()

    cursor.execute(
    "INSERT INTO songs (file_path, file_hash, original_title, user_title," \
    "duration, file_size, date_added, date_modified)" \
    "VALUES"
    "(?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
      (
      path_to_song,
      self._get_song_hash(path_to_song),
      original_title if original_title is not None else os.path.basename(path_to_song),
      user_title if user_title is not None else os.path.basename(path_to_song),
      "",        # get duration in here puhleaSE 
      file_size
      )
    )


  # Add songs [DONE]
  # Move entire folder
  # Delete Song [DONE]
  # Update song description [DONE]
  # Update song User Title


  def delete_song(
      self,
      path_to_song   : str | None = None,
      song_id        : int | None = None
      ):
    # As always, check the validity of the path:
    if path_to_song and not os.path.exists(path_to_song):
      print(f"Failed to find: {path_to_song}")
      return
    
    if song_id and song_id < 0:
      print(f"Received negative song ID: {song_id}")
      return

    # We have to first find the song:
    # The only way to do that is by specifically deleting that path
    cursor = self._connection.cursor()

    if path_to_song is not None: 
      # Now, it would be safer to sanitize this input, but since I expect all of this
      # to come from internal calls, I fairly certain that SQL exploits are not valid file syntax
      cursor.execute(f"DELETE FROM songs WHERE file_path = ?", (path_to_song))

    elif song_id is not None:
      cursor.execute(f"DELETE FROM songs WHERE id = ?", (str(song_id)))
    
    else:
      print("No song path or ID provided, query ignored.")
      return
    

  def update_song_description(
      self,
      new_description : str,
      path_to_song : str | None = None,
      song_id      : int | None = None):
    
    # As always, check the validity of the path:
    if path_to_song and not os.path.exists(path_to_song):
      print(f"Failed to find: {path_to_song}")
      return
    
    if song_id and song_id < 0:
      print(f"Received negative song ID: {song_id}")
      return 

    # We have to first find the song:
    # The only way to do that is by specifically deleting that path
    cursor = self._connection.cursor()

    if path_to_song is not None: 
      # Now, it would be safer to sanitize this input, but since I expect all of this
      # to come from internal calls, I fairly certain that SQL exploits are not valid file syntax
      cursor.execute(f"UPDATE songs set description = ? WHERE file_path = ?", (new_description, path_to_song))

    elif song_id is not None:
      cursor.execute(f"UPDATE songs set description = ? WHERE file_path = ?", (new_description, str(song_id)))
    
    else:
      print("No song path or ID provided, query ignored.")
      return


  def move_songs_to_new_folder(self, old_path : str, new_path : str):
    if not os.path.exists(new_path):
      print(f"New path ({new_path}) doesn't exist")
      return

    

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
          