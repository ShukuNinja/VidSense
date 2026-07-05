"""Stdout-free service layer for ingestion and question answering.

Both the CLI (main.py) and the future web backend call into these functions.
Progress is emitted through a ProgressReporter so the caller decides how to
present it (console prints for the CLI, SSE events for the API).
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.youtube_utils import download_clip
from src.audio_utils import extract_audio
from src.transcriber import transcribe_audio
from src.chunker import parse_srt, create_chunks, save_chunks
from src.embedder import (
    extract_texts,
    generate_embeddings,
    save_embeddings,
    load_chunk_data,
)
from src.indexer import build_faiss_index, save_faiss_index
from src.retriever import embed_query, search_index, filter_results, retrieve_chunks
from src.context_builder import build_context
from src.context_compressor import text_extraction, process_regions, compress_evidence
from src.generator import generate_answer, stream_answer
from src.conversation import contextualize_query
from src.console_utils import print_header, print_success
from src.constants import (
    CHUNK_FOLDER,
    DEFAULT_TOP_K,
    EMBEDDING_BATCH_SIZE,
    EMBEDDINGS_FOLDER_PATH,
    INDEXES_FOLDER_PATH,
)


class ProgressReporter:
    """No-op progress sink. Subclass to render stages however you like."""

    def start(self, key: str, title: str) -> None:
        pass

    def success(self) -> None:
        pass


class ConsoleReporter(ProgressReporter):
    """Prints stage headers and successes to the console (used by the CLI)."""

    def start(self, key: str, title: str) -> None:
        print_header(title)

    def success(self) -> None:
        print_success()


@dataclass
class IngestResult:
    video_title: str
    language: str
    clip_path: str
    audio_path: str
    transcript_txt_path: str
    transcript_srt_path: str
    chunk_json_path: str
    embeddings_path: str
    index_path: str
    chunk_data: dict
    index: object  # faiss index


def ingest_video(info, start_time, end_time, stream_url, reporter=None) -> IngestResult:
    """Download a clip, transcribe it, and build a searchable FAISS index.

    Returns an IngestResult with all artifact paths plus the in-memory index and
    chunk data (so the caller can answer questions immediately). Raises
    PipelineError on any operational failure.
    """
    reporter = reporter or ProgressReporter()
    video_title = info["title"]

    reporter.start("download", "Downloading Clip...")
    clip_path = download_clip(info, start_time, end_time, stream_url)
    reporter.success()

    reporter.start("audio", "Extracting Audio...")
    audio_path = extract_audio(clip_path)
    reporter.success()

    reporter.start("transcribe", "Transcribing Audio...")
    transcript_txt_path, transcript_srt_path, language = transcribe_audio(audio_path)
    reporter.success()

    reporter.start("chunk", "Generating Chunks...")
    subtitles = parse_srt(transcript_srt_path)
    chunks = create_chunks(subtitles)
    chunk_json_path = save_chunks(chunks, video_title, language, CHUNK_FOLDER)
    chunk_data = load_chunk_data(chunk_json_path)
    reporter.success()

    reporter.start("index", "Embedding & Building Index...")
    texts = extract_texts(chunk_data)
    embeddings = generate_embeddings(texts, EMBEDDING_BATCH_SIZE)
    embeddings_path = save_embeddings(embeddings, video_title, EMBEDDINGS_FOLDER_PATH)
    index = build_faiss_index(embeddings)
    index_path = save_faiss_index(index, video_title, INDEXES_FOLDER_PATH)
    reporter.success()

    return IngestResult(
        video_title=video_title,
        language=language,
        clip_path=clip_path,
        audio_path=audio_path,
        transcript_txt_path=transcript_txt_path,
        transcript_srt_path=transcript_srt_path,
        chunk_json_path=chunk_json_path,
        embeddings_path=embeddings_path,
        index_path=index_path,
        chunk_data=chunk_data,
        index=index,
    )


def build_answer_context(query, history, index, chunk_data) -> dict:
    """Everything up to (but not including) generation for one turn.

    Decides follow-up vs new topic, then runs retrieval -> expansion ->
    compression. Returns the compressed evidence plus the metadata both the
    blocking and streaming answer paths need.
    """
    search_query, is_followup = contextualize_query(query, history)
    effective_history = history if is_followup else None

    query_embedding = embed_query(search_query)

    scores, indices = search_index(query_embedding, index, DEFAULT_TOP_K)
    filtered_scores, filtered_indices = filter_results(scores, indices)
    retrieved_chunks = retrieve_chunks(chunk_data, filtered_scores, filtered_indices)

    evidence = build_context(retrieved_chunks)
    evidence = text_extraction(evidence)
    # process_regions needs the 1-D query vector, not the (1, dim) batch.
    evidence = process_regions(evidence, query_embedding[0])
    compressed_evidence = compress_evidence(evidence)

    return {
        "search_query": search_query,
        "is_followup": is_followup,
        "effective_history": effective_history,
        "compressed_evidence": compressed_evidence,
    }


def citations_from(compressed_evidence) -> list:
    """Compact citation list (region id + clip-relative time span) for the UI."""
    return [
        {
            "region_id": region["region_id"],
            "start_time": region["start_time"],
            "end_time": region["end_time"],
        }
        for region in compressed_evidence.get("regions", [])
    ]


def answer_question(query, history, index, chunk_data) -> dict:
    """Answer one turn (blocking). Returns the generator result augmented with
    `is_followup` and the `search_query` used for retrieval. The caller owns
    history state (e.g. whether to reset it when is_followup is False)."""
    ctx = build_answer_context(query, history, index, chunk_data)

    result = generate_answer(
        query, ctx["compressed_evidence"], history=ctx["effective_history"]
    )
    result["is_followup"] = ctx["is_followup"]
    result["search_query"] = ctx["search_query"]

    return result


def stream_answer_question(query, history, index, chunk_data):
    """Answer one turn as a stream of events.

    Yields, in order: one {"type":"meta", ...}, many {"type":"token","text":...},
    then one {"type":"done", "answer", "is_followup", "citations"}.
    """
    ctx = build_answer_context(query, history, index, chunk_data)

    yield {
        "type": "meta",
        "is_followup": ctx["is_followup"],
        "search_query": ctx["search_query"],
    }

    parts = []
    for piece in stream_answer(
        query, ctx["compressed_evidence"], history=ctx["effective_history"]
    ):
        parts.append(piece)
        yield {"type": "token", "text": piece}

    yield {
        "type": "done",
        "answer": "".join(parts),
        "is_followup": ctx["is_followup"],
        "citations": citations_from(ctx["compressed_evidence"]),
    }
