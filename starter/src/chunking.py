"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping windows and retain page metadata."""
    if not page.text or page.metadata.get("is_blank"):
        return []

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    start = 0
    idx = 0
    text_len = len(page.text)

    while start < text_len:
        end = min(start + size, text_len)
        chunk_text = page.text[start:end].strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_f{idx}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "strategy": "fixed_size",
                        "chunk_index": idx,
                        "char_start": start,
                        "char_end": end,
                        "char_count": len(chunk_text),
                    },
                )
            )
            idx += 1
        if end >= text_len:
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    if not page.text or page.metadata.get("is_blank"):
        return []

    # Split paragraphs by double newlines or single newline
    raw_paras = [p.strip() for p in page.text.split("\n\n") if p.strip()]
    if not raw_paras:
        raw_paras = [page.text.strip()]

    # Break any oversized paragraph exceeding max_size
    paras: list[str] = []
    for p in raw_paras:
        if len(p) <= max_size:
            paras.append(p)
        else:
            lines = p.split("\n")
            curr: list[str] = []
            for l in lines:
                candidate = "\n".join(curr + [l])
                if len(candidate) <= max_size:
                    curr.append(l)
                else:
                    if curr:
                        paras.append("\n".join(curr))
                    curr = [l]
            if curr:
                paras.append("\n".join(curr))

    # Group consecutive short paragraphs without exceeding max_size
    chunks: list[Chunk] = []
    curr_group: list[str] = []
    idx = 0

    for p in paras:
        candidate = "\n\n".join(curr_group + [p])
        if len(candidate) <= max_size:
            curr_group.append(p)
        else:
            if curr_group:
                chunk_text = "\n\n".join(curr_group).strip()
                chunks.append(
                    Chunk(
                        chunk_id=f"{page.document_id}_p{page.page}_p{idx}",
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=chunk_text,
                        metadata={
                            **page.metadata,
                            "strategy": "by_paragraph",
                            "chunk_index": idx,
                            "char_count": len(chunk_text),
                        },
                    )
                )
                idx += 1
            curr_group = [p]

    if curr_group:
        chunk_text = "\n\n".join(curr_group).strip()
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}_p{page.page}_p{idx}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata={
                    **page.metadata,
                    "strategy": "by_paragraph",
                    "chunk_index": idx,
                    "char_count": len(chunk_text),
                },
            )
        )

    return chunks
