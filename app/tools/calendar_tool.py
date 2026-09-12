"""
Compliance Deadlines & Calendar Agent Tool for Pakistani Legal & Tax Assistant.
Supports:
1. Extraction & Calculation of Statutory Deadlines (FBR, SECP, High Court)
2. One-Click Google Calendar Event Links
3. RFC 5545 Universal .ics Calendar File Generation (Outlook, Apple Calendar, Google Calendar)
"""

import re
import urllib.parse
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional


# Statutory Limitation Rules in Pakistani Law (Income Tax Ordinance 2001, Sales Tax Act 1990, Companies Act 2017)
STATUTORY_DEADLINES = {
    "sec_127_appeal": {
        "title": "FBR Sec 127 Appeal Deadline (CIR Appeals)",
        "limitation_days": 30,
        "law": "Income Tax Ordinance, 2001 - Section 127",
        "description": "Statutory 30-day limitation to file Appeal before Commissioner (Appeals) against Assessment Order.",
        "location": "Commissioner Inland Revenue (Appeals) Office",
    },
    "sec_131_appeal": {
        "title": "ATIR Sec 131 Appeal Deadline (Appellate Tribunal)",
        "limitation_days": 60,
        "law": "Income Tax Ordinance, 2001 - Section 131",
        "description": "Statutory 60-day limitation to file Appeal before Appellate Tribunal Inland Revenue (ATIR).",
        "location": "Appellate Tribunal Inland Revenue (ATIR)",
    },
    "sec_133_reference": {
        "title": "High Court Sec 133 Reference Application",
        "limitation_days": 90,
        "law": "Income Tax Ordinance, 2001 - Section 133",
        "description": "Statutory 90-day limitation to file Reference Application before the High Court on question of law.",
        "location": "High Court",
    },
    "sec_122_show_cause": {
        "title": "FBR Sec 122 Notice Compliance Deadline",
        "limitation_days": 15,
        "law": "Income Tax Ordinance, 2001 - Section 122(9)",
        "description": "Statutory deadline to submit written reply and compliance documents to Show Cause Notice under Section 122.",
        "location": "FBR IRIS Portal / Unit Office",
    },
    "sec_111_unexplained": {
        "title": "FBR Sec 111 Notice Explanation Deadline",
        "limitation_days": 15,
        "law": "Income Tax Ordinance, 2001 - Section 111",
        "description": "Deadline to submit documentary explanation for unexplained income/assets before assessment.",
        "location": "FBR IRIS Portal",
    },
    "sec_176_production": {
        "title": "FBR Sec 176 Production of Books Deadline",
        "limitation_days": 7,
        "law": "Income Tax Ordinance, 2001 - Section 176",
        "description": "Requisition notice compliance: produce books of accounts, bank statements, or attend hearing.",
        "location": "FBR IRIS Portal / Tax Office",
    },
    "sec_147_advance_tax": {
        "title": "FBR Section 147 Advance Tax Quarterly Installment",
        "law": "Income Tax Ordinance, 2001 - Section 147",
        "description": "Quarterly advance income tax payment deadline to avoid default surcharge under Section 205.",
        "location": "FBR e-Payment / National Bank / State Bank",
    },
    "secp_form_a": {
        "title": "SECP Form A / Form 29 Annual Filing",
        "limitation_days": 30,
        "law": "Companies Act, 2017 - Section 130",
        "description": "Statutory requirement to file Annual Return (Form A) within 30 days of Annual General Meeting (AGM).",
        "location": "SECP eServices Portal",
    },
    "annual_return_individual": {
        "title": "FBR Annual Income Tax Return (Salaried / AOP)",
        "law": "Income Tax Ordinance, 2001 - Section 118",
        "description": "Statutory deadline (September 30) for filing Annual Tax Return for individuals and AOPs.",
        "location": "FBR IRIS Portal",
    },
    "annual_return_company": {
        "title": "FBR Annual Income Tax Return (Companies)",
        "law": "Income Tax Ordinance, 2001 - Section 118",
        "description": "Statutory deadline (December 31) for corporate tax return filing for tax year ending June 30.",
        "location": "FBR IRIS Portal",
    },
}


def parse_date_from_string(text: str) -> Optional[date]:
    """
    Attempts to parse a calendar date from string (e.g. '15 March 2026', '2026-03-15', '15-03-2026').
    """
    date_patterns = [
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",  # YYYY-MM-DD
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",  # DD-MM-YYYY
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
    ]

    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }

    # Match named month format
    named_match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text, re.IGNORECASE)
    if named_match:
        d = int(named_match.group(1))
        m_name = named_match.group(2).lower()
        y = int(named_match.group(3))
        if m_name in months:
            try:
                return date(y, months[m_name], d)
            except ValueError:
                pass

    # Match ISO YYYY-MM-DD
    iso_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # Match DD-MM-YYYY
    dmy_match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", text)
    if dmy_match:
        try:
            return date(int(dmy_match.group(3)), int(dmy_match.group(2)), int(dmy_match.group(1)))
        except ValueError:
            pass

    return None


def get_next_advance_tax_deadline(today: Optional[date] = None) -> date:
    """Calculates the next Section 147 advance tax quarterly installment date."""
    if not today:
        today = date.today()

    year = today.year
    quarters = [
        date(year, 9, 15),   # Q1
        date(year, 12, 15),  # Q2
        date(year + 1, 3, 15),  # Q3
        date(year + 1, 6, 15),  # Q4
    ]

    for q_date in quarters:
        if q_date >= today:
            return q_date
    return date(year + 1, 9, 15)


def generate_google_calendar_url(
    title: str,
    target_date: date,
    description: str = "",
    location: str = "FBR / SECP Portal"
) -> str:
    """
    Builds a direct 1-click Google Calendar Web Intent URL.
    Opens calendar with pre-filled title, date, notes, and 24h reminder.
    """
    start_str = target_date.strftime("%Y%m%d")
    # For all-day event in Google Calendar, end date is next day
    next_day = target_date + timedelta(days=1)
    end_str = next_day.strftime("%Y%m%d")

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{start_str}/{end_str}",
        "details": f"{description}\n\nGenerated automatically by LegalTax AI Compliance Agent.",
        "location": location,
        "sprop": "website:legaltax.ai",
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"


def generate_ics_content(
    title: str,
    target_date: date,
    description: str = "",
    location: str = "FBR / SECP Portal"
) -> str:
    """
    Generates standard RFC 5545 iCalendar (.ics) string.
    Supported natively by Apple Calendar, Microsoft Outlook, Windows Calendar, Google Calendar.
    Includes automated 24-hour reminder alarm.
    """
    dt_str = target_date.strftime("%Y%m%d")
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    clean_title = title.replace("\n", " ").replace(";", "\\;").replace(",", "\\,")
    clean_desc = description.replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")
    uid = f"{target_date.strftime('%Y%m%d')}-{abs(hash(clean_title))}@legaltax.ai"

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LegalTax AI//Compliance Deadlines Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART;VALUE=DATE:{dt_str}",
        f"DTEND;VALUE=DATE:{dt_str}",
        f"SUMMARY:{clean_title}",
        f"DESCRIPTION:{clean_desc}",
        f"LOCATION:{location}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "TRIGGER:-P1D",  # Reminder 1 day prior
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder: {clean_title} is due tomorrow!",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(ics_lines)


def detect_compliance_deadlines(
    query: str,
    answer_text: str = "",
    notice_summary: Optional[str] = None,
    base_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Analyzes user query, notice facts, and legal answer to detect statutory deadlines.
    STRICT FILTER: Only generates calendar cards if the user specifically asked for
    an appeal, deadline, limitation period, or uploaded an assessment notice.
    """
    q_lower = (query or "").lower()
    has_notice_doc = bool(notice_summary and notice_summary.strip())

    # User MUST specifically mention appeal, deadline, limitation, or notice limitation
    deadline_cues = [
        "deadline", "last date", "last day", "limitation", "limitation period",
        "file appeal", "apply appeal", "appeal deadline", "appeal limitation",
        "time limit", "how many days to appeal", "due date", "calendar",
        "notice date", "compliance date", "order received", "notice received",
        "advance tax date", "installment deadline", "aakhri tareekh", "kitne din"
    ]
    is_deadline_query = any(c in q_lower for c in deadline_cues) or has_notice_doc

    # If the user did NOT ask about a deadline or appeal date, do NOT show any calendar card!
    if not is_deadline_query:
        return []

    combined_text = f"{query} {notice_summary or ''}".lower()
    today = base_date or date.today()
    events: List[Dict[str, Any]] = []

    # Check if a specific notice date was mentioned
    notice_date = parse_date_from_string(query)
    if not notice_date and notice_summary:
        notice_date = parse_date_from_string(notice_summary)
    if not notice_date:
        notice_date = today

    # 1. Section 127 Appeal to CIR(Appeals) - 30 Days
    if any(k in combined_text for k in ["127", "cir(a)", "appeal before commissioner", "appeal deadline", "file appeal", "apply appeal", "assessment order", "appeal against order"]):
        deadline_date = notice_date + timedelta(days=STATUTORY_DEADLINES["sec_127_appeal"]["limitation_days"])
        days_left = (deadline_date - today).days
        event_info = STATUTORY_DEADLINES["sec_127_appeal"]
        events.append({
            "id": "sec_127_appeal",
            "title": event_info["title"],
            "law": event_info["law"],
            "date": deadline_date.strftime("%Y-%m-%d"),
            "display_date": deadline_date.strftime("%d %B %Y"),
            "days_left": days_left,
            "description": f"{event_info['description']} (Notice Date: {notice_date.strftime('%d %b %Y')}).",
            "location": event_info["location"],
            "google_calendar_url": generate_google_calendar_url(
                title=event_info["title"],
                target_date=deadline_date,
                description=event_info["description"],
                location=event_info["location"],
            ),
        })

    # 2. Section 131 Appeal to ATIR - 60 Days
    if any(k in combined_text for k in ["131", "atir", "appellate tribunal", "tribunal appeal"]):
        deadline_date = notice_date + timedelta(days=STATUTORY_DEADLINES["sec_131_appeal"]["limitation_days"])
        days_left = (deadline_date - today).days
        event_info = STATUTORY_DEADLINES["sec_131_appeal"]
        events.append({
            "id": "sec_131_appeal",
            "title": event_info["title"],
            "law": event_info["law"],
            "date": deadline_date.strftime("%Y-%m-%d"),
            "display_date": deadline_date.strftime("%d %B %Y"),
            "days_left": days_left,
            "description": f"{event_info['description']} (Order Date: {notice_date.strftime('%d %b %Y')}).",
            "location": event_info["location"],
            "google_calendar_url": generate_google_calendar_url(
                title=event_info["title"],
                target_date=deadline_date,
                description=event_info["description"],
                location=event_info["location"],
            ),
        })

    # 3. Section 147 Advance Tax Installment
    if any(k in combined_text for k in ["147", "advance tax", "quarterly installment", "advance tax payment"]):
        next_q = get_next_advance_tax_deadline(today)
        days_left = (next_q - today).days
        event_info = STATUTORY_DEADLINES["sec_147_advance_tax"]
        events.append({
            "id": "sec_147_advance_tax",
            "title": event_info["title"],
            "law": event_info["law"],
            "date": next_q.strftime("%Y-%m-%d"),
            "display_date": next_q.strftime("%d %B %Y"),
            "days_left": days_left,
            "description": f"{event_info['description']} for Quarter Ending.",
            "location": event_info["location"],
            "google_calendar_url": generate_google_calendar_url(
                title=event_info["title"],
                target_date=next_q,
                description=event_info["description"],
                location=event_info["location"],
            ),
        })

    # 4. Section 122 / 111 Notice Compliance (15 Days)
    if any(k in combined_text for k in ["show cause", "122(", "122 (", "section 122", "section 111", "reply to notice"]) and not any(e["id"] == "sec_127_appeal" for e in events):
        deadline_date = notice_date + timedelta(days=15)
        days_left = (deadline_date - today).days
        event_info = STATUTORY_DEADLINES["sec_122_show_cause"]
        events.append({
            "id": "sec_122_compliance",
            "title": event_info["title"],
            "law": event_info["law"],
            "date": deadline_date.strftime("%Y-%m-%d"),
            "display_date": deadline_date.strftime("%d %B %Y"),
            "days_left": days_left,
            "description": f"Submit written defense before tax officer under Section 122(9) (Notice Date: {notice_date.strftime('%d %b %Y')}).",
            "location": event_info["location"],
            "google_calendar_url": generate_google_calendar_url(
                title=event_info["title"],
                target_date=deadline_date,
                description=event_info["description"],
                location=event_info["location"],
            ),
        })

    # 5. SECP Compliance / Form A
    if any(k in combined_text for k in ["secp", "form a", "form 29", "agm", "annual return company", "companies act"]):
        deadline_date = notice_date + timedelta(days=30)
        days_left = (deadline_date - today).days
        event_info = STATUTORY_DEADLINES["secp_form_a"]
        events.append({
            "id": "secp_form_a",
            "title": event_info["title"],
            "law": event_info["law"],
            "date": deadline_date.strftime("%Y-%m-%d"),
            "display_date": deadline_date.strftime("%d %B %Y"),
            "days_left": days_left,
            "description": f"{event_info['description']} (AGM / Baseline Date: {notice_date.strftime('%d %b %Y')}).",
            "location": event_info["location"],
            "google_calendar_url": generate_google_calendar_url(
                title=event_info["title"],
                target_date=deadline_date,
                description=event_info["description"],
                location=event_info["location"],
            ),
        })

    # Limit to top 2 relevant events to avoid clutter
    return events[:2]
