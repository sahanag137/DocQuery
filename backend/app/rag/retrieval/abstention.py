def should_abstain(
    results: list[dict],
    threshold: float = 0.25
) -> bool:

    if not results:
        return True

    return results[0]["score"] < threshold


def get_abstention_message() -> str:

    return (
        "I couldn't find enough relevant information "
        "in the provided document to answer this question."
    )
