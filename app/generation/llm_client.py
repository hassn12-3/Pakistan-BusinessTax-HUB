import io
from PIL import Image
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, GEMINI_API_KEYS, GEMINI_MODEL
from app.generation.prompt_templates import (
    TRANSLATION_SYSTEM_PROMPT,
    NOTICE_EXTRACTION_PROMPT,
    LEGAL_QA_SYSTEM_PROMPT,
    build_legal_qa_prompt,
)

_genai_clients: Dict[str, genai.Client] = {}


def get_genai_client(key_idx: int = 0) -> genai.Client:
    """Returns an authenticated Google GenAI client, rotating if needed."""
    keys = GEMINI_API_KEYS if GEMINI_API_KEYS else ([GOOGLE_API_KEY] if GOOGLE_API_KEY else [""])
    idx = key_idx % max(1, len(keys))
    chosen_key = keys[idx]
    if chosen_key not in _genai_clients:
        _genai_clients[chosen_key] = genai.Client(api_key=chosen_key)
    return _genai_clients[chosen_key]


def analyze_notice_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Multimodal inspection: Reads a tax or legal notice image, skips boilerplates,
    and extracts core facts and a targeted search query with multi-key rotation.
    """
    num_keys = max(1, len(GEMINI_API_KEYS))
    for k_idx in range(num_keys):
        try:
            client = get_genai_client(k_idx)
            pil_img = Image.open(io.BytesIO(image_bytes))
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[pil_img, NOTICE_EXTRACTION_PROMPT],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                ),
            )
            text = response.text.strip()

            summary = ""
            search_query = ""

            if "SEARCH_QUERY:" in text:
                parts = text.split("SEARCH_QUERY:")
                search_query = parts[1].strip()
                summary = parts[0].replace("SUMMARY:", "").strip()
            else:
                summary = text
                search_query = text[:150]

            return {
                "summary": summary,
                "search_query": search_query,
            }
        except Exception:
            continue

    return {
        "summary": "Could not extract full notice details from image.",
        "search_query": "tax compliance notice requirements",
    }


def translate_query_if_needed(query: str, language: str = "English") -> str:
    """
    Translates non-English queries (Roman Urdu or Urdu) into standard English
    before performing retrieval against English statutory documents.
    Rotates across keys and provides fallback keyword mapping.
    """
    if not query or language.lower() == "english":
        return query

    import re

    # Common localized tax & legal terminology mappings for rapid fallback
    local_glossary = [
        (r"\b(kitna|kitni|hisaab|calculate)\s*tax\b", "tax calculation liability"),
        (r"\bsalana\s*(aamdani|kamai|income)\b", "annual taxable income"),
        (r"\bmahana\b", "monthly"),
        (r"\bnotis\b", "show cause notice"),
        (r"\bchhoot\b", "exemption tax credit"),
        (r"\bmunafa\b", "profit business turnover"),
        (r"\bwazahat\b", "explanation statutory rules"),
        (r"\bappeal\b", "appeal Section 127"),
    ]

    num_keys = max(1, len(GEMINI_API_KEYS))
    for k_idx in range(num_keys):
        try:
            client = get_genai_client(k_idx)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Translate this query to English for legal research: '{query}'",
                config=types.GenerateContentConfig(
                    system_instruction=TRANSLATION_SYSTEM_PROMPT,
                    temperature=0.0,
                ),
            )
            translated = response.text.strip()
            if translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1]
            if translated:
                return translated
        except Exception:
            continue

    # Graceful fallback: Apply keyword normalization
    fallback_q = query
    for pat, rep in local_glossary:
        fallback_q = re.sub(pat, rep, fallback_q, flags=re.IGNORECASE)
    return fallback_q


def generate_legal_answer(
    query: str,
    target_language: str,
    context_chunks: List[Dict[str, Any]],
    notice_summary: Optional[str] = None,
) -> str:
    """
    Generates a legally grounded answer with citations using Gemini 3.5 Flash,
    incorporating any uploaded notice details.
    """
    client = get_genai_client()

    # Format context chunks
    context_blocks = []
    for i, c in enumerate(context_chunks, start=1):
        filename = c.get("filename", "Unknown Document")
        issuing_body = c.get("issuing_body", "")
        page = c.get("page", "?")
        section = c.get("section") or c.get("section_heading_full") or "General Provision"
        text = c.get("text", "")

        block = (
            f"[Source {i}]: Document: '{filename}' ({issuing_body}) | "
            f"Section: {section} | Page: {page}\n"
            f"Content:\n{text}\n"
        )
        context_blocks.append(block)

    full_context = "\n---\n".join(context_blocks)
    if notice_summary:
        full_context = f"FACTS EXTRACTED FROM UPLOADED NOTICE:\n{notice_summary}\n\n" + full_context

    system_instruction = LEGAL_QA_SYSTEM_PROMPT.format(target_language=target_language)
    prompt_text = build_legal_qa_prompt(query, target_language, full_context)

    num_keys = max(1, len(GEMINI_API_KEYS))
    models_to_try = [GEMINI_MODEL, "gemini-3.5-flash", "gemini-2.5-flash"]
    unique_models = [m for i, m in enumerate(models_to_try) if m and m not in models_to_try[:i]]

    last_err = None
    for k_idx in range(num_keys):
        client = get_genai_client(k_idx)
        for model_name in unique_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    ),
                )
                return response.text.strip()
            except Exception as e:
                last_err = e
                continue

    return f"Error communicating with Gemini model: {str(last_err)}"


def generate_legal_answer_stream(
    query: str,
    target_language: str,
    context_chunks: List[Dict[str, Any]],
    notice_summary: Optional[str] = None,
):
    """
    Streams the legal answer token-by-token using Gemini 3.5 Flash for ultra-low latency.
    Supports key rotation across available keys.
    """
    context_blocks = []
    for i, c in enumerate(context_chunks, start=1):
        filename = c.get("filename", "Unknown Document")
        issuing_body = c.get("issuing_body", "")
        page = c.get("page", "?")
        section = c.get("section") or c.get("section_heading_full") or "General Provision"
        text = c.get("text", "")

        block = (
            f"[Source {i}]: Document: '{filename}' ({issuing_body}) | "
            f"Section: {section} | Page: {page}\n"
            f"Content:\n{text}\n"
        )
        context_blocks.append(block)

    full_context = "\n---\n".join(context_blocks)
    if notice_summary:
        full_context = f"FACTS EXTRACTED FROM UPLOADED NOTICE:\n{notice_summary}\n\n" + full_context

    system_instruction = LEGAL_QA_SYSTEM_PROMPT.format(target_language=target_language)
    prompt_text = build_legal_qa_prompt(query, target_language, full_context)

    num_keys = max(1, len(GEMINI_API_KEYS))
    stream_err = None

    for k_idx in range(num_keys):
        try:
            client = get_genai_client(k_idx)
            stream = client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            stream_err = e
            continue

    yield f"Error in streaming generation: {str(stream_err)}"

