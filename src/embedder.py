import json
import os
import numpy as np
from src.file_utils import get_unique_filepath, sanitize_filename
from sentence_transformers import SentenceTransformer
from src.constants import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, NORMALIZE_EMBEDDINGS

_model = None

def load_chunk_data(chunk_file_path: str) -> dict:
    with open(chunk_file_path, 'r', encoding = 'utf-8') as file:
        chunk_data = json.load (file)
    return chunk_data

def extract_texts(chunk_data: dict) -> list[str]:
    return [
        chunk["text"] 
        for chunk in chunk_data["chunks"]
    ]

def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    
    return _model

def generate_embeddings(texts: list[str], EMBEDDING_BATCH_SIZE) -> np.ndarray:
    if not texts:
        raise ValueError("No texts provided for embedding.")
    
    model = get_model()

    embeddings = model.encode(
        texts,
        batch_size = EMBEDDING_BATCH_SIZE,
        show_progress_bar = True,
        normalize_embeddings = NORMALIZE_EMBEDDINGS,
        convert_to_numpy = True
    )

    return embeddings.astype(np.float32)

def save_embeddings(embeddings: np.ndarray, video_title: str, EMBEDDINGS_FOLDER_PATH):
    embeddings_file_name = sanitize_filename(video_title)
    embeddings_file_path = get_unique_filepath(embeddings_file_name, EMBEDDINGS_FOLDER_PATH, ".npy")
    os.makedirs(EMBEDDINGS_FOLDER_PATH, exist_ok=True)
    np.save(embeddings_file_path, embeddings)
    
    return embeddings_file_path