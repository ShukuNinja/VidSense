from src.youtube_utils import get_video_id


def _to_seconds(value):
    """Seconds from 'HH:MM:SS' or SRT-style 'HH:MM:SS,mmm' (ms dropped)."""
    core = value.split(",")[0]
    hours, minutes, seconds = core.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def _to_hms(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def enrich_citations(citations, source_url, clip_start):
    """Turn clip-relative citations into absolute video timestamps + deep-links.

    Region times from the pipeline are relative to the clip (which starts at 0),
    so add the clip's start offset to get the position in the original video and
    build a `watch?v=...&t=<secs>s` link.
    """
    video_id = get_video_id(source_url)
    base = _to_seconds(clip_start)

    enriched = []
    for citation in citations:
        abs_start = base + _to_seconds(citation["start_time"])
        item = dict(citation)
        item["timestamp"] = _to_hms(abs_start)
        item["youtube_url"] = (
            f"https://www.youtube.com/watch?v={video_id}&t={abs_start}s"
            if video_id
            else None
        )
        enriched.append(item)

    return enriched
