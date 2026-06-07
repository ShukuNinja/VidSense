from src.chunker import create_chunks, parse_srt, save_chunks
from src.audio_utils import extract_audio
from src.transcriber import transcribe_audio
from src.youtube_utils import get_user_input, download_clip
import src.validators as validators
from src.console_utils import print_header, print_success, print_error, output_file
from src.constants import CHUNK_FOLDER

def main():

    print_header("YT Clip Downloader")
    info, start_time, end_time, stream_url = get_user_input()
    print_header("Downloading Clip...")
    clip_path = download_clip(info, start_time, end_time, stream_url)
    if not clip_path:
        print_error()
        return
    else:
        print_success()
    print_header("Extracting Audio...")
    audio_path = extract_audio(clip_path)
    if not audio_path:
        print_error()
        return
    else:
        print_success()
    print_header("Transcribing Audio...")
    transcript_txt_path, transcript_srt_path, language = transcribe_audio(audio_path)
    if not transcript_txt_path:
        print_error()
        return
    else:
        print_success()

    

    subtitles = parse_srt(transcript_srt_path)
    chunks = create_chunks(subtitles)
    chunk_json_path = save_chunks(chunks, info["title"], language, CHUNK_FOLDER)
    if not chunk_json_path:
        print_error()
        return
    else:
        print_success()

    output_file(clip_path, audio_path, transcript_txt_path, transcript_srt_path, chunk_json_path)

    print_header("Chunk Generation Completed")

    

if __name__ == "__main__":
    main()