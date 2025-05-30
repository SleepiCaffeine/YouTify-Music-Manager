import utility as util
import os

from PySide6.QtMultimedia import ( QMediaPlayer, QMediaFormat )
from PySide6.QtCore import QUrl

class AudioPlayer:
  # The currently played audio segment
  _audio_segment = None
  # Currently opened file that's being played by _stream
  _curr_file = None

  player = QMediaPlayer()

  # Volume Slider from MIN to MAX
  _curr_volume : int = 0
  _VOLUME_MAX : int = 100
  _VOLUME_MIN : int = 0

  _curr_time_stamp : float = 0.0

  _is_stopped      : bool  = False
  

  def __init__(self):
    # Attempting to fix
    # qt.multimedia.audioresampler: Resampling failed -1072875851
    self.player.setPlaybackRate(48000)
    pass

  def play_song(self, path : str):
    try:
      print(path)
      self.player.setSource(QUrl.fromLocalFile(path))
      self.player.play()

    except Exception as e:
      print(str(e))