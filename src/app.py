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
from main import download_yt_video_with_hook, DownloadTracker

import utility as util
from PlaylistElement import (PlayListContainer, PlaylistElement)


# ------ Config File Shenanigans ------

config_obj          = json.load(open(os.path.join(util.SOURCE_PATH, 'config.json'), 'r'))


def get_audio_download_dir() -> str:
    return config_obj["audio_download_path"]

def get_config_object() -> dict:
    return config_obj

def update_audio_download_dir(new_dir : str) -> None:
    if os.path.exists(new_dir):
        config_obj["audio_download_path"] = new_dir



class YoutubeDownloadWidget(QWidget):

    progress_updated_signal   = Signal(object)
    download_completed_signal = Signal()
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        self.label = QLabel("Some Youtube Music Manager", alignment=Qt.AlignmentFlag.AlignCenter)

        
        
        self.yt_download_widget = QWidget()
        self.yt_download_widget.setMaximumSize(200, 80)
        self.yt_download_layout = QVBoxLayout(self.yt_download_widget)

        

        # Create tex input for the URL
        self.yt_text_input = QPlainTextEdit()
        self.yt_text_input.setPlaceholderText("Enter in a valid Youtube URL")

        
        self.progress_updated_signal.connect(self.update_progress_display)
        self.progress_bar = self.create_progress_bar()
        self.progress_bar.setVisible(False)
        
        self.yt_download_button = QPushButton("Download Video!")
        self.yt_download_button.clicked.connect(self.start_download)
        
        self.yt_download_layout.addWidget(self.yt_text_input)
        self.yt_download_layout.addWidget(self.yt_download_button)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)



        layout.addWidget(self.label)
        layout.addWidget(self.yt_download_widget)
    
        layout.addWidget(self.progress_bar)
        
        self.current_download_task = None
    
    def update_progress_bar(self, new_value):
        self.progress_bar.setValue(new_value)

    def create_progress_bar(self):
        result = QProgressBar()
        result.setRange(0, 100)
        result.setValue(0)
        return result

    def start_download(self):
        # Reset bar after possible previous interaction
        self.update_progress_bar(0)
        self.progress_bar.setVisible(True)
        

        if self.current_download_task is not None and not self.current_download_task.done():
            self.label.setText("Download already in progress...")
            return
        
        # URL validation
        url = self.yt_text_input.toPlainText().strip()
        if len(url) == 0 or ("youtube." not in url and "youtu.be" not in url):
            self.label.setText("Please enter a valid YouTube URL")
            return
        
        self.current_download_task = asyncio.create_task(self.yt_download_url(url))

    def youtube_audio_download_callback(self, tracker : DownloadTracker):
         QTimer.singleShot(0, lambda: self.update_progress_display(tracker))
    

    def update_progress_display(self, tracker : DownloadTracker):
        self.update_progress_bar(tracker.percent)
        self.label.setText(str(tracker))
        QApplication.processEvents()
    
    

    async def yt_download_url(self, url: str):
        try:
            
            task = asyncio.create_task(download_yt_video_with_hook(
                url, 
                get_audio_download_dir(), 
                self.youtube_audio_download_callback
            ))

            self.label.setText("Began download!")

            # Now... I hear you..
            # However for whatever strange reason - yt-dlp doesn't
            # want to callback with any relavant info

            # Sooooo.... the UX demands outweigh the logic
            self.update_progress_bar(2)
            await asyncio.sleep(0.1)
            self.update_progress_bar(5)
            await asyncio.sleep(0.2)
            self.update_progress_bar(12)
            await asyncio.sleep(0.3)
            self.update_progress_bar(14)
            await asyncio.sleep(1)
            self.update_progress_bar(32)
            
            error_code, progress = await task 
            
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
            # Keep progress bar visible to show final result
            QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))  # Hide after 3 seconds
            # Emit signal to inform that a download is done
            self.download_completed_signal.emit()


class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize the media playback stuff
        self._audio_output = QAudioOutput()
        self._player       = QMediaPlayer()
        self._curr_path : str = ""
        self._player.setAudioOutput(self._audio_output)
        
    @Slot()
    def set_source(self, path : str):
        if self._curr_path != path and os.path.exists(path):
            self._player.stop()
            self._player.setSource(path)
            self._curr_path = path

    @Slot()
    def play_song(self):
        self._player.play()

    @Slot()
    def pause_song(self):
        self._player.pause()

    @Slot()
    def _ensure_stopped(self):
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._player.stop()


class UIContainer(QWidget):

    _play_song_signal = Signal(str, int)
    

    def __init__(self, parent : MainApplication):
        super().__init__()
        
        list_of_songs = [os.path.join(get_audio_download_dir(), song) 
                         for song in util.get_audio_file_names( get_audio_download_dir() )]
  
        self._playlist_container = PlayListContainer(list_of_songs)
        self._playlist_container._selected_song.connect(self._play_song)

        # Ways to interact with the Audio Player
        self._audio_play_btn = QPushButton()
        self._audio_play_btn.setText("Play!")
        self._audio_play_btn.clicked.connect(parent.handlePlayButtonClick)

        # Youtube downloader shenanigans
        self._yt_downloader = YoutubeDownloadWidget()
        self._yt_downloader.download_completed_signal.connect(self._refresh_playlist)

        self._refresh_btn = QPushButton()
        self._refresh_btn.clicked.connect(self._refresh_playlist)
        self._refresh_btn.setText("Refresh")

        self._set_audio_download_folder_btn = QPushButton()
        self._set_audio_download_folder_btn.setText("Audio Location")
        self._set_audio_download_folder_btn.clicked.connect(self._update_audio_download_folder)


        # General layout
        layout = QHBoxLayout(self)
        layout.addWidget(self._playlist_container)
        
        layout.addWidget(self._yt_downloader)
        layout.addWidget(self._refresh_btn)
        layout.addWidget(self._set_audio_download_folder_btn)

    @Slot(str)
    def _play_song(self, path : str, index_of_song : int):
        self._play_song_signal.emit(path, index_of_song)
    
    def _toggle_off_songs(self, index_to_ignore : int = -1):
        self._playlist_container._toggle_off_every_element(index_to_ignore)

    def _refresh_playlist(self):
        self._playlist_container.refresh_playlist_elements( get_audio_download_dir() )

    def _update_audio_download_folder(self):
        selected_dir = QFileDialog.getExistingDirectory()
        update_audio_download_dir(selected_dir)
        self._refresh_playlist()
        pass


class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()

        self._audio_player = AudioPlayer()
        
        self._ui_container = UIContainer(self)
        self._ui_container._play_song_signal.connect(self.handlePlayButtonClick)
        self.setCentralWidget(self._ui_container)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)
        open_action = QAction(icon=icon, text="&Open...", parent=self,
                              shortcut=QKeySequence.StandardKey.Open, triggered=self.open)


        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(open_action)

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

        file_dialog.setDirectory( get_audio_download_dir() )
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
  
  #  Update Config file
  with open(os.path.join(util.SOURCE_PATH, 'config.json'), 'w') as cfg:
    cfg.write( json.dumps(config_obj) )
 
  
