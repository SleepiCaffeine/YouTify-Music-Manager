from __future__ import annotations


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal, QUrl, QObject, )
from PySide6.QtGui import (QCursor, QDesktopServices, QGuiApplication, QIcon,
                           QKeySequence, QShortcut, QStandardItem,
                           QStandardItemModel, QAction, QColor, QMouseEvent, QColorConstants)

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
from typing import Callable

from main import download_yt_video_with_hook, DownloadTracker

import soundfile as sf
import utility as util

DARK_THEME_NO_HOVER = QColorConstants.DarkGray
DARK_THEME_HOVER = QColorConstants.Gray

LIGHT_THEME_HOVER = QColorConstants.LightGray
LIGHT_THEME_NO_HOVER = QColorConstants.White



class PlayListContainer(QFrame):

  _selected_song = Signal(str)

  def __init__(self, list_of_paths : list[str]):
    super().__init__()

    self._current_index = 0

    self._name = QLabel()
    self._name.setText("WAOW PLAYLIST")
    self._name.setMinimumSize(300, 80)
    self._name.setObjectName("playlist-container")
    # self._name.setStyleSheet("""
    #                          font-weight: bold;
    #                          background-color: dark-gray;""")

    self._desc = QLabel()
    self._desc.setText("this is so awesoem guys")

    self._more_options = QPushButton()
    self._more_options.setText("Options (WIP)")

    self._title_layout  = QVBoxLayout()
    self._title_layout.addWidget(self._name)
    self._title_layout.addWidget(self._desc)

    self._header_layout = QHBoxLayout()
    
    self._header_layout.addLayout(self._title_layout)
    self._header_layout.addStretch(2)
    self._header_layout.addWidget(self._more_options)

    # List of UI objects
    self._playlist : list[PlaylistElement] = []
    self._playlist_layout = QVBoxLayout()

    for idx, path in enumerate(list_of_paths):
      self._playlist.append( PlaylistElement(path, idx) )
      self._playlist[-1].connect_play_button(self.select_index)
      self._playlist_layout.addWidget( self._playlist[-1] )
      self._playlist_layout.addSpacing(5)


    general_layout = QVBoxLayout(self)
    general_layout.addLayout(self._header_layout)
    general_layout.addSpacing(10)
    general_layout.addLayout(self._playlist_layout)  


  def select_index(self, idx : int):
    self._current_index = idx
    self._selected_song.emit(self.get_current_song_path())
  
  
  def get_current_song_name(self):
    return self._playlist[self._current_index]._song_name
  def get_current_song_path(self):
    return self._playlist[self._current_index]._song_path




    






# Singular tab element of a playlist
# Multiple playlist elements make up a Playlist UI
class PlaylistElement(QFrame):
  
  _clicked_signal = Signal(int, name="Mouse Click")
  
  def __init__(self, path : str="", idx : int= 0):
    super().__init__()

    # Data
    self._my_index  : int = idx
    self._song_name : str = ""
    self._song_path : str = ""
    self.set_song(path)

    # Saving in milliseconds simply to avoid carrying floats around
    # and it's easy to convert back into seconds, or work with pydub
    self._length_ms : int

    # Mainly used as a debug tool, enabled once set_song() has been called
    # This is to prevent anything from trying to play a non-existent file
    self._song_is_set : bool = False

    

    # Layouts
    self._song_data_layout  = QVBoxLayout()
    self._button_layout     = QHBoxLayout()
    self._right_hand_layout = QVBoxLayout()
    main_layout             = QHBoxLayout(self)

    # Layout and Labels for the left side of the element
    self._song_name_label   = QLabel()
    self._song_name_label.setMaximumSize(300, 40)
    self._song_name_label.setText(self._song_name)
    self._song_length_label = QLabel()
    self._song_length_label.setMaximumSize(300, 30)
    self._song_length_label.setText(util.ms_to_text(self._length_ms))


    self._song_data_layout.addWidget(self._song_name_label)
    self._song_data_layout.addWidget(self._song_length_label)
    self._song_data_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)



    # Buttons for the right side:
    # TODO: add icons!
    self._play_btn                 = QPushButton() 
    self._remove_from_playlist_btn = QPushButton()
    self._other_options_btn        = QPushButton()

    self._play_btn.setText("Play")
    self._remove_from_playlist_btn.setText("Remove")
    self._other_options_btn.setText("More")

    # Button Layout
    self._button_layout.addWidget(self._play_btn)
    self._button_layout.addSpacing(10)
    self._button_layout.addWidget(self._remove_from_playlist_btn)
    self._button_layout.addSpacing(10)
    self._button_layout.addWidget(self._other_options_btn)
    self._button_layout.addSpacing(10)
    self._button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

    # Note area?
    self._note_textedit = QTextEdit()
    self._note_textedit.setVisible(False)    # Will stay invisible, unless enabled in the [...] menu
    self._note_textedit.setPlaceholderText("Add a personal note...")
    
    
    self._right_hand_layout.addLayout(self._button_layout)
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
    print(event)
    self.toggle_color()

  def toggle_color(self):
    pass

  @Slot()
  def connect_play_button(self, function : Callable):
    self._play_btn.clicked.connect(function)

  @Slot()
  def connect_remove_from_playlist_button(self, function : Callable):
    self._remove_from_playlist_btn.clicked.connect(function)

  @Slot()
  def connect_other_options_button(self, function : Callable):
    self._other_options_btn.clicked.connect(function)

  @Slot()
  def connect_clicked_signal(self, function : Callable):
    self._clicked_signal.connect(function)
