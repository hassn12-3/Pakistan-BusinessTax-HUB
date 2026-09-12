import io
from PIL import Image
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, GEMINI_MODEL
from app.generation.prompt_templates import (
    TRANSLATION_SYSTEM_PROMPT,
    NOTICE_EXTRACTION_PROMPT,
    LEGAL_QA_SYSTEM_PROMPT,
    build_legal_qa_prompt,
)

_genai_client = None


def get_genai_client() -> genai.Client:
    """Returns an authenticated Google GenAI client."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _genai_client


def analyze_notice_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Multimodal inspection: Reads a tax or legal notice image, skips boilerplates,
    and extracts core facts and a targeted search query.
    """
    client = get_genai_client()
    try:
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
    except Exception as e:
        print(f"Notice image analysis error: {e}")
        return {
            "summary": "Could not extract full notice details from image.",
            "search_query": "tax compliance notice requirements",
        }


def translate_query_if_needed(query: str, language: str = "English") -> str:
    """
    Translates non-English queries (Roman Urdu or Urdu) into standard English
    before performing retrieval against English statutory documents.
    """
    if language.lower() == "english":
        return query

    client = get_genai_client()
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"Translate this query to English for legal research: '{query}'",
            config=types.GenerateContentConfig(
                system_instruction=TRANSLATION_SYSTEM_PROMPT,
                temperature=0.0,
            ),
        )
        translated = response.text.strip()
        # Clean potential quotes
        if translated.startswith('"') and translated.endswith('"'):
            translated = translated[1:-1]
        return translated or query
    except Exception as e:
        print(f"Translation error: {e}. Using original query.")
        return query


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

    models_to_try = [GEMINI_MODEL, "gemini-flash-latest", "gemini-2.5-pro", "gemini-3-flash-preview"]
    unique_models = []
    for m in models_to_try:
        if m and m not in unique_models:
            unique_models.append(m)

    last_err = None
    import time

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
            time.sleep(0.5)

    return f"Error communicating with Gemini model: {str(last_err)}"


def generate_legal_answer_stream(
    query: str,
    target_language: str,
    context_chunks: List[Dict[str, Any]],
    notice_summary: Optional[str] = None,
):
    """
    Streams the legal answer token-by-token using Gemini 3.5 Flash for ultra-low latency.
    """
    client = get_genai_client()

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

    try:
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
    except Exception as e:
        yield f"Error in streaming generation: {str(e)}"

