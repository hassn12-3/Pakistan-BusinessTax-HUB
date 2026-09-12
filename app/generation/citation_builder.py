from typing import List, Dict, Any


def build_citations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Constructs structured citation metadata for each retrieved chunk,
    providing exact filename, issuing body, section, page, and text excerpt.
    """
    citations = []
    seen = set()

    for c in chunks:
        filename = c.get("filename", "")
        page = c.get("page", 1)
        section = c.get("section") or c.get("section_heading_full") or "General Provision"
        issuing_body = c.get("issuing_body", "Legal Document")

        # Dedup by filename and page
        key = (filename, page, section)
        if key in seen:
            continue
        seen.add(key)

        excerpt = c.get("text", "")[:280].strip()
        if len(c.get("text", "")) > 280:
            excerpt += "..."

        citation = {
            "doc_id": c.get("doc_id", ""),
            "filename": filename,
            "issuing_body": issuing_body,
            "page": page,
            "section": section,
            "excerpt": excerpt,
            "url_ref": f"/docs/{filename}#page={page}",
            "citation_label": f"{filename} (Page {page})",
        }
        citations.append(citation)

    return citations
