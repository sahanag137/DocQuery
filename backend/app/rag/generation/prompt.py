def build_prompt(
    question: str,
    context: str
) -> str:

    return f"""
You are an AI document assistant.

Answer the question using ONLY the information
contained in the provided document context.

Rules:
- Do not use outside knowledge.
- Do not invent facts.
- If the answer is not present in the context,
  clearly say that the information is not available
  in the provided document.
- Give a direct and concise answer.
- Use the provided source and page information
  when relevant.

DOCUMENT CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
""".strip()
