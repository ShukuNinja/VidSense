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

    return subprocess.run(cmd)



    
