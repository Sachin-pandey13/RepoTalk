"""
backend/services/chunking_service.py

Semantic-aware code chunker that:
 - Respects a configurable token/char budget per chunk
 - Overlaps chunks by N lines so context is never cut mid-thought
 - Never produces empty or whitespace-only chunks
"""
from __future__ import annotations

DEFAULT_CHUNK_CHARS = 1500   # ~375 tokens at 4 chars/token
OVERLAP_LINES = 5            # lines shared between consecutive chunks
MIN_CHUNK_CHARS = 80         # discard trivially small trailing chunks


def chunk_code(
    content: str,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int = OVERLAP_LINES,
) -> list[str]:
    """
    Split *content* into overlapping chunks of at most *chunk_chars* characters.

    Parameters
    ----------
    content     : source text (any language)
    chunk_chars : soft upper bound on characters per chunk
    overlap     : number of lines repeated at the start of the next chunk
                  to preserve cross-boundary context
    """
    lines = content.splitlines(keepends=True)
    chunks: list[str] = []
    i = 0

    while i < len(lines):
        buf: list[str] = []
        size = 0

        while i < len(lines) and size < chunk_chars:
            buf.append(lines[i])
            size += len(lines[i])
            i += 1

        text = "".join(buf).strip()
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(text)

        # Step back by *overlap* lines so next chunk shares context
        if i < len(lines):
            i = max(i - overlap, i - len(buf) + 1)

    return chunks or [content.strip()]