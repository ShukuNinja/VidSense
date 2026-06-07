def print_header(title):
    print(f"==========================\n{title}\n=============================")
def print_success():
    print(" ✔️ SUCCESS")
def print_error():
    print(" ❌ ERROR")

def output_file(clip_path, audio_path, transcript_txt_path, transcript_srt_path, chunk_json_path):
    print(f"Video:\n{clip_path}")
    print(f"Audio:\n{audio_path}")
    print(f"Transcript:\n{transcript_txt_path}")
    print(f"Subtitle:\n{transcript_srt_path}")
    print(f"Chunk JSON:\n{chunk_json_path}")
    print("All files have been saved successfully.\n\n")
