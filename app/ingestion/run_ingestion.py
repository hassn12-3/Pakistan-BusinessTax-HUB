import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

from app.config import DOCUMENTS_DIR, CHUNKS_FILE, DATA_DIR
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.chunker import chunk_page_markdown
from app.ingestion.metadata_extractor import (
    get_issuing_body,
    extract_version_date,
    extract_clean_section,
)


def run_ingestion() -> None:
    """
    Executes the ingestion pipeline:
      1. Discovers all PDFs in documents/ (flat directory).
      2. Parses pages with pymupdf4llm.
      3. Extracts document-level metadata (issuing_body, version_date).
      4. Chunks each page using MarkdownHeaderTextSplitter & RecursiveCharacterTextSplitter.
      5. Extracts clean section labels.
      6. Writes final tagged chunks to data/chunks.json.
      7. Prints execution summary.
    """
    if not os.path.exists(DOCUMENTS_DIR):
        print(f"Error: Documents directory does not exist: {DOCUMENTS_DIR}")
        sys.exit(1)

    # Ensure output data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all PDF files in documents/
    pdf_files = sorted(
        [
            f
            for f in os.listdir(DOCUMENTS_DIR)
            if f.lower().endswith(".pdf")
            and not f.startswith("._")
            and os.path.isfile(os.path.join(DOCUMENTS_DIR, f))
        ]
    )

    if not pdf_files:
        print(f"No PDF files found in {DOCUMENTS_DIR}.")
        return

    print(f"Found {len(pdf_files)} PDF file(s) for ingestion.")

    all_chunks: List[Dict[str, Any]] = []
    chunk_id_counter = 0

    unknown_issuing_docs = []
    missing_version_docs = []
    null_section_chunk_count = 0

    # Process each PDF
    for filename in pdf_files:
        pdf_path = os.path.join(DOCUMENTS_DIR, filename)
        issuing_body = get_issuing_body(filename)
        if issuing_body == "Unknown":
            unknown_issuing_docs.append(filename)

        print(f"\nProcessing: {filename} [{issuing_body}]")
        try:
            pages = parse_pdf(pdf_path)
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            continue

        if not pages:
            print(f"Warning: No pages extracted from {filename}")
            continue

        # Extract version date from the first page text
        first_page_text = pages[0].get("text", "")
        version_date = extract_version_date(first_page_text)
        if not version_date:
            missing_version_docs.append(filename)

        # Chunk each page with progress bar
        pbar_desc = f"  Chunking {filename[:30]}"
        for page in tqdm(pages, desc=pbar_desc, unit="page", leave=False):
            page_text = page.get("text", "")
            page_num = page.get("page", 1)

            page_chunks = chunk_page_markdown(
                page_markdown=page_text, page_number=page_num
            )

            for item in page_chunks:
                heading_full = item.get("section_heading_full")
                clean_sec = extract_clean_section(heading_full)

                if clean_sec is None:
                    null_section_chunk_count += 1

                chunk_entry = {
                    "chunk_id": chunk_id_counter,
                    "text": item.get("text", ""),
                    "doc_id": page.get("doc_id"),
                    "filename": page.get("filename"),
                    "issuing_body": issuing_body,
                    "page": page_num,
                    "section": clean_sec,
                    "section_heading_full": heading_full,
                    "version_date": version_date,
                }
                all_chunks.append(chunk_entry)
                chunk_id_counter += 1

    # Save to data/chunks.json
    print(f"\nWriting {len(all_chunks)} chunks to {CHUNKS_FILE}...")
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    # Summary Report
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total documents processed: {len(pdf_files)}")
    print(f"Total chunks created:     {len(all_chunks)}")

    if unknown_issuing_docs:
        print(f"\nDocuments with Unknown issuing body ({len(unknown_issuing_docs)}):")
        for doc in unknown_issuing_docs:
            print(f"  - {doc}")
    else:
        print("\nAll documents mapped to recognized issuing bodies.")

    if missing_version_docs:
        print(f"\nDocuments with version_date not detected ({len(missing_version_docs)}):")
        for doc in missing_version_docs:
            print(f"  - {doc}")
    else:
        print("\nVersion dates detected for all documents.")

    print(
        f"\nChunks with null section: {null_section_chunk_count} / {len(all_chunks)} "
        f"(preserved as front-matter, preamble, or table-of-contents)"
    )
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()
