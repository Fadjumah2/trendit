"""
Deterministic validator for LLM-drafted GBP posts. Runs AFTER the LLM draft
and BEFORE the MCP create_local_post/update_local_post tool is ever called.

Deliberately not another LLM call — char counts, regex, enum checks, and
required-field checks are cheap, fast, and 100% reproducible. Keeping this
non-LLM is what makes "auto-fix or flag for owner edit" trustworthy.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "agent" / "policy_rules.json"
_RULES = json.loads(_RULES_PATH.read_text())

_URL_RE = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_RE = re.compile(r"(\+?\d[\d\-\.\s]{7,}\d)")


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    auto_fixed_fields: list[str] = field(default_factory=list)
    fixed_content: dict | None = None


def validate_post(post_type: str, content: dict) -> ValidationResult:
    """
    content shape (from LLM draft), e.g.:
    {
      "title": "...",
      "body": "...",
      "cta": "BOOK",
      "event_start": "2026-08-01T00:00:00Z",   # event/offer only
      "event_end": "2026-08-03T00:00:00Z",
      "coupon_code": "SUMMER10",                # offer only
      "redemption_link_or_instructions": "...",
      "media_urls": ["https://..."]
    }
    """
    if post_type not in _RULES:
        return ValidationResult(passed=False, errors=[f"Unknown post_type '{post_type}'"])

    errors: list[str] = []
    auto_fixed: list[str] = []
    fixed = dict(content)  # working copy for auto-fixes

    common = _RULES["common"]
    type_rules = _RULES[post_type]

    # --- required fields ---
    for req_field in type_rules.get("required_fields", []):
        if not fixed.get(req_field):
            errors.append(f"Missing required field: {req_field}")

    # --- title length ---
    title = fixed.get("title", "") or ""
    if len(title) > common["title_max_chars"]:
        fixed["title"] = title[: common["title_max_chars"]].rstrip()
        auto_fixed.append("title")

    # --- description/body length ---
    body = fixed.get("body", "") or ""
    if len(body) > common["description_max_chars"]:
        errors.append(
            f"Body exceeds hard max of {common['description_max_chars']} chars "
            f"({len(body)} chars) — needs a rewrite, not a truncation."
        )
    elif len(body) > common["description_ideal_max_chars"]:
        # Not an error — Maps truncates early, but this is a soft warning only.
        auto_fixed.append("body_over_ideal_length_warning")

    # --- forbidden content: URLs, emails, phone numbers in body ---
    if _URL_RE.search(body):
        errors.append("Body contains a URL — use the CTA link field instead.")
    if _EMAIL_RE.search(body):
        errors.append("Body contains an email address — not allowed in post body.")
    if _PHONE_RE.search(body):
        errors.append("Body appears to contain a phone number — not allowed in post body.")

    # --- CTA enum check ---
    cta = fixed.get("cta")
    if cta and cta not in common["cta_enum"]:
        errors.append(f"CTA '{cta}' not in allowed enum: {common['cta_enum']}")

    # --- event/offer date fields ---
    if post_type in ("event", "offer"):
        start, end = fixed.get("event_start"), fixed.get("event_end")
        if start and end and start >= end:
            errors.append("event_start must be before event_end")

    # --- images (only checks metadata the caller provides — actual pixel
    #     dimension check happens where the image bytes are available,
    #     e.g. at upload time, not here) ---
    for url in fixed.get("media_urls", []) or []:
        if not url.lower().endswith((".jpg", ".jpeg")):
            errors.append(f"Image '{url}' is not a .jpg — required format only.")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        auto_fixed_fields=auto_fixed,
        fixed_content=fixed if auto_fixed else None,
    )
