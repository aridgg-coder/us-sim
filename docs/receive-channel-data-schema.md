# Receive Channel Data Schema

This document defines the planned Phase 2 artifact contract for moving from a
pressure-field display pipeline to a receive-data-style reconstruction pipeline.

The purpose of this schema is to stabilize the interface between:

- the MATLAB simulation wrapper
- the backend normalization layer
- the future Python beamforming and reconstruction modules

## Design Goals

- avoid changing the frontend API while the reconstruction backend evolves
- keep k-Wave and TUSX integration details behind a project-owned artifact
- support both legacy pressure-field outputs and future receive-channel outputs
- capture enough geometry and acquisition metadata to support delay-and-sum
  beamforming and later clinical-style extensions

## Artifact Overview

Phase 2 introduces a new run artifact written alongside the existing run files.

Suggested filename:

- `receive_channel_data.npz`

Current implementation note:

- the MATLAB wrapper currently writes an intermediate raw file
  `receive_channel_data.mat`
- the Python backend then materializes the planned
  `receive_channel_data.npz` artifact from that raw file
- this keeps the public artifact contract stable while avoiding a direct MATLAB
  dependency on writing NumPy archives

Suggested companion metadata file:

- `receive_channel_metadata.json`

The binary payload contains the sampled receive data arrays.
The JSON metadata contains units, geometry, acquisition parameters, and shape
descriptions.

## Proposed Files Per Run

- `tusx_input.json`
- `tusx_result.json`
- `pressure_field.mat` (legacy fallback / debug output)
- `receive_channel_data.mat` (current MATLAB-side raw channel-data artifact)
- `receive_channel_data.npz` (Phase 2 primary reconstruction input)
- `receive_channel_metadata.json`
- `reconstruction_metadata.json` (written by the Python reconstruction layer)
- `bmode_image.png`

## Binary Data Payload

Suggested `receive_channel_data.npz` arrays:

- `rf_data`
  - shape: `[transmit_event_count, receive_element_count, sample_count]`
  - dtype: `float32`
  - units: pressure-like receive signal units as emitted by the simulation
- `time_axis_s`
  - shape: `[sample_count]`
  - dtype: `float64`
  - units: seconds
- `element_positions_mm`
  - shape: `[receive_element_count, 3]`
  - dtype: `float64`
  - units: mm
- `element_normals`
  - shape: `[receive_element_count, 3]`
  - dtype: `float64`
  - unit vectors in world or probe coordinates, as declared in metadata
- `tx_event_origin_mm`
  - shape: `[transmit_event_count, 3]`
  - dtype: `float64`
  - units: mm

Optional future arrays:

- `tx_delays_s`
- `rx_apodization`
- `tx_apodization`
- `analytic_signal`

## Metadata Contract

Suggested `receive_channel_metadata.json` structure:

```json
{
  "schema_version": "receive-channel-v1",
  "job_id": "<job-id>",
  "created_at_utc": "<timestamp>",
  "engine": "tusx",
  "simulation_backend": {
    "toolbox": "k-wave",
    "wrapper": "tusx_matlab_launcher.m",
    "resolution": "phase2-receive-channel"
  },
  "data_layout": {
    "rf_data_shape": [1, 128, 4096],
    "array_order": ["tx", "rx", "sample"],
    "dtype": "float32"
  },
  "units": {
    "distance": "mm",
    "time": "s",
    "sampling_frequency": "Hz",
    "center_frequency": "Hz",
    "sound_speed": "m/s"
  },
  "probe": {
    "probe_id": "phase2-linear-array-prototype",
    "element_count": 128,
    "pitch_mm": 0.3,
    "kerf_mm": 0.05,
    "element_width_mm": 0.25,
    "element_height_mm": 10.0,
    "coordinate_frame": "probe_local"
  },
  "acquisition": {
    "transmit_event_count": 1,
    "receive_element_count": 128,
    "sample_count": 4096,
    "sampling_frequency_hz": 40000000.0,
    "center_frequency_hz": 2500000.0,
    "sound_speed_m_per_s": 1540.0,
    "tx_focus_mm": 55.0,
    "tx_steering_deg": 0.0,
    "recorded_quantity": "pressure_time_series"
  },
  "coordinate_system": {
    "frame": "world",
    "handedness": "right-handed",
    "axes": {
      "x": "left-right",
      "y": "anterior-posterior",
      "z": "inferior-superior"
    }
  },
  "source_artifacts": {
    "tusx_input_path": "<path>",
    "run_directory": "<path>",
    "pressure_field_path": "<path-or-empty>"
  }
}
```

## Required Metadata Fields

These fields should be treated as mandatory in Phase 2:

- `schema_version`
- `job_id`
- `engine`
- `data_layout.rf_data_shape`
- `data_layout.array_order`
- `probe.element_count`
- `acquisition.transmit_event_count`
- `acquisition.receive_element_count`
- `acquisition.sample_count`
- `acquisition.sampling_frequency_hz`
- `acquisition.center_frequency_hz`
- `acquisition.sound_speed_m_per_s`
- `acquisition.recorded_quantity`
- `coordinate_system.frame`

## Coordinate Conventions

The metadata must explicitly declare whether element positions are stored in:

- probe-local coordinates
- world coordinates
- simulation-grid coordinates

Preferred Phase 2 convention:

- store element positions in world coordinates in millimeters
- store probe-local geometry separately in the `probe` block if needed

This reduces ambiguity for Python-side reconstruction.

## Reconstruction Consumer Expectations

The future Python reconstruction layer should assume:

- `rf_data[tx, rx, sample]` ordering unless metadata says otherwise
- the receive aperture geometry is fully described by metadata plus
  `element_positions_mm`
- delay-and-sum beamforming can be implemented without reading MATLAB-specific
  structs or private toolbox outputs

## Backward Compatibility

Phase 2 should preserve the current pressure-field path.

Recommended behavior:

- if `receive_channel_data.npz` exists, prefer it for reconstruction
- otherwise fall back to `pressure_field.mat` and the existing Phase 1 display
  processor

This allows iterative rollout without breaking older runs.

## Implementation Notes

Likely first producer:

- `scripts/tusx_matlab_launcher.m`

Likely first consumers:

- `backend/app/simulation_engines.py`
- future `backend/app/reconstruction/` modules

Likely first beamforming method:

- delay-and-sum on a single transmit event and a linear receive aperture

## Initial Minimal Phase 2 Target

To keep scope controlled, the first usable Phase 2 version only needs:

- one transmit event
- one receive aperture
- per-element pressure-over-time recording
- stable time axis
- stable element geometry metadata
- one Python delay-and-sum implementation

That is enough to cross the boundary from pressure-field visualization to
receive-data reconstruction without overcommitting to a full clinical pipeline
up front.