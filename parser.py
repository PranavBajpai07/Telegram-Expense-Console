"""Plain-English transaction parser for Telegram expense messages."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


class ParseError(ValueError):
    """Raised when a message cannot be turned into a transaction."""


# Edit these lists to change category behavior. Keep keywords lowercase.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "travel": [
        "ola",
        "uber",
        "rapido",
        "metro",
        "bus",
        "train",
        "flight",
        "cab",
        "auto",
        "petrol",
        "diesel",
        "parking",
        "toll",
    ],
    "food": [
        "swiggy",
        "zomato",
        "dinner",
        "lunch",
        "breakfast",
        "chai",
        "coffee",
        "tea",
        "restaurant",
        "cafe",
        "pizza",
        "burger",
        "biryani",
        "snack",
        "meal",
    ],
    "groceries": [
        "blinkit",
        "zepto",
        "bigbasket",
        "dmart",
        "grocery",
        "groceries",
        "milk",
        "vegetables",
        "veggies",
        "fruit",
        "fruits",
        "kirana",
    ],
    "clothes": [
        "myntra",
        "ajio",
        "shirt",
        "jeans",
        "shoe",
        "shoes",
        "dress",
        "kurta",
        "clothes",
        "clothing",
        "fashion",
    ],
    "rent": [
        "rent",
        "house rent",
        "flat rent",
        "maintenance",
        "deposit",
    ],
    "bills": [
        "bill",
        "bills",
        "electricity",
        "water",
        "wifi",
        "internet",
        "broadband",
        "mobile",
        "phone",
        "gas",
        "cylinder",
        "recharge",
        "dth",
        "emi",
        "subscription",
    ],
    "luxuries": [
        "netflix",
        "prime",
        "spotify",
        "hotstar",
        "gym",
        "movie",
        "movies",
        "cinema",
        "salon",
        "spa",
        "game",
        "games",
        "vacation",
        "holiday",
        "pub",
        "bar",
    ],
    "investments": [
        "sip",
        "mutual fund",
        "mutualfund",
        "etf",
        "stocks",
        "stock",
        "shares",
        "nifty",
        "sensex",
        "ppf",
        "nps",
        "fd",
        "rd",
        "investment",
        "invest",
    ],
    "health": [
        "doctor",
        "hospital",
        "medicine",
        "medicines",
        "pharmacy",
        "apollo",
        "practo",
        "health",
        "clinic",
        "test",
        "scan",
        "dentist",
        "therapy",
    ],
    "education": [
        "course",
        "class",
        "tuition",
        "book",
        "books",
        "school",
        "college",
        "exam",
        "udemy",
        "coursera",
        "education",
        "learning",
    ],
    "other": [],
}

INCOME_KEYWORDS = [
    "salary",
    "refund",
    "cashback",
    "received",
    "credited",
    "credit",
    "income",
    "bonus",
    "reimbursement",
    "reimbursed",
    "paid back",
    "got back",
    "interest",
    "dividend",
]

FILLER_WORDS = {
    "spent",
    "spend",
    "paid",
    "pay",
    "payment",
    "bought",
    "buy",
    "purchase",
    "purchased",
    "on",
    "for",
    "at",
    "to",
    "from",
    "the",
    "a",
    "an",
    "of",
    "my",
    "with",
    "using",
    "via",
    "by",
    "rs",
    "inr",
    "rupee",
    "rupees",
    "got",
}

AMOUNT_RE = re.compile(
    r"""
    (?<![\w.])
    (?:₹\s*|rs\.?\s*|inr\s*)?
    (?P<number>
        (?:\d{1,3}(?:,\d{2,3})+|\d+)
        (?:\.\d+)?
    )
    \s*
    (?P<suffix>k|l|lac|lakh|lakhs|cr|crore|crores)?
    \s*
    (?:rs\.?|inr|rupees?)?
    (?![\w.])
    """,
    re.IGNORECASE | re.VERBOSE,
)

SUFFIX_MULTIPLIERS = {
    "k": Decimal("1000"),
    "l": Decimal("100000"),
    "lac": Decimal("100000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "cr": Decimal("10000000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
}


def parse_message(message: str) -> dict[str, Any]:
    """Parse a Telegram message into amount, category, note, and type."""
    if not message or not message.strip():
        raise ParseError("Message is empty.")

    amount_match = AMOUNT_RE.search(message)
    if not amount_match:
        raise ParseError("I could not find an amount.")

    amount = _parse_amount(amount_match)
    normalized = _normalize_text(message)
    txn_type = "income" if _contains_any(normalized, INCOME_KEYWORDS) else "expense"
    category = _guess_category(normalized)
    note = _build_note(message, amount_match)

    return {
        "amount": _friendly_number(amount),
        "category": category,
        "note": note or category,
        "type": txn_type,
    }


def parse(message: str) -> dict[str, Any]:
    """Small alias for scripts/tests."""
    return parse_message(message)


def _parse_amount(match: re.Match[str]) -> Decimal:
    raw_number = match.group("number").replace(",", "")
    suffix = (match.group("suffix") or "").lower()
    try:
        amount = Decimal(raw_number)
    except InvalidOperation as exc:
        raise ParseError("The amount did not look like a number.") from exc

    amount *= SUFFIX_MULTIPLIERS.get(suffix, Decimal("1"))
    if amount <= 0:
        raise ParseError("Amount must be greater than zero.")
    return amount


def _friendly_number(amount: Decimal) -> int | float:
    if amount == amount.to_integral_value():
        return int(amount)
    return float(amount)


def _guess_category(normalized_text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "other":
            continue
        if _contains_any(normalized_text, keywords):
            return category
    return "other"


def _contains_any(normalized_text: str, keywords: list[str]) -> bool:
    return any(_contains_keyword(normalized_text, keyword) for keyword in keywords)


def _contains_keyword(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = _normalize_text(keyword)
    return re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized_text) is not None


def _build_note(message: str, amount_match: re.Match[str]) -> str:
    without_amount = f"{message[:amount_match.start()]} {message[amount_match.end():]}"
    normalized = _normalize_text(without_amount)
    words = [word for word in normalized.split() if word not in FILLER_WORDS]
    return " ".join(words).strip()


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("₹", " rs ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
