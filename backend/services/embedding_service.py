from sentence_transformers import SentenceTransformer
from backend.services.chunking_service import chunk_code
from backend.services.vector_db_service import collection


model = SentenceTransformer("all-MiniLM-L6-v2")


code_chunks = []


def index_repository(parsed_files):

    global code_chunks

    code_chunks = []

    # Optional: clear old embeddings before re-indexing
    existing = collection.get()

    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    for file_data in parsed_files:

        file_path = file_data["file"]

        functions = file_data.get("functions", [])
        classes = file_data.get("classes", [])
        imports = file_data.get("imports", [])

        text_representation = f"""
        File: {file_path}

        Functions:
        {functions}

        Classes:
        {classes}

        Imports:
        {imports}
        """

        # Split into semantic chunks
        chunks = chunk_code(text_representation)

        for chunk in chunks:

            vector = model.encode(chunk).tolist()

            collection.add(
                documents=[chunk],
                embeddings=[vector],
                metadatas=[{"file": file_path}],
                ids=[f"{file_path}_{len(code_chunks)}"]
            )

            code_chunks.append({
                "file": file_path,
                "content": chunk
            })

    return {
        "indexed_chunks": len(code_chunks)
    }


def semantic_search(query, top_k=5):

    query_vector = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k
    )

    formatted_results = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, distance in zip(
        documents,
        metadatas,
        distances
    ):

        formatted_results.append({
            "file": meta["file"],
            "content": doc,
            "score": distance
        })

    return formatted_results