import json
from typing import Dict, Any, List, Optional, Generator
from app.generation.llm_client import (
    translate_query_if_needed,
    analyze_notice_image,
    generate_legal_answer_stream,
)
from app.generation.stt_client import transcribe_audio
from app.graph.crag_flow import run_agentic_flow, router_node, legal_retriever_node, tax_calculator_node
from app.tools.calendar_tool import detect_compliance_deadlines
from app.tools.official_portals import detect_official_portal_link
from app.retrieval.cache import GLOBAL_QUERY_CACHE


def transcribe_voice(audio_bytes: bytes, language: str = "English") -> str:
    """Helper to transcribe spoken voice into text for the input bar."""
    return transcribe_audio(audio_bytes, language=language)


def ask_question(
    query: str = "",
    image_bytes: Optional[bytes] = None,
    audio_bytes: Optional[bytes] = None,
    language: str = "English",
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Core entrypoint for Agentic Multimodal Legal & Tax Research:
      0. High-Speed Query Cache check (0.005s instant return)
      1. Voice STT: If voice audio is provided, transcribes speech into text.
      2. Vision: If an image is uploaded (e.g. tax notice/order), extracts facts.
      3. LangGraph Agentic Flow:
         - Fast-Path Intent Routing (Legal Query vs. Tax Calculation vs. Dual Query)
         - Deterministic Tax Calculator Tool (Salaried, AOP, Super Tax Sec 4C)
         - Hybrid Vector & Keyword Retrieval (FAISS + BM25)
         - Grounded Legal & Financial Synthesis in requested language.
    """
    clean_query = (query or "").strip()

    # Step 0: High-Speed Cache check for repeated or pre-seeded queries (0.005s)
    if not image_bytes and not audio_bytes and clean_query:
        cached_result = GLOBAL_QUERY_CACHE.get(clean_query, language=language)
        if cached_result:
            return cached_result

    notice_summary = None
    search_query = ""
    voice_transcript = None

    # Step 1: Voice STT transcription if voice audio is provided
    if audio_bytes:
        voice_transcript = transcribe_audio(audio_bytes, language=language)
        if voice_transcript:
            clean_query = voice_transcript if not clean_query else f"{clean_query} {voice_transcript}"

    # Step 2: Multimodal image analysis if an image is provided
    if image_bytes:
        notice_data = analyze_notice_image(image_bytes)
        notice_summary = notice_data.get("summary", "")
        extracted_search = notice_data.get("search_query", "")

        if clean_query:
            english_user_query = translate_query_if_needed(clean_query, language=language)
            search_query = f"{extracted_search} {english_user_query}".strip()
        else:
            search_query = extracted_search
            if language == "Roman Urdu":
                clean_query = "Is notice ki wazahat karein, konse sections lage hain aur aage kya legal tareeqa-kar apnaana hoga?"
            elif language == "Urdu (اردو)":
                clean_query = "اس نوٹس کی قانونی وضاحت کریں، کون سی دفعات لاگو ہیں اور کیا کارروائی ضروری ہے؟"
            else:
                clean_query = "Explain this legal/tax notice, the sections cited, and the required compliance or appeal action."
    else:
        if not clean_query:
            return {
                "answer": "Please enter a question, speak into the microphone, or upload a notice image.",
                "citations": [],
                "original_query": query,
                "english_query": "",
                "language": language,
                "retrieved_chunks": [],
                "notice_summary": None,
                "voice_transcript": voice_transcript,
                "intent": "EMPTY",
                "calculation_result": None,
                "calendar_events": [],
                "portal_info": None,
            }
        search_query = translate_query_if_needed(clean_query, language=language)

    # Step 3: Execute LangGraph Agentic Workflow
    flow_result = run_agentic_flow(
        query=clean_query,
        language=language,
        notice_summary=notice_summary,
        search_query=search_query,
    )

    # Step 4: Compliance Deadlines & Calendar Agent
    calendar_events = detect_compliance_deadlines(
        query=clean_query,
        answer_text=flow_result.get("answer", ""),
        notice_summary=notice_summary,
    )

    # Step 5: Official Government Portal Detection
    portal_info = detect_official_portal_link(
        query=clean_query,
        answer_text=flow_result.get("answer", ""),
    )

    result = {
        "answer": flow_result.get("answer", ""),
        "citations": flow_result.get("citations", []),
        "original_query": clean_query,
        "english_query": flow_result.get("search_query") or search_query,
        "language": language,
        "retrieved_chunks": flow_result.get("retrieved_chunks", []),
        "notice_summary": notice_summary,
        "voice_transcript": voice_transcript,
        "intent": flow_result.get("intent", "LEGAL_RAG"),
        "calculation_result": flow_result.get("calculation_result"),
        "calendar_events": calendar_events,
        "portal_info": portal_info,
    }

    # Cache successful text response for subsequent users
    if not image_bytes and not audio_bytes and result.get("answer"):
        GLOBAL_QUERY_CACHE.set(clean_query, result, language=language)

    return result


def ask_question_stream(
    query: str = "",
    image_bytes: Optional[bytes] = None,
    audio_bytes: Optional[bytes] = None,
    language: str = "English",
) -> Generator[str, None, None]:
    """
    Streaming generator emitting Server-Sent Events (SSE):
      - 'event: meta'   -> sends pre-computed cards (tax, calendar, portal, citations)
      - 'event: token'  -> sends progressive text tokens as they generate (<1.5s start)
      - 'event: done'   -> signals completion
    """
    clean_query = (query or "").strip()

    # Cache check: if cached, stream immediately in < 0.01s!
    if not image_bytes and not audio_bytes and clean_query:
        cached = GLOBAL_QUERY_CACHE.get(clean_query, language=language)
        if cached:
            meta_payload = {
                "intent": cached.get("intent", "LEGAL_RAG"),
                "calculation_result": cached.get("calculation_result"),
                "calendar_events": cached.get("calendar_events", []),
                "portal_info": cached.get("portal_info"),
                "citations": cached.get("citations", []),
                "notice_summary": cached.get("notice_summary"),
                "cached": True,
            }
            yield f"event: meta\ndata: {json.dumps(meta_payload)}\n\n"
            # Yield cached answer
            yield f"event: token\ndata: {json.dumps({'text': cached.get('answer', '')})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

    notice_summary = None
    search_query = ""

    if image_bytes:
        notice_data = analyze_notice_image(image_bytes)
        notice_summary = notice_data.get("summary", "")
        search_query = notice_data.get("search_query", "")
        if not clean_query:
            clean_query = "Explain this legal/tax notice and required actions."

    if not clean_query:
        yield f"event: done\ndata: {json.dumps({'error': 'Empty query'})}\n\n"
        return

    # 1. Fast-Path Router
    router_state = {
        "clean_query": clean_query,
        "language": language,
        "notice_summary": notice_summary,
        "search_query": search_query or clean_query,
    }
    routed = router_node(router_state)
    intent = routed.get("intent", "LEGAL_RAG")
    tax_params = routed.get("tax_params")
    search_q = routed.get("search_query") or clean_query

    calc_result = None
    if intent in ["TAX_CALC", "DUAL"] and tax_params:
        calc_state = {"tax_params": tax_params}
        calc_out = tax_calculator_node(calc_state)
        calc_result = calc_out.get("calculation_result")

    retrieved_chunks = []
    citations = []
    if intent in ["LEGAL_RAG", "DUAL"]:
        ret_state = {"clean_query": clean_query, "search_query": search_q}
        ret_out = legal_retriever_node(ret_state)
        retrieved_chunks = ret_out.get("retrieved_chunks", [])
        citations = ret_out.get("citations", [])

    # Action Agents
    calendar_events = detect_compliance_deadlines(
        query=clean_query,
        answer_text=clean_query,
        notice_summary=notice_summary,
    )
    portal_info = detect_official_portal_link(
        query=clean_query,
        answer_text=clean_query,
    )

    # Immediately emit metadata (cards render in frontend in <1 second!)
    meta_payload = {
        "intent": intent,
        "calculation_result": calc_result,
        "calendar_events": calendar_events,
        "portal_info": portal_info,
        "citations": citations,
        "notice_summary": notice_summary,
        "cached": False,
    }
    yield f"event: meta\ndata: {json.dumps(meta_payload)}\n\n"

    # If pure TAX_CALC without legal questions, emit calculation summary and finish
    if intent == "TAX_CALC" and calc_result:
        fmt = calc_result["formatted"]
        cat = calc_result["category"].capitalize()
        ans = (
            f"### Computed Tax Liability ({cat})\n\n"
            f"- **Taxable Income:** {fmt['taxable_income']}\n"
            f"- **Base Income Tax:** {fmt['base_tax']}\n"
            f"- **Section 4C Super Tax:** {fmt['super_tax_4c']}\n"
            f"- **Total Tax Liability:** **{fmt['total_tax_liability']}**\n"
            f"- **Effective Tax Rate:** **{fmt['effective_rate']}**\n\n"
            f"*Computed strictly under the First Schedule of the Income Tax Ordinance 2001 (Finance Act 2024).*"
        )
        yield f"event: token\ndata: {json.dumps({'text': ans})}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

        # Cache calculation result
        if not image_bytes and not audio_bytes:
            GLOBAL_QUERY_CACHE.set(clean_query, {**meta_payload, "answer": ans}, language=language)
        return

    # Stream legal synthesis tokens progressively from Gemini!
    full_answer_parts = []
    try:
        for chunk in generate_legal_answer_stream(
            query=clean_query,
            target_language=language,
            context_chunks=retrieved_chunks,
            notice_summary=notice_summary,
        ):
            if chunk:
                full_answer_parts.append(chunk)
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
    except Exception as e:
        err_msg = f"\n\n*Error during streaming generation: {str(e)}*"
        full_answer_parts.append(err_msg)
        yield f"event: token\ndata: {json.dumps({'text': err_msg})}\n\n"

    full_answer = "".join(full_answer_parts)
    yield f"event: done\ndata: {{}}\n\n"

    # Store in cache
    if not image_bytes and not audio_bytes and full_answer:
        final_cached = {
            **meta_payload,
            "answer": full_answer,
            "original_query": clean_query,
            "language": language,
        }
        GLOBAL_QUERY_CACHE.set(clean_query, final_cached, language=language)
