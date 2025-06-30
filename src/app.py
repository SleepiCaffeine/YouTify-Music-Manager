from __future__ import annotations


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal, QUrl, QObject)
from PySide6.QtGui import (QCursor, QDesktopServices, QGuiApplication, QIcon,
                           QKeySequence, QShortcut, QStandardItem,
                           QStandardItemModel, QAction)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,
                               QCommandLinkButton, QDateTimeEdit, QDial,
                               QDialog, QDialogButtonBox, QFileSystemModel,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListView, QMenu, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton,
                               QScrollBar, QSizePolicy, QSlider, QSpinBox,
                               QStyleFactory, QTableWidget, QTabWidget,
                               QTextBrowser, QTextEdit, QToolBox, QToolButton,
                               QTreeView, QVBoxLayout, QWidget, QMainWindow, QFileDialog)

from PySide6.QtMultimedia import (QAudioDecoder, QAudioOutput, QMediaFormat, QAudio, QMediaPlayer)

import PySide6.QtAsyncio as QtAsyncio

import sys, random, os, asyncio, json, io, sqlite3
import re


import utility as util
import config
import logging
from typing import Dict, Any, Optional, Tuple, List
from playlist import (PlayListContainer, PlaylistElement)
from widgets import (MusicDownloadWidget, AudioPlayer, UIContainer) 
from database import DatabaseConnection





class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()

        self._audio_player  = AudioPlayer()
        self._db_connection = DatabaseConnection()
        
        # Initialize UI with all playlists to show to the user
        self._ui_container  = UIContainer(self, self._db_connection.get_all_playlists())
        

        self._ui_container._play_song_signal.connect(self.handlePlayButtonClick)
        self._ui_container._new_songs_downloaded.connect(self.update_with_new_songs)
        self._ui_container._request_songs_for_refresh.connect(self.send_playlist_songs_to_ui)
        self._ui_container._create_new_playlist_in_db.connect(self._create_new_playlist_in_db)
        self._ui_container._update_db_with_new_song_in_playlist.connect(self._add_new_song_to_playlist)
        self._ui_container._request_all_songs_to_add_to_playlist.connect(self._send_all_songs_to_AddSongWindow)

        self.setCentralWidget(self._ui_container)


    def closeEvent(self, event):
        self._audio_player._ensure_stopped()
        event.accept()

    def send_all_songs_to_ui(self):
        self._ui_container.refresh_playlist(self._db_connection.get_all_songs())

    def send_playlist_songs_to_ui(self, playlist_data : Dict[str, Any]):
        songs = self._db_connection.get_songs_by_playlist_id(playlist_data.get('id', -1))
        print(f"MAIN APP send_playlist_songs_to_ui: {songs}")

        self._ui_container.refresh_playlist(songs)

    def _send_all_songs_to_AddSongWindow(self, playlist_id : int):
        songs = self._db_connection.get_songs_NOT_in_playlist_by_id(playlist_id)
        print(f"MAIN APP _send_all_songs_to_AddSongWindow: {songs}")
        self._ui_container.send_all_songs_to_playlist_container_for_addSongWindow(songs)


    def update_with_new_songs(self, download_path : str):
        # At this point, new songs have been downloaded, but not yet added to the DB
        # This function checks what new files have been added to the folder
        # Could be reused to just add more songs

        logging.debug(f"Update called with: {download_path}")

        # Create a list of all the song locations
        ### [Technically original_title, and file_path do the same thing, but this is just for semantics] 
        all_current_songs = [song["file_path"] for song in self._db_connection.get_all_songs()]
        # Look at the file location to find any new ones
        for file in os.listdir(download_path):
            logging.debug(f"checking file: {file}")
            # If the file is an appropriate audio file

            if os.path.splitext(file)[1] in [".wav", ".mp3", ".webm"]:
                logging.debug("File valid format!")
                # If it isn't already in the table
                full_path = os.path.join(download_path, file)
                if full_path not in all_current_songs:
                    self._db_connection.create_song(full_path)
                else:
                    pass        
        self.send_all_songs_to_ui()


    def handlePlayButtonClick(self, song_id : int, song_path : str):
        # There are 3 possible states:
        # 1. The player is stopped (No song/Finished previous)
        # 2. It is paused
        # 3. It is playing

        # If the user is attempting to play a song with the same path as the current one,
        # This means that they're trying to either pause or unpause the song.

        if self._audio_player._curr_song_id == song_id:
            if self._audio_player._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._audio_player.pause_song()
            else:
                self._audio_player.play_song()
        
        # Otherwise, they're trying to play something else.

        else:
            self._ui_container._toggle_off_songs(song_id)
            self._audio_player._ensure_stopped()
            self._audio_player.set_source(song_id, song_path)
            self._audio_player.play_song()
    
    
    def update_songs_directory(self, path : str):
        # The received path was through file dialogue, so it should be valid
        # First clear the database, since all of the information is now invalid
        logging.debug(f"Called update_songs_directory with : {path}")
        self._db_connection.clear_all()
        # For each file
        for file in os.listdir(path):
            # Get only the filename
            filename = os.fsdecode(file)
            # And add it along with the whole path to the database
            self._db_connection.create_song(os.path.join(path, filename))

                    
    
    def set_audio_source(self, path : str):
        self._audio_player.set_source(path)

    
    def _make_unique_name(self, is_song : bool, template_name : str = "Untitled"):
        # Function to create a song that doesn't already exist in the tables

        all_names = []
        if is_song:
            all_names = [song["user_title"] for song in self._db_connection.get_all_songs()]
        else:
            all_names = [playlist["name"] for playlist in self._db_connection.get_all_playlists()]

        pattern = r'^(.+) \((\d+)\)$'
        # Matched all text until parentheses into g1,
        # Parenthesis with digit into g2
        match = re.match(pattern, template_name)
        
        if match:
            # Extract base text and current number
            base_text = match.group(1)
            current_num = int(match.group(2))
            # Increment the number
            new_num = current_num + 1
            return f"{base_text} ({new_num})"
        else:
            # No number found, add (1)
            return f"{template_name} (1)"


    def _create_new_playlist_in_db(self):
        playlist_id = self._db_connection.create_playlist(self._make_unique_name(False), "Add your description!")
        if playlist_id is None:
            playlist_id = self._db_connection.create_playlist(self._make_unique_name(False, "Really untitled?"), "Add your description!")
        
        if playlist_id is None:
            raise RuntimeError("Attempting to create playlist resulted in an error!")
        
        # At this point, the playlist exists, so the information is passed on to the UI
        playlist_info = self._db_connection.get_playlist(playlist_id)
        if playlist_info is None:
            raise RuntimeError("After playtlist creation, failuire to retrieve data from database!")
        self._ui_container.handle_new_playlist(playlist_info)

    def _add_new_song_to_playlist(self, playlist_id : int, song_id : int):
        self._db_connection.add_song_to_playlist(playlist_id, song_id)


    @Slot()
    def open(self):
        self._audio_player._ensure_stopped()
        file_dialog = QFileDialog(self)

        if file_dialog.exec() == QDialog.DialogCode.Accepted:
            url = file_dialog.selectedUrls()[0].toLocalFile()
            self._audio_player.set_source(url)


if __name__ == "__main__":
  app = QApplication([])
  
  # Looks like Linux
  app.setStyle("Fusion")
  
  MainWindow = MainApplication()
  MainWindow.setWindowTitle("YouTify Music Manager")
  MainWindow.show()

  QtAsyncio.run(handle_sigint=True)
  
