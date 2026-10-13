from __future__ import annotations

from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup

from ..config import AuditConfig
from ..models import Evidence
from .narrative import extract_narrative_evidence


def _headers(config: AuditConfig) -> dict[str, str]:
    return {"User-Agent": "DANDI-Metadata-Audit-Core/1.4"}


def fetch_curated_record(config: AuditConfig) -> tuple[dict[str, Any], list[Evidence]]:
    """Read the curated ASAP dataset metadata used by the CatalystNeuro usage page."""
    try:
        response = requests.get(
            config.catalyst_datasets_url,
            headers=_headers(config),
            timeout=config.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = yaml.safe_load(response.text) or {}
        datasets = payload.get("datasets", []) if isinstance(payload, dict) else []
    except Exception as exc:
        print(f"CatalystNeuro metadata warning: {type(exc).__name__}: {exc}")
        return {}, []

    for row in datasets:
        if str(row.get("id", "")).zfill(6) != config.dandiset_id:
            continue
        record = {
            "Dandiset ID": config.dandiset_id,
            "PI": row.get("pi", ""),
            "Catalyst Modality": row.get("modality", ""),
            "Brain Region": row.get("region", ""),
            "Species": row.get("species", ""),
            "Year": row.get("year", ""),
            "Dataset Status": row.get("status", ""),
            "Release Date": row.get("release", ""),
            "Source": config.catalyst_datasets_url,
        }
        evidence = []
        if record["Species"]:
            evidence.append(Evidence(
                audit_field="species",
                value=record["Species"],
                source_type="CatalystNeuro curated dataset metadata",
                source_location=config.catalyst_datasets_url,
                confidence="High",
                review_status="Structured Evidence",
            ))
        return record, evidence
    return {}, []


def extract_confirmed_pages(config: AuditConfig) -> tuple[list[dict[str, Any]], list[Evidence]]:
    """Read only CatalystNeuro pages explicitly supplied by the user.

    There is deliberately no search/discovery step in the core engine. A page is
    treated as confirmed only when it is supplied with --catalyst-url.
    """
    rows: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    for url in config.catalyst_urls:
        print(f"Reading confirmed CatalystNeuro page: {url}")
        try:
            response = requests.get(url, headers=_headers(config), timeout=config.request_timeout_seconds)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()
            text = " ".join(soup.get_text(" ").split())
            title = soup.title.get_text(strip=True) if soup.title else ""
            rows.append({
                "Dandiset ID": config.dandiset_id,
                "URL": url,
                "Title": title,
                "Status": "Success",
                "Characters": len(text),
            })
            evidence.extend(extract_narrative_evidence(
                text=text,
                source_type="Confirmed CatalystNeuro page",
                source_location=url,
            ))
        except Exception as exc:
            rows.append({
                "Dandiset ID": config.dandiset_id,
                "URL": url,
                "Title": "",
                "Status": "Failed",
                "Characters": 0,
                "Error": f"{type(exc).__name__}: {exc}",
            })
    return rows, evidence
