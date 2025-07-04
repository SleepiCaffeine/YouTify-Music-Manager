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
from mylogger import global_logger

DARK_THEME_NO_HOVER = QColorConstants.DarkGray
DARK_THEME_HOVER = QColorConstants.Gray

LIGHT_THEME_HOVER = QColorConstants.LightGray
LIGHT_THEME_NO_HOVER = QColorConstants.White



class SongSelection(QWidget):

  _selected_signal = Signal(int)

  def __init__(self, song_id : int, song_name : str, song_length : int | str ):
    super().__init__()

    self._id = song_id

    layout = QGridLayout(self)
    self._name = QLabel()
    self._name.setText(song_name)
    
    self._length = QLabel()

    if type(song_length) == str:
      self._length.setText(song_length)

    elif type(song_length) == int:
      self._length.setText(util.ms_to_text(song_length))

    else:
      raise RuntimeError(f"Passed type \"{type(song_length)} as song_length in SongSelection object initializer\"")

    layout.addWidget(self._name,   0, 0)
    layout.addWidget(self._length, 1, 0)


    self._add_button = QPushButton()
    self._add_button.clicked.connect(self._handle_add_btn_clicked)
    self._add_button.setText("Add Song")
    self._add_button.setMaximumSize(80, 25)
    layout.addWidget(self._add_button, 1, 1)


  def _handle_add_btn_clicked(self):
    self._selected_signal.emit(self._id)

  def get_name(self) -> str:
    return self._name.text()



class AddSongWindow(QDialog):

  _song_selected_signal = Signal(dict)

  def __init__(self):
    super().__init__()
    global_logger.debug("Created AddSongWindow")

    main_layout = QVBoxLayout(self)
    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    self._song_selections : List[SongSelection]  = []
    self._available_songs : List[Dict[str, Any]] = []

    self._search_bar = QLineEdit(placeholderText="Search for songs... ")
    self._search_bar.textChanged.connect(self._search_text_changed)
    self._search_bar.setMaximumHeight(40)


    self._songs_layout = QVBoxLayout()
    self._songs_layout.setAlignment(Qt.AlignmentFlag.AlignTop)


    main_layout.addWidget(self._search_bar)
    main_layout.addLayout(self._songs_layout)



  def _search_text_changed(self, text : str):
     # Clear all visible choices
    self._delete_layout_elements()

    # Add only the ones that match
    for song in self._available_songs:
      regex_match = re.match(text, song["user_title"])
      if regex_match is not None:
        self.add_element(song)

  
  def _delete_layout_elements(self):
    for i in range(self._songs_layout.count()):
      try:
        self._songs_layout.takeAt(i).widget().deleteLater()
      except Exception as e:
        pass


  def add_element(self, song_data : Dict[str, Any]):
    global_logger.debug(f"Added element in AddSongWindow: {song_data}")
    
    song = SongSelection(song_id=song_data['id'], song_name=song_data['user_title'], song_length=song_data['duration'])
    song._selected_signal.connect(self._handle_add_song_signal)
    self._song_selections.append(song)
    self._songs_layout.addWidget(song)
    self._songs_layout.update()


  def _handle_add_song_signal(self, id : int):
    
    song = {}
    for s in self._available_songs:
      if s['id'] == id:
        song = s
        break

    self._song_selected_signal.emit(song)
    self.close()

  def _set_available_songs(self, songs : list[Dict[str, Any]] = []):
    global_logger.debug(f"Set songs in AddSongWindow: {songs}")

    self._available_songs = songs
    for song in self._available_songs:
      self.add_element(song)
  




class PlayListContainer(QWidget):

  _play_button_clicked      = Signal(int, str)
  _request_every_song       = Signal()
  _update_db_with_new_song_in_playlist = Signal(int, int) # Playlist ID, Song ID
  _request_every_song_not_in_playlist = Signal(int)
  
  _delete_element_clicked_signal = Signal(int,  name="Delete Element Clicked")
  _delete_playlist_clicked_signal = Signal(int, name="Delete Playlist Clicked")
  

  def __init__(self, playlist_data : Dict[str, Any] = {}, songs_query : List[Dict[str, Any]] = []):
    

    super().__init__()

    self.general_layout = QVBoxLayout(self)
    
   # self.setStyleSheet(open(os.path.join(util.STYLE_LOCATION, 'PlaylistStyle.qss')).read())

    self._current_index = 0
    self._songs = []
    self._playlist_data = playlist_data
    self._initialized = playlist_data != {} and songs_query != []

    # List of UI objects
    self._playlist : list[PlaylistElement] = []
    self._playlist_layout = QVBoxLayout()

    self._search_bar = QLineEdit(placeholderText="Search for songs... ")
    self._search_bar.textChanged.connect(self._search_text_changed)
    self._search_bar.setMaximumSize(300, 30)


    self._name = QLabel()
    self._name.setObjectName("PlaylistTitle")


    self._desc = QLabel()
    self._desc.setObjectName("PlaylistDescription")


    self._more_options = QPushButton()
    self._more_options.setText("Options (WIP)")

    self._add_song_btn = QPushButton()
    self._add_song_btn.setText("Add song")
    self._add_song_btn.clicked.connect(self.handle_add_song_clicked)
  
    self.refresh_playlist_elements(self._songs)



    # This is set for when there isn't anything selected
    if self._playlist_data == {}:
      self._no_playlist_text = QLabel()
      self._no_playlist_text.setText("You don't currently have a playlist selected.")
      self._playlist_layout.addWidget(self._no_playlist_text)

    else:
      self._update_playlist_data(playlist_data)

    self._header_layout  = QHBoxLayout()
    
    self._title_layout   = QVBoxLayout()
    self._title_layout.addWidget(self._name)
    self._title_layout.addWidget(self._desc)

    self._buttons_layout = QVBoxLayout()
    self._buttons_layout.addWidget(self._add_song_btn)
    self._buttons_layout.addWidget(self._more_options)

    self._header_layout.addLayout(self._title_layout)
    self._header_layout.addLayout(self._buttons_layout)

    self._playlist_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    if self._initialized:
      self.general_layout.addLayout(self._header_layout)
      self.general_layout.addWidget(self._search_bar)
      self.general_layout.addLayout(self._playlist_layout)


    self.refresh_playlist_elements(self._songs)
    
    
    
    self.setMinimumWidth(400)

  

  def _update_playlist_data(self, playlist_data : Dict[str, Any]):
    self._playlist_data = playlist_data
    self._initialized = True
    self._name.setText(self._playlist_data["name"])
    self._desc.setText(self._playlist_data["description"])
    self.general_layout.addLayout(self._header_layout)
    self.general_layout.addWidget(self._search_bar)
    self.general_layout.addLayout(self._playlist_layout)


  def handle_add_song_clicked(self):
    
    self._request_every_song_not_in_playlist.emit(self._playlist_data['id'])    


  def _handle_add_song_clicked_callback(self, all_songs : List[Dict[str, Any]]):
    add_song_window = AddSongWindow()
    add_song_window._set_available_songs(all_songs)

    add_song_window._song_selected_signal.connect(self._handle_add_song_song_data)
    add_song_window.exec_()
  

  def _handle_add_song_song_data(self, song_data : Dict[str, Any]):
    self.add_element(song_data)
    self._update_db_with_new_song_in_playlist.emit(self._playlist_data['id'], song_data['id'])
    


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
        self.add_layout_element(PlaylistElement(song))

  


  def get_current_song_name(self):
    return self._playlist[self._current_index]._song_name
  def get_current_song_path(self):
    return self._playlist[self._current_index]._song_path
  

  def add_layout_element( self, new_element : PlaylistElement ):

     # Quick check if this is the text prompting to make a playlist is still there:
    # Because if so - it needs to be deleted
    if len(self._playlist) == 0:
      self._delete_layout_elements()

    new_element._play_clicked_signal.connect(self._play_button_clicked)
    new_element._delete_clicked_signal.connect(self._delete_element)
    self._playlist_layout.addWidget( new_element )
    self._playlist.append( new_element )
    self.update()
    
    
  

  def add_element(self, song : Dict[str, Any]):
    # TODO: Change this so it orders itself with the propper playlist positions in 'playlists' table
    global_logger.debug(f"Adding Element to PlaylistContainer: {song}")
    
    self._songs.append(song)
    self.add_layout_element(PlaylistElement(song))
    

    self.updateGeometry()


  def _delete_element(self, song_id : int):
    global_logger.debug(f"Deleting element with ID: {song_id} from PlaylistContainer")
    # Find the element with the ID
    for i, element in enumerate(self._playlist):
      if element._id == song_id:
        # Remove it from the layout
        self._playlist_layout.removeWidget(element)
        # Remove it from the list
        self._playlist.pop(i)
        # Delete the element
        element.deleteLater()
        # Remove it from the songs list
        self._songs = [s for s in self._songs if s['id'] != song_id]
        # Emit a signal to delete it from the DB
        self._delete_element_clicked_signal.emit(song_id)
        return

    pass

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
    global_logger.debug(f"Refreshing PlaylistContainer with: {new_songs} ")
    self._delete_layout_elements()
    self._delete_elements()

    for song in (new_songs if new_songs is not None else self._songs):
      self.add_element(song)






PLAY_ICON  = QIcon(util.ICON_LOCATION + 'PLAY_ICON.svg')
PAUSE_ICON = QIcon(util.ICON_LOCATION + 'PAUSE_ICON.svg')

# Singular tab element of a playlist
# Multiple playlist elements make up a Playlist UI
class PlaylistElement(QFrame):
  
  _clicked_signal        = Signal(int, name="Mouse Click")
  _play_clicked_signal   = Signal(int, str)
  _delete_clicked_signal = Signal(int, name="Delete Clicked")
  
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
    self._play_btn.clicked.connect(self.on_play_btn_click)

    self._remove_from_playlist_btn.setText("Remove")
    self._remove_from_playlist_btn.setObjectName("RemoveButton")
    self._remove_from_playlist_btn.clicked.connect(self.on_delete_btn_click)

    self._other_options_btn.setText("More")

    
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
  def on_delete_btn_click(self):
    global_logger.debug(f"PlaylistElement {self._id} delete button clicked")
    self._delete_clicked_signal.emit(self._id)

  @Slot()
  def connect_play_button(self, function : Callable):
    self._play_clicked_signal.connect(function)

  

  @Slot()
  def connect_other_options_button(self, function : Callable):
    self._other_options_btn.clicked.connect(function)

  @Slot()
  def connect_clicked_signal(self, function : Callable):
    self._clicked_signal.connect(function)
