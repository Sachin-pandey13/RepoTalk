def chunk_code(content: str, chunk_size: int = 40):
    
    lines = content.split("\n")

    chunks = []

    for i in range(0, len(lines), chunk_size):

        chunk = "\n".join(lines[i:i + chunk_size])

        chunks.append(chunk)

    return chunks