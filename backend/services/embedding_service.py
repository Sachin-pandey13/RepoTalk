from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


model = SentenceTransformer("all-MiniLM-L6-v2")


code_chunks = []
embeddings = []


def index_repository(parsed_files):

    global code_chunks
    global embeddings

    code_chunks = []
    embedding_vectors = []

    for file_data in parsed_files:

        file_path = file_data["file"]

        functions = file_data.get("functions", [])
        classes = file_data.get("classes", [])
        imports = file_data.get("imports", [])

        text_representation = f"""
        File: {file_path}
        Functions: {functions}
        Classes: {classes}
        Imports: {imports}
        """

        code_chunks.append(text_representation)

        vector = model.encode(text_representation)

        embedding_vectors.append(vector)

    embeddings = np.array(embedding_vectors)

    return {
        "indexed_files": len(code_chunks)
    }


def semantic_search(query, top_k=5):

    query_vector = model.encode(query)

    similarities = cosine_similarity(
        [query_vector],
        embeddings
    )[0]

    top_indices = similarities.argsort()[-top_k:][::-1]

    results = []

    for idx in top_indices:

        results.append({
            "score": float(similarities[idx]),
            "content": code_chunks[idx]
        })

    return results