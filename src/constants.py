import os

# Folder Paths
AUDIO_FOLDER = "data/audio"
VIDEO_FOLDER = "data/videos"
TRANSCRIPTS_FOLDER = "data/transcripts"
CHUNK_FOLDER = "data/chunks"


# FFmpeg Settings
DEFAULT_VIDEO_FORMAT = "mp4"
DEFAULT_AUDIO_FORMAT = "wav"

# YouTube Settings
DEFAULT_LANGUAGE = "en"

# Embedding Configuration
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 32
NORMALIZE_EMBEDDINGS = True

# Query Embedding Instruction
INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)

# Vector Store Paths
VECTOR_STORE_FOLDER_PATH = "data/vector_store"
EMBEDDINGS_FOLDER_PATH = "data/vector_store/embeddings"
INDEXES_FOLDER_PATH = "data/vector_store/indexes"

# Retrieval Settings
DEFAULT_TOP_K = 20
ALPHA = 0.85
ABSOLUTE_SCORE_THRESHOLD = 0.6

#Retrieval evaluation report
RETRIEVAL_RESULTS_FOLDER = "data/retrieval_results"
RETRIEVAL_TEST_QUERIES = [
    # Exact Match
    "Who developed Java?",
    "What is JVM?",
    "What is JRE?",
    "What is JDK?",
    "What is bytecode?",
    "What is JShell?",
    "What is a variable?",
    "What is a compiler?",
    "What is a class?",
    "What is a method?",

    # Semantic Paraphrase
    "Who is responsible for creating Java?",
    "Who owns Java now?",
    "Why is Java platform independent?",
    "Why can Java run on multiple operating systems?",
    "What converts Java code into machine readable form?",
    "What software executes Java programs?",
    "Why do developers need JDK?",
    "What is the purpose of JShell?",
    "Why is Java popular in companies?",
    "Why is Java considered maintainable?",

    # Multi-Hop
    "How does Java code reach the JVM?",
    "What is the relationship between JDK JRE and JVM?",
    "Why do developers need JDK while users only need JRE?",
    "How does Java achieve Write Once Run Anywhere?",
    "What happens when javac compiles a Java file?",
    "How does a Java program start executing?",

    # Concept Expansion
    "Explain the Java execution flow.",
    "Explain Java architecture.",
    "How does Java run internally?",
    "How are Java applications executed?",
    "Describe the lifecycle of a Java program.",
    "What happens behind the scenes when Java code runs?",

    # Chunk Boundary Tests
    "Why do we need public static void main?",
    "What is the main method signature?",
    "Why does Java require a class?",
    "What is the difference between JShell and Java files?",
    "Why do we compile before running?",
    "What is generated after compilation?",

    # Similar Concept Tests
    "Difference between JVM and JDK",
    "Difference between JDK and JRE",
    "Difference between print and println",
    "Difference between byte and int",
    "Difference between float and double",
    "Difference between class and object",

    # Data Type Tests
    "What are primitive data types?",
    "What is an integer data type?",
    "What is a float?",
    "What is a double?",
    "What is a boolean?",
    "What is a character data type?",
    "Why does float require an f suffix?",
    "Why does long require an l suffix?",
    "What is the range of a byte?",
    "What is the range of an int?",

    # Stress Tests
    "Who created Java and who owns it now?",
    "Why is Java called Write Once Run Anywhere?",
    "How does bytecode help Java become platform independent?",
    "How are variables used during processing?",
    "Why does JVM require bytecode instead of Java source code?",
    "How does a programmer code reach the operating system?",

    # Negative Tests
    "What is the color of the shirt?",
    "Who is the president of India?",
    "What is ReactJS?",
    "How do neural networks work?",
    "What is Kubernetes?",
    "How do airplanes fly?",
    "What is quantum computing?"
]

SANITY_TEST_QUERIES = [
    "Who developed Java?",
    "Who is responsible for creating Java?",
    "What is Kubernetes?",
    "How does Java achieve Write Once Run Anywhere?"
]

GOLDEN_QUERIES = [
    "Who developed Java?",
    "What is JVM?",
    "What is JDK?",
    "What is JRE?",
    "Why is Java platform independent?",
    "How does Java achieve Write Once Run Anywhere?",
    "What is bytecode?",
    "How does Java code reach the JVM?",
    "Difference between JDK and JRE",
    "What is Kubernetes?"
]

EVALUATION_QUERIES = [
    "What is JVM?",
    "Explain JVM, JRE and JDK.",
    "Summarize everything about JVM.",
    "How does Java execution work?",
    "Why is Java platform independent?"
]

# LLM Settings
NO_EVIDENCE_RESPONSE = (
    "The video does not provide sufficient "
    "information to answer this question."
)

MODEL_NAME = os.getenv("VIDSENSE_MODEL", "llama3.2:3b")

# Controls Ollama's `think` request option:
#   None  -> don't send the param (for non-reasoning models like llama3.2)
#   False -> ask a reasoning model (e.g. qwen3) to skip its thinking phase
#   True  -> allow full chain-of-thought
# A plain instruct model answers directly and fast; reasoning models (qwen3)
# stay slow even with think=False because they narrate reasoning in the answer.
OLLAMA_THINK = None

# Conversation Settings
# How many recent (question, answer) turns to remember for follow-up questions.
MAX_HISTORY_TURNS = 6

# Ollama Resilience
# Total attempts per chat call. Guards against the transient CUDA cold-load
# crash where llama-server dies on the first request but recovers on retry.
OLLAMA_MAX_ATTEMPTS = 2
OLLAMA_RETRY_DELAY = 2.0

#Compression Settings
SIMILARITY_THRESHOLD = 0.60
DENSITY_THRESHOLD = 0.5
