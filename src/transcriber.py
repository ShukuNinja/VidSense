from faster_whisper import WhisperModel
import os
from src.constants import TRANSCRIPTS_FOLDER
from src.file_utils import get_unique_filepath
from src.time_utils import format_timestamp


try:
    model = WhisperModel(
        "medium",
        device="cuda",
        compute_type="float16"
    )
except Exception as exc:
    print(f"CUDA initialization failed: {exc}")
    print("Falling back to CPU mode.")
    model = WhisperModel(
        "medium",
        device="cpu",
        compute_type="int8"
    )


def transcribe_audio(audio_path):

    audio_path = os.path.abspath(audio_path)


    transcript_filename = os.path.splitext(
        os.path.basename(audio_path)
    )[0]

    txt_path = get_unique_filepath(transcript_filename, TRANSCRIPTS_FOLDER, ".txt")

    srt_path = get_unique_filepath(transcript_filename, TRANSCRIPTS_FOLDER, ".srt")


    segments, info = model.transcribe(audio_path)


    print(f"Language detected: {info.language}")
    print(f"Confidence: {info.language_probability:.2%}")

    with open(txt_path, "w", encoding="utf-8") as txt_file, \
         open(srt_path, "w", encoding="utf-8") as srt_file:
        for index, segment in enumerate(segments, start=1):       
            
            txt_file.write(segment.text.strip() + "\n")        
            srt_file.write(f"{index}\n")
            srt_file.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
            srt_file.write(segment.text.strip() + "\n\n")

    return txt_path, srt_path, info.language