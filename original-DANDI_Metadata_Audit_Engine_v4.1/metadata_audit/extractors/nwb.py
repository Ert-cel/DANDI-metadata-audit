from __future__ import annotations

from typing import Any

import h5py
import remfile
from pynwb import NWBHDF5IO

from ..config import AuditConfig
from ..utils import container_names, get_attribute, unique_nonempty


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


def _extract_one(asset: Any, disk_cache: Any, dandiset_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    asset_path = str(asset.path)
    asset_id = str(getattr(asset, "identifier", ""))
    url = asset.get_content_url(follow_redirects=1, strip_query=True)
    remote_file = remfile.File(url, disk_cache=disk_cache)
    try:
        with h5py.File(remote_file, mode="r") as h5_file:
            with NWBHDF5IO(file=h5_file, mode="r", load_namespaces=True) as io:
                nwbfile = io.read()
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
                    "extraction_error": None,
                }
                return row, object_rows, electrode_rows
    finally:
        remote_file.close()


def extract_nwb_assets(config: AuditConfig, assets: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    config.cache_directory.mkdir(parents=True, exist_ok=True)
    disk_cache = remfile.DiskCache(str(config.cache_directory))
    selected = assets[: config.max_assets] if config.max_assets else assets
    nwb_rows, object_rows, electrode_rows = [], [], []

    for index, asset in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] Reading {asset.path}")
        try:
            row, objects, electrodes = _extract_one(asset, disk_cache, config.dandiset_id)
            nwb_rows.append(row)
            object_rows.extend(objects)
            electrode_rows.extend(electrodes)
        except Exception as error:
            print(f"    Failed: {type(error).__name__}: {error}")
            nwb_rows.append({
                "dandiset_id": config.dandiset_id,
                "asset_id": getattr(asset, "identifier", None),
                "asset_path": getattr(asset, "path", None),
                "extraction_status": "Failed",
                "extraction_error": f"{type(error).__name__}: {error}",
            })
    return nwb_rows, object_rows, electrode_rows
