# Folder Paths
AUDIO_FOLDER = "data/audio"
VIDEO_FOLDER = "data/videos"
TRANSCRIPTS_FOLDER = "data/transcripts"
CHUNK_FOLDER = "data/chunks"


# FFmpeg Settings
DEFAULT_VIDEO_FORMAT = "mp4"
DEFAULT_AUDIO_FORMAT = "mp3"

# YouTube Settings
DEFAULT_LANGUAGE = "en"

# Embedding Configuration
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 32
NORMALIZE_EMBEDDINGS = True

# Query Embedding Instruction
QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)

# Vector Store Paths
VECTOR_STORE_FOLDER = "data/vector_store"
EMBEDDINGS_FOLDER = "data/vector_store/embeddings"
INDEXES_FOLDER = "data/vector_store/indexes"