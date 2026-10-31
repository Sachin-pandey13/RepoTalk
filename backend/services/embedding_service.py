from sentence_transformers import SentenceTransformer

from backend.services.chunking_service import chunk_code
from backend.services.vector_db_service import collection


model = SentenceTransformer("all-MiniLM-L6-v2")


code_chunks = []


def index_repository(parsed_files, repo_name):
    """
    Index repository code chunks into ChromaDB.

    Only embeddings belonging to the specified repository are removed
    before re-indexing. Other repositories remain untouched.
    """

    global code_chunks

    code_chunks = []

    # Remove only existing embeddings for this repository.
    existing = collection.get(
        where={"repo_name": repo_name}
    )

    if existing["ids"]:
        collection.delete(
            ids=existing["ids"]
        )

    for file_data in parsed_files:

        file_path = file_data["file"]

        functions = file_data.get("functions", [])
        classes = file_data.get("classes", [])
        imports = file_data.get("imports", [])

        text_representation = f"""
        Repository: {repo_name}

        File: {file_path}

        Functions:
        {functions}

        Classes:
        {classes}

        Imports:
        {imports}
        """

        chunks = chunk_code(text_representation)

        for chunk in chunks:

            vector = model.encode(chunk).tolist()

            chunk_id = f"{repo_name}_{file_path}_{len(code_chunks)}"

            collection.add(
                documents=[chunk],
                embeddings=[vector],
                metadatas=[
                    {
                        "file": file_path,
                        "repo_name": repo_name
                    }
                ],
                ids=[chunk_id]
            )

            code_chunks.append({
                "repo_name": repo_name,
                "file": file_path,
                "content": chunk
            })

    return {
        "repository": repo_name,
        "indexed_chunks": len(code_chunks)
    }


def semantic_search(query, repo_name, top_k=5):
    """
    Perform semantic search restricted to a specific repository.
    """

    query_vector = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where={
            "repo_name": repo_name
        }
    )

    formatted_results = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, distance in zip(
        documents,
        metadatas,
        distances
    ):

        formatted_results.append({
            "repo_name": meta.get("repo_name"),
            "file": meta.get("file"),
            "content": doc,
            "score": distance
        })

    return formatted_results