from __future__ import annotations


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal, QUrl, QObject, )
from PySide6.QtGui import (QCursor, QDesktopServices, QGuiApplication, QIcon,
                           QKeySequence, QShortcut, QStandardItem,
                           QStandardItemModel, QAction, QColor, QMouseEvent, QColorConstants,
                           QPalette)

from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,
                               QCommandLinkButton, QDateTimeEdit, QDial,
                               QDialog, QDialogButtonBox, QFileSystemModel,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListView, QMenu, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton,
                               QScrollBar, QSizePolicy, QSlider, QSpinBox,
                               QStyleFactory, QTableWidget, QTabWidget,
                               QTextBrowser, QTextEdit, QToolBox, QToolButton,
                               QTreeView, QVBoxLayout, QWidget, QMainWindow, QFileDialog, QFrame, QGraphicsItem, QGraphicsPixmapItem,
                               QGraphicsRectItem, QGraphicsScene, QGraphicsView,
                               QGraphicsWidget, QStyle)

from PySide6.QtMultimedia import (QAudioDecoder, QAudioOutput, QMediaFormat, QAudio, QMediaPlayer)

import PySide6.QtAsyncio as QtAsyncio

import sys, random, os, asyncio
import re
from typing import Callable

from downloader import DownloadTracker
from typing import Dict, Any, Optional, Tuple, List

import soundfile as sf
import utility as util

DARK_THEME_NO_HOVER = QColorConstants.DarkGray
DARK_THEME_HOVER = QColorConstants.Gray

LIGHT_THEME_HOVER = QColorConstants.LightGray
LIGHT_THEME_NO_HOVER = QColorConstants.White



class PlayListContainer(QFrame):

  _play_button_clicked = Signal(int, str)

  def __init__(self, songs_query : List[Dict[str, Any]]):
    

    super().__init__()

    self._current_index = 0
    self._songs = songs_query

    self._search_bar = QLineEdit(placeholderText="Search for songs or playlists... ")
    self._search_bar.textChanged.connect(self._search_text_changed)

    self._name = QLabel()
    self._name.setText("Title of Playlist")
    self._name.setObjectName("PlaylistTitle")

    self._desc = QLabel()
    self._desc.setText("This is what a description of a playlist might look like.\nYou should give it a try!")
    self._desc.setObjectName("PlaylistDescription")

    self._more_options = QPushButton()
    self._more_options.setText("Options (WIP)")

    # List of UI objects
    self._playlist : list[PlaylistElement] = []
    self._playlist_layout = QVBoxLayout()


    self._title_layout  = QVBoxLayout()
    self._title_layout.addWidget(self._name)
    self._title_layout.addWidget(self._desc)

    self._header_layout = QHBoxLayout()
    
    self._header_layout.addLayout(self._title_layout)
    self._header_layout.addWidget(self._search_bar)
    self._header_layout.addWidget(self._more_options)

    self.refresh_playlist_elements(self._songs)


    general_layout = QVBoxLayout(self)
    general_layout.addLayout(self._header_layout)
    general_layout.addSpacing(10)
    general_layout.addLayout(self._playlist_layout)  

    self.setStyleSheet(open(os.path.join(util.STYLE_LOCATION, 'PlaylistStyle.qss')).read())
    
    color = QPalette()
    color.setColor(QPalette.ColorRole.Text, QColor("#FF00FF"))
    self._name.setPalette(color)



  def play_song(self, idx : int):
    self._current_index = idx
    self._play_button_clicked.emit(self.get_current_song_path(), self._current_index)
  

  def _search_text_changed(self, text : str):
    # Update selection with all of the songs that match the text
    
    # Clear all visible choices
    self._delete_layout_elements()
    self._delete_elements()

    # Add only the ones that match
    for song in self._songs:
      regex_match = re.match(text, song["user_title"])
      if regex_match is not None:
        self.add_element(song)

  


  def get_current_song_name(self):
    return self._playlist[self._current_index]._song_name
  def get_current_song_path(self):
    return self._playlist[self._current_index]._song_path
  

  def add_element(self, song : Dict[str, Any]):
    # TODO: Change this so it orders itself with the propper playlist positions in 'playlists' table
    self._playlist.append( PlaylistElement(song) )
    self._playlist[-1]._play_clicked_signal.connect(self._play_button_clicked)
    self._playlist_layout.addWidget( self._playlist[-1] )
    self.update()

  # Whenever you start playing a different song, this function sends out a notification
  # To every  element, an example would be to toggle back the 'PLAY_ICON'
  def _toggle_off_every_element(self, index_to_skip : int = -1):
    for i, element in enumerate(self._playlist):
      if i != index_to_skip:
        element.toggle_off()


  def _delete_layout_elements(self):
    for i in range(self._playlist_layout.count()):
      try:
        # For whatever reason, deleting elements like the spec says doesn't work
        # It only results in the objects being misaligned, and doesn't even remove
        # all of them. Anyway, this is a miserable, but working solution for the time being
        self._playlist_layout.takeAt(i).widget().deleteLater()
      except Exception as e:
        pass
    
  def _delete_elements(self):
    if len(self._playlist) > 0:
      for i in range(len(self._playlist), 0, -1):
        self._playlist[i-1].deleteLater()
    self._playlist = []




  def refresh_playlist_elements(self, new_songs : List[Dict[str, Any]] | None = None):
    
    self._delete_layout_elements()
    self._delete_elements()

    for song in (new_songs if new_songs is not None else self._songs):
      self.add_element(song)






PLAY_ICON  = QIcon(util.ICON_LOCATION + 'PLAY_ICON.svg')
PAUSE_ICON = QIcon(util.ICON_LOCATION + 'PAUSE_ICON.svg')

# Singular tab element of a playlist
# Multiple playlist elements make up a Playlist UI
class PlaylistElement(QFrame):
  
  _clicked_signal      = Signal(int, name="Mouse Click")
  _play_clicked_signal = Signal(int, str)
  
  def __init__(self, song_data : Dict[str, Any] ):
    super().__init__()

    self.setObjectName("PlaylistElement")
    self.setStyleSheet(open(os.path.join(util.STYLE_LOCATION, 'PlaylistStyle.qss')).read())

    # Data
    self._data      : Dict[str, Any] = song_data
    self._id        : int            = self._data["id"]
    self._song_name : str            = self._data["user_title"]
    self._song_path : str            = self._data["file_path"]
    self.set_song(self._song_path)

    # Saving in milliseconds simply to avoid carrying floats around
    # and it's easy to convert back into seconds, or work with pydub
    self._length_ms : int = self._data["duration"] * 1000
    # Mainly used as a debug tool, enabled once set_song() has been called
    # This is to prevent anything from trying to play a non-existent file
    self._song_is_set : bool = False


    self._is_playing = False

    

    # Layouts
    self._song_data_layout           = QVBoxLayout()
    self._song_length_and_btn_layout = QHBoxLayout()
    self._button_layout     = QHBoxLayout()
    self._right_hand_layout = QVBoxLayout()
    main_layout             = QHBoxLayout(self)

    # Layout and Labels for the left side of the element
    self._song_name_label   = QLabel()
    self._song_name_label.setObjectName("SongName")

    MAX_SONG_NAME_LENGTH = 60
    if len(self._song_name) > MAX_SONG_NAME_LENGTH:
      self._song_name_label.setText(self._song_name[:MAX_SONG_NAME_LENGTH - 3] + '...') 
    else:
      self._song_name_label.setText(self._song_name) 


    self._song_length_label = QLabel()
    self._song_length_label.setObjectName("SongLength")
    self._song_length_label.setText(util.ms_to_text(self._length_ms))


    self._song_data_layout.addWidget(self._song_name_label)
    self._song_data_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    
    self._song_length_and_btn_layout.addWidget(self._song_length_label)
    self._song_length_and_btn_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)



    # Buttons for the right side:
    # TODO: add icons!
    self._play_btn                 = QPushButton() 
    self._remove_from_playlist_btn = QPushButton()
    self._other_options_btn        = QPushButton()

    
    self._play_btn.setIcon(PLAY_ICON)
    self._play_btn.setAutoFillBackground(False)
    self._play_btn.setObjectName("PlayButton")

    self._remove_from_playlist_btn.setText("Remove")
    self._other_options_btn.setText("More")

    self._play_btn.clicked.connect(self.on_play_btn_click)

    # Button Layout
    self._button_layout.addWidget(self._play_btn)
    self._button_layout.addWidget(self._remove_from_playlist_btn)
    self._button_layout.addWidget(self._other_options_btn)
    self._button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

    self._song_length_and_btn_layout.addLayout(self._button_layout)
    self._song_data_layout.addLayout(self._song_length_and_btn_layout)


    # Note area?
    self._note_textedit = QTextEdit()
    self._note_textedit.setVisible(False)    # Will stay invisible, unless enabled in the [...] menu
    self._note_textedit.setPlaceholderText("Add a personal note...")
    
    
    self._right_hand_layout.addWidget(self._note_textedit)

    # Layout of the whole item
    main_layout.addLayout(self._song_data_layout)
    main_layout.addLayout(self._right_hand_layout)


    
    """
            LEFT-HAND      SPACER                 RIGHT-HAND    
    |-----------------------|---|-----------------------------------------------------|
    +--------------------------------------------------------------------------------+
    |  SONG NAME             | |> (play/pause) ... (rename) X (remove from playlist) | 
    |  LENGTH [00:00]        | [ note area :                                       ] |
    +--------------------------------------------------------------------------------+
    """ 


    self.setMaximumSize(600, 100)
    self.setMinimumSize(400, 60)

    self.setObjectName('playlist-elem')
    # self.setStyleSheet('#playlist-elem {background-color: gray ;}')

    self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    


    


  def set_song(self, filepath : str):
    # Assert this file even exists:
    # This should be done in PlaylistContainer or even above, but I'd rather be safe than sorry
    if not os.path.exists(filepath):
      raise Exception(f"{filepath} does not exist!")
    # This is so FFmpeg doesn't cry
    filepath = filepath.replace('\\', '/')
    # Get the filename
    file_name = os.path.basename(filepath)
    # Strip the last ending .*
    file_name = file_name[:file_name.rfind('.')]
    self._song_name = file_name
    self._song_path = filepath

    # Get the length of the sound:
    loaded_soundfile = sf.SoundFile(filepath)
    self._length_ms = int(1000 * (loaded_soundfile.frames / loaded_soundfile.samplerate))
    self._song_is_set = True

      
  def mouseMoveEvent(self, event: QMouseEvent):
    # Change color here
    # print(event)
    # self.toggle_color()
    pass


  def toggle_off(self):
    self._play_btn.setIcon(PLAY_ICON)

  @Slot()
  def on_play_btn_click(self):

    self._is_playing = not self._is_playing
    if self._is_playing:
      self._play_btn.setIcon(PAUSE_ICON)
    else:
      self._play_btn.setIcon(PLAY_ICON)
    self._play_clicked_signal.emit(self._id, self._song_path)
  
  @Slot()
  def connect_play_button(self, function : Callable):
    self._play_clicked_signal.connect(function)

  @Slot()
  def connect_remove_from_playlist_button(self, function : Callable):
    self._remove_from_playlist_btn.clicked.connect(function)

  @Slot()
  def connect_other_options_button(self, function : Callable):
    self._other_options_btn.clicked.connect(function)

  @Slot()
  def connect_clicked_signal(self, function : Callable):
    self._clicked_signal.connect(function)
