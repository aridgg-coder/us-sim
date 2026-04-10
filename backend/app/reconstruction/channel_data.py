from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import scipy.io
import scipy.signal


def materialize_receive_channel_npz(
    *,
    raw_mat_path: str | Path,
    npz_path: str | Path,
    metadata_json_path: str | Path,
) -> tuple[Path, dict[str, Any]]:
    raw_path = Path(raw_mat_path)
    npz_output_path = Path(npz_path)
    metadata_path = Path(metadata_json_path)

    mat_data = scipy.io.loadmat(raw_path)
    rf_data = np.asarray(mat_data["rf_data"], dtype=np.float32)
    time_axis_s = np.asarray(mat_data["time_axis_s"], dtype=np.float64).reshape(-1)
    element_positions_mm = np.asarray(mat_data["element_positions_mm"], dtype=np.float64)
    element_normals = np.asarray(mat_data["element_normals"], dtype=np.float64)
    tx_event_origin_mm = np.asarray(mat_data["tx_event_origin_mm"], dtype=np.float64)

    npz_output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_output_path,
        rf_data=rf_data,
        time_axis_s=time_axis_s,
        element_positions_mm=element_positions_mm,
        element_normals=element_normals,
        tx_event_origin_mm=tx_event_origin_mm,
    )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return npz_output_path, metadata


def _interpolate_rf_trace(trace: np.ndarray, sample_index: np.ndarray) -> np.ndarray:
    lower = np.floor(sample_index).astype(np.int64)
    upper = np.clip(lower + 1, 0, trace.shape[0] - 1)
    lower = np.clip(lower, 0, trace.shape[0] - 1)
    fraction = sample_index - lower
    return ((1.0 - fraction) * trace[lower]) + (fraction * trace[upper])


def reconstruct_bmode_from_receive_channel(
    *,
    npz_path: str | Path,
    metadata_json_path: str | Path,
    output_dir: str | Path,
    output_basename: str = "bmode_image",
) -> str:
    npz_data = np.load(npz_path)
    metadata = json.loads(Path(metadata_json_path).read_text(encoding="utf-8"))

    rf_data = np.asarray(npz_data["rf_data"], dtype=np.float64)
    time_axis_s = np.asarray(npz_data["time_axis_s"], dtype=np.float64)
    element_positions_mm = np.asarray(npz_data["element_positions_mm"], dtype=np.float64)
    tx_event_origin_mm = np.asarray(npz_data["tx_event_origin_mm"], dtype=np.float64)

    sampling_frequency_hz = float(metadata["acquisition"]["sampling_frequency_hz"])
    sound_speed_m_per_s = float(metadata["acquisition"]["sound_speed_m_per_s"])
    sound_speed_mm_per_s = sound_speed_m_per_s * 1000.0
    tx_index = 0

    lateral_positions = element_positions_mm[:, 0]
    min_x = float(np.min(lateral_positions))
    max_x = float(np.max(lateral_positions))
    x_grid_mm = np.linspace(min_x - 5.0, max_x + 5.0, 96)
    max_depth_mm = max(40.0, float(np.max(time_axis_s) * sound_speed_mm_per_s * 0.5))
    z_grid_mm = np.linspace(2.0, max_depth_mm, 192)

    image = np.zeros((z_grid_mm.shape[0], x_grid_mm.shape[0]), dtype=np.float64)
    tx_origin = tx_event_origin_mm[tx_index]
    rf_event = rf_data[tx_index]

    for row_index, depth_mm in enumerate(z_grid_mm):
        pixel_x = x_grid_mm
        pixel_z = np.full_like(pixel_x, depth_mm)

        tx_distance_mm = np.sqrt(
            (pixel_x - tx_origin[0]) ** 2
            + (pixel_z - tx_origin[2]) ** 2
        )

        beamformed_line = np.zeros_like(pixel_x)
        for rx_index in range(element_positions_mm.shape[0]):
            rx_position = element_positions_mm[rx_index]
            rx_distance_mm = np.sqrt(
                (pixel_x - rx_position[0]) ** 2
                + (pixel_z - rx_position[2]) ** 2
            )
            total_time_s = (tx_distance_mm + rx_distance_mm) / sound_speed_mm_per_s
            sample_index = total_time_s * sampling_frequency_hz
            valid = (sample_index >= 0.0) & (sample_index < (rf_event.shape[1] - 1))
            interpolated = np.zeros_like(pixel_x)
            if np.any(valid):
                interpolated[valid] = _interpolate_rf_trace(rf_event[rx_index], sample_index[valid])
            beamformed_line += interpolated

        image[row_index] = beamformed_line

    analytic_signal = scipy.signal.hilbert(image, axis=0)
    envelope = np.abs(analytic_signal)
    reference = max(float(np.percentile(envelope, 99.5)), 1e-12)
    envelope_db = 20.0 * np.log10(np.maximum(envelope, 1e-12) / reference)
    dynamic_range_db = 55.0
    envelope_db = np.clip(envelope_db, -dynamic_range_db, 0.0)
    envelope_uint8 = (((envelope_db + dynamic_range_db) / dynamic_range_db) * 255.0).astype(np.uint8)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{output_basename}.png"
    reconstruction_metadata_path = output_root / "reconstruction_metadata.json"

    plt.figure(figsize=(8, 6))
    plt.imshow(
        envelope_uint8,
        cmap="gray",
        aspect="auto",
        origin="upper",
        extent=[float(x_grid_mm[0]), float(x_grid_mm[-1]), float(z_grid_mm[-1]), float(z_grid_mm[0])],
    )
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()

    reconstruction_metadata = {
        "schema_version": "reconstruction-metadata-v1",
        "method": "delay-and-sum",
        "source": str(npz_path),
        "metadata": str(metadata_json_path),
        "imageShape": [int(value) for value in envelope_uint8.shape],
        "xGridMm": [float(x_grid_mm[0]), float(x_grid_mm[-1]), int(x_grid_mm.shape[0])],
        "zGridMm": [float(z_grid_mm[0]), float(z_grid_mm[-1]), int(z_grid_mm.shape[0])],
        "dynamicRangeDb": dynamic_range_db,
        "transmitEventIndex": tx_index,
    }
    reconstruction_metadata_path.write_text(
        json.dumps(reconstruction_metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    return str(output_path)