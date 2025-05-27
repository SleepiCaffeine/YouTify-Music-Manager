import json
import yt_dlp
import os

import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
from typing import Callable, Optional, Dict, Any

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
    self.speed : str | float | None = 0
    self.eta   : str | float | None = 0
    self.total_bytes : str | int | None = 0
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

"""
Creates, and returns a progress hook to pass into yt_dpl
progress_callback : Function to call with this DownloadProgress object at the end of the function
"""
def create_progress_hook(self, progress_callback : Optional[Callable] = None):
  
  progress_object = None
  
  def progress_hook(info : Dict[str, Any]):
    # Modify upper scope variable
    nonlocal progress_object
    info_dict : Dict[str, Any] = info.get('info_dict', {})

    if info['status'] == 'error':
      if progress_object == None:
        progress_object = DownloadTracker('Unknown')

      progress_object.status   = 'Error'
      progress_object.percent  = 0


    if progress_object == None:
        progress_object = DownloadTracker(info_dict.get('webpage_url', 'Unknown'))
    progress_object.filename = info_dict.get('filename', 'Unknown')


    if info["status"] == "downloading":
      progress_object.status   = 'downloading'

      if info_dict.get('total_bytes'):
        progress_object.total_bytes = info_dict['total_bytes']
      elif progress_object.total_bytes == None and info_dict.get('total_bytes_estimate'):
        progress_object.total_bytes = info_dict['total_bytes_estimate']        

      if info_dict.get('speed'):
        # info_dict['speed'] is saved as B/s, hence the division to get MB/s 
        progress_object.speed = info_dict['speed'] / (1024 * 1024)
      
      progress_object.eta = info_dict.get('eta')
      progress_object.downloaded_bytes = info_dict.get('downloaded_bytes', 0)
      
      progress_object.percent = int(progress_object.downloaded_bytes) / int(progress_object.total_bytes) if progress_object.downloaded_bytes and progress_object.total_bytes else 0.0
      
    
    elif info['status'] == 'finished':

      progress_object.status   = 'finished'
      progress_object.percent  = 100.0
      progress_object.speed    = 0
      progress_object.eta      = 0

    # Callback if provided
    if progress_callback and progress_object:
      progress_callback(progress_object)

  return progress_hook



# Returns an error code on error. Downloads a Youtube video as an mp3 into output_dir.
# Accepts a hook that will be called as the download progresses and exposes a DownloadTracker object.
async def download_yt_video_with_hook(URL : str, output_dir : str = output_dir, hook : Optional[Callable] = None) -> tuple[int, DownloadTracker] :

  def download_sync(url, out_dir, callback):
    
    phook = create_progress_hook(callback)
    
    ydl_opts = {
    'format': 'mp3/bestaudio/best',   
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'mp3',  # EDITABLE
    }],
      'outtmpl': out_dir + '%(title)s.%(ext)s',
      'progress_hooks' : [phook]
  }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      try:
        error_code = ydl.download([url])
        tracker = None
        
        if phook.__closure__ == None:
          tracker = DownloadTracker(URL)
          tracker.status = 'finished'
          tracker.percent = 100.0
        else:
          tracker = phook.__closure__[0].cell_contents
        return error_code, tracker
      
      except Exception as e:
        bad_tracker = DownloadTracker(URL)
        bad_tracker.status = 'error'
        return -1, bad_tracker
  
  
  loop = asyncio.get_event_loop()
  with ThreadPoolExecutor() as executor:
    return await loop.run_in_executor(executor, download_sync, URL, output_dir, hook)