from urllib.parse import urlparse

from src.errors import PipelineError

def validate_timestamp(timestamp):
    if len(timestamp.split(":")) != 3:
        return False
    hr,min,sec = timestamp.split(":")
    if not (hr.isdigit() and min.isdigit() and sec.isdigit()):
        return False
    
    if int(min) >=60 or int (sec) >= 60:
        return False
    
    parsed_seconds = int(hr)*3600 + int(min)*60 + int(sec)
    return parsed_seconds >= 0

def timestamp_to_seconds(timestamp):
    hr,min,sec = timestamp.split(":")
    return int(hr)*3600 + int(min)*60 + int(sec)

def validate_timerange(start_time,end_time):
    if not (validate_timestamp(start_time) and validate_timestamp(end_time)):
        return False
    
    start_seconds = timestamp_to_seconds(start_time)
    end_seconds = timestamp_to_seconds(end_time)

    return start_seconds < end_seconds

def seconds_to_timestamp(seconds):
    hr = seconds // 3600
    min = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hr:02d}:{min:02d}:{sec:02d}"

def valid_video_duration(start_time, end_time, video_duration):
    start_seconds = timestamp_to_seconds(start_time)
    end_seconds = timestamp_to_seconds(end_time)
    return start_seconds >= 0 and end_seconds <= video_duration and start_seconds < end_seconds


def validate_url(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    
    valid_domains = {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be"
    }

    if not parsed.scheme or not parsed.netloc:
        return False
    if parsed.netloc not in valid_domains:
        return False
    
    return parsed.netloc in valid_domains

def fail(message):
    raise PipelineError(message)
