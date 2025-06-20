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
from playlist import (PlayListContainer)




class MusicDownloadWidget(QWidget):

  progress_updated_signal   = Signal(object)
  download_completed_signal = Signal()
  

  def __init__(self):
    super().__init__()
    layout = QVBoxLayout(self)

    self.output_dir : str = ""

    self.spotify_downloader = SpotifyDownloader()
    self.yt_downloader      = YoutubeDownloader()
    
    self.label = QLabel("Music Downloader", alignment=Qt.AlignmentFlag.AlignCenter)

    # Create tex input for the URL
    self.text_input = QPlainTextEdit()
    self.text_input.setPlaceholderText("Enter in a valid Youtube/Spotify URL")

    self.progress_updated_signal.connect(self.update_progress_display)

    self.download_button = QPushButton("Download Music!")
    self.download_button.clicked.connect(self.start_download)
    

    layout.addWidget(self.label)
    layout.addWidget(self.text_input)
    layout.addWidget(self.download_button)
    
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.current_download_task = None


  def start_download(self):

    if self.current_download_task is not None and not self.current_download_task.done():
      self.set_label("Download already in progress...")
      return
    
    # URL validation
    url = self.text_input.toPlainText().strip()
    if len(url) == 0:
      self.set_label("you didn't add no text???")
      return

    # YOUTUBE LINK:
    # Note to self: maybe add some other form of link validation in the future
    if (link in url for link in ["youtube.", "youtu.be"]):
      self.current_download_task = asyncio.create_task(self.yt_download_url(url))
      return

    elif (link in url for link in ["play.spotify", "open.spotify"]):
      self.current_download_task = asyncio.create_task(self.spotify_download_url(url))
      return
    
    elif "spotify:" in url:
       self.set_label("This app currently doesn't support URIs :/\nTry with a regular URL instead")
    
    else:
      self.set_label("Please enter in a valid Youtube/Spotify track URL")


  def set_label(self, text : str):
    self.label.setText(text)


  def youtube_audio_download_callback(self, tracker : DownloadTracker):
    QTimer.singleShot(0, lambda: self.update_progress_display(tracker))
  

  def update_progress_display(self, tracker : DownloadTracker):
    self.label.setText(str(tracker))
    QApplication.processEvents()
  

  async def spotify_download_url(self, url : str):
    try:
      self.spotify_downloader.download_link(url)
    except SpotifyDownloaderException as e:
      print(e)
    finally:
       return   
    
  
  async def yt_download_url(self, url: str):
    try:
        
      task = asyncio.create_task(self.yt_downloader.download_yt_video_with_hook(
          url, 
          config.get_audio_download_dir(), 
          self.youtube_audio_download_callback
      ))

      self.label.setText("Began download!")
        
      error_code, progress = await task 
      #TODO: change these error codes to simply be exceptions
      match error_code:
          case -1:
              self.label.setText(f"Failed download, because Youtube thought this is a bot.\nTurn off any VPNs or update your cookies in the settings")
          case 0:
              self.label.setText(f"Download completed!")
          case _:
              self.label.setText(f"An error occured with your download! Try again later")
                  
                  
          
    except Exception as e:
      self.label.setText(f"Download failed: {str(e)}")

    finally:
      self.current_download_task = None
      # Emit signal to inform that a download is done
      self.download_completed_signal.emit()

  def update_output_dir(self, path: str):
    if not os.path.exists(path):
      raise Exception("Provided path doesn't exist")
    else:
      self.output_dir = path


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
    print(f"setting id: {song_id}")
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

  _play_song_signal = Signal(int)
  _update_songs_dir = Signal(str)
  

  def __init__(self, parent, list_of_songs : List[Dict[str, Any]]):
    super().__init__()
    # Will have to change the way a playlist is loaded
    self._playlist_container = PlayListContainer(list_of_songs)
    self._playlist_container._play_button_clicked.connect(self._play_song)

    # Ways to interact with the Audio Player
    self._audio_play_btn = QPushButton()
    self._audio_play_btn.setText("Play!")
    self._audio_play_btn.clicked.connect(parent.handlePlayButtonClick)


    self._music_downloader = MusicDownloadWidget()
    self._music_downloader.download_completed_signal.connect(self._refresh_playlist)
    self._music_downloader.update_output_dir(config.get_audio_download_dir())

    self._refresh_btn = QPushButton()
    self._refresh_btn.clicked.connect(self._refresh_playlist)
    self._refresh_btn.setText("Refresh")

    self._set_audio_download_folder_btn = QPushButton()
    self._set_audio_download_folder_btn.setText("Audio Location")
    self._set_audio_download_folder_btn.clicked.connect(self._update_audio_download_folder)


    self._update_songs_dir.connect(parent.update_songs_directory)

    # General layout
    layout = QHBoxLayout(self)
    layout.addWidget(self._playlist_container)
    
    layout.addWidget(self._music_downloader)
    layout.addWidget(self._refresh_btn)
    layout.addWidget(self._set_audio_download_folder_btn)

  @Slot(str)
  def _play_song(self,index_of_song : int):
    self._play_song_signal.emit(index_of_song)

  
  def _toggle_off_songs(self, index_to_ignore : int = -1):
    self._playlist_container._toggle_off_every_element(index_to_ignore)

  def _refresh_playlist(self):
    self._playlist_container.refresh_playlist_elements( config.get_audio_download_dir() )

  def _update_audio_download_folder(self):
    # Get dir through native WindowBox
    selected_dir = QFileDialog.getExistingDirectory()
    config.update_audio_download_dir(selected_dir)
    # Update Directory where songs are stored
    self._music_downloader.update_output_dir(config.get_audio_download_dir())
    # Update directory where the database points
    self._update_songs_dir.emit(selected_dir)
    # Refresh UI
    self._refresh_playlist()
    pass