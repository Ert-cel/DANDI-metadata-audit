from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Iterable

from .config import MULTIPLE_VALUES, NOT_REPORTED


def safe_value(value: Any) -> Any:
    if value is None:
        return NOT_REPORTED
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            value = value.strip()
            return value or NOT_REPORTED
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if item is not None]
        return "; ".join(item for item in items if item) or NOT_REPORTED
    return str(value)


def raw_value(value: Any) -> Any:
    value = safe_value(value)
    return None if value == NOT_REPORTED else value


def get_attribute(obj: Any, attribute: str) -> Any:
    if obj is None:
        return None
    return raw_value(getattr(obj, attribute, None))


def container_names(container: Any) -> list[str]:
    if container is None:
        return []
    try:
        return [str(name) for name in container.keys()]
    except (AttributeError, TypeError):
        return []


def unique_nonempty(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value is None:
            continue
        pieces = value.split(";") if isinstance(value, str) else [str(value)]
        for piece in pieces:
            piece = piece.strip()
            if not piece or piece.casefold() in {"none", "nan", "not reported", "n/a"}:
                continue
            key = piece.casefold()
            if key not in seen:
                seen.add(key)
                output.append(piece)
    return output


def consensus(values: Iterable[Any]) -> str:
    unique = unique_nonempty(values)
    if not unique:
        return NOT_REPORTED
    if len(unique) == 1:
        return unique[0]
    if len(unique) <= 4:
        return "; ".join(unique)
    return MULTIPLE_VALUES


def normalize_field_name(name: Any) -> str:
    if name is None:
        return ""
    text = str(name).strip().lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("e.g.", " ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def flatten_json(value: Any, prefix: str = "", rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if rows is None:
        rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flatten_json(child, path, rows)
    elif isinstance(value, list):
        if not value:
            rows.append({"source_path": prefix, "value": None})
        else:
            for index, child in enumerate(value):
                flatten_json(child, f"{prefix}[{index}]", rows)
    else:
        rows.append({"source_path": prefix, "value": value})
    return rows


def recursively_find_dois(value: Any) -> list[str]:
    text = json.dumps(value, default=str)
    matches = re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, flags=re.IGNORECASE)
    output: list[str] = []
    for match in matches:
        doi = match.rstrip(".,;)]}\"")
        if doi.casefold() not in {item.casefold() for item in output}:
            output.append(doi)
    return output
