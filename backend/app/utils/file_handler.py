"""
file_handler.py

File storage, validation, security, and streaming utilities for DocQuery.
Includes path-traversal prevention, extension/MIME verification, and HTTP 206
Partial Content range request handling for inline PDF viewing.
"""

import os
from pathlib import Path
import re
from typing import Generator, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import settings

# Content type mappings
MIME_MAP = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent directory traversal and invalid characters.

    Args:
        filename: Raw filename provided by client.

    Returns:
        Clean, safe basename.
    """
    # Extract only the base name (strips path separators)
    clean = Path(filename).name
    # Replace dangerous or unwanted characters
    clean = re.sub(r"[^\w\s\.-]", "_", clean)
    clean = clean.strip()
    if not clean:
        clean = f"document_{uuid.uuid4().hex[:8]}"
    return clean


def validate_file_extension(filename: str, allowed_extensions: Set[str]) -> Tuple[str, str]:
    """
    Verify that the file has an approved extension.

    Args:
        filename: Filename to check.
        allowed_extensions: Set of allowed extensions in lowercase (e.g. {'.pdf', '.txt'}).

    Returns:
        Tuple of (extension, mime_type).

    Raises:
        HTTPException 400 if invalid.
    """
    ext = Path(filename).suffix.lower()
    if not ext or ext not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {allowed}",
        )
    mime_type = MIME_MAP.get(ext, "application/octet-stream")
    return ext, mime_type


def generate_unique_filename(original_filename: str) -> Tuple[str, str]:
    """
    Generate a unique storage filename combining a UUID and sanitized name.

    Returns:
        Tuple of (unique_id, stored_filename).
    """
    unique_id = uuid.uuid4().hex
    clean_name = sanitize_filename(original_filename)
    stored_filename = f"{unique_id}__{clean_name}"
    return unique_id, stored_filename


def delete_file_if_exists(file_path: Path | str) -> bool:
    """Safely delete a file if it exists on disk."""
    try:
        p = Path(file_path)
        if p.is_file():
            p.unlink()
            return True
    except OSError:
        pass
    return False


def range_request_response(
    file_path: Path,
    request: Request,
    content_type: str = "application/pdf",
    inline_filename: Optional[str] = None,
) -> Response:
    """
    Stream a file with support for HTTP Range requests (HTTP 206 Partial Content).
    Enables instant seeking, fast rendering, and page jumping in browser PDF viewers.

    Args:
        file_path: Path to the physical file on disk.
        request: FastAPI request object containing headers.
        content_type: MIME type of the file.
        inline_filename: Optional filename to show in Content-Disposition.

    Returns:
        FastAPI Response (FileResponse or StreamingResponse with 206).
    """
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist on disk.",
        )

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    filename_header = inline_filename or file_path.name

    # If no range header is requested, serve normal response
    if not range_header:
        headers = {
            "Content-Disposition": f'inline; filename="{filename_header}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        }
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            headers=headers,
        )

    # Parse Range: bytes=start-end
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return Response(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

    start_str, end_str = range_match.groups()
    start = int(start_str)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_length = end - start + 1

    def iter_file_chunk() -> Generator[bytes, None, None]:
        with file_path.open("rb") as f:
            f.seek(start)
            remaining = chunk_length
            chunk_size = 64 * 1024  # 64 KB
            while remaining > 0:
                bytes_to_read = min(remaining, chunk_size)
                data = f.read(bytes_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": content_type,
        "Content-Disposition": f'inline; filename="{filename_header}"',
    }

    return StreamingResponse(
        iter_file_chunk(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
