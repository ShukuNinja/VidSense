import subprocess

from src import validators
import os 
from src.constants import AUDIO_FOLDER
from src.file_utils import get_unique_filepath



def extract_audio(clip_path):
    audio_filename, _ = os.path.splitext(os.path.basename(clip_path))
    audio_path = get_unique_filepath(audio_filename, AUDIO_FOLDER, ".wav")
    
    cmd = [
    "ffmpeg",
    "-hide_banner",
    "-loglevel", "error",
    "-i", clip_path,
    audio_path
    ]

    if subprocess.run(cmd).returncode != 0:
        validators.fail("Failed to extract audio.")
        
    return audio_path
