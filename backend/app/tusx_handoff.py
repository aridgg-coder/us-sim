from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .phantom_data import load_phantom_manifest, load_tissue_properties


def build_reconstruction_artifact_paths(run_dir: Path) -> dict[str, str]:
    return {
        "pressure_field_file": str(run_dir / "pressure_field.mat"),
        "receive_channel_raw_file": str(run_dir / "receive_channel_data.mat"),
        "receive_channel_data_file": str(run_dir / "receive_channel_data.npz"),
        "receive_channel_metadata_file": str(run_dir / "receive_channel_metadata.json"),
        "reconstruction_metadata_file": str(run_dir / "reconstruction_metadata.json"),
    }


def build_tusx_input_package(
    *,
    handoff_payload: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    phantom_manifest = load_phantom_manifest()
    tissue_properties = load_tissue_properties()
    reconstruction_artifact_paths = build_reconstruction_artifact_paths(run_dir)

    package = {
        "schema_version": "tusx-input-v1",
        "engine": "tusx",
        "job_id": handoff_payload["job_id"],
        "created_at_utc": handoff_payload["created_at_utc"],
        "phantom": {
            "id": phantom_manifest["id"],
            "version": phantom_manifest["version"],
            "coordinate_system": phantom_manifest["coordinateSystem"],
            "structures": phantom_manifest["structures"],
            "probe_targets": phantom_manifest["probeTargets"],
        },
        "tissue_properties": tissue_properties,
        "simulation_request": {
            "anatomy_model_id": handoff_payload["anatomy_model_id"],
            "phantom_version": handoff_payload["phantom_version"],
            "probe_pose": handoff_payload["probe_pose"],
            "ultrasound_parameters": handoff_payload["ultrasound_parameters"],
        },
        "artifacts": {
            "run_directory": str(run_dir),
            "result_file": str(run_dir / "tusx_result.json"),
            "log_file": str(run_dir / "tusx_wrapper.log"),
            **reconstruction_artifact_paths,
        },
    }

    package_path = run_dir / "tusx_input.json"
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return {
        "package_path": str(package_path),
        "schema_version": package["schema_version"],
        **reconstruction_artifact_paths,
    }

