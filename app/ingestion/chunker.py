from typing import List, Dict, Any, Optional
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for English legal text.
    Standard rule of thumb: ~4 characters per token.
    """
    return max(1, len(text) // 4)


def chunk_page_markdown(
    page_markdown: str,
    page_number: int,
    max_tokens: int = 800,
    overlap_tokens: int = 75,
) -> List[Dict[str, Any]]:
    """
    Splits a single page's markdown text using MarkdownHeaderTextSplitter
    along '##' and '###' headers. If any resulting chunk exceeds max_tokens (~800),
    it is further split using RecursiveCharacterTextSplitter (chunk_overlap ~75 tokens),
    carrying forward the section_heading_full and page number.
    """
    if not page_markdown or not page_markdown.strip():
        return []

    headers_to_split_on = [
        ("##", "section_heading_full"),
        ("###", "section_heading_full"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    header_docs = markdown_splitter.split_text(page_markdown)

    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap_tokens,
        length_function=estimate_tokens,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
    )

    chunks: List[Dict[str, Any]] = []

    for doc in header_docs:
        raw_text = doc.page_content.strip()
        if not raw_text:
            continue

        heading = doc.metadata.get("section_heading_full")
        token_count = estimate_tokens(raw_text)

        if token_count > max_tokens:
            sub_texts = recursive_splitter.split_text(raw_text)
            for sub_text in sub_texts:
                clean_sub = sub_text.strip()
                if clean_sub:
                    chunks.append(
                        {
                            "text": clean_sub,
                            "page": page_number,
                            "section_heading_full": heading,
                        }
                    )
        else:
            chunks.append(
                {
                    "text": raw_text,
                    "page": page_number,
                    "section_heading_full": heading,
                }
            )

    return chunks
