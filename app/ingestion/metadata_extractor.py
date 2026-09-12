import re
from typing import Optional

FBR_KEYWORDS = [
    "income_tax_ordinance",
    "income_tax_ordinanace",  # handles common typo in legal PDF filenames
    "sales_tax_act",
    "income_tax_rules",
    "sales_tax_rules",
    "finance_act",
    "withholding_tax",
]

SECP_KEYWORDS = [
    "companies_act",
    "single_member_companies_rules",
    "limited_liability_partnership_act",
    "limited_liability_partnership",
    "secp_incorporation_guide",
    "company_regulations",
    "companies_regulations",
]


def get_issuing_body(filename: str) -> str:
    """
    Determines the issuing body (FBR or SECP) based on keyword matching
    against the normalized filename. Return 'Unknown' if no match, and print
    a warning listing any 'Unknown' files so naming mismatches get caught.
    """
    # Alphanumeric normalization for delimiter-agnostic matching
    def clean_str(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    norm_filename = clean_str(filename)

    # Check FBR keywords
    for kw in FBR_KEYWORDS:
        if clean_str(kw) in norm_filename:
            return "FBR"

    # Check SECP keywords
    for kw in SECP_KEYWORDS:
        if clean_str(kw) in norm_filename:
            return "SECP"

    print(f"Warning: Unknown issuing body for file: '{filename}'")
    return "Unknown"


def extract_version_date(first_page_text: Optional[str]) -> Optional[str]:
    """
    Extracts version/amendment date from the first page text using regex patterns
    such as 'amended upto DD.MM.YYYY' / 'DD-MM-YYYY' patterns (case-insensitive),
    or text dates like 'AMENDED UPTO 30TH JUNE, 2026'. Returns None if not found.
    """
    if not first_page_text:
        return None

    # Match 'amended upto DD.MM.YYYY' / 'DD-MM-YYYY' or 'amended upto DD Month, YYYY'
    pattern = (
        r"(?:amended|updated)\s*(?:up\s*to|upto)[:\s]*"
        r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4}|\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})"
    )
    match = re.search(pattern, first_page_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Numeric date pattern (DD.MM.YYYY or DD-MM-YYYY)
    date_match = re.search(r"\b(\d{1,2}[.\-]\d{1,2}[.\-]\d{4})\b", first_page_text)
    if date_match:
        return date_match.group(1).strip()

    return None


def extract_clean_section(header_text: Optional[str]) -> Optional[str]:
    """
    Given a markdown header string like '## Section 113. Minimum tax on turnover',
    extracts the clean citation-ready section label (e.g. 'Section 113') via regex.
    Returns None if no standard section/rule/regulation identifier is present.
    """
    if not header_text:
        return None

    # Strip markdown header hashes and outer whitespace
    cleaned = re.sub(r"^#+\s*", "", header_text).strip()

    # Match patterns like:
    # 'Section 113', 'Section 113A', 'Section 113(1)', 'Rule 12', 'Regulation 4', 'Clause 5', 'Article 3', 'Schedule 3'
    pattern = (
        r"\b(Section|Sec\.|Rule|Regulation|Reg\.|Clause|Article|Schedule)\s+"
        r"([0-9]+[A-Za-z]*(?:\([0-9A-Za-z]+\))*|[IVXLCDM]+|[0-9]+)\b"
    )
    match = re.search(pattern, cleaned, re.IGNORECASE)
    if match:
        unit_type = match.group(1).strip()
        # Canonicalize unit prefix
        if unit_type.lower().startswith("sec"):
            prefix = "Section"
        elif unit_type.lower().startswith("reg"):
            prefix = "Regulation"
        else:
            prefix = unit_type.capitalize()

        unit_number = match.group(2).strip()
        return f"{prefix} {unit_number}"

    return None
