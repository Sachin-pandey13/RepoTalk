"""
backend/services/embedding_service.py

Indexes repository source code into ChromaDB and performs semantic search.

Key improvements over the original:
 • Embeds REAL source code chunks, not just function-name lists
 • Stores rich metadata (file, language, function names, line range)
 • Deduplicates chunk IDs with a content hash to avoid collisions
 • Batch-inserts for speed
 • semantic_search returns scored results sorted by relevance
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

from sentence_transformers import SentenceTransformer

from backend.services.chunking_service import chunk_code
from backend.services.vector_db_service import collection

# ── Model (loaded once at import time) ────────────────────────────────────────
# all-MiniLM-L6-v2 is fast (~80MB) and good for code similarity.
# Swap for "BAAI/bge-base-en-v1.5" or "microsoft/codebert-base" for better
# code-specific recall at the cost of more RAM / slower encode.
_model = SentenceTransformer("all-MiniLM-L6-v2")

_BATCH_SIZE = 64   # Chroma insert batch size

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
    ".cs": "csharp", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".kt": "kotlin",
    ".sh": "shell", ".md": "markdown",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".html": "html", ".css": "css",
}


def _chunk_id(repo_name: str, file_path: str, idx: int, text: str) -> str:
    """Stable, collision-safe chunk ID."""
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:8]
    safe_path = file_path.replace("\\", "/").replace(" ", "_")
    return f"{repo_name}::{safe_path}::{idx}::{digest}"


def _extract_fn_names(file_data: dict) -> list[str]:
    """Return a flat list of function names from parsed file data."""
    fns = file_data.get("functions", [])
    names: list[str] = []
    for f in fns:
        if isinstance(f, dict):
            names.append(f.get("name", ""))
        elif isinstance(f, str):
            names.append(f)
    return [n for n in names if n]


def index_repository(parsed_files: list[dict], repo_name: str) -> dict:
    """
    Index every source file in *parsed_files* into ChromaDB.

    Steps per file:
      1. Build a rich header (file path, language, function/class names,
         imports) prepended to each chunk so the embedding carries context.
      2. Chunk the raw source with overlap.
      3. Encode all chunks in one batch.
      4. Insert into ChromaDB with metadata.

    Existing embeddings for this repo are removed first so re-indexing is
    always clean.
    """
    # --- Remove stale embeddings for this repo ----------------------------
    existing = collection.get(where={"repo_name": repo_name})
    if existing["ids"]:
        # Delete in batches of 500 to avoid Chroma limits
        ids = existing["ids"]
        for i in range(0, len(ids), 500):
            collection.delete(ids=ids[i : i + 500])

    total_chunks = 0
    skipped = 0

    # Accumulators for batch insert
    docs: list[str] = []
    embeddings: list[list[float]] = []
    metas: list[dict] = []
    ids: list[str] = []

    def _flush():
        nonlocal total_chunks
        if not docs:
            return
        collection.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)
        total_chunks += len(docs)
        docs.clear(); embeddings.clear(); metas.clear(); ids.clear()

    for file_data in parsed_files:
        if "error" in file_data:
            skipped += 1
            continue

        file_path: str = file_data.get("file", "")
        ext = os.path.splitext(file_path)[1].lower()
        language = LANGUAGE_MAP.get(ext, "text")

        fn_names = _extract_fn_names(file_data)
        class_names: list[str] = file_data.get("classes", [])
        imports: list[str] = file_data.get("imports", [])
        source: str = file_data.get("source", "")

        # Build a context header to prepend to every chunk
        header_lines = [
            f"# Repository: {repo_name}",
            f"# File: {file_path}",
            f"# Language: {language}",
        ]
        if fn_names:
            header_lines.append(f"# Functions: {', '.join(fn_names[:20])}")
        if class_names:
            header_lines.append(f"# Classes: {', '.join(class_names[:10])}")
        if imports:
            header_lines.append(f"# Imports: {'; '.join(imports[:15])}")
        header = "\n".join(header_lines) + "\n\n"

        # If there is no source (e.g., binary file slipped through), skip
        if not source.strip():
            skipped += 1
            continue

        chunks = chunk_code(source)

        for idx, chunk in enumerate(chunks):
            full_text = header + chunk
            cid = _chunk_id(repo_name, file_path, idx, full_text)

            # Approximate start/end line from chunk position
            chars_before = len("".join(chunks[:idx]))
            line_offset = source[:chars_before].count("\n") + 1

            vector = _model.encode(full_text, show_progress_bar=False).tolist()

            docs.append(full_text)
            embeddings.append(vector)
            metas.append({
                "repo_name": repo_name,
                "file": file_path,
                "language": language,
                "chunk_index": idx,
                "line_start": line_offset,
                "functions": ", ".join(fn_names[:10]),
                "classes": ", ".join(class_names[:5]),
            })
            ids.append(cid)

            if len(docs) >= _BATCH_SIZE:
                _flush()

    _flush()

    return {
        "repository": repo_name,
        "indexed_chunks": total_chunks,
        "skipped_files": skipped,
        "total_files": len(parsed_files),
    }


def semantic_search(
    query: str,
    repo_name: str,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    """
    Cosine-similarity search restricted to *repo_name*.

    Returns results sorted best-first (lowest cosine distance = most similar).
    Each result dict contains: repo_name, file, language, content, score,
    line_start, functions.
    """
    if not query.strip():
        return []

    # Check we have any documents for this repo
    count_check = collection.get(where={"repo_name": repo_name}, limit=1)
    if not count_check["ids"]:
        return []

    query_vector = _model.encode(query, show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, 10),
        where={"repo_name": repo_name},
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    formatted: list[dict] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        formatted.append({
            "repo_name": meta.get("repo_name", repo_name),
            "file": meta.get("file", ""),
            "language": meta.get("language", ""),
            "content": doc,
            "score": round(1.0 - dist, 4),   # convert distance → similarity
            "line_start": meta.get("line_start", 1),
            "functions": meta.get("functions", ""),
        })

    # Sort by similarity descending
    formatted.sort(key=lambda x: x["score"], reverse=True)
    return formatted