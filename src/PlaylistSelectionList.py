from __future__ import annotations


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal, QUrl, QObject, QEvent)
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

import sys
import random
import os
import re
from typing import Callable

from typing import Dict, Any, Optional, Tuple, List
import utility as util

class PlaylistSelectionList(QFrame):
  
  _activate_playlist   = Signal(int)
  _create_new_playlist = Signal()

  def __init__(self, list_of_playlists : List[Dict[str, Any]]):
    super().__init__()
    
    self._current_highlighed_pos : int
    self._playlists = list_of_playlists

    # List of UI objects
    self._selection_list : list[PlaylistSelection] = []
    self._selection_layout = QVBoxLayout()

    self._header_layout = QHBoxLayout()

    # If no playlists exit, the user should be informed they can make one
    self._create_playlist_label = QLabel()
    self._create_playlist_label.setText("You currently have no playlists, try making one with the button nex to the search bar!")
    self._selection_layout.addWidget(self._create_playlist_label)
    # But if playlists exist, well then there's no need...
    if len(self._playlists) != 0:
      self._create_playlist_label.setVisible(False)
      self.refresh_selections(self._playlists)


    general_layout = QVBoxLayout(self)
    general_layout.addLayout(self._selection_layout)  

    # self.setStyleSheet(open(os.path.join(util.STYLE_LOCATION, 'PlaylistStyle.qss')).read())
   


  def activate_playlist(self, playlist_id : int):
    # Send signal to update the playlist songs on another element
    self._activate_playlist.emit(playlist_id)
    
  

  def _search_text_changed(self, text : str):
    # Update selection with all of the playlists that match the text
    
    # Clear all visible choices
    self._delete_layout_elements()

    # Add only the ones that match
    for plist in self._playlists:
      regex_match = re.match(text, plist["name"])
      if regex_match is not None:
        self.add_element(plist)

  
  def add_element(self, playlist : Dict[str, Any]):
    # Quick check if this is the text prompting to make a playlist is still there:
    # Because if so - it needs to be deleted
    if len(self._selection_list) == 0:
      self._delete_layout_elements()

    self._selection_list.append( PlaylistSelection(playlist) )
    # TODO: Change this to selection, instead of playing
    # self._selection_list[-1]._play_clicked_signal.connect(self._play_button_clicked)
    self._selection_layout.addWidget( self._selection_list[-1] )
    self.update()


  # Whenever you start playing a different song, this function sends out a notification
  def _toggle_off_every_element(self, index_to_skip : int = -1):
    for i, element in enumerate(self._selection_list):
      if i != index_to_skip:
        element.toggle_off()


  def _delete_layout_elements(self):
    for i in range(self._selection_layout.count()):
      try:
        # For whatever reason, deleting elements like the spec says doesn't work
        # It only results in the objects being misaligned, and doesn't even remove
        # all of them. Anyway, this is a miserable, but working solution for the time being
        self._selection_layout.takeAt(i).widget().deleteLater()
      except Exception as e:
        pass




  def refresh_selections(self, playlists : List[Dict[str, Any]] | None = None):
    self._delete_layout_elements()
    for playlist in (playlists if playlists is not None else self._playlists):
      self.add_element(playlist)




# Singular tab element of a playlist
# Multiple playlist elements make up a Playlist UI
class PlaylistSelection(QFrame):
  
  _selected_signal = Signal(dict)           # Sends up a signal with all of the playlist data to load up elsewhere
  _play_signal     = Signal()               # Sends up a signal to notify that this playlist should also start playing
  
  
  def __init__(self, playlist_data : Dict[str, Any] ):
    super().__init__()

    self.setObjectName("PlaylistSelection")
    self.setStyleSheet(open(os.path.join(util.STYLE_LOCATION, 'PlaylistStyle.qss')).read())

    # Data
    self._data        : Dict[str, Any] = playlist_data
    self._id          : int            = self._data["id"]
    self._name        : str            = self._data["name"]
    self._description : str            = (self._data["description"] if len(self._data["description"]) <= 100 else self._data["description"][:97] + '...')
    self._image       : bytes # Maybe in the future, the ability to add a playlist image


    # Saving in milliseconds simply to avoid carrying floats around
    # and it's easy to convert back into seconds, or work with pydub
    self._length_ms  : int = self._data["total_duration"] * 1000

    self._song_count : int = self._data["song_count"]

    self._is_highlighted : bool = False    
    

    self._title_label = QLabel()
    self._title_label.setText(self._name)

    self._description_label = QLabel()
    self._description_label.setText(self._description)

    self._left_side_layout = QVBoxLayout()
    self._left_side_layout.addWidget(self._title_label)
    self._left_side_layout.addWidget(self._description_label)

    
    self._play_btn = QPushButton()
    self._play_btn.setText("Play")
    self._play_btn.clicked.connect(self._handle_play_btn_click)

    self._other_options_btn = QPushButton()
    self._other_options_btn.setText("More")
    self._other_options_btn.clicked.connect(self._handle_other_options_btn)

    self._button_layout = QHBoxLayout()
    self._button_layout.addWidget(self._play_btn)
    self._button_layout.addWidget(self._other_options_btn)
    self._button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
    
    
    self._length_and_count_layout = QHBoxLayout()



    self._right_side_layout = QVBoxLayout()
    self._right_side_layout.addLayout(self._button_layout)
    self._right_side_layout.addLayout(self._length_and_count_layout)


    main_layout             = QHBoxLayout(self)
    
    # Layout of the whole item
    main_layout.addLayout(self._left_side_layout)
    main_layout.addLayout(self._right_side_layout)


    
    """
            LEFT-HAND                       RIGHT-HAND    
    |----------------------------------------------------------------------------------|
    +----------------------------------------------------------------------------------+
    |  PLAYLIST TITLE             | |> (play, no-random) ... (rename, delete playlist) | 
    |  Description...             | 00h 00m length             | 00 songs              |
    +----------------------------------------------------------------------------------+
    """ 


    self.setMaximumSize(600, 100)
    self.setMinimumSize(400, 60)

    self.setObjectName('playlist-selection')
    self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    


  
  def enterEvent(self, event : QEvent):
    print("EnterEvent")

    if not self._is_highlighted:
      self.toggle_on()
  
  def leaveEvent(self, event : QEvent):
    print("LeaveEvent")

    if not self._is_highlighted:
      self.toggle_off()
  
  
    


  def toggle_on(self):
    self._is_highlighted = True
    # Do something to show to the user
  
  def toggle_off(self):
    self._is_highlighted = False
    # Do something to show to the user


  
  def _handle_play_btn_click(self):
    self._selected_signal.emit(self._data) # Update UI to show playlist songs
    self._play_signal.emit()               # Tell AudioManager to begin playing
    pass

  def _handle_other_options_btn(self):
    pass