from src.youtube_utils import get_user_input
from src.console_utils import print_header, print_success, print_error, output_file
from src.pipeline import ingest_video, answer_question, ConsoleReporter
from src.llm import health_check
from src.errors import PipelineError


def ingest_clip():
    """CLI wrapper: gather input, run ingestion, print the artifact summary.

    Returns (chunk_data, index) on success, or None if a PipelineError aborts
    ingestion so the caller can stop cleanly.
    """
    try:
        print_header("YT Clip Downloader")
        info, start_time, end_time, stream_url = get_user_input()

        result = ingest_video(info, start_time, end_time, stream_url, ConsoleReporter())

        output_file(
            result.clip_path,
            result.audio_path,
            result.transcript_txt_path,
            result.transcript_srt_path,
            result.chunk_json_path,
        )

        print_header("Index Built")
        print(f"Embeddings:\n{result.embeddings_path}")
        print(f"Index:\n{result.index_path}")
        print_success()

        return result.chunk_data, result.index

    except PipelineError as exc:
        print_error()
        print(f"    {exc}")
        return None


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

        try:
            result = answer_question(query, history, index, chunk_data)
        except Exception as exc:
            print_error()
            print(f"    Failed to answer the question: {exc}")
            continue

        # New/unrelated topic -> forget prior turns and start a fresh thread.
        if not result["is_followup"]:
            history = []

        print("\nAnswer")
        print("-" * 40)
        print(result["answer"])

        history.append({"query": query, "answer": result["answer"]})


def main():
    ingested = ingest_clip()
    if ingested is None:
        return
    chunk_data, index = ingested

    print_header("Checking LLM...")
    ok, message = health_check()
    if not ok:
        print_error()
        if message:
            print(f"    {message}")
        print("    Skipping the question stage. Your index has been saved and")
        print("    can be queried later once the LLM is available.")
        return
    print_success()

    question_loop(chunk_data, index)


if __name__ == "__main__":
    main()
