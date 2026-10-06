def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1000,
    overlap: int = 150
) -> list[dict]:

    chunks = []

    for page_data in pages:
        text = page_data["text"]
        page_number = page_data["page"]

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            if end < len(text):
                split = text.rfind(" ", start, end)

                if split > start:
                    end = split

            chunk = text[start:end].strip()

            if chunk:
                chunks.append({
                    "text": chunk,
                    "page": page_number,
                    "chunk_id": len(chunks)
                })

            if end >= len(text):
                break

            start = max(end - overlap, start + 1)

    return chunks
