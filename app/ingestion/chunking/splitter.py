import uuid
import logfire
from embedding.model import embed_texts

MAX_CHUNK_SIZE = 1500
MIN_CHUNK_SIZE = 40
QDRANT_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _merge_metadata(metadata_list: list[dict]) -> dict:
    keys = set()
    for m in metadata_list:
        keys.update(m.keys())
    merged = {}
    for key in keys:
        values = [m[key] for m in metadata_list if key in m]
        unique = []
        for v in values:
            if v not in unique:
                unique.append(v)
        merged[key] = unique[0] if len(unique) == 1 else sorted(unique) if all(isinstance(u, (int, str)) for u in unique) else unique
    return merged


def _build_chunk(texts: list[str], metadata_list: list[dict]) -> dict:
    return {"text": "\n\n".join(texts).strip(), "metadata": _merge_metadata(metadata_list)}


def _hard_split_oversized(seg, max_size: int) -> list[dict]:
    pieces = []
    for i in range(0, len(seg.text), max_size):
        piece = seg.text[i:i + max_size].strip()
        if piece:
            pieces.append(_build_chunk([piece], [seg.metadata]))
    return pieces


def _group_segments(segments: list, max_size: int) -> list[dict]:
    chunks, current_texts, current_metadata, current_len = [], [], [], 0

    def flush():
        if current_texts:
            chunks.append(_build_chunk(current_texts, current_metadata))

    for seg in segments:
        starts_new_section = seg.kind == "title" and current_texts
        exceeds_budget = current_len + len(seg.text) > max_size and current_texts

        if starts_new_section or exceeds_budget:
            flush()
            current_texts, current_metadata, current_len = [], [], 0

        if len(seg.text) > max_size:
            flush()
            current_texts, current_metadata, current_len = [], [], 0
            chunks.extend(_hard_split_oversized(seg, max_size))
            continue

        current_texts.append(seg.text)
        current_metadata.append(seg.metadata)
        current_len += len(seg.text)

    flush()
    return chunks


def _merge_small_chunks(chunks: list[dict], min_size: int) -> list[dict]:
    if not chunks:
        return chunks
    merged = []
    for chunk in chunks:
        if merged and len(merged[-1]["text"]) < min_size:
            prev = merged.pop()
            chunk = _build_chunk([prev["text"], chunk["text"]], [prev["metadata"], chunk["metadata"]])
        merged.append(chunk)
    if len(merged) > 1 and len(merged[-1]["text"]) < min_size:
        last, prev = merged.pop(), merged.pop()
        merged.append(_build_chunk([prev["text"], last["text"]], [prev["metadata"], last["metadata"]]))
    return merged


def chunk_segments(segments: list, max_size: int = MAX_CHUNK_SIZE, min_size: int = MIN_CHUNK_SIZE) -> list[dict]:
    with logfire.span("✂️ Chunking + embedding", n_segments=len(segments)):
        grouped = _merge_small_chunks(_group_segments(segments, max_size), min_size)
        valid = [c for c in grouped if c["text"]]

        for i, chunk in enumerate(valid):
            source_file = chunk["metadata"].get("source_file", "unknown")
            chunk["id"] = str(uuid.uuid5(QDRANT_NAMESPACE, f"{source_file}:{i}"))

        if valid:
            vectors = embed_texts([c["text"] for c in valid])
            for chunk, vector in zip(valid, vectors):
                chunk["vector"] = vector

        logfire.info(f"✅ {len(valid)} chunks, embedded")
        return valid