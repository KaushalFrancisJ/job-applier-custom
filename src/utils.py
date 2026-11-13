"""
Text and Unicode sanitization utilities.
Ensures pitch notes, screening answers, and JSON database records
use clean standard ASCII punctuation without curly quotes, em-dashes,
or escaped Unicode sequences (like \\u2019).
"""
from typing import Optional


def sanitize_unicode(text: Optional[str]) -> Optional[str]:
    """
    Normalizes typographic Unicode characters (curly quotes, dashes, non-breaking spaces)
    into standard ASCII counterparts.
    """
    if not text or not isinstance(text, str):
        return text

    # Handle raw escaped string representations if present
    if r"\u2019" in text:
        text = text.replace(r"\u2019", "'")
    if r"\u2018" in text:
        text = text.replace(r"\u2018", "'")
    if r"\u201c" in text:
        text = text.replace(r"\u201c", '"')
    if r"\u201d" in text:
        text = text.replace(r"\u201d", '"')
    if r"\u2013" in text:
        text = text.replace(r"\u2013", "-")
    if r"\u2014" in text:
        text = text.replace(r"\u2014", "-")
    if r"\u2026" in text:
        text = text.replace(r"\u2026", "...")

    # Unicode character mapping
    replacements = {
        "\u2019": "'",   # ’ Right single quote / curly apostrophe
        "\u2018": "'",   # ‘ Left single quote
        "\u201a": "'",   # ‚ Low single quote
        "\u201b": "'",   # ‛ High-reversed single quote
        "\u201c": '"',   # “ Left double quote
        "\u201d": '"',   # ” Right double quote
        "\u201e": '"',   # „ Low double quote
        "\u201f": '"',   # ‟ High-reversed double quote
        "\u0060": "'",   # ` Backtick (when used as single quote)
        "\u00b4": "'",   # ´ Acute accent
        "\u2013": "-",   # – En-dash
        "\u2014": "-",   # — Em-dash
        "\u2026": "...", # … Ellipsis
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # Byte order mark
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return text
