import logfire
from pypdf import PdfReader
from models import Segment # processor.py contains this class
from pathlib import Path

def parse_pdf(file_path: Path) -> list[Segment]:
    with logfire.span("PDF Parsing (local)", filename=file_path):
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            logfire.info(f"PDF has {total_pages} pages.")

            segments: list[Segment] = []
            blank_pages: list[int] = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    for para in text.split("\n\n"):
                        para = para.strip()
                        if para:
                            segments.append(
                                Segment(
                                    text=para, kind="text",
                                    metadata={"source_file": file_path.name, "page": [i + 1]}
                                )
                            )
                else:
                    blank_pages.append(i + 1)

            for page_num in blank_pages:
                page = reader.pages[page_num - 1]
                fallback_text = page.extract_text() or ""
                for para in fallback_text.split("\n\n"):
                    para = para.strip()
                    if para:
                        segments.append(Segment(
                            text=para, kind="text",
                            metadata={"source_file": str(file_path), "page": [page_num]}
                        ))

            if blank_pages:
                logfire.info(f"pypdf returned blank on pages {blank_pages} — retrying with pdfplumber.")
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for page_num in blank_pages:
                            page = pdf.pages[page_num - 1]
                            fallback_text = page.extract_text() or ""
                            for para in fallback_text.split("\n\n"):
                                para = para.strip()
                                if para:
                                    segments.append(Segment(text=para, kind="text"))
                except Exception as plumber_err:
                    logfire.warning(f"pdfplumber fallback failed: {plumber_err}")

            if not segments:
                logfire.warning(f"No text extracted from {file_path}. File may be fully image-based.")
            else:
                logfire.info(f"Extracted {len(segments)} segments from {file_path}.")

            return segments

        except Exception as e:
            logfire.error(f"PDF Parse Failed for {file_path}: {e}")
            raise