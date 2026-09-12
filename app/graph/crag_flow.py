"""
Agentic RAG & Workflow with LangGraph for Pakistani Legal & Tax Research.

Combines:
1. Intent Routing (Legal Query vs. Tax Calculation vs. Dual Query)
2. Deterministic Tax Calculator Tool (Salaried, Business, and Section 4C Super Tax)
3. Hybrid Retrieval (FAISS + BM25 statutory chunks)
4. Context Synthesis (Bilingual/Trilingual: English, Roman Urdu, Urdu)
"""

import json
import re
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from google.genai import types

from app.config import GEMINI_MODEL
from app.generation.llm_client import (
    get_genai_client,
    translate_query_if_needed,
    generate_legal_answer,
)
from app.generation.citation_builder import build_citations
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.tools.tax_calculator import calculate_pakistan_tax, parse_currency_amount, format_tax_summary_markdown


class AgentState(TypedDict):
    query: str
    clean_query: str
    language: str
    notice_summary: Optional[str]
    intent: str  # "LEGAL_RAG", "TAX_CALC", or "DUAL"
    search_query: str
    tax_params: Optional[Dict[str, Any]]
    calculation_result: Optional[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    final_answer: str


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Classifies user intent and extracts tax computation parameters if relevant.
    Determines whether the request is:
      - 'LEGAL_RAG': Pure legal/compliance question.
      - 'TAX_CALC': Tax calculation request (e.g. salary tax, super tax on 25 crore).
      - 'DUAL': Both a legal research question and a tax calculation request.
    """
    query = state["clean_query"]
    notice_summary = state.get("notice_summary") or ""
    language = state.get("language", "English")

    # Fast heuristic check for tax calculation keywords
    tax_keywords = [
        "calculate", "calculator", "calculation", "tax on", "how much tax",
        "tax liability", "super tax", "section 4c", "salary tax", "salary of",
        "income of", "crore", "crores", "lakh", "lakhs", "million", "millions",
        "kitna tax", "tax kitna", "hisaab", "tax calculate"
    ]
    has_tax_cue = any(kw in query.lower() for kw in tax_keywords)
    extracted_amount = parse_currency_amount(query)
    legal_research_cues = [
        "explain", "requirements", "filing", "return", "exemption", "exempt",
        "notice", "appeal", "contest", "remedy", "defense", "tribunal", "order",
        "show cause", "audit", "compliance", "penalty", "consequences", "due date",
        "clause", "regulation", "section", "ordinance", "provision", "procedure", "wazahat", "batao"
    ]
    has_substantive_legal_q = any(cue in query.lower() for cue in legal_research_cues)

    # FAST-PATH 1: Queries without a financial amount and without an attached notice
    # If there is no numeric amount, no computation can be performed -> 100% LEGAL_RAG!
    if not extracted_amount and not notice_summary:
        search_query = translate_query_if_needed(query, language=language)
        return {
            "intent": "LEGAL_RAG",
            "tax_params": None,
            "search_query": search_query,
        }

    # FAST-PATH 2: Dual query when user asks for tax calculation AND legal explanations/rules
    if extracted_amount and has_substantive_legal_q and not notice_summary:
        q_lower = query.lower()
        is_monthly = any(m in q_lower for m in ["month", "pm", "per month", "mahina"])
        is_company = any(c in q_lower for c in ["company", "corporate", "pvt", "limited", "ltd"])
        is_biz = is_company or any(b in q_lower for b in ["business", "aop", "firm", "proprietor", "non-salaried"])
        category = "company" if is_company else ("business" if is_biz else "salaried")
        search_query = translate_query_if_needed(query, language=language)

        return {
            "intent": "DUAL",
            "tax_params": {
                "income": extracted_amount,
                "is_monthly": is_monthly,
                "category": category,
                "tax_year": "2024-2025",
            },
            "search_query": search_query,
        }

    # FAST-PATH 3: Clear tax calculation query with parsed amount and no legal questions
    if extracted_amount and (has_tax_cue or not notice_summary):
        q_lower = query.lower()
        is_monthly = any(m in q_lower for m in ["month", "pm", "per month", "mahina"])
        is_company = any(c in q_lower for c in ["company", "corporate", "pvt", "limited", "ltd"])
        is_biz = is_company or any(b in q_lower for b in ["business", "aop", "firm", "proprietor", "non-salaried"])
        category = "company" if is_company else ("business" if is_biz else "salaried")

        return {
            "intent": "TAX_CALC",
            "tax_params": {
                "income": extracted_amount,
                "is_monthly": is_monthly,
                "category": category,
                "tax_year": "2024-2025",
            },
            "search_query": "Income Tax Ordinance Pakistan First Schedule Slabs",
        }

    # Fallback to LLM classifier only for complex multimodal notice documents
    client = get_genai_client()
    system_prompt = (
        "You are an intent classifier and parameter extractor for a Pakistani Legal and Tax Assistant.\n"
        "Analyze the user query (and optional notice summary) and return a strict JSON object with keys:\n"
        "- intent: 'TAX_CALC' (if only tax calculation is requested), "
        "'LEGAL_RAG' (if only statutory/legal analysis or rules are asked), "
        "or 'DUAL' (if user asks BOTH for tax calculation and legal advice/appeals/remedies/definitions).\n"
        "- amount: number or null (the annual or monthly income/turnover amount in PKR numbers).\n"
        "- is_monthly: boolean (true if user specifies monthly salary/income, false if annual or unspecified).\n"
        "- category: 'salaried' or 'business' (default 'salaried' unless AOP, business, company or non-salaried is mentioned).\n"
        "- tax_year: '2024-2025' or the stated tax year.\n"
        "- search_query: English search query to retrieve relevant statutory law or tax sections.\n"
        "Output ONLY valid JSON."
    )

    full_context = f"User Query: {query}\nNotice Summary: {notice_summary}"

    intent = "LEGAL_RAG"
    tax_params = None
    search_query = state.get("search_query") or query

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_context,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        data = json.loads(response.text.strip())
        intent = data.get("intent", "LEGAL_RAG")
        amt = data.get("amount") or extracted_amount

        if intent in ["TAX_CALC", "DUAL"] or (amt and has_tax_cue):
            if not amt and extracted_amount:
                amt = extracted_amount

            if amt:
                tax_params = {
                    "income": float(amt),
                    "is_monthly": bool(data.get("is_monthly", False)),
                    "category": str(data.get("category", "salaried")),
                    "tax_year": str(data.get("tax_year", "2024-2025")),
                }
            else:
                tax_params = None

        search_query = data.get("search_query") or translate_query_if_needed(query, language=language)

    except Exception:
        if extracted_amount and has_tax_cue:
            intent = "DUAL" if has_legal_cue else "TAX_CALC"
            tax_params = {
                "income": extracted_amount,
                "is_monthly": "month" in query.lower(),
                "category": "business" if "business" in query.lower() or "aop" in query.lower() else "salaried",
                "tax_year": "2024-2025",
            }
        else:
            intent = "LEGAL_RAG"
            tax_params = None

        search_query = translate_query_if_needed(query, language=language)


    return {
        "intent": intent,
        "tax_params": tax_params,
        "search_query": search_query,
    }


def tax_calculator_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes deterministic statutory calculation using the Pakistan Tax Calculator tool.
    """
    tax_params = state.get("tax_params")
    if not tax_params or not tax_params.get("income"):
        return {"calculation_result": None}

    calc_result = calculate_pakistan_tax(
        income=tax_params["income"],
        category=tax_params.get("category", "salaried"),
        tax_year=tax_params.get("tax_year", "2024-2025"),
        is_monthly=tax_params.get("is_monthly", False),
    )

    return {"calculation_result": calc_result}


def legal_retriever_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieves statutory context and builds citations from FAISS + BM25 index.
    """
    search_query = state.get("search_query") or state.get("clean_query") or ""
    if not search_query.strip():
        search_query = "Income Tax Ordinance Pakistan super tax rates"

    retrieved = hybrid_retrieve(query=search_query, top_k=3)
    citations = build_citations(retrieved)[:2]

    return {
        "retrieved_chunks": retrieved,
        "citations": citations,
    }


def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Fuses tax calculation results and legal context into a cohesive,
    well-structured statutory legal response in the target language.
    """
    intent = state.get("intent", "LEGAL_RAG")
    calc_result = state.get("calculation_result")
    retrieved_chunks = state.get("retrieved_chunks", [])
    query = state.get("clean_query", "")
    language = state.get("language", "English")
    notice_summary = state.get("notice_summary")

    # If only tax calculation without legal questions
    if intent == "TAX_CALC" and calc_result:
        ans = format_tax_summary_markdown(calc_result, language=language)
        return {"final_answer": ans}

    # If pure legal RAG or Dual query
    legal_answer = generate_legal_answer(
        query=query,
        target_language=language,
        context_chunks=retrieved_chunks,
        notice_summary=notice_summary,
    )

    if intent == "DUAL" and calc_result:
        calc_header = format_tax_summary_markdown(calc_result, language=language)
        separator = "\n\n---\n\n### ⚖️ Grounded Statutory Legal Research & Analysis\n\n"
        final_answer = calc_header + separator + legal_answer
    else:
        final_answer = legal_answer

    return {"final_answer": final_answer}


def route_decision(state: AgentState) -> str:
    """Branching logic after intent routing."""
    intent = state.get("intent", "LEGAL_RAG")
    if intent == "TAX_CALC" and state.get("tax_params"):
        return "tax_calculator"
    elif intent == "DUAL":
        return "dual_path"
    else:
        return "legal_retriever"


def create_crag_flow():
    """Builds and compiles the LangGraph Agentic RAG workflow."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("tax_calculator", tax_calculator_node)
    workflow.add_node("legal_retriever", legal_retriever_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define Workflow Edges
    workflow.add_edge(START, "router")

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "tax_calculator": "tax_calculator",
            "legal_retriever": "legal_retriever",
            "dual_path": "tax_calculator",
        },
    )

    # From tax_calculator: If DUAL, go to legal_retriever; if TAX_CALC, go to synthesizer
    def after_calc_decision(state: AgentState) -> str:
        if state.get("intent") == "DUAL":
            return "legal_retriever"
        return "synthesizer"

    workflow.add_conditional_edges(
        "tax_calculator",
        after_calc_decision,
        {
            "legal_retriever": "legal_retriever",
            "synthesizer": "synthesizer",
        },
    )

    workflow.add_edge("legal_retriever", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


# Global compiled app singleton
agent_app = create_crag_flow()


def run_agentic_flow(
    query: str,
    language: str = "English",
    notice_summary: Optional[str] = None,
    search_query: str = "",
) -> Dict[str, Any]:
    """
    Executes the compiled LangGraph workflow.
    """
    initial_state: AgentState = {
        "query": query,
        "clean_query": query,
        "language": language,
        "notice_summary": notice_summary,
        "intent": "LEGAL_RAG",
        "search_query": search_query,
        "tax_params": None,
        "calculation_result": None,
        "retrieved_chunks": [],
        "citations": [],
        "final_answer": "",
    }

    final_state = agent_app.invoke(initial_state)

    return {
        "answer": final_state.get("final_answer", ""),
        "citations": final_state.get("citations", []),
        "retrieved_chunks": final_state.get("retrieved_chunks", []),
        "intent": final_state.get("intent", "LEGAL_RAG"),
        "calculation_result": final_state.get("calculation_result"),
        "search_query": final_state.get("search_query", ""),
    }
