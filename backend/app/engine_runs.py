from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import SimulationRequest
from .simulation_engines import EngineName, EngineResult
from .tusx_handoff import build_reconstruction_artifact_paths, build_tusx_input_package


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "run_artifacts"


def write_engine_run_artifacts(
    *,
    job_id: str,
    engine: EngineName,
    request: SimulationRequest,
    result: EngineResult,
) -> dict[str, Any]:
    timestamp = datetime.now(UTC)
    run_dir = RUNS_DIR / timestamp.strftime("%Y%m%d") / f"{engine}-{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    reconstruction_artifact_paths = build_reconstruction_artifact_paths(run_dir)

    request_payload = request.model_dump(mode="json")
    normalized_result_payload = {
        "grayscale_image_url": result.grayscale_image_url,
        "summary": result.summary.model_dump(mode="json"),
        "path_segments": [segment.model_dump(mode="json") for segment in result.path_segments],
        "region_hits": [region.model_dump(mode="json") for region in result.region_hits],
    }
    handoff_payload = {
        "engine": engine,
        "job_id": job_id,
        "created_at_utc": timestamp.isoformat(),
        "phantom_version": request.phantom_version,
        "anatomy_model_id": request.anatomy_model_id,
        "run_directory": str(run_dir),
        "probe_pose": request_payload["probe_pose"],
        "ultrasound_parameters": request_payload["ultrasound_parameters"],
        "artifacts": reconstruction_artifact_paths,
        "notes": (
            "External-engine handoff artifact. "
            "The active TUSX runner consumes this file and writes tusx_result.json back into the same run directory."
        ),
    }
    manifest_payload = {
        "job_id": job_id,
        "engine": engine,
        "created_at_utc": timestamp.isoformat(),
        "files": [
            "request.json",
            "normalized_result.json",
            "external_handoff.json",
            "tusx_input.json",
            "pressure_field.mat",
            "receive_channel_data.npz",
            "receive_channel_metadata.json",
            "reconstruction_metadata.json",
        ],
    }

    (run_dir / "request.json").write_text(
        json.dumps(request_payload, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "normalized_result.json").write_text(
        json.dumps(normalized_result_payload, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "external_handoff.json").write_text(
        json.dumps(handoff_payload, indent=2) + "\n", encoding="utf-8"
    )
    tusx_package_metadata = (
        build_tusx_input_package(handoff_payload=handoff_payload, run_dir=run_dir)
        if engine == "tusx"
        else None
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "run_directory": str(run_dir),
        "manifest_path": str(run_dir / "manifest.json"),
        "handoff_path": str(run_dir / "external_handoff.json"),
        "tusx_input_path": (
            tusx_package_metadata["package_path"] if tusx_package_metadata else ""
        ),
        "pressure_field_path": reconstruction_artifact_paths["pressure_field_file"],
        "receive_channel_data_path": reconstruction_artifact_paths["receive_channel_data_file"],
        "receive_channel_metadata_path": reconstruction_artifact_paths["receive_channel_metadata_file"],
        "reconstruction_metadata_path": reconstruction_artifact_paths["reconstruction_metadata_file"],
        "created_at_utc": timestamp.isoformat(),
        "adapter_version": "tusx-path-b-v1",
    }
