"""
context_builder.py

Formats retrieved document chunks and optional conversation history
into a structured, deduplicated context block for the LLM.
"""

from typing import Dict, List, Optional


def build_context(
    results: List[Dict],
    max_characters: int = 24000
) -> str:
    """
    Format retrieved chunks into a clean context string with source and page attribution.
    Deduplicates identical or near-identical text blocks.
    """
    if max_characters <= 0 or not results:
        return ""

    context_blocks = []
    total_length = 0
    seen_texts = set()

    for result in results:
        source = result.get("source", "Document")
        page = result.get("page", 1)
        text = result.get("text", "")

        if not isinstance(text, str):
            continue

        cleaned_text = text.strip()
        if not cleaned_text:
            continue

        # Simple deduplication check on prefix
        preview_key = cleaned_text[:120].lower()
        if preview_key in seen_texts:
            continue
        seen_texts.add(preview_key)

        block = (
            f"[Document: {source} | Page: {page}]\n"
            f"{cleaned_text}"
        )

        separator_length = len("\n\n---\n\n") if context_blocks else 0
        remaining = max_characters - total_length - separator_length

        if remaining <= 100:
            break

        if len(block) > remaining:
            block = block[:remaining].rstrip() + "..."

        context_blocks.append(block)
        total_length += separator_length + len(block)

        if total_length >= max_characters:
            break

    return "\n\n---\n\n".join(context_blocks)


def format_chat_history(messages: List[Dict], max_turns: int = 4) -> str:
    """Format recent user/assistant conversation turns for conversational continuity."""
    if not messages:
        return ""

    recent = messages[-max_turns * 2:]
    formatted = []
    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "").strip()
        if content:
            formatted.append(f"{role}: {content}")

    return "\n".join(formatted)
