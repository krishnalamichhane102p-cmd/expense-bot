# ============================================
# parser.py — Smart Expense Text Parser
# ============================================
import re
from config import CATEGORY_KEYWORDS, DEFAULT_CATEGORY

def parse_expense(text: str) -> dict | None:
    """
    Parse a free-text expense message.

    Supported formats:
      "Coffee 3.50"
      "lunch 12"
      "Uber ride 8.75"
      "bought shoes 45.00"
      "3.50 coffee"          ← amount first also works
      "/add coffee 3.50"     ← with command prefix

    Returns:
      {"description": str, "amount": float, "category": str}
      or None if parsing fails.
    """
    # Strip command prefix if present
    text = re.sub(r"^/add\s*", "", text.strip(), flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return None

    # ── Pattern 1: "Description Amount"  e.g. "Coffee 3.50"
    match = re.match(r"^(.+?)\s+([\d]+(?:[.,]\d{1,2})?)$", text)
    if match:
        description = match.group(1).strip()
        amount_str  = match.group(2).replace(",", ".")
        try:
            amount = float(amount_str)
            if amount <= 0:
                return None
            return {
                "description": description,
                "amount":      amount,
                "category":    detect_category(description),
            }
        except ValueError:
            pass

    # ── Pattern 2: "Amount Description"  e.g. "3.50 coffee"
    match = re.match(r"^([\d]+(?:[.,]\d{1,2})?)\s+(.+)$", text)
    if match:
        amount_str  = match.group(1).replace(",", ".")
        description = match.group(2).strip()
        try:
            amount = float(amount_str)
            if amount <= 0:
                return None
            return {
                "description": description,
                "amount":      amount,
                "category":    detect_category(description),
            }
        except ValueError:
            pass

    return None   # Could not parse


def detect_category(description: str) -> str:
    """Match description keywords to a category."""
    lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return DEFAULT_CATEGORY


def format_amount(amount: float, currency: str = "$") -> str:
    """Format a float as a currency string."""
    return f"{currency}{amount:,.2f}"
