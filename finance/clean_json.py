import json
import re
import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional



DATE_PATTERN = re.compile(r"/Date\((\d+)\)/")
TAG_PATTERN = re.compile(r"<[^>]+>")


def wcf_date_to_iso(value: str) -> Optional[str]:
    """
    Convert /Date(1776460630493)/ to ISO-8601 UTC string.
    """
    if not isinstance(value, str):
        return None

    match = DATE_PATTERN.search(value)
    if not match:
        return None

    millis = int(match.group(1))
    dt = datetime.fromtimestamp(millis / 1000, tz=timezone.utc)
    return dt.isoformat()


def clean_html_text(text: str) -> str:
    """
    Decode HTML entities, remove tags, normalize whitespace.
    """
    if not isinstance(text, str):
        return text

    # Decode HTML entities (&lt;, &amp;, &bdquo;, etc.)
    text = html.unescape(text)

    # Remove HTML tags
    text = TAG_PATTERN.sub(" ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a single tender record.
    """
    cleaned = dict(record)

    # Clean text fields
    for field in ("TenderName", "TenderDescription", "OrganizationName"):
        if field in cleaned:
            cleaned[field] = clean_html_text(cleaned[field])

    # Convert date fields
    for field in ("CreatedDate", "ModifiedDate", "PublicationDate", "Deadline"):
        if field in cleaned:
            iso_date = wcf_date_to_iso(cleaned[field])
            if iso_date:
                cleaned[field] = iso_date

    return cleaned


def clean_json(input_path: str, output_path: str) -> None:
    """
    Load JSON array, clean all records, save cleaned JSON.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    cleaned_data = [clean_record(item) for item in data]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    clean_json("/Users/I741614/testCais.json", "/Users/I741614/testCais-clean.json")