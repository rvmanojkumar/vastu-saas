import re
import unicodedata
from typing import Any, Optional

# XML 1.0 illegal control chars (keep tab, LF, CR)
_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

RULE_TEXT_FIELDS = (
    "title",
    "description_en",
    "description_hi",
    "description_mr",
    "remedy_en",
    "remedy_hi",
    "remedy_mr",
    "sug_remedy_en",
    "sug_remedy_hi",
    "sug_remedy_mr",
    "color",
    "therapy",
    "result",
    "entity_name",
)


def sanitize_rule_text(value: Any) -> Optional[str]:
    """Keep quotes, slashes and punctuation; strip only chars that break XML/PDF/Word."""
    if value is None:
        return None
    text = str(value)
    text = unicodedata.normalize("NFC", text)
    # Curly quotes/dashes still display as quotes/dashes, but are safer for Word XML
    text = (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u00ab", '"')
        .replace("\u00bb", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    text = _ILLEGAL_XML.sub("", text)
    # Neutralize Jinja so admin text cannot break PDF/Word templates
    text = (
        text.replace("{{", "{ {")
        .replace("}}", "} }")
        .replace("{%", "{ %")
        .replace("%}", "% }")
    )
    return text


def sanitize_rule_payload(data: dict) -> dict:
    cleaned = dict(data)
    for key in RULE_TEXT_FIELDS:
        if key in cleaned and cleaned[key] is not None:
            cleaned[key] = sanitize_rule_text(cleaned[key])
    return cleaned


def sanitize_display_text(value: Any) -> str:
    if value is None:
        return ""
    return sanitize_rule_text(value) or ""
