import json
import time
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests


URL = "https://service.eop.bg/NX1Service.svc/GetPublishedTendersBySpecified"

PAYLOAD = {
    "searchParameters": {
        "StartIndex": 1,
        "EndIndex": 1000,
        "PropertyFilters": [],
        "SearchText": "",
        "SearchProperty": {
            "PropertyDisplayName": "str_Today_opened",
            "PropertyName": "Status",
            "PropertyValue": "1"
        },
        "OrderAscending": False,
        "OrderColumn": "PublicationDate",
        "Keywords": []
    }
}

DATE_PATTERN = re.compile(r"/Date\((\d+)\)/")
TAG_PATTERN = re.compile(r"<[^>]+>")


def wcf_date_to_iso(value: str) -> Optional[str]:
    if not isinstance(value, str):
        return None

    match = DATE_PATTERN.search(value)
    if not match:
        return None

    millis = int(match.group(1))
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()


def clean_html_text(text: str) -> str:
    text = html.unescape(text)
    text = TAG_PATTERN.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_clean_and_store():
    print("➡ Starting download...")

    r = requests.post(URL, json=PAYLOAD)
    r.raise_for_status()

    data = r.json()
    records = data.get("CurrentPageResults", [])

    print(f"✅ Downloaded {len(records)} records")

    cleaned = []
    for rec in records:
        rec["TenderName"] = clean_html_text(rec.get("TenderName", ""))
        rec["TenderDescription"] = clean_html_text(rec.get("TenderDescription", ""))

        for d in ("CreatedDate", "ModifiedDate", "PublicationDate", "Deadline"):
            iso = wcf_date_to_iso(rec.get(d))
            if iso:
                rec[d] = iso

        cleaned.append(rec)

    epoch = int(time.time())
    output_path = Path.home() / f"{epoch}-cais-data.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"✅ File created: {output_path}")


if __name__ == "__main__":
    fetch_clean_and_store()