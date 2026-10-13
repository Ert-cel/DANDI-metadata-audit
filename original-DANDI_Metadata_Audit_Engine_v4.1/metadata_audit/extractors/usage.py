from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen

from ..config import AuditConfig


def _number(value: Any) -> float | int | str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if text.startswith("<"):
        return text
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return text


def extract_usage_summary(config: AuditConfig) -> list[dict[str, Any]]:
    """Retrieve only the headline DANDI access statistics used in the core workbook."""
    try:
        request = Request(config.usage_summaries_url, headers={"User-Agent": "DANDI-Metadata-Audit-Core/1.4"})
        with urlopen(request, timeout=config.request_timeout_seconds) as response:
            archive_bytes = response.read()
        totals_bytes = None
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.name.removeprefix("content/") == "totals.json" and member.isfile():
                    handle = archive.extractfile(member)
                    totals_bytes = handle.read() if handle else None
                    break
        totals = json.loads(totals_bytes.decode("utf-8")) if totals_bytes else {}
    except Exception as exc:
        print(f"Usage statistics warning: {type(exc).__name__}: {exc}")
        return [{
            "Dandiset ID": config.dandiset_id,
            "Statistics Status": "Unavailable",
            "Statistics Source": config.usage_summaries_url,
            "Error": f"{type(exc).__name__}: {exc}",
        }]

    summary: dict[str, Any] = {}
    if isinstance(totals, dict):
        summary = totals.get(config.dandiset_id, totals.get(str(config.dandiset_id), {})) or {}
    elif isinstance(totals, list):
        for row in totals:
            if isinstance(row, dict) and str(row.get("dandiset_id", "")).zfill(6) == config.dandiset_id:
                summary = row
                break

    return [{
        "Dandiset ID": config.dandiset_id,
        "Statistics Status": "Available" if summary else "No recorded traffic",
        "Statistics Source": config.usage_summaries_url,
        "Statistics Retrieved": datetime.now().isoformat(timespec="seconds"),
        "Total Bytes Served": _number(summary.get("total_bytes_sent", summary.get("bytes_sent"))),
        "Full Downloads": summary.get("total_number_of_downloads", summary.get("downloads", summary.get("full_downloads", ""))),
        "Total Requests": summary.get("total_number_of_requests", summary.get("requests", "")),
        "Unique Requesters": summary.get("number_of_requesters", summary.get("unique_requesters", "")),
        "Unique Countries": summary.get("number_of_unique_countries", summary.get("unique_countries", "")),
        "Unique Regions": summary.get("number_of_unique_regions", summary.get("unique_regions", "")),
        "Data Size Bytes": _number(summary.get("size", summary.get("dataset_size_bytes"))),
    }]
