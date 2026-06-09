from src.indexer import build_faiss_index, save_faiss_index
from src.embedder import extract_texts, generate_embeddings, load_chunk_data, save_embeddings
from src.chunker import create_chunks, parse_srt, save_chunks
from src.audio_utils import extract_audio
from src.transcriber import transcribe_audio
from src.youtube_utils import get_user_input, download_clip
import src.validators as validators
from src.console_utils import print_header, print_success, print_error, output_file
from src.constants import CHUNK_FOLDER, EMBEDDING_BATCH_SIZE, EMBEDDINGS_FOLDER_PATH, INDEXES_FOLDER_PATH

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

    chunk_data = load_chunk_data(chunk_json_path)
    texts = extract_texts(chunk_data)
    embeddings = generate_embeddings(texts, EMBEDDING_BATCH_SIZE)
    embeddings_file_path = save_embeddings(embeddings, info["title"], EMBEDDINGS_FOLDER_PATH)
    index = build_faiss_index(embeddings)
    index_file_path = save_faiss_index(index, info["title"], INDEXES_FOLDER_PATH)
    


    output_file(clip_path, audio_path, transcript_txt_path, transcript_srt_path, chunk_json_path)

    print_header("Chunk Generation Completed")

    

if __name__ == "__main__":
    main()