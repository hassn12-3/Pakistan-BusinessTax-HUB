"""
Official Government Portal Registry & Detection Agent for Pakistan Legal & Tax.
Detects when user inquires about NTN registration, SECP company registration,
or ATL verification and provides direct verified portal links with automated browser launch.
"""

from typing import Dict, Any, Optional, List


OFFICIAL_PORTALS = {
    "fbr_ntn_registration": {
        "id": "fbr_ntn",
        "name": "FBR IRIS Taxpayer Registration (Form 181 / NTN)",
        "url": "https://iris.fbr.gov.pk/",
        "domain": "iris.fbr.gov.pk",
        "authority": "Federal Board of Revenue (FBR)",
        "law": "Income Tax Ordinance, 2001 - Section 181",
        "description": "Official FBR IRIS portal for new National Tax Number (NTN) registration and filing Form 181.",
        "steps": [
            "1. Click 'Registration for Unregistered Person' on the IRIS portal.",
            "2. Enter your 13-digit CNIC, mobile network, and email address.",
            "3. Enter the SMS and Email OTP verification codes.",
            "4. Log in and submit Form 181 with your address and utility bill.",
        ],
    },
    "secp_company_registration": {
        "id": "secp_incorp",
        "name": "SECP eServices Portal (Company Name & Incorporation)",
        "url": "https://eservices.secp.gov.pk/",
        "domain": "eservices.secp.gov.pk",
        "authority": "Securities and Exchange Commission of Pakistan (SECP)",
        "law": "Companies Act, 2017 - Section 16",
        "description": "Official SECP eServices portal to reserve company name and submit incorporation documents.",
        "steps": [
            "1. Create an account on SECP eServices.",
            "2. Submit Form 1 for Company Name Reservation.",
            "3. Upon approval, submit Form II (Memorandum and Articles of Association).",
            "4. Pay digital incorporation challan via 1Link or bank.",
        ],
    },
    "fbr_atl_inquiry": {
        "id": "fbr_atl",
        "name": "FBR Active Taxpayer List (ATL) Online Verification",
        "url": "https://e.fbr.gov.pk/",
        "domain": "e.fbr.gov.pk",
        "authority": "Federal Board of Revenue (FBR)",
        "law": "Income Tax Ordinance, 2001 - Tenth Schedule",
        "description": "Official online portal to verify Filer / Non-Filer ATL status for banking and withholding taxes.",
        "steps": [
            "1. Open the portal and select 'Active Taxpayer List (Income Tax)'.",
            "2. Enter your 13-digit CNIC or 7-digit NTN.",
            "3. Verify active filer status and effective withholding tax rates.",
        ],
    },
}


def detect_official_portal_link(query: str, answer_text: str = "") -> Optional[Dict[str, Any]]:
    """
    STRICT FILTER: ONLY returns an official government portal link if the user explicitly asks for
    a link/website/portal or specifically asks where/how to register or apply.
    """
    q_lower = (query or "").lower()

    # User MUST specifically ask for a link, portal, or state registration/application intent
    link_intent_cues = [
        "link", "website", "portal", "url", "give link", "give me link",
        "where to apply", "where to register", "how to register", "want to register",
        "i want to register", "apply for ntn", "register for ntn", "register ntn",
        "register company", "apply online", "open portal", "login link", "form link",
        "link de", "website batao", "portal open", "check filer status", "check atl"
    ]
    is_link_requested = any(cue in q_lower for cue in link_intent_cues)

    # If user did NOT ask for a link or to register, return None immediately
    if not is_link_requested:
        return None

    # 1. NTN Registration / Form 181 / FBR Registration
    if any(k in q_lower for k in [
        "ntn", "form 181", "taxpayer registration", "fbr registration", "iris registration"
    ]):
        p = OFFICIAL_PORTALS["fbr_ntn_registration"].copy()
        p["auto_open"] = any(k in q_lower for k in ["register", "want", "apply", "open", "karna", "chahiye"])
        return p

    # 2. SECP Company Registration / Name Reservation
    if any(k in q_lower for k in [
        "secp", "company registration", "register company", "incorporate",
        "name reservation", "form 1", "eservices", "pvt ltd register"
    ]):
        p = OFFICIAL_PORTALS["secp_company_registration"].copy()
        p["auto_open"] = any(k in q_lower for k in ["register", "want", "apply", "open", "karna", "chahiye"])
        return p

    # 3. Active Taxpayer List (ATL)
    if any(k in q_lower for k in ["atl", "active taxpayer list", "filer status", "check filer"]):
        p = OFFICIAL_PORTALS["fbr_atl_inquiry"].copy()
        p["auto_open"] = any(k in q_lower for k in ["check", "open", "verify", "status"])
        return p

    return None
