from __future__ import annotations


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal)
from PySide6.QtGui import (QCursor, QDesktopServices, QGuiApplication, QIcon,
                           QKeySequence, QShortcut, QStandardItem,
                           QStandardItemModel)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,
                               QCommandLinkButton, QDateTimeEdit, QDial,
                               QDialog, QDialogButtonBox, QFileSystemModel,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListView, QMenu, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton,
                               QScrollBar, QSizePolicy, QSlider, QSpinBox,
                               QStyleFactory, QTableWidget, QTabWidget,
                               QTextBrowser, QTextEdit, QToolBox, QToolButton,
                               QTreeView, QVBoxLayout, QWidget, QMainWindow)

import PySide6.QtAsyncio as QtAsyncio

import sys, random, os, asyncio

from main import download_yt_video_with_hook, DownloadTracker

dir_path = os.path.dirname(os.path.realpath(__file__))



class YoutubeDownloadWidget(QWidget):

    progress_updated = Signal(object)
    
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        
        
        self.label = QLabel("Youtube to mp3 converter", alignment=Qt.AlignmentFlag.AlignCenter)
        self.output_dir = os.path.join(dir_path, '..', 'audio-downloads\\')
        
        
        self.yt_download_widget = QWidget()
        self.yt_download_widget.setMaximumSize(200, 80)
        self.yt_download_layout = QVBoxLayout(self.yt_download_widget)

        # Create tex input for the URL
        self.yt_text_input = QPlainTextEdit()
        self.yt_text_input.setPlaceholderText("Enter in a valid Youtube URL")
        self.yt_text_input.setMaximumSize(200, 30)

        
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
        if not url or "youtube." not in url or "youtu.be" not in url:
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
                self.output_dir, 
                self.youtube_audio_download_callback
            ))

            self.label.setText("Began download!")

            # Now... I hear you..
            # However for whatever strange reason - yt-dlp doesn't
            # want to callback with any relavant info

            # Sooooo.... the UX demands outweigh the logic
            # self.update_progress_bar(2)
            # await asyncio.sleep(0.1)
            # self.update_progress_bar(5)
            # await asyncio.sleep(0.2)
            # self.update_progress_bar(12)
            # await asyncio.sleep(0.3)
            # self.update_progress_bar(14)
            # await asyncio.sleep(1)
            # self.update_progress_bar(32)
            
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






if __name__ == "__main__":
  app = QApplication([])
  # Looks like Linux
  app.setStyle("Fusion")
  

  MainWindow = YoutubeDownloadWidget()
  MainWindow.setWindowTitle("YouTify Music Manager")
  MainWindow.show()

  QtAsyncio.run(handle_sigint=True)
