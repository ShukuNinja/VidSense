import os

import numpy as np
from src.constants import INDEXES_FOLDER_PATH
import faiss
from src.file_utils import get_unique_filepath, sanitize_filename

def build_faiss_index(embeddings: np.ndarray):
    
    if embeddings is None:
        raise ValueError("Embeddings cannot be None.")
    
    if embeddings.shape[0] == 0:
        raise ValueError("Embeddings not provided for indexing.")
    
    if not isinstance(embeddings, np.ndarray):
        raise ValueError("Embeddings must be a NumPy array.")
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    return index

def save_faiss_index(index, video_title, INDEXES_FOLDER_PATH):
    if index is None:
        raise ValueError("FAISS index cannot be None.")
    
    index_file_name = sanitize_filename(video_title)
    index_file_path = get_unique_filepath(index_file_name, INDEXES_FOLDER_PATH, ".index")
    faiss.write_index(index, index_file_path)

    return index_file_path


def load_faiss_index(index_file_path):
    if not os.path.isfile(index_file_path):
        raise FileNotFoundError(f"FAISS index file not found: {index_file_path}")
    return faiss.read_index(index_file_path)


