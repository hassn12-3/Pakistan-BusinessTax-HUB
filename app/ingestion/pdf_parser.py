import os
from typing import List, Dict, Any
import pymupdf4llm


def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parses a PDF file into per-page markdown chunks using pymupdf4llm.
    Output is a list of per-page dicts, each containing:
      - doc_id: filename without extension
      - filename: original PDF filename (stored as-is for clickable citations)
      - page: 1-indexed page number
      - text: markdown text of the page
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    doc_id, _ = os.path.splitext(filename)

    # page_chunks=True extracts a list of per-page dicts
    page_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)

    pages: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(page_chunks):
        if isinstance(chunk, dict):
            page_text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            raw_page = meta.get("page")
            # Ensure 1-indexed page number
            if raw_page is None:
                page_num = idx + 1
            elif isinstance(raw_page, int):
                # If 0-indexed (e.g. first page is 0), adjust to 1-indexed
                page_num = raw_page + 1 if raw_page == idx and idx == 0 else raw_page
            else:
                page_num = idx + 1
        else:
            page_text = str(chunk)
            page_num = idx + 1

        pages.append(
            {
                "doc_id": doc_id,
                "filename": filename,
                "page": page_num,
                "text": page_text,
            }
        )

    return pages
