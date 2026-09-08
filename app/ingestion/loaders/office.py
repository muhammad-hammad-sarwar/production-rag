import logfire
from unstructured.partition.auto import partition
from models import Segment # processor.py contains this class
from pathlib import Path

def parse_office(file_path: Path) -> list[Segment]:
    with logfire.span("📄 Office Document Parsing", filename=file_path):
        try:
            elements = partition(filename=str(file_path))

            segments: list[Segment] = []
            for el in elements:
                text = str(el).strip()
                if not text:
                    continue

                category = type(el).__name__  # "Title", "NarrativeText", "ListItem", "Table"...
                if category == "Title":
                    kind = "title"
                elif category == "ListItem":
                    kind = "list_item"
                elif category == "Table":
                    kind = "table"
                else:
                    kind = "text"

                page_number = getattr(el.metadata, "page_number", None)
                segments.append(Segment(text=text, kind=kind, metadata={"page": [page_number], "source_file": file_path.name}))

            if not segments:
                logfire.warning(f"⚠️ Unstructured returned empty output for {file_path}")
            else:
                logfire.info(f"✅ Extracted {len(segments)} structured segments")

            return segments
        except Exception as e:
            logfire.error(f"❌ Office Parse Failed: {e}")
            raise