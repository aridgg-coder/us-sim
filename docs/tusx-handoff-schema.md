# TUSX Handoff Schema

## Purpose

This document describes the placeholder handoff payload written for the TUSX-first integration path.

Current artifact location per run:

- `backend/run_artifacts/<date>/tusx-<job-id>/external_handoff.json`
- `backend/run_artifacts/<date>/tusx-<job-id>/tusx_input.json`

## Current Fields

### `external_handoff.json`

- `engine`
- `job_id`
- `created_at_utc`
- `phantom_version`
- `anatomy_model_id`
- `probe_pose`
- `ultrasound_parameters`
- `notes`

### `tusx_input.json`

- `schema_version`
- `engine`
- `job_id`
- `created_at_utc`
- `phantom`
- `tissue_properties`
- `simulation_request`
- `artifacts`

## Current Wrapper Flow

1. the backend writes `external_handoff.json`
2. the backend writes `tusx_input.json`
3. the backend calls the configured TUSX runner command
4. the runner writes `tusx_result.json`
5. the backend normalizes that result into the API response

## Near-Term Mapping Goal

The current package should evolve into a concrete TUSX adapter contract with:

- normalized phantom input path
- simulation volume path
- probe specification
- acoustic parameter block
- output directory path
- run-mode metadata
- optional CT/MR-derived acoustic volume inputs

## Design Constraint

The project-owned API and phantom format remain stable even if the eventual TUSX runner requires a different file layout or parameter naming scheme.

That means the adapter is responsible for translation, not the frontend or benchmark files.
