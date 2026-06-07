from src.file_utils import sanitize_filename
import srt
import json
import os
from src.time_utils import format_timestamp

def parse_srt(srt_path):
    sub_list = []
    with open (srt_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    subtitles = srt.parse(content)

    for sub in subtitles:
        sub_list.append({
            "start_time": sub.start,
            "end_time": sub.end,
            "text": sub.content.strip()
        })
    
    return sub_list
        

def build_chunk(chunk_id, start_time, end_time, word_count, text):
    return {
        "chunk_id": chunk_id,
        "start_time": start_time,
        "end_time": end_time,
        "word_count": word_count,
        "text": text
    }


def create_chunks(subtitles, max_words=400):
    chunks = []
    current_chunk_text = []
    current_word_count = 0
    current_chunk_start_time = None
    current_chunk_end_time = None
    chunk_id = 1
    for sub in subtitles:
        word_count = len(sub["text"].split())
        if current_word_count + word_count <= max_words:
            current_chunk_text.append(sub["text"])
            current_word_count += word_count
            if current_chunk_start_time is None:
                current_chunk_start_time = sub["start_time"]
            current_chunk_end_time = sub["end_time"]

            
            
        else:
            chunks.append(build_chunk(chunk_id, current_chunk_start_time, current_chunk_end_time, current_word_count, " ".join(current_chunk_text)))
            chunk_id += 1
            current_chunk_start_time = sub["start_time"]
            current_chunk_end_time = sub["end_time"]
            current_chunk_text = [sub["text"]]
            current_word_count = word_count


    if current_chunk_text:
        chunks.append(build_chunk(chunk_id, current_chunk_start_time, current_chunk_end_time, current_word_count, " ".join(current_chunk_text)))

    return chunks



def save_chunks(chunks, video_title, language, output_path):
    serializable_chunks = []
    video_title = sanitize_filename(video_title)
    for chunk in chunks:
        serializable_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "start_time": format_timestamp(chunk["start_time"]),
            "end_time": format_timestamp(chunk["end_time"]),
            "word_count": chunk["word_count"],
            "text": chunk["text"]
        })
    dataset = {
        "video_title": video_title,
        "language" : language,
        "total_chunks" : len(chunks),
        "chunks": serializable_chunks
    }


    output_file = os.path.join(output_path, f"{video_title}_{language}.json")
    os.makedirs(output_path, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=4)
    
    return output_file
