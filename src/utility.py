import os

PROJECT_PATH   = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
SOURCE_PATH    = os.path.join(PROJECT_PATH, 'src\\')
ICON_LOCATION  = os.path.join(PROJECT_PATH, 'icons\\')
STYLE_LOCATION = os.path.join(SOURCE_PATH, 'style\\')

def get_dir_filenames( dir : str ) -> list[str]:
  files = []
  for entry in os.scandir(dir):
    if not entry.is_file():
      continue
    files.append(entry.name)
  
  return files


def get_audio_file_names(dir : str) -> list[str]:
  audio_files = []
  all_files = get_dir_filenames(dir)

  # some random encodings I found, should probably double check these
  # since you can probably make some nasty stuff but eh. genuinely have never seen half of these
  valid_encodings = ["mp3", "adts", "3gp", "mov", "ogg", "wav", "rtp", "webm", "aac", "wma", "flac", "alac"]

  for file in all_files:
    for enc in valid_encodings:
      if file.endswith('.' + enc):
        audio_files.append(file)

  # This method isn't great, because anyone can add any file there
  # with an arbitrary ending, and this would be none the wiser
  # However the alternative of doing some serious byte sniffing
  # to determine the legitimacy of EVERY file would be insane.

  # this is also like a small project for a friend, so I don't give a shit
  return audio_files

def ms_to_text(ms : int) -> str:
  seconds = ms // 1000
  return f"{(seconds // 60):02d}:{(seconds % 60):02d}"