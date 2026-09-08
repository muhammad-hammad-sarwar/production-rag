import logfire
from models import Segment # processor.py contains this class
from pathlib import Path

def parse_text(file_path: Path) -> list[Segment]:
    with logfire.span("📄 Text Parsing", filename=file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            segments = [Segment(text=p, kind="text", metadata={"page": None, "source_file": file_path.name}) for p in paragraphs]

            logfire.info(f"✅ Extracted {len(segments)} paragraph segments")
            return segments
        except Exception as e:
            logfire.error(f"❌ Text Parse Failed: {e}")
            raise