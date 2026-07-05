class PipelineError(Exception):
    """An anticipated, user-facing failure in the ingestion pipeline.

    Raised for operational failures the user can act on (invalid input, a
    failed download, failed audio extraction). ingest_clip() catches it once
    and aborts with a clear message instead of an abrupt exit() or a stack
    trace. Programming-contract violations elsewhere still use ValueError.
    """
    pass
