from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget, QPlainTextEdit)
import PySide6.QtAsyncio as QtAsyncio

import sys, random, os, asyncio

from main import download_yt_video_with_hook, DownloadTracker

dir_path = os.path.dirname(os.path.realpath(__file__))



class YoutubeDownloadWidget(QMainWindow):

    progress_updated = Signal(object)
    
    def __init__(self):
        super().__init__()
        
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Enter in a valid Youtube URL")
        self.label = QLabel("Youtube to mp3 converter", alignment=Qt.AlignmentFlag.AlignCenter)
        self.output_dir = os.path.join(dir_path, '..', 'audio-downloads\\')
        
        self.progress_updated.connect(self.update_progress_display)
        
        async_download_trigger = QPushButton("Download Video!")
        async_download_trigger.clicked.connect(self.start_download)
        
        layout.addWidget(self.label)
        layout.addWidget(self.text_input)
        layout.addWidget(async_download_trigger)
        
        self.current_download_task = None
    
    def start_download(self):
        if self.current_download_task is not None and not self.current_download_task.done():
            self.label.setText("Download already in progress...")
            return
        
        url = self.text_input.toPlainText().strip()
        if not url:
            self.label.setText("Please enter a valid YouTube URL")
            return
        
        self.current_download_task = asyncio.create_task(self.yt_download_url(url))
    
    def youtube_audio_download_callback(self, tracker : DownloadTracker):
        self.progress_updated.emit(tracker)
    
    def update_progress_display(self, tracker : DownloadTracker):
        self.label.setText(str(tracker))
    

    async def yt_download_url(self, url: str):
        try:
            self.label.setText("Began download!")
            
            error_code, progress = await download_yt_video_with_hook(
                url, 
                self.output_dir, 
                self.youtube_audio_download_callback
            )
            
            if error_code != 0:
                self.label.setText(f"Error code: {error_code}")
            else:
                self.label.setText(f"Download completed! Saved to {self.output_dir}")
                
        except Exception as e:
            self.label.setText(f"Download failed: {str(e)}")
        finally:
            self.current_download_task = None




if __name__ == "__main__":
  app = QApplication([])

  MainWindow = YoutubeDownloadWidget()
  MainWindow.show()

  QtAsyncio.run(handle_sigint=True)
