import subprocess

def create_clip(
    stream_url,
    start_time,
    end_time,
    output_file
):
    cmd = [
    "ffmpeg",
    "-hide_banner",
    "-loglevel", "error",
    "-y",
    "-ss", start_time,
    "-to", end_time,
    "-i", stream_url,
    "-c", "copy",
    output_file
]

    # Return whether ffmpeg succeeded. Previously this returned the
    # CompletedProcess object, which is always truthy, so a failed clip
    # (non-zero exit) slipped through download_clip's `if not result` guard.
    return subprocess.run(cmd).returncode == 0



    
