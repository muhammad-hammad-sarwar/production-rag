import json
import logfire
from pathlib import Path
from dotenv import load_dotenv
import os

from loaders.html import parse_html
from loaders.office import parse_office
from loaders.pdf import parse_pdf
from loaders.text import parse_text
from chunking.splitter import chunk_segments
from embedding.qdrant_setup import get_qdrant_client, ensure_collection, COLLECTION_NAME

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"), environment="development", service_name="enterprise-ingestion-service")

SUPPORTED_EXTENSIONS = {".pptx", ".docx", ".txt", ".html", ".pdf"}
CHECKPOINT_PATH = Path("embedded_ids.json")


def parse_file(file: Path):
    ext = file.suffix.lower()
    if ext in (".pptx", ".docx"):
        return parse_office(file)
    elif ext == ".txt":
        return parse_text(file)
    elif ext == ".html":
        return parse_html(file)
    elif ext == ".pdf":
        return parse_pdf(file)
    raise ValueError(f"Unsupported extension: {ext}")


def load_checkpoint() -> set[str]:
    return set(json.loads(CHECKPOINT_PATH.read_text())) if CHECKPOINT_PATH.exists() else set()


def save_checkpoint(ids: set[str]):
    CHECKPOINT_PATH.write_text(json.dumps(sorted(ids)))


def process_directory(directory: Path, qdrant_client) -> dict:
    all_chunks: list[dict] = []
    file_status: list[dict] = []
    embedded_ids = load_checkpoint()

    for file in directory.iterdir():
        if not file.is_file():
            continue

        ext = file.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logfire.warning(f"Skipping unsupported file: {file.name}")
            file_status.append({"file": file.name, "status": "skipped"})
            continue

        try:
            segments = parse_file(file)
            if not segments:
                file_status.append({"file": file.name, "status": "empty"})
                continue

            chunks = chunk_segments(segments)  # id + vector already attached here
            new_chunks = [c for c in chunks if c["id"] not in embedded_ids]

            if new_chunks:
                points = [
                    {"id": c["id"], "vector": c["vector"], "payload": {"text": c["text"], **c["metadata"]}}
                    for c in new_chunks
                ]
                qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
                embedded_ids.update(c["id"] for c in new_chunks)
                save_checkpoint(embedded_ids)  # after every file — crash-safe

            all_chunks.extend(chunks)
            file_status.append({"file": file.name, "status": "ok", "n_chunks": len(chunks), "n_new": len(new_chunks)})
            logfire.info(f"Processed {file.name}: {len(chunks)} chunks, {len(new_chunks)} new")

        except Exception as e:
            logfire.error(f"Failed to process {file.name}: {e}")
            file_status.append({"file": file.name, "status": "failed", "error": str(e)})
            continue

    return {"chunks": all_chunks, "file_status": file_status}


def dump_chunks_to_json(directory, all_chunks: list[dict]):
    out_path = directory / "chunks_debug.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    logfire.info(f"Wrote {len(all_chunks)} chunks to {out_path}")


def read_files(root_directory: Path):
    data_dir = root_directory / Path("DATA")
    # target_dir = data_dir / "test_data"
    target_dir = data_dir / "noisy_data"
    # target_dir = data_dir / "true_data"

    client = get_qdrant_client()
    ensure_collection(client)

    results = process_directory(target_dir, client)
    dump_chunks_to_json(target_dir, results["chunks"])  # fixed: was passing the whole dict before


if __name__ == "__main__":
    root_directory = Path(__file__).parent.parent.parent
    read_files(root_directory)