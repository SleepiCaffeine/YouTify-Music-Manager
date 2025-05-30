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

import sys, random, os, asyncio
from main import download_yt_video_with_hook, DownloadTracker

import utility as util
from PlaylistElement import (PlayListContainer, PlaylistElement)


CURRENT_PATH         = os.path.dirname(os.path.realpath(__file__))
# Add a way to change this
AUDIO_DOWNLOADS_PATH = os.path.join(os.path.split(CURRENT_PATH)[0],  'audio-downloads\\') 


class YoutubeDownloadWidget(QWidget):

    progress_updated = Signal(object)
    
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

        
        self.progress_updated.connect(self.update_progress_display)
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
                AUDIO_DOWNLOADS_PATH, 
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
        if self._curr_path != path and os.path.exists(path) :
            self._player.stop()
            self._player.setSource(path)
            self._curr_path = path

    @Slot()
    def play_song(self):
        self._player.play()

    @Slot()
    def pause_song(self):
        self._player.pause()


class UIContainer(QWidget):
    def __init__(self, parent : MainApplication):
        super().__init__()
        
        list_of_songs = [os.path.join(AUDIO_DOWNLOADS_PATH, x).replace('\\\\', '/').replace('\\', '/') for x in util.get_audio_file_names(AUDIO_DOWNLOADS_PATH)]
        
        self._playlist_container = PlayListContainer(list_of_songs)
        self._playlist_container._selected_song.connect(self._play_song)

        # Ways to interact with the Audio Player
        self._audio_play_btn = QPushButton()
        self._audio_play_btn.setText("Play!")
        self._audio_play_btn.clicked.connect(parent.handlePlayButtonClick)

        # Youtube downloader shenanigans
        self._yt_downloader = YoutubeDownloadWidget()

        # General layout
        layout = QHBoxLayout(self)
        layout.addWidget(self._playlist_container)
        
        #layout.addWidget(self._yt_downloader)
        #layout.addLayout(self._audio_btn_lay)

    @Slot(str)
    def _play_song(self, path : str):
        self.parent().handlePlayButtonClick(path)


class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()

        self._audio_player = AudioPlayer()
        

        self._ui_container = UIContainer(self)
        self.setCentralWidget(self._ui_container)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)
        open_action = QAction(icon=icon, text="&Open...", parent=self,
                              shortcut=QKeySequence.StandardKey.Open, triggered=self.open)


        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(open_action)

    def closeEvent(self, event):
        self._ensure_stopped()
        event.accept()

    def handlePlayButtonClick(self, path : str):

        if self._audio_player._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._audio_player.pause_song()
        else:
            self._audio_player.set_source(path)
            self._audio_player.play_song() 
    
                    
    
    def set_audio_source(self, path : str):
        self._audio_player.set_source(path)

    @Slot()
    def _ensure_stopped(self):
        if self._audio_player._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._audio_player._player.stop()
    

    @Slot()
    def open(self):
        self._ensure_stopped()
        file_dialog = QFileDialog(self)

        file_dialog.setDirectory( AUDIO_DOWNLOADS_PATH )
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
