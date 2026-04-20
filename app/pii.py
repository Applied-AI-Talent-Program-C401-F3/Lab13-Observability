from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    # email must include + for plus-addressing (devops+alerts@domain.com)
    "email": r"[\w.+\-]+@[\w.-]+\.\w+",
    "phone_vn": r"(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}",
    # credit_card before cccd: prevent 12-digit prefix from masking a 16-digit card
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "cccd": r"\b\d{12}\b",
    "passport": r"\b[A-Z]\d{7,8}\b",
    "address_vn": r"\b(?:đường|phố|quận|huyện|phường|xã|thành\s+phố|tỉnh)\b",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    # catch-all: any @ surviving pattern matching (e.g. SQL %@%, template vars)
    # is still a PII indicator and must not appear in logs
    safe = re.sub(r"@", "[REDACTED_AT]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
