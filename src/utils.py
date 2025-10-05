from __future__ import annotations

from typing import Iterable


def chunked(iterable: Iterable, size: int):
    """Yield successive chunks from an iterable."""
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

