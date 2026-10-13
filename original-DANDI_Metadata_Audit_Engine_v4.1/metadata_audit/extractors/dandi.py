from __future__ import annotations

from typing import Any

from dandi.dandiapi import DandiAPIClient

from ..config import AuditConfig
from ..utils import safe_value


def extract_dandiset(config: AuditConfig) -> tuple[dict[str, Any], list[dict[str, Any]], list[Any]]:
    print(f"Connecting to DANDI {config.dandiset_id}, version {config.version}...")
    with DandiAPIClient() as client:
        dandiset = client.get_dandiset(config.dandiset_id, config.version)
        metadata = dandiset.get_raw_metadata()
        assets = list(dandiset.get_assets(order="path"))

        asset_rows: list[dict[str, Any]] = []
        nwb_assets: list[Any] = []
        for asset in assets:
            try:
                asset_metadata = asset.get_raw_metadata()
            except Exception:
                asset_metadata = {}
            path = str(getattr(asset, "path", ""))
            asset_rows.append({
                "dandiset_id": config.dandiset_id,
                "version": config.version,
                "asset_id": getattr(asset, "identifier", None),
                "asset_path": path,
                "asset_size_bytes": asset_metadata.get("contentSize"),
                "encoding_format": asset_metadata.get("encodingFormat"),
                "date_modified": asset_metadata.get("dateModified"),
                "digest": safe_value(asset_metadata.get("digest")),
            })
            if path.lower().endswith(".nwb"):
                nwb_assets.append(asset)

    print(f"Found {len(assets)} assets, including {len(nwb_assets)} NWB files.")
    return metadata, asset_rows, nwb_assets
