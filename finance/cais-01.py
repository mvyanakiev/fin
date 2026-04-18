import json
import time
from pathlib import Path

import requests


URL = "https://service.eop.bg/NX1Service.svc/GetPublishedTendersBySpecified"

HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
}

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


def fetch_and_store():
    # 1. POST request
    response = requests.post(URL, headers=HEADERS, json=PAYLOAD)
    response.raise_for_status()

    # 2. Parse JSON
    raw_data = response.json()

    # 3. Extract ONLY CurrentPageResults
    if "CurrentPageResults" not in raw_data:
        raise ValueError("Expected key 'CurrentPageResults' not found in response")

    cleaned_data = raw_data["CurrentPageResults"]

    # 4. Generate filename
    epoch_time = int(time.time())
    filename = f"{epoch_time}-cais–data.json"

    # 5. Write to user home directory
    output_path = Path.home() / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(cleaned_data)} records to:")
    print(f"   {output_path}")


if __name__ == "__main__":
    fetch_and_store()