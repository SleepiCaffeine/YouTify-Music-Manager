import json
import yt_dlp
import os


from PySide6.QtCore import (QDateTime, QDir, QLibraryInfo, QSysInfo, Qt,
                            QTimer, Slot, qVersion, Signal, QObject)
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

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, Optional, Dict, Any, Tuple

# Anything with an 'EDITABLE' above them
# means that they should be editable within the UI

# EDITABLE
URLS = ['https://www.youtube.com/watch?v=-v5vCLLsqbA']

# EDITABLE
output_dir = os.path.pardir + '/audio_downloads/'



"""
|  progress_hooks:    A list of functions that get called on download
|                     progress, with a dictionary with the entries
|                     * status: One of "downloading", "error", or "finished".
|                               Check this first and ignore unknown values.
|                     * info_dict: The extracted info_dict
|
|                     If status is one of "downloading", or "finished", the
|                     following properties may also be present:
|                     * filename: The final filename (always present)
|                     * tmpfilename: The filename we're currently writing to
|                     * downloaded_bytes: Bytes on disk
|                     * total_bytes: Size of the whole file, None if unknown
|                     * total_bytes_estimate: Guess of the eventual file size,
|                                             None if unavailable.
|                     * elapsed: The number of seconds since download started.
|                     * eta: The estimated time in seconds, None if unknown
|                     * speed: The download speed in bytes/second, None if
|                              unknown
|                     * fragment_index: The counter of the currently
|                                       downloaded video fragment.
|                     * fragment_count: The number of fragments (= individual
|                                       files that will be merged)
|
|                     Progress hooks are guaranteed to be called at least once
|                     (with status "finished") if the download is successful.
"""

# DownloadTracker is a wrapper class for the dictionary of information that
# yt_dlp.YoutubeDL provides through its progress_hooks. A full list of what
# available can be seen above
class DownloadTracker:

  def __init__(self, url : str):
    self.url = url
    self.status : str = "starting"
    self.percent : float = 0.0
    self.speed : str
    self.eta   : float | None = 0
    self.total_bytes : int | None = 0
    self.downloaded_bytes : int = 0
    self.filename : str = ""

  def __str__(self):
    match self.status:
      case "downloading":
        return f"[{self.percent:.2f}%] {self.filename} | Speed: {self.speed or 'N/A'} | ETA: {self.eta or 'N/A'}"
      case "finished":
        return f"[100%] {self.filename} - Download complete!"
      case "error":
        return f"[ERROR] {self.filename} - Download failed!"
      case _:
        return f"[{self.status.upper()}] {self.url}"




def format_bytes(bytes_value : float) -> str:
    if bytes_value is None:
        return None
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}/s"
        bytes_value /= 1024.0
    # this is for when google uses this
    return f"{bytes_value:.1f} PB/s"


def format_info_dict(info : Dict):
  progress_object = None
  info_dict : Dict[str, Any] = info.get('info_dict', {})

  # Create an error progress object if needed
  if info['status'] == 'error':
    if progress_object == None:
      progress_object = DownloadTracker('Unknown')

    progress_object.status   = 'Error'
    progress_object.percent  = 0

  # Create a progress object if one wasn't created earlier
  if progress_object == None:
      progress_object = DownloadTracker(info_dict.get('webpage_url', 'Unknown'))
  progress_object.filename = info_dict.get('filename', 'Unknown')

  # Here is where most of the dictionary parsing happens
  if info["status"] == "downloading":
    progress_object.status = 'downloading'
    
    # Get the total bytes downloaded if provided
    progress_object.total_bytes     = info_dict.get('total_bytes', 0)
    if progress_object.total_bytes == 0:
      progress_object.total_bytes   = info_dict.get('total_bytes_estimate', 0)        

    # Get the rest of the download info
    progress_object.speed            = format_bytes(info_dict.get('speed', 0))
    progress_object.eta              = info_dict.get('eta')
    progress_object.downloaded_bytes = info_dict.get('downloaded_bytes', 0)
    progress_object.percent          = int(progress_object.downloaded_bytes) / int(progress_object.total_bytes) if progress_object.downloaded_bytes and progress_object.total_bytes else 0.0
    
  # Format the data once it's finished
  elif info['status'] == 'finished':
    progress_object.status   = 'finished'
    progress_object.percent  = 100.0
    progress_object.speed    = "0 B/s"
    progress_object.eta      = 0
  
  return progress_object

def get_percent_from_download_log(log_str : str) -> float:
   # Example string
   # [download] 100% of   94.86MiB in 00:00:04 at 19.60MiB/s
   if "[download]" not in log_str:
      return 0
   return float(log_str[10:15].strip())


class ProgressSignalEmitter(QObject):
    progress_updated = Signal(object)





def yt_download_progress_hook(emitter : ProgressSignalEmitter, info : Dict):
  progress_obj = format_info_dict(info)  
  # Emit information in a TS way
  emitter.progress_updated.emit(progress_obj)


async def download_yt_video_with_hook(url: str, output_dir: str, progress_callback: Callable[[DownloadTracker], None]) -> tuple[int, DownloadTracker]:

    # Create signal emitter
    signal_emitter = ProgressSignalEmitter()
    signal_emitter.progress_updated.connect(progress_callback)
    
    # Create progress hook with the signal emitter
    progress_hook = partial(yt_download_progress_hook, signal_emitter)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
    'format': 'wav/bestaudio/best',
    'extractaudio': True,
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'wav',   # EDITABLE
          'preferredquality': '192', # EDITABLE        
      },
      {
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'wav',
      }
      ],
      # Trying to strongarm a palletable format so QtMediaOutput doesn't shit itself
      'postprocessor_args': [
        '-ar', '48000',      # Sample rate: 48kHz
        '-ac', '2',          # Channels: stereo
        '-sample_fmt', 's16' # Sample format: 16-bit signed integer
      ],

      'progress_hooks' : [progress_hook],
      "quiet" : True,
      "no_warnings" : True,
      'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
  }
    
    tracker = DownloadTracker(url)

    try:
       
      loop = asyncio.get_event_loop()

      def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          return ydl.download([url])

      result = await loop.run_in_executor(None, download)
      return result, tracker

    except yt_dlp.utils.DownloadError as err:
       error_msg = str(err)
       tracker.status = "error"

       if "sign in" in error_msg or "unable to extract" in error_msg:
          return -1, tracker # Youtube asking you if you're a bot
       else :
          return -2, tracker # Some other error
       
    except Exception as err:
       tracker.status = "error"
       return -3, tracker # heebee jeebies