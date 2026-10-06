def build_context(
    results: list[dict],
    max_characters: int = 6000
) -> str:

    context = []
    total_length = 0

    for result in results:

        source = result.get(
            "source",
            "Unknown"
        )

        page = result.get(
            "page",
            "Unknown"
        )

        text = result["text"]

        block = (
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Content:\n{text}"
        )

        if total_length + len(block) > max_characters:
            break

        context.append(block)
        total_length += len(block)

    return "\n\n---\n\n".join(context)
