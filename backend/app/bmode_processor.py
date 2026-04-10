"""B-mode display reconstruction for k-Wave pressure-field outputs.

This module currently provides a research-grade display pipeline, not a full
clinical RF beamforming stack. It takes a 2D slice from a simulated pressure
field, applies envelope detection, optional depth gain and smoothing, then log
compresses the result into a grayscale image.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scipy.io
import scipy.ndimage
import scipy.signal


@dataclass(frozen=True)
class BModeProcessingConfig:
    slice_axis: int | None = None
    slice_index: int | None = None
    envelope_axis: int = 0
    dynamic_range_db: float = 55.0
    depth_gain_db: float = 18.0
    smoothing_sigma: float = 0.8
    top_percentile: float = 99.5
    output_basename: str = "bmode_image"


DEFAULT_CONFIG = BModeProcessingConfig()


def _resolve_slice_axis(field: np.ndarray, config: BModeProcessingConfig) -> int | None:
    if field.ndim < 3:
        return None
    if config.slice_axis is not None:
        return int(np.clip(config.slice_axis, 0, field.ndim - 1))
    return field.ndim - 1


def _resolve_slice_index(field: np.ndarray, axis: int, config: BModeProcessingConfig) -> int:
    if config.slice_index is None:
        return field.shape[axis] // 2
    return int(np.clip(config.slice_index, 0, field.shape[axis] - 1))


def _extract_bmode_slice(
    pressure_field: np.ndarray, config: BModeProcessingConfig
) -> tuple[np.ndarray, dict[str, int | None]]:
    if pressure_field.ndim == 2:
        return pressure_field.astype(np.float64), {"slice_axis": None, "slice_index": None}

    slice_axis = _resolve_slice_axis(pressure_field, config)
    assert slice_axis is not None
    slice_index = _resolve_slice_index(pressure_field, slice_axis, config)

    selected_slice = np.take(pressure_field, indices=slice_index, axis=slice_axis)
    return selected_slice.astype(np.float64), {
        "slice_axis": slice_axis,
        "slice_index": slice_index,
    }


def _apply_depth_gain(envelope: np.ndarray, depth_gain_db: float) -> np.ndarray:
    if depth_gain_db <= 0:
        return envelope

    gain_db = np.linspace(0.0, depth_gain_db, envelope.shape[0], dtype=np.float64)
    gain_linear = np.power(10.0, gain_db / 20.0)[:, np.newaxis]
    return envelope * gain_linear


def _compress_envelope_to_uint8(
    envelope: np.ndarray, config: BModeProcessingConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    finite_envelope = np.asarray(envelope, dtype=np.float64)
    reference = float(np.percentile(finite_envelope, config.top_percentile))
    reference = max(reference, 1e-12)

    envelope_db = 20.0 * np.log10(np.maximum(finite_envelope, 1e-12) / reference)
    envelope_db = np.clip(envelope_db, -config.dynamic_range_db, 0.0)
    envelope_normalized = (envelope_db + config.dynamic_range_db) / config.dynamic_range_db
    envelope_uint8 = (envelope_normalized * 255.0).astype(np.uint8)

    stats = {
        "reference_amplitude": reference,
        "min_db": -float(config.dynamic_range_db),
        "max_db": 0.0,
        "top_percentile": float(config.top_percentile),
    }
    return envelope_uint8, envelope_db, stats


def _build_metadata(
    pressure_field: np.ndarray,
    selected_slice: np.ndarray,
    config: BModeProcessingConfig,
    slice_metadata: dict[str, int | None],
    compression_stats: dict[str, float],
) -> dict[str, object]:
    return {
        "processor": "phase1-display-pipeline-v1",
        "pressureFieldShape": [int(value) for value in pressure_field.shape],
        "sliceShape": [int(value) for value in selected_slice.shape],
        "sliceAxis": slice_metadata["slice_axis"],
        "sliceIndex": slice_metadata["slice_index"],
        "config": asdict(config),
        "compression": compression_stats,
    }


def process_bmode_image(
    pressure_field_file: str,
    output_dir: str,
    config: BModeProcessingConfig = DEFAULT_CONFIG,
) -> str:
    """Process a k-Wave pressure field into a display-oriented B-mode image."""
    mat_data = scipy.io.loadmat(pressure_field_file)
    pressure_field = np.asarray(mat_data["pressure_field"], dtype=np.float64)

    bmode_image, artifacts = create_bmode_from_pressure_field(
        pressure_field,
        grid_info=None,
        config=config,
        return_artifacts=True,
    )

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{config.output_basename}.png"

    np.save(output_root / f"{config.output_basename}_envelope.npy", artifacts["envelope"])
    np.save(output_root / f"{config.output_basename}_envelope_db.npy", artifacts["envelope_db"])
    (output_root / f"{config.output_basename}_metadata.json").write_text(
        json.dumps(artifacts["metadata"], indent=2) + "\n",
        encoding="utf-8",
    )

    plt.figure(figsize=(8, 6))
    plt.imshow(bmode_image, cmap="gray", aspect="auto", origin="upper")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()

    return str(output_path)


def create_bmode_from_pressure_field(
    pressure_field: np.ndarray,
    grid_info: dict | None = None,
    config: BModeProcessingConfig = DEFAULT_CONFIG,
    return_artifacts: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, object]]:
    """Create a display-oriented B-mode image from a pressure-field array."""
    del grid_info

    selected_slice, slice_metadata = _extract_bmode_slice(pressure_field, config)
    analytic_signal = scipy.signal.hilbert(selected_slice, axis=config.envelope_axis)
    envelope = np.abs(analytic_signal)
    envelope = _apply_depth_gain(envelope, config.depth_gain_db)

    if config.smoothing_sigma > 0:
        envelope = scipy.ndimage.gaussian_filter(envelope, sigma=config.smoothing_sigma)

    bmode_image, envelope_db, compression_stats = _compress_envelope_to_uint8(envelope, config)
    artifacts = {
        "envelope": envelope,
        "envelope_db": envelope_db,
        "metadata": _build_metadata(
            pressure_field,
            selected_slice,
            config,
            slice_metadata,
            compression_stats,
        ),
    }

    if return_artifacts:
        return bmode_image, artifacts
    return bmode_image