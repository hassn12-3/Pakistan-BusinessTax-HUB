"""
Statutory Tax Calculator Module for Legal Research Assistant
Based on the Pakistan Income Tax Ordinance, 2001 and Finance Act 2024-2026.

Features deterministic calculations for:
- Salaried Individuals (Division I, Part I, First Schedule)
- Non-Salaried / Business Individuals & AOPs (Division I, Part I, First Schedule)
- Super Tax on High-Earning Persons (Section 4C)
- Surcharge on High Earners (Finance Act 2024, Section 4AB)
"""

import re
from typing import Dict, Any, Optional, Tuple


def parse_currency_amount(text: str) -> Optional[float]:
    """
    Extracts numerical values from natural language expressions like:
      - '25 crore' / '25 cr' -> 250,000,000
      - '50 lakh' / '50 lacs' -> 5,000,000
      - '150 million' / '150M' -> 150,000,000
      - '1.5 billion' -> 1,500,000,000
      - '48k' -> 48,000
      - 'Rs. 4,500,000' -> 4,500,000
    """
    if not text:
        return None

    cleaned = text.lower().replace(",", "").strip()

    # Ignore statutory section numbers, rules, years, and acts
    # e.g., "Section 153", "Sec 122", "Rule 76", "Act 2017", "Year 2024"
    scrubbed = re.sub(r"\b(?:section|sec\.?|rule|page|year|act|schedule|dated?)\s*\d+\b", "", cleaned)

    # Pattern for expressions like: 25 crore, 2.5 billion, 150 million, 50 lakh, 48k
    word_multipliers = [
        (r"(\d+(?:\.\d+)?)\s*(?:billion|arab|b)\b", 1_000_000_000),
        (r"(\d+(?:\.\d+)?)\s*(?:crore|cr)\b", 10_000_000),
        (r"(\d+(?:\.\d+)?)\s*(?:million|m)\b", 1_000_000),
        (r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\b", 100_000),
        (r"(\d+(?:\.\d+)?)\s*(?:thousand|k)\b", 1_000),
    ]

    for pattern, mult in word_multipliers:
        m = re.search(pattern, scrubbed)
        if m:
            try:
                val = float(m.group(1)) * mult
                return val
            except ValueError:
                continue

    # Explicit currency prefix like Rs. 5000000 or PKR 5000000
    m_pkr = re.search(r"(?:rs\.?|pkr|rupees)\s*(\d+(?:\.\d+)?)", scrubbed)
    if m_pkr:
        try:
            return float(m_pkr.group(1))
        except ValueError:
            pass

    # Bare numbers: Only treat as currency amount if >= 10,000 (tax threshold starts at 600k)
    m_num = re.search(r"\b(\d{5,}(?:\.\d+)?)\b", scrubbed)
    if m_num:
        try:
            val = float(m_num.group(1))
            if val not in [2021, 2022, 2023, 2024, 2025, 2026]:
                return val
        except ValueError:
            pass

    return None


def calculate_salaried_tax(annual_income: float) -> Tuple[float, str]:
    """
    Salaried Tax Slabs (Pakistan Finance Act 2024/2026, Division I, Part I, First Schedule)
    """
    if annual_income <= 600_000:
        return 0.0, "Up to Rs. 600,000: 0% (Exempt)"
    elif annual_income <= 1_200_000:
        tax = (annual_income - 600_000) * 0.05
        return tax, "Rs. 600,001 to Rs. 1,200,000: 5% of amount exceeding Rs. 600,000"
    elif annual_income <= 2_200_000:
        tax = 30_000 + (annual_income - 1_200_000) * 0.15
        return tax, "Rs. 1,200,001 to Rs. 2,200,000: Rs. 30,000 + 15% exceeding Rs. 1,200,000"
    elif annual_income <= 3_200_000:
        tax = 180_000 + (annual_income - 2_200_000) * 0.25
        return tax, "Rs. 2,200,001 to Rs. 3,200,000: Rs. 180,000 + 25% exceeding Rs. 2,200,000"
    elif annual_income <= 4_100_000:
        tax = 430_000 + (annual_income - 3_200_000) * 0.30
        return tax, "Rs. 3,200,001 to Rs. 4,100,000: Rs. 430,000 + 30% exceeding Rs. 3,200,000"
    else:
        tax = 700_000 + (annual_income - 4_100_000) * 0.35
        return tax, "Exceeding Rs. 4,100,000: Rs. 700,000 + 35% exceeding Rs. 4,100,000"


def calculate_business_tax(annual_income: float) -> Tuple[float, str]:
    """
    Non-Salaried / Business Individuals & AOP Slabs (Division I, Part I, First Schedule)
    """
    if annual_income <= 600_000:
        return 0.0, "Up to Rs. 600,000: 0% (Exempt)"
    elif annual_income <= 1_200_000:
        tax = (annual_income - 600_000) * 0.15
        return tax, "Rs. 600,001 to Rs. 1,200,000: 15% exceeding Rs. 600,000"
    elif annual_income <= 1_600_000:
        tax = 90_000 + (annual_income - 1_200_000) * 0.20
        return tax, "Rs. 1,200,001 to Rs. 1,600,000: Rs. 90,000 + 20% exceeding Rs. 1,200,000"
    elif annual_income <= 3_200_000:
        tax = 170_000 + (annual_income - 1_600_000) * 0.30
        return tax, "Rs. 1,600,001 to Rs. 3,200,000: Rs. 170,000 + 30% exceeding Rs. 1,600,000"
    elif annual_income <= 5_600_000:
        tax = 650_000 + (annual_income - 3_200_000) * 0.40
        return tax, "Rs. 3,200,001 to Rs. 5,600,000: Rs. 650,000 + 40% exceeding Rs. 3,200,000"
    else:
        tax = 1_610_000 + (annual_income - 5_600_000) * 0.45
        return tax, "Exceeding Rs. 5,600,000: Rs. 1,610,000 + 45% exceeding Rs. 5,600,000"


def calculate_super_tax_4c(annual_income: float) -> Tuple[float, float, str]:
    """
    Super Tax on High-Earning Persons under Section 4C of Income Tax Ordinance 2001
    Applicable if taxable income > Rs. 150 Million.
    Returns: (super_tax_amount, rate_percentage, description)
    """
    if annual_income <= 150_000_000:
        return 0.0, 0.0, "Below Rs. 150M threshold (Section 4C exempt)"
    elif annual_income <= 200_000_000:
        rate = 0.01
        tax = annual_income * rate
        return tax, 1.0, "Section 4C (Rs. 150M - 200M): 1% of income"
    elif annual_income <= 250_000_000:
        rate = 0.02
        tax = annual_income * rate
        return tax, 2.0, "Section 4C (Rs. 200M - 250M): 2% of income"
    elif annual_income <= 300_000_000:
        rate = 0.03
        tax = annual_income * rate
        return tax, 3.0, "Section 4C (Rs. 250M - 300M): 3% of income"
    elif annual_income <= 350_000_000:
        rate = 0.04
        tax = annual_income * rate
        return tax, 4.0, "Section 4C (Rs. 300M - 350M): 4% of income"
    elif annual_income <= 400_000_000:
        rate = 0.06
        tax = annual_income * rate
        return tax, 6.0, "Section 4C (Rs. 350M - 400M): 6% of income"
    elif annual_income <= 500_000_000:
        rate = 0.08
        tax = annual_income * rate
        return tax, 8.0, "Section 4C (Rs. 400M - 500M): 8% of income"
    else:
        rate = 0.10
        tax = annual_income * rate
        return tax, 10.0, "Section 4C (Exceeding Rs. 500M): 10% of income"


def calculate_corporate_tax(taxable_income: float) -> Tuple[float, str]:
    """Corporate Tax rate (29% for general companies under Division II, Part II, First Schedule)."""
    rate = 0.29
    tax = taxable_income * rate
    return tax, "Section 4 / Division II, Part II: 29% flat corporate tax rate"


def calculate_pakistan_tax(
    income: float,
    category: str = "salaried",
    tax_year: str = "2024-2025",
    is_monthly: bool = False,
    deductions: float = 0.0,
    advance_tax_paid: float = 0.0,
) -> Dict[str, Any]:
    """
    Main deterministic calculation engine for Pakistan Income Tax.
    Supports Salaried, Business / AOP, and Corporate entities with deductions and advance tax.
    """
    if is_monthly:
        annual_gross = income * 12.0
    else:
        annual_gross = income

    # Taxable income after allowable deductions
    taxable_income = max(0.0, annual_gross - deductions)
    monthly_income = taxable_income / 12.0

    cat = category.lower().strip()
    is_corporate = "company" in cat or "corp" in cat or "pvt" in cat
    is_salaried = not is_corporate and "non" not in cat and ("salaried" in cat or "salary" in cat or "individual" in cat or cat == "")

    if is_corporate:
        base_tax, slab_desc = calculate_corporate_tax(taxable_income)
        statutory_ref = "First Schedule, Part II, Division II (Corporate Rate: 29%)"
        cat_label = "Private Limited Company"
    elif is_salaried:
        base_tax, slab_desc = calculate_salaried_tax(taxable_income)
        statutory_ref = "First Schedule, Part I, Division I (Salaried Individuals)"
        cat_label = "Salaried Individual"
    else:
        base_tax, slab_desc = calculate_business_tax(taxable_income)
        statutory_ref = "First Schedule, Part I, Division I (Business Individuals / AOPs)"
        cat_label = "Business Individual / AOP"

    # Surcharge on High Income: 10% of income tax if taxable income > Rs. 10M
    surcharge = 0.0
    surcharge_desc = "Not applicable (Income ≤ Rs. 10M)"
    if taxable_income > 10_000_000 and not is_corporate:
        surcharge = base_tax * 0.10
        surcharge_desc = "10% Surcharge on income tax payable (Finance Act 2024, Income > Rs. 10M)"

    # Super Tax under Section 4C for heavy/high-bracket income (> Rs. 150M)
    super_tax, super_tax_rate, super_tax_desc = calculate_super_tax_4c(taxable_income)

    total_annual_tax = base_tax + surcharge + super_tax
    net_tax_payable = max(0.0, total_annual_tax - advance_tax_paid)
    total_monthly_tax = total_annual_tax / 12.0

    effective_tax_rate = (total_annual_tax / taxable_income * 100.0) if taxable_income > 0 else 0.0
    net_annual_take_home = taxable_income - total_annual_tax
    net_monthly_take_home = net_annual_take_home / 12.0

    return {
        "gross_income": annual_gross,
        "deductions": deductions,
        "annual_income": taxable_income,
        "monthly_income": monthly_income,
        "category": cat_label,
        "tax_year": tax_year,
        "slab_description": slab_desc,
        "statutory_reference": statutory_ref,
        "base_tax": base_tax,
        "surcharge": surcharge,
        "surcharge_description": surcharge_desc,
        "super_tax_4c": super_tax,
        "super_tax_rate_pct": super_tax_rate,
        "super_tax_description": super_tax_desc,
        "total_annual_tax": total_annual_tax,
        "advance_tax_paid": advance_tax_paid,
        "net_tax_payable": net_tax_payable,
        "total_monthly_tax": total_monthly_tax,
        "effective_tax_rate_pct": round(effective_tax_rate, 2),
        "net_annual_income": net_annual_take_home,
        "net_monthly_income": net_monthly_take_home,
        # Formatted string fields for immediate UI/Markdown display
        "formatted": {
            "gross_income": f"PKR {annual_gross:,.0f}",
            "deductions": f"PKR {deductions:,.0f}",
            "annual_income": f"PKR {taxable_income:,.0f}",
            "monthly_income": f"PKR {monthly_income:,.0f}",
            "base_tax": f"PKR {base_tax:,.0f}",
            "surcharge": f"PKR {surcharge:,.0f}",
            "super_tax_4c": f"PKR {super_tax:,.0f}",
            "total_annual_tax": f"PKR {total_annual_tax:,.0f}",
            "advance_tax_paid": f"PKR {advance_tax_paid:,.0f}",
            "net_tax_payable": f"PKR {net_tax_payable:,.0f}",
            "total_monthly_tax": f"PKR {total_monthly_tax:,.0f}",
            "net_monthly_income": f"PKR {net_monthly_take_home:,.0f}",
            "effective_tax_rate": f"{effective_tax_rate:.2f}%",
        },
    }


def generate_tax_advisory_memo(calc_data: Dict[str, Any], business_type: str = "Corporate") -> str:
    """
    Generates strategic legal and tax mitigation commentary via Gemini.
    """
    from app.config import GEMINI_MODEL
    from app.generation.llm_client import get_genai_client
    from google.genai import types

    fmt = calc_data.get("formatted", {})
    prompt = f"""You are a senior Pakistani tax advocate and corporate legal counsel.
Provide a concise, professional 3-4 bullet Legal & Tax Advisory Memorandum for this taxpayer:
- Entity Type: {calc_data.get('category')}
- Tax Year: {calc_data.get('tax_year')}
- Gross Taxable Income: {fmt.get('annual_income')}
- Total Statutory Tax: {fmt.get('total_annual_tax')}
- Base Tax Slab: {calc_data.get('slab_description')}
- Super Tax (Sec 4C): {fmt.get('super_tax_4c')} ({calc_data.get('super_tax_rate_pct')}%)
- Advance Tax Deducted (WHT): {fmt.get('advance_tax_paid')}
- Net Tax Payable: {fmt.get('net_tax_payable')}

Include:
1. Statutory compliance requirement (Advance tax quarterly deadlines under Section 147, return filing under Section 114).
2. Super Tax (Section 4C) or Surcharge legal implications and case law status (if applicable).
3. Legitimate tax credits, depreciation allowances, or Second Schedule exemptions to reduce future liability.
4. Record maintenance to prevent Section 122/177 audit notices by CIR.

Format as clean bullet points without markdown headers or emojis. Keep it authoritative and boardroom ready."""

    try:
        client = get_genai_client()
        res = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return res.text.strip()
    except Exception as e:
        return (
            "1. Advance Tax Compliance: Ensure quarterly payment of advance tax under Section 147 of the Income Tax Ordinance, 2001.\n"
            "2. Super Tax (Section 4C): High earning individuals and companies are subject to progressive super tax rates payable at return filing.\n"
            "3. Withholding Reconciliation: Reconcile all tax deduction certificates (CPR/Iris) to adjust against net tax payable.\n"
            "4. Audit Readiness: Maintain audited financial statements and verifiable expenditure receipts to substantiate deductions."
        )

