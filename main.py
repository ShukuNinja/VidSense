from src.retriever import (
    embed_query,
    search_index,
    filter_results,
    retrieve_chunks,
)
from src.indexer import build_faiss_index, save_faiss_index
from src.embedder import (
    extract_texts,
    generate_embeddings,
    load_chunk_data,
    save_embeddings,
)
from src.chunker import create_chunks, parse_srt, save_chunks
from src.audio_utils import extract_audio
from src.transcriber import transcribe_audio
from src.youtube_utils import get_user_input, download_clip
from src.console_utils import print_header, print_success, print_error, output_file
from src.context_builder import build_context
from src.context_compressor import (
    text_extraction,
    process_regions,
    compress_evidence,
)
from src.generator import generate_answer
from src.conversation import contextualize_query
from src.ollama_manager import check_ollama_health
from src.constants import (
    CHUNK_FOLDER,
    DEFAULT_TOP_K,
    EMBEDDING_BATCH_SIZE,
    EMBEDDINGS_FOLDER_PATH,
    INDEXES_FOLDER_PATH,
)


def ingest_clip():
    """Download a YouTube clip, transcribe it, and build a searchable index.

    Returns (chunk_data, index) on success, or None on any failure so the
    caller can abort cleanly.
    """
    print_header("YT Clip Downloader")
    info, start_time, end_time, stream_url = get_user_input()

    print_header("Downloading Clip...")
    clip_path = download_clip(info, start_time, end_time, stream_url)
    if not clip_path:
        print_error()
        return None
    print_success()

    print_header("Extracting Audio...")
    audio_path = extract_audio(clip_path)
    if not audio_path:
        print_error()
        return None
    print_success()

    print_header("Transcribing Audio...")
    transcript_txt_path, transcript_srt_path, language = transcribe_audio(audio_path)
    if not transcript_txt_path:
        print_error()
        return None
    print_success()

    subtitles = parse_srt(transcript_srt_path)
    chunks = create_chunks(subtitles)
    chunk_json_path = save_chunks(chunks, info["title"], language, CHUNK_FOLDER)
    if not chunk_json_path:
        print_error()
        return None
    print_success()

    chunk_data = load_chunk_data(chunk_json_path)
    output_file(
        clip_path,
        audio_path,
        transcript_txt_path,
        transcript_srt_path,
        chunk_json_path,
    )

    print_header("Chunk Generation Completed")

    texts = extract_texts(chunk_data)
    embeddings = generate_embeddings(texts, EMBEDDING_BATCH_SIZE)
    embeddings_file_path = save_embeddings(
        embeddings, info["title"], EMBEDDINGS_FOLDER_PATH
    )
    index = build_faiss_index(embeddings)
    index_file_path = save_faiss_index(index, info["title"], INDEXES_FOLDER_PATH)

    print_header("Index Built")
    print(f"Embeddings:\n{embeddings_file_path}")
    print(f"Index:\n{index_file_path}")
    print_success()

    return chunk_data, index


def answer_query(query, search_query, chunk_data, index, history=None):
    """Run the full RAG pipeline for a single query and return the result dict.

    `search_query` drives retrieval and sentence scoring (a standalone rewrite for
    follow-ups); `query` is the user's original phrasing shown to the model. When
    `history` is provided, prior turns are replayed so the model can resolve
    references — otherwise the question is answered self-contained.
    """
    query_embedding = embed_query(search_query)

    scores, indices = search_index(query_embedding, index, DEFAULT_TOP_K)
    filtered_scores, filtered_indices = filter_results(scores, indices)
    retrieved_chunks = retrieve_chunks(chunk_data, filtered_scores, filtered_indices)

    evidence = build_context(retrieved_chunks)
    evidence = text_extraction(evidence)
    # process_regions scores each sentence against the query and needs the
    # 1-D query vector, not the (1, dim) batch that embed_query returns.
    evidence = process_regions(evidence, query_embedding[0])
    compressed_evidence = compress_evidence(evidence)

    return generate_answer(query, compressed_evidence, history=history)


def question_loop(chunk_data, index):
    """Conversationally answer questions about the ingested clip until the user quits.

    Follow-up questions remember previous turns; a question on a new, unrelated
    topic resets the memory and is answered on its own.
    """
    print_header("Ask Questions (type 'exit' or 'quit' to stop)")

    history = []

    while True:
        query = input("\nQuestion: ").strip()
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            break

        # Decide follow-up vs. new topic before touching the retrieval pipeline.
        search_query, is_followup = contextualize_query(query, history)
        if not is_followup:
            # New/unrelated topic -> forget prior turns and start a fresh thread.
            history = []

        try:
            result = answer_query(
                query,
                search_query,
                chunk_data,
                index,
                history=history if is_followup else None,
            )
        except Exception as exc:
            print_error()
            print(f"    Failed to answer the question: {exc}")
            continue

        print("\nAnswer")
        print("-" * 40)
        print(result["answer"])

        history.append({"query": query, "answer": result["answer"]})


def main():
    ingested = ingest_clip()
    if ingested is None:
        return
    chunk_data, index = ingested

    print_header("Checking Ollama...")
    if not check_ollama_health():
        print("    Skipping the question stage. Your index has been saved and")
        print("    can be queried later once Ollama is available.")
        return
    print_success()

    question_loop(chunk_data, index)


if __name__ == "__main__":
    main()
