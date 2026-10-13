from __future__ import annotations

from typing import Any
from datetime import date, datetime
import json
import gzip
from pathlib import Path

import h5py
import remfile
from pynwb import NWBHDF5IO

from ..config import AuditConfig
from ..processing.mapping import NWB_FIELD_ALIASES
from ..utils import container_names, get_attribute, unique_nonempty

PROPERTY_PREVIEW_LIMIT = 50000


def _plain(value: Any) -> Any:
    """Convert a metadata cell to JSON-compatible values without masking failures."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if hasattr(value, "item"):
        try:
            return _plain(value.item())
        except (ValueError, TypeError):
            pass
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "path") or hasattr(value, "name"):
        path = getattr(value, "path", None) or getattr(value, "name", None)
        if isinstance(path, str):
            return path
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "tolist"):
        return _plain(value.tolist())
    raise TypeError(type(value).__name__)


def _deep_rows(nwbfile: Any, h5_file: Any, did: str, aid: str, apath: str) -> list[dict[str, Any]]:
    """PyNWB table cells plus native HDF5 metadata, including extension fields."""
    rows: list[dict[str, Any]] = []
    base = {"dandiset_id": did, "asset_id": aid, "asset_path": apath}
    for obj in [nwbfile, *nwbfile.all_children()]:
        columns = getattr(obj, "columns", None)
        if columns is None:
            continue
        opath = str(getattr(obj, "path", None) or getattr(obj, "name", ""))
        for col in columns:
            name = str(getattr(col, "name", ""))
            data = getattr(col, "data", None)
            if not name or data is None:
                continue
            if name.lower() in {"spike_times", "waveform_mean", "waveform_sd", "waveforms",
                                "image_mask", "pixel_mask", "voxel_mask", "timestamps", "data"}:
                rows.append({**base, "object_path": opath, "property": name, "value": "",
                             "shape": str(getattr(data, "shape", "")),
                             "evidence_kind": "array inventory", "read_status": "Signal/array values not read"})
                continue
            try:
                count = len(data)
                for start in range(0, count, 1024):
                    chunk = data[start:start + 1024]
                    for offset, value in enumerate(chunk):
                        try:
                            plain = _plain(value)
                            display = plain if isinstance(plain, str) else json.dumps(plain, ensure_ascii=False, allow_nan=False)
                        except (TypeError, ValueError, OverflowError):
                            rows.append({**base, "object_path": opath, "property": name,
                                         "row_index": start + offset, "value": "",
                                         "evidence_kind": "table cell unreadable", "read_status": "Unsupported value"})
                            continue
                        rows.append({**base, "object_path": opath, "property": name,
                                     "row_index": start + offset, "value": display[:32000],
                                     "value_truncated": len(display) > 32000,
                                     "evidence_kind": "NWB table cell", "read_status": "Read"})
            except Exception as exc:
                rows.append({**base, "object_path": opath, "property": name,
                             "value": "", "evidence_kind": "table read error",
                             "read_status": f"{type(exc).__name__}: {exc}"[:500]})

    def visit(path: str, item: Any) -> None:
        if isinstance(item, h5py.Group):
            kind = "NWB group attribute"
        elif isinstance(item, h5py.Dataset):
            kind = "NWB dataset attribute"
            shape = tuple(item.shape)
            # Describe signal payloads instead of reading multi-GB recordings.
            rows.append({**base, "object_path": "/" + path, "property": "[array]",
                         "value": "", "shape": str(shape), "dtype": str(item.dtype),
                         "evidence_kind": "array inventory", "read_status": "Shape/dtype only"})
            if shape == ():
                try:
                    value = _plain(item[()])
                    rows.append({**base, "object_path": "/" + path, "property": "[scalar]",
                                 "value": str(value)[:32000], "evidence_kind": "NWB scalar dataset",
                                 "read_status": "Read"})
                except Exception as exc:
                    rows.append({**base, "object_path": "/" + path, "property": "[scalar]",
                                 "value": "", "evidence_kind": "scalar read error",
                                 "read_status": f"{type(exc).__name__}: {exc}"[:500]})
        else:
            return
        for attr in item.attrs.keys():
            try:
                value = item.attrs[attr]
                if isinstance(value, h5py.Reference):
                    value = h5_file[value].name if value else "Unresolved HDF5 reference"
                if hasattr(value, "tolist"):
                    value = value.tolist()
                plain = _plain(value)
                serialized = plain if isinstance(plain, str) else json.dumps(plain, ensure_ascii=False, allow_nan=False)
                rows.append({**base, "object_path": "/" + path, "property": "@" + str(attr),
                             "value": serialized[:32000], "value_truncated": len(serialized) > 32000,
                             "evidence_kind": kind, "read_status": "Read"})
            except Exception as exc:
                rows.append({**base, "object_path": "/" + path, "property": "@" + str(attr),
                             "value": "", "evidence_kind": "attribute read error",
                             "read_status": f"{type(exc).__name__}: {exc}"[:500]})
    visit("", h5_file)  # visititems excludes attributes on the root group.
    h5_file.visititems(visit)
    return rows


def _properties(nwbfile: Any, dandiset_id: str, asset_id: str, asset_path: str) -> list[dict[str, Any]]:
    """Inventory PyNWB metadata without reading signal arrays or entire tables."""
    rows = []
    seen = set()
    objects = [nwbfile] + list(nwbfile.all_children())
    for obj in objects:
        oid = getattr(obj, "object_id", None) or id(obj)
        if oid in seen:
            continue
        seen.add(oid)
        path = getattr(obj, "path", None) or getattr(obj, "name", "") or "/"
        kind = getattr(obj, "neurodata_type", type(obj).__name__)
        try:
            fields = dict(getattr(obj, "fields", {}) or {})
        except Exception:
            fields = {}
        # Include top-level scalar properties even when a PyNWB version does not
        # expose them in .fields.
        if obj is nwbfile:
            for name in ("identifier", "session_id", "session_start_time", "session_description",
                         "experiment_description", "experimenter", "institution", "lab", "keywords",
                         "related_publications", "protocol", "surgery", "virus", "pharmacology",
                         "data_collection", "notes", "stimulus_notes"):
                fields.setdefault(name, getattr(obj, name, None))
        for name, value in fields.items():
            if value is None:
                continue
            # Containers and datasets are represented by their own object rows;
            # never stringify an array or trigger a remote signal-data read.
            if isinstance(value, (str, int, float, bool, date, datetime)):
                display = str(value)
            elif isinstance(value, (tuple, list)) and len(value) <= 20 and all(
                isinstance(v, (str, int, float, bool)) for v in value
            ):
                display = "; ".join(map(str, value))
            else:
                continue
            if display.strip():
                rows.append({"dandiset_id": dandiset_id, "asset_id": asset_id,
                             "asset_path": asset_path, "object_path": str(path),
                             "neurodata_type": str(kind), "property": str(name),
                             "value": display[:32000], "value_truncated": len(display) > 32000,
                             "evidence_kind": "NWB structured field"})
        # DynamicTable metadata: column names and descriptions, never all rows.
        columns = getattr(obj, "columns", None)
        for col in columns if columns is not None else ():
            name = getattr(col, "name", None)
            if name:
                rows.append({"dandiset_id": dandiset_id, "asset_id": asset_id,
                             "asset_path": asset_path, "object_path": str(path),
                             "neurodata_type": str(kind), "property": "column:" + str(name),
                             "value": str(getattr(col, "description", "") or ""),
                             "evidence_kind": "NWB table column definition"})
    return rows


def _object_row(asset_id: str, asset_path: str, category: str, name: str, obj: Any) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_path": asset_path,
        "object_category": category,
        "object_name": name,
        "neurodata_type": type(obj).__name__,
        "description": get_attribute(obj, "description"),
        "unit": get_attribute(obj, "unit"),
        "rate": get_attribute(obj, "rate"),
        "starting_time": get_attribute(obj, "starting_time"),
        "comments": get_attribute(obj, "comments"),
    }


def _extract_one(asset: Any, disk_cache: Any, dandiset_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    asset_path = str(asset.path)
    asset_id = str(getattr(asset, "identifier", ""))
    url = asset.get_content_url(follow_redirects=1, strip_query=True)
    remote_file = remfile.File(url, disk_cache=disk_cache)
    try:
        with h5py.File(remote_file, mode="r") as h5_file:
            with NWBHDF5IO(file=h5_file, mode="r", load_namespaces=True) as io:
                nwbfile = io.read()
                properties = _properties(nwbfile, dandiset_id, asset_id, asset_path)
                properties.extend(_deep_rows(nwbfile, h5_file, dandiset_id, asset_id, asset_path))
                property_errors = sum("error" in str(p.get("evidence_kind", "")) or
                                      p.get("read_status") == "Unsupported value" for p in properties)
                subject = nwbfile.subject

                device_names, device_descriptions, device_models, manufacturers = [], [], [], []
                object_rows: list[dict[str, Any]] = []
                for name, device in nwbfile.devices.items():
                    device_names.append(name)
                    device_descriptions.append(get_attribute(device, "description"))
                    device_models.append(get_attribute(device, "model_name"))
                    manufacturers.append(get_attribute(device, "manufacturer"))
                    object_rows.append(_object_row(asset_id, asset_path, "device", str(name), device))

                locations, group_descriptions, group_devices = [], [], []
                electrode_rows: list[dict[str, Any]] = []
                for group_name, group in nwbfile.electrode_groups.items():
                    device_name = get_attribute(getattr(group, "device", None), "name")
                    location = get_attribute(group, "location")
                    description = get_attribute(group, "description")
                    locations.append(location)
                    group_descriptions.append(description)
                    group_devices.append(device_name)
                    electrode_rows.append({
                        "asset_id": asset_id,
                        "asset_path": asset_path,
                        "electrode_group_name": group_name,
                        "description": description,
                        "location": location,
                        "device": device_name,
                    })

                for category, container in [
                    ("acquisition", nwbfile.acquisition),
                    ("stimulus", nwbfile.stimulus),
                    ("processing_module", nwbfile.processing),
                    ("analysis", nwbfile.analysis),
                ]:
                    for name, obj in container.items():
                        object_rows.append(_object_row(asset_id, asset_path, category, str(name), obj))
                for obj in nwbfile.all_children():
                    object_rows.append(_object_row(asset_id, asset_path, "nested",
                                                   str(getattr(obj, "path", "") or getattr(obj, "name", "")), obj))

                row = {
                    "dandiset_id": dandiset_id,
                    "asset_id": asset_id,
                    "asset_path": asset_path,
                    "identifier": get_attribute(nwbfile, "identifier"),
                    "session_id": get_attribute(nwbfile, "session_id"),
                    "session_start_time": get_attribute(nwbfile, "session_start_time"),
                    "timestamps_reference_time": get_attribute(nwbfile, "timestamps_reference_time"),
                    "session_description": get_attribute(nwbfile, "session_description"),
                    "experiment_description": get_attribute(nwbfile, "experiment_description"),
                    "experimenter": get_attribute(nwbfile, "experimenter"),
                    "institution": get_attribute(nwbfile, "institution"),
                    "lab": get_attribute(nwbfile, "lab"),
                    "keywords": get_attribute(nwbfile, "keywords"),
                    "related_publications": get_attribute(nwbfile, "related_publications"),
                    "subject_id": get_attribute(subject, "subject_id"),
                    "sex": get_attribute(subject, "sex"),
                    "date_of_birth": get_attribute(subject, "date_of_birth"),
                    "age": get_attribute(subject, "age"),
                    "age_reference": get_attribute(subject, "age_reference"),
                    "strain": get_attribute(subject, "strain"),
                    "species": get_attribute(subject, "species"),
                    "genotype": get_attribute(subject, "genotype"),
                    "subject_description": get_attribute(subject, "description"),
                    "device_names": "; ".join(unique_nonempty(device_names)) or None,
                    "device_descriptions": "; ".join(unique_nonempty(device_descriptions)) or None,
                    "device_models": "; ".join(unique_nonempty(device_models)) or None,
                    "device_manufacturers": "; ".join(unique_nonempty(manufacturers)) or None,
                    "electrode_group_names": "; ".join(container_names(nwbfile.electrode_groups)) or None,
                    "electrode_locations": "; ".join(unique_nonempty(locations)) or None,
                    "electrode_group_descriptions": "; ".join(unique_nonempty(group_descriptions)) or None,
                    "electrode_group_devices": "; ".join(unique_nonempty(group_devices)) or None,
                    "electrode_count": len(nwbfile.electrodes) if nwbfile.electrodes is not None else 0,
                    "acquisition_object_names": "; ".join(container_names(nwbfile.acquisition)) or None,
                    "stimulus_object_names": "; ".join(container_names(nwbfile.stimulus)) or None,
                    "processing_module_names": "; ".join(container_names(nwbfile.processing)) or None,
                    "analysis_object_names": "; ".join(container_names(nwbfile.analysis)) or None,
                    "extraction_status": "Success",
                    "metadata_read_errors": property_errors,
                    "extraction_error": None,
                }
                return row, object_rows, electrode_rows, properties
    finally:
        remote_file.close()


def extract_nwb_assets(config: AuditConfig, assets: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    config.cache_directory.mkdir(parents=True, exist_ok=True)
    disk_cache = remfile.DiskCache(str(config.cache_directory))
    selected = assets[: config.max_assets] if config.max_assets else assets
    nwb_rows, object_rows, electrode_rows, property_rows, matching_rows = [], [], [], [], []
    catalog = json.loads((Path(__file__).resolve().parents[1] / "field_catalog.json").read_text(encoding="utf-8"))
    targets = {r["field"].casefold() for r in catalog}
    targets.update(alias.casefold() for aliases in NWB_FIELD_ALIASES.values() for alias in aliases)
    sidecar = config.output_directory / f"NWB_Properties_{config.dandiset_id}.jsonl.gz"

    with gzip.open(sidecar, "wt", encoding="utf-8") as output:
        for index, asset in enumerate(selected, start=1):
            print(f"[{index}/{len(selected)}] Reading {asset.path}")
            try:
                row, objects, electrodes, properties = _extract_one(asset, disk_cache, config.dandiset_id)
                nwb_rows.append(row)
                object_rows.extend({"dandiset_id": config.dandiset_id, **obj} for obj in objects)
                electrode_rows.extend({"dandiset_id": config.dandiset_id, **item} for item in electrodes)
                for prop in properties:
                    output.write(json.dumps(prop, ensure_ascii=False, default=str) + "\n")
                    if len(property_rows) < PROPERTY_PREVIEW_LIMIT:
                        property_rows.append(prop)
                    field = str(prop.get("property", "")).lstrip("@").casefold()
                    if field == "[scalar]":
                        field = str(prop.get("object_path", "")).rsplit("/", 1)[-1].casefold()
                    value = str(prop.get("value", ""))
                    if field in targets and value and prop.get("read_status") in (None, "Read"):
                        matching_rows.append(prop)
            except Exception as error:
                print(f"    Failed: {type(error).__name__}: {error}")
                nwb_rows.append({
                    "dandiset_id": config.dandiset_id,
                    "asset_id": getattr(asset, "identifier", None),
                    "asset_path": getattr(asset, "path", None),
                    "extraction_status": "Failed",
                    "extraction_error": f"{type(error).__name__}: {error}",
                })
    return nwb_rows, object_rows, electrode_rows, property_rows, matching_rows
