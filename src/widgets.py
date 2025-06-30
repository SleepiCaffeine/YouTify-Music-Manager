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

import sys, random, os, asyncio, json, io
from downloader import (DownloadTracker, YoutubeDownloader,  SpotifyDownloader, SpotifyDownloaderException)

import utility as util
from typing import Dict, Any, Optional, Tuple, List
import config
from mylogger import global_logger
from playlist import (PlayListContainer)
from PlaylistSelectionList import PlaylistSelectionList


class MusicDownloader(QObject):
  progress_updated_signal   = Signal(object)
  download_completed_signal = Signal()
  

  def __init__(self, callback_handler):

    super().__init__()

    self.output_dir : str = ""

    self.spotify_downloader = SpotifyDownloader()
    self.yt_downloader      = YoutubeDownloader()

    self.progress_updated_signal.connect(callback_handler)

    self.current_download_task = None


  def start_download(self, url : str) -> Tuple[str, bool]:

    if self.current_download_task is not None and not self.current_download_task.done():
      return ("Download already in progress...", False)

    if len(url) == 0:
      return ("you didn't add no text???", False)

    # YOUTUBE LINK:
    # Note to self: maybe add some other form of link validation in the future
    if (link in url for link in ["youtube.", "youtu.be"]):
      self.current_download_task = asyncio.create_task(self.yt_download_url(url))
      return ("Started Download", True)

    elif (link in url for link in ["play.spotify", "open.spotify"]):
      self.current_download_task = asyncio.create_task(self.spotify_download_url(url))
      return ("Started Download", True)
    
    elif "spotify:" in url:
       return ("This app currently doesn't support URIs :/\nTry with a regular URL instead", False)
    
    else:
      return ("Please enter in a valid Youtube/Spotify track URL", False)


  def youtube_audio_download_callback(self, tracker : DownloadTracker):
    QTimer.singleShot(0, lambda: self.update_progress_display(tracker))
  

  def update_progress_display(self, tracker : DownloadTracker):
    
    QApplication.processEvents()
    self.progress_updated_signal.emit(tracker)
  

  async def spotify_download_url(self, url : str):
    try:
      self.spotify_downloader.download_link(url)
    except SpotifyDownloaderException as e:
      print(e)
    finally:
       return   
    
  
  async def yt_download_url(self, url: str) -> bool:
    try:
        
      task = asyncio.create_task(self.yt_downloader.download_yt_video_with_hook(
          url, 
          config.get_audio_download_dir(), 
          self.youtube_audio_download_callback
      ))
        
      error_code, progress = await task 
      #TODO: change these error codes to simply be exceptions
      match error_code:
          case -1:
            raise RuntimeError(f"Failed download, because Youtube thought this is a bot.\nTurn off any VPNs or update your cookies in the settings")
          case 0:
            return True
          case _:
            raise RuntimeError(f"An error occured with your download! Try again later")
              
                  
                  
          
    except Exception as e:
      raise e

    finally:
      self.current_download_task = None
      # Emit signal to inform that a download is done
      self.download_completed_signal.emit()


  def update_output_dir(self, path: str):
    if not os.path.exists(path):
      raise Exception("Provided path doesn't exist")
    else:
      self.output_dir = path



class MusicDownloadWidget(QWidget):

  progress_updated_signal   = Signal(object)
  download_completed_signal = Signal()
  

  def __init__(self):
    super().__init__()
    layout = QVBoxLayout(self)
    
    self.downloader = MusicDownloader(self.update_progress_display)
    self.downloader.download_completed_signal.connect(self.download_completed_signal)
    
    self.label = QLabel("Music Downloader", alignment=Qt.AlignmentFlag.AlignCenter)

    # Create tex input for the URL
    self.text_input = QPlainTextEdit()
    self.text_input.setPlaceholderText("Enter in a valid Youtube/Spotify URL")


    self.download_button = QPushButton("Download Music!")
    self.download_button.clicked.connect(self.start_download)
    

    layout.addWidget(self.label)
    layout.addWidget(self.text_input)
    layout.addWidget(self.download_button)
    
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.current_download_task = None


  def start_download(self):
    
    str, result = self.downloader.start_download(self.text_input.toPlainText().strip())
    self.set_label(str)
    

  def set_label(self, text : str):
    self.label.setText(text)


  def youtube_audio_download_callback(self, tracker : DownloadTracker):
    QTimer.singleShot(0, lambda: self.update_progress_display(tracker))
  

  def update_progress_display(self, tracker : DownloadTracker):
    self.label.setText(str(tracker))
    QApplication.processEvents()
  


  def update_output_dir(self, path: str):
    self.downloader.update_output_dir(path)



class AudioPlayer:
  def __init__(self):
    # Initialize the media playback stuff
    self._audio_output = QAudioOutput()
    self._player       = QMediaPlayer()
    self._curr_path    : str = ""
    self._curr_song_id : int = 0
    self._player.setAudioOutput(self._audio_output)
      
  @Slot()
  def set_source(self, song_id : int, path_to_song : str):
    print(f"setting id: {song_id}\npath: {path_to_song}")
    if self._curr_song_id != song_id and os.path.exists(path_to_song):
      self._player.stop()
      self._player.setSource(path_to_song)
      self._curr_song_id = song_id

  @Slot()
  def play_song(self):
    print("play")
    self._player.play()

  @Slot()
  def pause_song(self):
    print("pause")

    self._player.pause()

  @Slot()
  def _ensure_stopped(self):
    if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
      self._player.stop()


class UIContainer(QWidget):

  _play_song_signal              = Signal(int, str) # Song ID and Song path
  _play_specific_playlist_signal = Signal()         
  _update_songs_dir              = Signal(str)      # Directory where downloads should be placed
  _new_songs_downloaded          = Signal(str)      # Directory where to look for new songs
  _request_songs_for_refresh     = Signal(dict)     # Signal up to MainApplication to callback with songs table.
  _create_new_playlist_in_db     = Signal()         # Signal up to MainApplication to create a new playlist.
  _update_db_with_new_song_in_playlist = Signal(int, int) # Signal up to MainApplication to join playlist ID and song ID in the joint table
  _request_all_songs_to_add_to_playlist = Signal(int)  # Request every available song, that isn't already in the playlist to add. Playlist ID

  

  def __init__(self, parent, list_of_playlists : List[Dict[str, Any]]):

    super().__init__()

    global_logger.debug(f"Initialized UIContainer with {list_of_playlists}")

    # Loads selection of playlist to the user
    self._playlist_selection_list = PlaylistSelectionList(list_of_playlists)
    self._playlist_selection_list._activate_playlist.connect(self._activate_playlist)
    self._playlist_selection_list._play_specific_playlist.connect(self._handle_playing_playlist)

    self._search_bar = QLineEdit(placeholderText="Search for playlists... ")
    self._search_bar.textChanged.connect(self._playlist_selection_list._search_text_changed)
    self._search_bar.setMaximumHeight(40)

    self._create_new_playlist_btn = QPushButton()
    self._create_new_playlist_btn.setText("New")
    self._create_new_playlist_btn.clicked.connect(self._create_new_playlist_in_db.emit)

    # Loads the container to display the songs in a certain playlist
    self._playlist_container = PlayListContainer()
    self._playlist_container._play_button_clicked.connect(self._play_song)
    self._playlist_container._update_db_with_new_song_in_playlist.connect(self._update_db_with_new_song_in_playlist.emit)
    self._playlist_container._request_every_song_not_in_playlist.connect(self._request_all_songs_to_add_to_playlist.emit)

    # Widget to facilitate downloading from yt/spotify
    self._music_downloader = MusicDownloadWidget()
    self._music_downloader.setMaximumWidth(100)
    self._music_downloader.download_completed_signal.connect(self.send_out_download_dir_signal)
    self._music_downloader.update_output_dir(config.get_audio_download_dir())

    # Will be deteled, but I want to keep this, just so I would remember that I made it
    self._set_audio_download_folder_btn = QPushButton()
    self._set_audio_download_folder_btn.setText("Audio Location")
    self._set_audio_download_folder_btn.clicked.connect(self._update_audio_download_folder)

    self._update_songs_dir.connect(parent.update_songs_directory)

    # General layout
    layout = QHBoxLayout(self)
    
    self.playlist_selection_layout        = QVBoxLayout()
    self.playlist_selection_search_layout = QHBoxLayout()

    self.playlist_selection_search_layout.addWidget(self._search_bar)
    self.playlist_selection_search_layout.addWidget(self._create_new_playlist_btn)

    self.playlist_selection_layout.addLayout(self.playlist_selection_search_layout)
    self.playlist_selection_layout.addWidget(self._playlist_selection_list)
    
    layout.addWidget(self._music_downloader)
    layout.addLayout(self.playlist_selection_layout)
    layout.addWidget(self._playlist_container)
    
    

    # layout.addWidget(self._refresh_btn)
    # layout.addWidget(self._set_audio_download_folder_btn)

  @Slot(str)
  def _play_song(self, song_id : int, song_path : str):
    global_logger.debug(f"Emitting _play_song_signal from UIContainer with ID: {song_id} | PATH: {song_path}")
    self._play_song_signal.emit(song_id, song_path)

  
  def _toggle_off_songs(self, index_to_ignore : int = -1):
    self._playlist_container._toggle_off_every_element(index_to_ignore)


  def send_out_download_dir_signal(self):
    self._new_songs_downloaded.emit(self._music_downloader.downloader.output_dir)


  def refresh_playlist(self, songs : List[Dict[str, Any]]):
    self._playlist_container.refresh_playlist_elements(songs)


  def send_all_songs_to_playlist_container_for_addSongWindow(self, all_songs : List[Dict[str, Any]]):
    self._playlist_container._handle_add_song_clicked_callback(all_songs)

  def _update_audio_download_folder(self):
    # Get dir through native WindowBox
    selected_dir = QFileDialog.getExistingDirectory()
    config.update_audio_download_dir(selected_dir)
    # Update Directory where songs are stored
    self._music_downloader.update_output_dir(config.get_audio_download_dir())
    # Update directory where the database points
    self._update_songs_dir.emit(selected_dir)
    
    self.send_out_download_dir_signal()
    pass


  
  def _activate_playlist(self, playlist_index_in_arr : int):
    global_logger.debug(f"UIContainer caught _activate_playlist with index: {playlist_index_in_arr}")

    # This is called when a user clicks 'Play' on a PlaylistSelection
    # I would much more prefer loading up things separately but alas
    playlist = self._playlist_selection_list._selection_list[playlist_index_in_arr]
    global_logger.debug(f"UIContainer is loading playlist {playlist._data}")

    self._playlist_container._update_playlist_data(playlist._data)
    self._request_songs_for_refresh.emit(playlist._data["id"])


  def handle_new_playlist(self, playlist_data : Dict[str, Any]):
    global_logger.debug(f"UIContainer caught _play_specific_playlist with data: {playlist_data}")

    # This function is responsible for displaying the playlist in the selection screen
    self._playlist_selection_list.add_element(playlist_data)
    
    # AND making the new playlist the current "Active" one
    self._request_songs_for_refresh.emit(playlist_data)
    pass


  def _handle_playing_playlist(self, playlist_index_in_arr : int):
    playlist = self._playlist_selection_list._selection_list[playlist_index_in_arr]
    


  def load_playlist_container(self, playlist_data : Dict[str, Any], songs : List[Dict[str, Any]]):

    self._playlist_container = PlayListContainer(playlist_data, songs)
    self._playlist_container.refresh_playlist_elements()