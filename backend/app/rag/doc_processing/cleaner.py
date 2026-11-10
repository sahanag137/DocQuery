"""
cleaner.py

Text cleaning and normalization module for DocQuery.
Standardizes whitespace and line breaks while strictly preserving markdown headings,
code snippets, technical notations, numbers, and punctuation.
"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text:
    - Standardizes unicode representations (NFKC normalization).
    - Converts carriage returns (\\r\\n and \\r) to \\n.
    - Strips non-printable control characters except standard whitespace (\\n, \\t).
    - Removes trailing spaces from individual lines while preserving indentation.
    - Collapses excessive vertical whitespace (3+ consecutive newlines) into 2 newlines.
    - Collapses runs of horizontal spaces within lines.
    - Preserves headings, punctuation, casing, code, and technical information.
    """
    if not text:
        return ""

    # 1. Unicode normalization (NFKC normalizes ligatures and special spaces)
    text = unicodedata.normalize("NFKC", text)

    # 2. Normalize carriage returns to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove non-printable control characters (keep \n and \t)
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or (unicodedata.category(ch)[0] != "C" and ord(ch) >= 32)
    )

    # 4. Normalize line whitespace
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped_right = line.rstrip()
        # Preserve leading indentation (for lists, code, markdown)
        leading_space_len = len(stripped_right) - len(stripped_right.lstrip(" "))
        leading = " " * leading_space_len
        rest = stripped_right.lstrip(" ")
        # Collapse multiple internal spaces
        rest_collapsed = re.sub(r"[ \t]+", " ", rest)
        cleaned_lines.append(leading + rest_collapsed)

    text = "\n".join(cleaned_lines)

    # 5. Collapse excessive line breaks (3+ newlines -> 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
