
"""
FastAPI Server for Legal Research Assistant & Corporate Tax Studio
Serves the ChatGPT-grade animated frontend and REST/Streaming APIs.
"""

import os
import io
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core import ask_question, ask_question_stream
from app.tools.tax_calculator import calculate_pakistan_tax, generate_tax_advisory_memo
from app.tools.pdf_generator import generate_tax_pdf_report
from app.tools.calendar_tool import generate_ics_content, parse_date_from_string

app = FastAPI(
    title="LegalTax AI - Pakistani Legal & Corporate Tax Studio",
    description="Enterprise Legal AI Platform for FBR & SECP Statutory Research and Tax Computations",
    version="2.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaxCalcRequest(BaseModel):
    gross_revenue: float
    category: str = "Private Limited Company"
    tax_year: str = "2024-2025"
    deductions: float = 0.0
    advance_tax: float = 0.0
    taxpayer_name: str = "Corporate Client"


class PDFDownloadRequest(BaseModel):
    calc_data: dict
    advisory_memo: str = ""
    taxpayer_name: str = "Corporate Client"


@app.get("/")
def serve_index():
    """Serves the primary ChatGPT-style single page application."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "LegalTax AI API is running. UI building in progress..."}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "LegalTax AI", "version": "2.0.0"}


@app.post("/api/chat")
async def chat_endpoint(
    query: str = Form(""),
    language: str = Form("English"),
    notice_image: Optional[UploadFile] = File(None),
):
    """
    Multimodal Chat Endpoint:
    Processes user query and optional notice image through LangGraph Agentic RAG workflow.
    """
    image_bytes = None
    if notice_image:
        image_bytes = await notice_image.read()

    try:
        result = ask_question(
            query=query,
            image_bytes=image_bytes,
            language=language,
        )
        return {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "intent": result.get("intent", "LEGAL_RAG"),
            "calculation_result": result.get("calculation_result"),
            "notice_summary": result.get("notice_summary"),
            "english_query": result.get("english_query", ""),
            "calendar_events": result.get("calendar_events", []),
            "portal_info": result.get("portal_info"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream_endpoint(
    query: str = Form(""),
    language: str = Form("English"),
    notice_image: Optional[UploadFile] = File(None),
):
    """
    Real-Time SSE Streaming Endpoint:
    Streams metadata cards in <1.0s and tokens progressively directly from Gemini.
    """
    image_bytes = None
    if notice_image:
        image_bytes = await notice_image.read()

    generator = ask_question_stream(
        query=query,
        image_bytes=image_bytes,
        language=language,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/calendar/download-ics")
def download_ics_endpoint(
    title: str = "Compliance Deadline",
    date_str: str = "",
    desc: str = "",
    location: str = "FBR / SECP Pakistan",
):
    """
    RFC 5545 Universal iCalendar file generator for Outlook, Apple Calendar, Windows Calendar.
    """
    try:
        from datetime import datetime
        dt = parse_date_from_string(date_str)
        if not dt:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()

        ics_text = generate_ics_content(
            title=title,
            target_date=dt,
            description=desc,
            location=location,
        )
        safe_filename = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip().replace(" ", "_")
        return Response(
            content=ics_text.encode("utf-8"),
            media_type="text/calendar",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}.ics"'},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid calendar date or parameters: {e}")


@app.post("/api/calculate")
def calculate_endpoint(req: TaxCalcRequest):
    """
    Deterministic Statutory Tax Calculation & AI Legal Strategy Memo.
    """
    try:
        calc_result = calculate_pakistan_tax(
            income=req.gross_revenue,
            category=req.category,
            tax_year=req.tax_year,
            deductions=req.deductions,
            advance_tax_paid=req.advance_tax,
        )
        advisory = generate_tax_advisory_memo(calc_result, business_type=req.category)
        return {
            "calculation": calc_result,
            "advisory_memo": advisory,
            "taxpayer_name": req.taxpayer_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-pdf")
def download_pdf_endpoint(req: PDFDownloadRequest):
    """
    Generates and returns the official PDF Tax Assessment Memorandum.
    """
    try:
        pdf_bytes = generate_tax_pdf_report(
            calc_data=req.calc_data,
            advisory_memo=req.advisory_memo,
            taxpayer_name=req.taxpayer_name,
        )
        filename = f"Tax_Advisory_{req.taxpayer_name.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount static assets (HTML, CSS, JS, PDF documents)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    # Port 7860 is default for Hugging Face Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Starting LegalTax AI Server on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
