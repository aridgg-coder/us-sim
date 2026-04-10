# Ultrasound Reconstruction README

This document captures the current project context and the agreed roadmap for
moving from the current pressure-field-based image display toward more
clinical-style ultrasound image reconstruction.

## Current State

The current pipeline uses k-Wave to generate an acoustic pressure field and then
uses a local Python display processor to turn that pressure field into a
grayscale B-mode-like image.

Current implementation points:

- Pressure-field generation: `scripts/tusx_matlab_launcher.m`
- Result normalization and image serving: `backend/app/simulation_engines.py`
- Display reconstruction: `backend/app/bmode_processor.py`

Important limitation:

- The current image is not produced from simulated receive channel data.
- It is produced from a post-processed slice of the final simulated pressure
  field.
- That is useful for visualization and debugging, but it is not a full clinical
  imaging chain.

## Role Of k-Wave And TUSX

- `k-Wave` is the acoustic solver.
- `TUSX` is the transcranial ultrasound simulation toolbox and setup pipeline
  that uses k-Wave under the hood.
- Our code currently wraps that environment and normalizes results for the web
  application.

Current plan:

- avoid modifying upstream k-Wave code unless there is a proven hard blocker
- avoid modifying upstream TUSX core unless a narrow extension is truly needed
- first change our own wrapper and reconstruction code

## Why The Current Output Is Not Yet Clinical-Style

Clinical-style B-mode imaging usually depends on:

- transmit events
- receive aperture geometry
- per-element receive time series or RF/channel data
- delay-and-sum or other beamforming
- dynamic receive focusing
- apodization
- envelope detection
- log compression
- scan conversion

The current pipeline only has the final pressure field and a lightweight display
processor, so it cannot yet reproduce a full clinical imaging chain.

## Agreed Roadmap

### Phase 1: Improve The Current Display Pipeline

Goal:

- improve the quality and debuggability of the existing pressure-field display
  path without changing the acoustic solver path yet

Status:

- started
- `backend/app/bmode_processor.py` has already been upgraded to support:
  - configurable slice selection
  - relative log compression
  - depth gain
  - light smoothing
  - intermediate artifact outputs (`envelope`, `envelope_db`, metadata)

Why this phase matters:

- it improves the usefulness of the current simulator immediately
- it avoids blocking on channel-data or beamforming changes

### Phase 2: Move To Receive-Data-Style Outputs

Goal:

- change the MATLAB simulation wrapper so it records per-element or aperture-like
  receive time series instead of only saving a final pressure-field snapshot

Expected changes:

- update `scripts/tusx_matlab_launcher.m`
- extend `backend/app/tusx_handoff.py`
- extend `backend/app/simulation_engines.py`
- define a stable artifact schema for receive/channel data

Expected non-changes:

- do not fork k-Wave just to request different sensor outputs
- do not fork TUSX just to change our local handoff/output plumbing unless
  absolutely necessary

### Phase 3: Clinical-Style Reconstruction

Goal:

- reconstruct images from receive/channel data rather than from a pressure-field
  slice

Expected features:

- delay-and-sum beamforming
- dynamic receive focusing
- apodization
- envelope detection
- log compression
- scan conversion

Possible later additions:

- coherence-based methods
- adaptive beamforming
- skull-aware compensation or transcranial-specific refinements

## Immediate Next Steps

1. Finish CQ500 CT import validation and confirm a usable full-head CT-derived
   outer surface.
2. Keep Phase 1 improvements in place and iterate if the display quality needs
   further tuning.
3. Define the Phase 2 receive/channel-data artifact schema before changing the
   MATLAB output contract.
4. Update the MATLAB launcher to record receive aperture time-series data.
5. Add a first Python delay-and-sum reconstruction path.

## Design Principles

- Prefer improving our wrapper code before touching upstream dependencies.
- Keep the old pressure-field display path as a fallback while Phase 2 and Phase
  3 are being built.
- Save intermediate artifacts so reconstruction behavior is inspectable and not
  opaque.
- Treat this as a staged transition, not a rewrite.

## Interpretation Guide

Short version:

- today: pressure-field visualization
- next: receive-data simulation outputs
- later: RF/channel-data beamforming and more clinical-style reconstruction

That is the intended evolution path for this repository.