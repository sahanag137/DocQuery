"""
prompt.py

Prompt construction module for DocQuery.
Provides specialized system and user prompts for different question types:
- Detailed Q&A with page citations
- Document summarization and section breakdowns
- Comparative and conceptual analysis
- Follow-up conversation continuity
"""

from typing import Optional


def build_prompt(
    question: str,
    context: str,
    chat_history: Optional[str] = None,
    intent: Optional[str] = None
) -> str:
    """
    Construct an optimized prompt for the LLM based on context, query intent,
    and prior conversation history.
    """
    history_section = ""
    if chat_history and chat_history.strip():
        history_section = f"""
PREVIOUS CONVERSATION CONTEXT:
{chat_history.strip()}
"""

    return f"""You are an advanced AI document assistant for DocQuery.

Your task is to understand and answer the user's question accurately and comprehensively using ONLY the provided document context.

CORE INSTRUCTIONS:
1. Answer using ONLY the information provided in the DOCUMENT CONTEXT below.
2. Structure your answer clearly with concise paragraphs, headings, or bullet points where appropriate.
3. When referencing facts, concepts, or statements from the document, cite the relevant page numbers whenever available (e.g., "(Page 3)").
4. If the question asks for a summary, explain the overarching topics, key concepts, findings, and conclusions present in the context.
5. If the question asks to compare concepts, clearly contrast their definitions, advantages, disadvantages, and relationships based on the text.
6. If the question refers to a specific page or section, prioritize the information from that part of the document.
7. If the answer cannot be determined or is not addressed in the provided document context, state honestly that the document does not contain sufficient information for that question. Do not speculate or invent facts.
{history_section}
DOCUMENT CONTEXT:
<context>
{context}
</context>

USER QUESTION:
{question}

ANSWER:
""".strip()
