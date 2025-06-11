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


import utility as util
import config
from playlist import (PlayListContainer, PlaylistElement)
from widgets import (MusicDownloadWidget, AudioPlayer, UIContainer) 






class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()

        self._audio_player = AudioPlayer()
        
        self._ui_container = UIContainer(self)
        self._ui_container._play_song_signal.connect(self.handlePlayButtonClick)
        self.setCentralWidget(self._ui_container)


    def closeEvent(self, event):
        self._audio_player._ensure_stopped()
        event.accept()

    def handlePlayButtonClick(self, path : str, index_of_song : int):
        # There are 3 possible states:
        # 1. The player is stopped (No song/Finished previous)
        # 2. It is paused
        # 3. It is playing

        # If the user is attempting to play a song with the same path as the current one,
        # This means that they're trying to either pause or unpause the song.

        if self._audio_player._curr_path == path:
            if self._audio_player._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._audio_player.pause_song()
            else:
                self._audio_player.play_song()
        
        # Otherwise, they're trying to play something else.

        else:
            self._ui_container._toggle_off_songs(index_of_song)
            self._audio_player._ensure_stopped()
            self._audio_player.set_source(path)
            self._audio_player.play_song()
        
                    
    
    def set_audio_source(self, path : str):
        
        self._audio_player.set_source(path)
    

    @Slot()
    def open(self):
        self._audio_player._ensure_stopped()
        file_dialog = QFileDialog(self)

        file_dialog.setDirectory( config.get_audio_download_dir() )
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
  
  config.update_config_file()
 
  
