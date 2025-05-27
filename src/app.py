from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget, QPlainTextEdit)
import PySide6.QtAsyncio as QtAsyncio

import sys, random, os, asyncio

from main import download_yt_video_with_hook, DownloadTracker

dir_path = os.path.dirname(os.path.realpath(__file__))



class YoutubeDownloadWidget(QMainWindow):
  def __init__(self):
    super().__init__()

    widget = QWidget()
    self.setCentralWidget(widget)
    layout = QVBoxLayout(widget)
    

    self.text_input = QPlainTextEdit()
    self.text_input.setPlaceholderText("Enter in a valid Youtube URL")
    self.label      = QLabel("Youtube to mp3 converter", alignment = Qt.AlignmentFlag.AlignCenter)
    self.output_dir = os.path.join(dir_path + '\\..\\audio-downloads\\')


    async_download_trigger = QPushButton("Download Video!")
    async_download_trigger.clicked.connect(lambda: asyncio.ensure_future(self.yt_download_url()))

    layout.addWidget(self.label)
    layout.addWidget(self.text_input)
    layout.addWidget(async_download_trigger)


  def youtube_audio_download_callback(self, tracker : DownloadTracker):
    self.label.setText(str(tracker))

  
  async def yt_download_url(self):
    yt_download = download_yt_video_with_hook(self.text_input.toPlainText(), self.output_dir, self.youtube_audio_download_callback)
    self.label.setText("Began download")

    error_code, tracker = await yt_download

    if error_code != 0:
      self.label.setText("Error code: " + str(error_code))
    else:
      self.label.setText("Saved file to " + self.output_dir)








if __name__ == "__main__":
  app = QApplication([])

  MainWindow = YoutubeDownloadWidget()
  MainWindow.show()

  QtAsyncio.run(handle_sigint=True)
