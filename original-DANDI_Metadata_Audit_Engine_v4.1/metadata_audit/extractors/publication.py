from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

from ..config import AuditConfig
from ..models import Evidence
from ..utils import recursively_find_dois, safe_value
from .narrative import extract_narrative_evidence


def _headers(config: AuditConfig) -> dict[str, str]:
    contact = config.contact_email or "metadata-audit@example.org"
    return {"User-Agent": f"DANDI-Metadata-Audit-Core/1.5 (mailto:{contact})"}


def discover_dois(dandiset_metadata: dict[str, Any], nwb_rows: list[dict[str, Any]]) -> list[str]:
    values: list[Any] = [dandiset_metadata]
    values.extend(row.get("related_publications") for row in nwb_rows)
    return recursively_find_dois(values)


def fetch_crossref(config: AuditConfig, doi: str) -> dict[str, Any] | None:
    response = requests.get(
        f"https://api.crossref.org/works/{doi}",
        headers=_headers(config),
        timeout=config.request_timeout_seconds,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("message", {})


def find_pubmed_record(config: AuditConfig, doi: str) -> dict[str, str]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search = requests.get(
        f"{base}/esearch.fcgi",
        params={"db": "pubmed", "term": f'"{doi}"[AID]', "retmode": "json"},
        headers=_headers(config),
        timeout=config.request_timeout_seconds,
    )
    search.raise_for_status()
    ids = search.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return {"pmid": "", "pmcid": ""}
    pmid = ids[0]
    link = requests.get(
        f"{base}/elink.fcgi",
        params={"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"},
        headers=_headers(config),
        timeout=config.request_timeout_seconds,
    )
    link.raise_for_status()
    pmcid = ""
    for linkset in link.json().get("linksets", []):
        for database in linkset.get("linksetdbs", []):
            links = database.get("links", [])
            if links:
                pmcid = f"PMC{links[0]}"
                break
    return {"pmid": pmid, "pmcid": pmcid}


def fetch_pmc_sections(config: AuditConfig, pmcid: str) -> list[dict[str, str]]:
    response = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pmc", "id": pmcid, "rettype": "full", "retmode": "xml"},
        headers=_headers(config),
        timeout=config.request_timeout_seconds,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    sections: list[dict[str, str]] = []
    for section in root.findall(".//sec"):
        title_element = section.find("./title")
        title = "".join(title_element.itertext()).strip() if title_element is not None else "Untitled"
        paragraphs = []
        for paragraph in section.findall("./p"):
            text = " ".join("".join(paragraph.itertext()).split())
            if text:
                paragraphs.append(text)
        if paragraphs:
            sections.append({"section_title": title, "section_text": " ".join(paragraphs)})
    return sections


def _is_methods_section(title: str) -> bool:
    terms = (
        "method", "material", "procedure", "surgery", "electrophysiology", "recording",
        "patch", "in vivo", "in vitro", "optogen", "histology", "behavior", "microscopy",
        "imaging", "animal", "viral", "injection",
    )
    lower = title.lower()
    return any(term in lower for term in terms)


def extract_publications(
    config: AuditConfig,
    dandiset_metadata: dict[str, Any],
    nwb_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Evidence]]:
    records: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    dois = discover_dois(dandiset_metadata, nwb_rows)
    print(f"Found {len(dois)} associated DOI candidate(s).")

    for doi in dois:
        print(f"Checking associated publication: {doi}")
        crossref = None
        pubmed = {"pmid": "", "pmcid": ""}
        error = ""
        try:
            crossref = fetch_crossref(config, doi)
            pubmed = find_pubmed_record(config, doi)
            if pubmed["pmcid"]:
                sections = fetch_pmc_sections(config, pubmed["pmcid"])
                selected_sections = [row for row in sections if _is_methods_section(row["section_title"])] or sections
                # Extract section-by-section so the exact Methods subsection remains attached
                # to every candidate. This is important for distinguishing surgery from
                # perfusion/histology and acquisition from analysis.
                for section in selected_sections:
                    evidence.extend(extract_narrative_evidence(
                        text=section["section_text"],
                        source_type="Confirmed publication methods (PMC)",
                        source_location=f"PMC:{pubmed['pmcid']} — {section['section_title']}",
                        doi=doi,
                        pmid=pubmed["pmid"],
                        pmcid=pubmed["pmcid"],
                    ))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"    Publication lookup warning: {error}")

        title = safe_value(crossref.get("title")) if crossref else "Not Reported"
        records.append({
            "Dandiset ID": config.dandiset_id,
            "DOI": doi,
            "PMID": pubmed.get("pmid", ""),
            "PMCID": pubmed.get("pmcid", ""),
            "Title": title,
            "Publisher": safe_value(crossref.get("publisher")) if crossref else "Not Reported",
            "Lookup Error": error,
        })
    return records, evidence
