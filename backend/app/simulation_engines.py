from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .models import (
    PathSegment,
    RegionHit,
    SimulationRequest,
    SimulationResponse,
    SimulationSummary,
)
from .phantom_data import get_tissue_by_id, load_phantom_manifest
from .bmode_processor import process_bmode_image
from .reconstruction.channel_data import (
    materialize_receive_channel_npz,
    reconstruct_bmode_from_receive_channel,
)
from .tusx_runner import run_tusx_external

EngineName = Literal["baseline", "tusx", "babelbrain"]


@dataclass(frozen=True)
class EngineResult:
    summary: SimulationSummary
    path_segments: list[PathSegment]
    region_hits: list[RegionHit]
    grayscale_image_url: str


def _baseline_simulation(request: SimulationRequest) -> EngineResult:
    phantom_manifest = load_phantom_manifest()
    focal_depth = request.ultrasound_parameters.focal_depth_mm
    frequency = request.ultrasound_parameters.frequency_mhz
    contact_angle = request.ultrasound_parameters.contact_angle_deg
    coupling_quality = request.ultrasound_parameters.coupling_quality

    skull_structure = next(
        (
            structure
            for structure in phantom_manifest.get("structures", [])
            if structure.get("id") == "skull"
        ),
        None,
    )
    skull_tissue = (
        get_tissue_by_id(skull_structure["tissueId"]) if skull_structure else None
    )
    skull_attenuation = float(skull_tissue["attenuation"]) if skull_tissue else 20.0

    structure_lengths_mm = {
        "scalp": 6.0 + (contact_angle * 0.08),
        "skull": 7.0 + (abs(contact_angle) * 0.06),
        "csf": 2.0,
        "brain": max(22.0, focal_depth - 14.0),
        "ventricles": max(2.0, min(9.0, (focal_depth - 42.0) * 0.2)),
    }

    path_segments: list[PathSegment] = []
    region_hits: list[RegionHit] = []
    total_attenuation = 0.0

    for structure in phantom_manifest.get("structures", []):
        structure_id = structure["id"]
        tissue_id = structure["tissueId"]
        tissue = get_tissue_by_id(tissue_id)
        if tissue is None:
            continue

        length_mm = round(structure_lengths_mm.get(structure_id, 4.0), 2)
        attenuation_contribution = round(
            (length_mm / 10.0) * float(tissue["attenuation"]) * frequency * 0.01,
            3,
        )
        total_attenuation += attenuation_contribution
        path_segments.append(
            PathSegment(
                structure_id=structure_id,
                tissue_id=tissue_id,
                length_mm=length_mm,
                attenuation_contribution=attenuation_contribution,
            )
        )

        hit_strength = round(
            max(
                0.05,
                (coupling_quality * request.ultrasound_parameters.intensity)
                / (1.0 + attenuation_contribution),
            ),
            3,
        )
        region_hits.append(
            RegionHit(
                structure_id=structure_id,
                label=structure["label"],
                hit_strength=hit_strength,
            )
        )

    attenuation_estimate = round(
        (frequency * 0.18)
        + (focal_depth * 0.01)
        + (contact_angle * 0.012)
        + ((1 - coupling_quality) * 0.8)
        + (skull_attenuation * 0.008),
        3,
    )
    attenuation_estimate = round(attenuation_estimate + (total_attenuation * 0.2), 3)
    reflection_estimate = round(
        (skull_attenuation * 0.012)
        + (abs(contact_angle) * 0.01)
        + ((1 - coupling_quality) * 0.4),
        3,
    )
    latency_ms = 1200 if request.output_mode == "baseline" else 4200

    return EngineResult(
        grayscale_image_url="/static/placeholder-grayscale.png",
        summary=SimulationSummary(
            attenuation_estimate=attenuation_estimate,
            focal_region_depth_mm=focal_depth,
            estimated_latency_ms=latency_ms + int(max(request.ultrasound_parameters.gain_db, 0) * 10),
            reflection_estimate=reflection_estimate,
        ),
        path_segments=path_segments,
        region_hits=region_hits,
    )


def _tusx_stub_simulation(request: SimulationRequest) -> EngineResult:
    baseline = _baseline_simulation(request)
    # TUSX-first path: until the external runner is wired in, normalize through
    # the same response shape while surfacing a slightly different latency/summary profile.
    summary = baseline.summary.model_copy(
        update={
            "attenuation_estimate": round(baseline.summary.attenuation_estimate * 0.97, 3),
            "reflection_estimate": round(baseline.summary.reflection_estimate * 1.05, 3),
            "estimated_latency_ms": baseline.summary.estimated_latency_ms + 450,
        }
    )
    return EngineResult(
        grayscale_image_url="/static/tusx-placeholder-grayscale.png",
        summary=summary,
        path_segments=baseline.path_segments,
        region_hits=baseline.region_hits,
    )


def run_tusx_engine(
    request: SimulationRequest, handoff_path: str | None, run_directory: str | None
) -> EngineResult:
    if handoff_path and run_directory:
        try:
            payload = run_tusx_external(Path(handoff_path), Path(run_directory))
            
            # Check if real k-Wave simulation was run (Phase 3)
            if is_real_kwave_result(payload):
                grayscale_image_url = _build_real_kwave_image_url(payload, run_directory)
            else:
                grayscale_image_url = payload["grayscale_image_url"]
            
            return EngineResult(
                grayscale_image_url=grayscale_image_url,
                summary=SimulationSummary(**payload["summary"]),
                path_segments=[
                    PathSegment(**segment) for segment in payload["path_segments"]
                ],
                region_hits=[
                    RegionHit(**region) for region in payload["region_hits"]
                ],
            )
        except Exception:
            # Fallback is intentional so local development can proceed before
            # a real TUSX installation is available.
            return _tusx_stub_simulation(request)
    return _tusx_stub_simulation(request)


def is_real_kwave_result(payload: dict) -> bool:
    """Check if the result comes from real k-Wave simulation (Phase 3)."""
    metadata = payload.get("simulation_metadata", {})
    return metadata.get("engine") == "k-wave" and metadata.get("resolution") == "Phase 3 (real k-Wave)"


def _build_real_kwave_image_url(payload: dict, run_directory: str | None) -> str:
    if not run_directory:
        return payload["grayscale_image_url"]

    run_dir = Path(run_directory)
    metadata = payload.get("simulation_metadata", {})
    raw_receive_channel_path = metadata.get("receive_channel_raw_file") or metadata.get("receive_channel_raw_path")
    receive_channel_data_path = metadata.get("receive_channel_data_file")
    receive_channel_metadata_path = metadata.get("receive_channel_metadata_file")
    pressure_field_path = metadata.get("pressure_field_file") or str(run_dir / "pressure_field.mat")

    bmode_image_path: Path | None = None
    if raw_receive_channel_path and receive_channel_data_path and receive_channel_metadata_path:
        raw_path = Path(raw_receive_channel_path)
        metadata_path = Path(receive_channel_metadata_path)
        if raw_path.exists() and metadata_path.exists():
            npz_path, _channel_metadata = materialize_receive_channel_npz(
                raw_mat_path=raw_path,
                npz_path=receive_channel_data_path,
                metadata_json_path=metadata_path,
            )
            bmode_image_path = Path(
                reconstruct_bmode_from_receive_channel(
                    npz_path=npz_path,
                    metadata_json_path=metadata_path,
                    output_dir=run_dir,
                )
            )

    if bmode_image_path is None:
        pressure_file = Path(pressure_field_path)
        if pressure_file.exists():
            bmode_image_path = Path(process_bmode_image(str(pressure_file), str(run_dir)))
        else:
            return payload["grayscale_image_url"]

    run_artifacts_root = Path(__file__).resolve().parents[2] / "run_artifacts"
    relative_image_path = bmode_image_path.relative_to(run_artifacts_root)
    return f"/static/{relative_image_path.as_posix()}"


def _babelbrain_stub_simulation(request: SimulationRequest) -> EngineResult:
    baseline = _baseline_simulation(request)
    summary = baseline.summary.model_copy(
        update={
            "estimated_latency_ms": baseline.summary.estimated_latency_ms + 700,
        }
    )
    return EngineResult(
        grayscale_image_url="/static/babelbrain-placeholder-grayscale.png",
        summary=summary,
        path_segments=baseline.path_segments,
        region_hits=baseline.region_hits,
    )


def run_simulation_engine(
    engine: EngineName,
    request: SimulationRequest,
    *,
    handoff_path: str | None = None,
    run_directory: str | None = None,
) -> EngineResult:
    if engine == "tusx":
        return run_tusx_engine(
            request, handoff_path=handoff_path, run_directory=run_directory
        )
    if engine == "babelbrain":
        return _babelbrain_stub_simulation(request)
    return _baseline_simulation(request)
