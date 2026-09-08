from bs4 import BeautifulSoup
from models import Segment # processor.py contains this class
import logfire
from pathlib import Path

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCK_TAGS = HEADING_TAGS | {"p", "li", "blockquote", "td", "th"}
JUNK_TAGS = ["script", "style", "meta", "noscript", "nav", "footer", "header", "svg"]

def parse_html(file_path: Path) -> list[Segment]:
    with logfire.span("📄 HTML Parsing", filename=file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # 1. Strip junk before walking, same as before
        for tag in soup(JUNK_TAGS):
            tag.decompose()

        # 2. Walk block-level tags in document order, not the whole tree flattened
        segments: list[Segment] = []
        for tag in soup.find_all(BLOCK_TAGS):
            # skip a tag if it's nested inside another block tag we'll already capture
            # (e.g. a <p> inside a <li> — avoid double-counting)
            if tag.find_parent(BLOCK_TAGS):
                continue

            text = tag.get_text(separator=" ", strip=True)
            if not text:
                continue

            if tag.name in HEADING_TAGS:
                kind = "title"
            elif tag.name == "li":
                kind = "list_item"
            elif tag.name in ("td", "th"):
                kind = "table"
            else:
                kind = "text"

            segments.append(Segment(text=text, kind=kind, metadata={"source_file": file_path.name, "page": None}))

        logfire.info(f"✅ Extracted {len(segments)} structured segments")
        return segments