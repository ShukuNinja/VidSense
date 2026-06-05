import os
from src.constants import VIDEO_FOLDER
from src.file_utils import get_unique_filepath, sanitize_filename
import src.validators as validators
from src.ffmpeg_utils import create_clip

try:
    import yt_dlp  # type: ignore
except Exception as e:
    raise ImportError("yt_dlp is required. Install it with: pip install yt-dlp") from e

class SilentLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

def get_video_title(info):
    return info.get("title")

def get_video_info(url):

    ydl_opts = {
    "js_runtimes": {
        "node": {}
    },
    "logger": SilentLogger(),
    "quiet": True,
    "no_warnings": True,
    "noprogress": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download = False)
    return info


def get_stream_url(info):
    best_format = None
    best_height = -1
    for fmt in info["formats"]:
        if (fmt.get("vcodec") != "none" 
        and fmt.get("acodec") != "none" 
        and fmt.get("ext") == "mp4"):
            if fmt.get("height", 0) > best_height:
                best_height = fmt.get("height", 0)    
                best_format = fmt

    if best_format:
        return best_format["url"]
    
    return None

def get_video_duration(info):
    return info.get("duration")

def get_user_input():

    url = input ("Enter the YouTube URL: ")
    if not validators.validate_url(url):
        validators.fail("INVALID URL. Please enter a valid YouTube URL.")

    try:
        info = get_video_info(url)
    except Exception as e:
        validators.fail("Error occurred while fetching video info.")

    start_time = input("Enter Start Time (HH:MM:SS): ")
    if not validators.validate_timestamp(start_time):
        validators.fail("INVALID START TIME. Please enter a valid timestamp in HH:MM:SS format.")

    end_time = input("Enter End Time (HH:MM:SS): ")
    if not validators.validate_timestamp(end_time):
        validators.fail("INVALID END TIME. Please enter a valid timestamp in HH:MM:SS format.")

    if not validators.validate_timerange(start_time, end_time):
        validators.fail("INVALID TIME RANGE. Start time must be less than end time.")

    video_duration = get_video_duration(info)

    if not (validators.valid_video_duration(start_time, end_time, video_duration)):
        validators.fail("GIVEN TIME RANGE DOES NOT BELONG TO THE VIDEO DURATION.")

    stream_url = get_stream_url(info)

    if stream_url is None:
        validators.fail("STREAM URL NOT FOUND.")

    return info, start_time, end_time, stream_url

def download_clip(info,start_time, end_time,stream_url):
    clip_path = get_unique_filepath(get_video_title(info), VIDEO_FOLDER, ".mp4")
    result = create_clip(stream_url, start_time,end_time, clip_path)
    if not result:
        return None
    
    return clip_path


