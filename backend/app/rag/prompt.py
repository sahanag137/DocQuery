"""
prompt.py — prompt templates that tie context + question together for the LLM.
"""

SYSTEM_PROMPT = (
    "You are a document Q&A assistant. Answer ONLY using the provided context. "
    "Cite sources using their bracket numbers, e.g. [1]. "
    "If the context does not contain the answer, say you don't have enough information."
)

RAG_TEMPLATE = """Context:
{context}

Question: {question}

Answer the question using only the context above. Include citation numbers like [1] for any claim you make."""


def build_prompt(question: str, context: str) -> list[dict]:
    """Return a chat-format message list ready to send to an LLM."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": RAG_TEMPLATE.format(context=context, question=question)},
    ]
