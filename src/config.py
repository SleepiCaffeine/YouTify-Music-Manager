import json, os
import utility as util

# ------ Config File Shenanigans ------

config_obj = json.load(open(os.path.join(util.SOURCE_PATH, 'config.json'), 'r'))


def get_audio_download_dir() -> str:
    return config_obj["audio_download_path"]

def get_config_object() -> dict:
    return config_obj

def update_audio_download_dir(new_dir : str) -> None:
    if os.path.exists(new_dir):
        config_obj["audio_download_path"] = new_dir

def update_config_file() -> None:
  with open(os.path.join(util.SOURCE_PATH, 'config.json'), 'w') as cfg:
    cfg.write( json.dumps(config_obj) )