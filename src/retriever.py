from src.embedder import get_model
from src.constants import ABSOLUTE_SCORE_THRESHOLD, ALPHA, DEFAULT_TOP_K, INSTRUCTION, WINDOW_SIZE, RETRIEVAL_TEST_QUERIES
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
    if scores.shape != indices.shape:
        raise ValueError(
            "Scores and indices must have the same shape."
        )
    if scores.ndim == 2:
        scores = scores[0]
        indices = indices[0]

    if scores.size == 0:
        return np.array([]), np.array([])
    
    relative_threshold = np.max(scores) * ALPHA
    threshold = max(relative_threshold, ABSOLUTE_SCORE_THRESHOLD)
    filtered_scores = scores[scores >= threshold]
    filtered_indices = indices[scores >= threshold]

    return filtered_scores, filtered_indices

def retrieve_chunks(chunk_data: dict, 
                    filtered_scores: np.ndarray,
                    filtered_indices: np.ndarray) -> list[dict]:
    
    score_lookup ={index: score for index, score in zip(filtered_indices, filtered_scores)}

    retrieved_chunks = []
    for chunk_id in filtered_indices:
        retrieved_chunk = {}
        chunk = chunk_data["chunks"][chunk_id]
        retrieved_chunk ["chunk_id"] = chunk["chunk_id"]
        retrieved_chunk["text"] = chunk["text"]
        retrieved_chunk["start_time"] = chunk["start_time"]
        retrieved_chunk["end_time"] = chunk["end_time"]
        retrieved_chunk["retrieval_score"] = score_lookup.get(chunk_id)
        retrieved_chunks.append(retrieved_chunk)

    return retrieved_chunks
