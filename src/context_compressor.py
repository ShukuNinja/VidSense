import re
import numpy as np

from src.constants import EMBEDDING_BATCH_SIZE, SIMILARITY_THRESHOLD, DENSITY_THRESHOLD
from src.embedder import generate_embeddings

def split_sentences(extracted_text):
    sanitised_text = re.split(r'[.!?]+', extracted_text)
    sentences = [sentence.strip() 
                 for sentence in sanitised_text 
                 if sentence.strip()]
    return sentences

def text_extraction(evidence):
    regions = evidence.get("regions", [])
    for region in regions:
        sentences = []
        extracted_text = ""
        chunks = region.get("chunks", [])
        for chunk in chunks:
            for sentence in split_sentences(chunk.get("text", "")):
                sentences.append(sentence)
            extracted_text += chunk.get("text", "") + " "
        region["extracted_text"] = extracted_text
        region["sentences"] = sentences
        region["total_sentences"] = len(sentences)

    return evidence

def embed_sentences(sentences):
    sentence_embeddings = []
    for sentence in sentences:
        if not sentence.strip():
            raise ValueError("Empty sentence found. Please check the extracted text.")
    
    return (generate_embeddings(sentences, EMBEDDING_BATCH_SIZE))


def score_sentences(
    query_embedding,
    sentence_embeddings,
    sentences
):

    scored_sentences = []

    for sentence, embedding in zip(
        sentences,
        sentence_embeddings
    ):

        score = np.dot(
            query_embedding,
            embedding
        )

        scored_sentences.append(
            {
                "sentence": sentence,
                "score": float(score)
            }
        )

    return scored_sentences

def process_regions(
    evidence,
    query_embedding
):

    for region in evidence["regions"]:

        sentences = region["sentences"]

        sentence_embeddings = embed_sentences(
            sentences
        )

        region["scored_sentences"] = score_sentences(
            query_embedding,
            sentence_embeddings,
            sentences
        )

    return evidence

def compute_density(
    region,
    similarity_threshold=SIMILARITY_THRESHOLD
):
    scored_sentences = region.get(
        "scored_sentences",
        []
    )

    total_sentences = region.get(
        "total_sentences",
        0
    )

    if total_sentences == 0:
        raise ValueError(
            "Total sentences is zero."
        )

    relevant_sentences = sum(
        1
        for sentence in scored_sentences
        if sentence["score"] >= similarity_threshold
    )

    binary_density = (
        relevant_sentences
        / total_sentences
    )

    weighted_density = (
        sum(
            sentence["score"]
            for sentence in scored_sentences
        )
        / total_sentences
    )

    region["relevant_sentences"] = (
        relevant_sentences
    )

    region["binary_density"] = (
        binary_density
    )

    region["weighted_density"] = (
        weighted_density
    )

    return region

def compress_region(region):

    compressed_region = {
    "region_id": region["region_id"],
    "binary_density": region["binary_density"],
    "weighted_density": region["weighted_density"],
    "start_time": region["start_time"],
    "end_time": region["end_time"]
}

    if region["binary_density"] >= DENSITY_THRESHOLD:

        compressed_region["mode"] = "full"
        compressed_region["text"] = region["extracted_text"]

    else:

        compressed_region["mode"] = "compressed"
        compressed_region["text"] = " ".join(
            sentence["sentence"]
            for sentence in region["scored_sentences"]
            if sentence["score"] >= SIMILARITY_THRESHOLD
        )

    return compressed_region

def compress_evidence(evidence):

    compressed_regions = []

    for region in evidence["regions"]:

        compute_density(region)

        compressed_region = compress_region(region)

        compressed_regions.append(
            compressed_region
        )

    return {
        "regions": compressed_regions
    }



