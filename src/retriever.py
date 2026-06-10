from src.embedder import get_model
from src.constants import DEFAULT_TOP_K, INSTRUCTION
import numpy as np

def embed_query(query: str) -> np.ndarray:
    if not query.strip():
        raise ValueError("Query cannot be empty.")

    model = get_model()
    query_text = INSTRUCTION + query
    return model.encode([query_text], 
                        normalize_embeddings = True, 
                        convert_to_numpy=True)



def search_index(query_embedding: np.ndarray, index, top_k: int = DEFAULT_TOP_K) -> tuple[np.ndarray, np.ndarray]:
    
    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )
    
    if query_embedding is None:
        raise ValueError(
            "Query embedding cannot be None."
        )
    if index is None:
        raise ValueError(
            "FAISS index cannot be None."
        )
    
    scores,indices = index.search(
        query_embedding, top_k
    )

    return scores, indices

def filter_results(scores: np.ndarray, indices: np.ndarray):
    pass

def expand_context(retrieved_indices: np.ndarray):
    pass

def retrieve_chunks(expanded_indices: np.ndarray, 
                    chunk_data: list, 
                    scores: np.ndarray) -> list[dict]:
    
    pass

