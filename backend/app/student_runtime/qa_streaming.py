from __future__ import annotations

import re
from collections.abc import Iterator


def iter_answer_chunks(answer: str, *, max_chunk_size: int = 24) -> Iterator[str]:
    text = (answer or "").strip()
    if not text:
        return

    segments = re.split(r"(?<=[。！？；\n])", text)
    pending = ""

    for segment in segments:
        piece = (segment or "").strip()
        if not piece:
            continue
        if len(piece) > max_chunk_size:
            if pending:
                yield pending
                pending = ""
            for start in range(0, len(piece), max_chunk_size):
                yield piece[start:start + max_chunk_size]
            continue
        if len(pending) + len(piece) > max_chunk_size:
            if pending:
                yield pending
            pending = piece
            continue
        pending += piece

    if pending:
        yield pending
