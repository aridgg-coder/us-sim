# TUSX Integration Plan

## Goal

Adopt a `Path B` strategy in which TUSX is the first external simulation integration for the project, while preserving the app's in-house phantom, UI, API, provenance, and validation layers.

## Role of TUSX

TUSX is treated as:

- the first external transcranial simulation adapter
- an offline or batch-oriented acoustic modeling backend
- a reference implementation for skull-aware ultrasound propagation

TUSX is not treated as:

- the system of record for phantom metadata
- the frontend anatomy viewer
- the scenario-management layer
- the product-facing API contract

## Integration Boundaries

### Keep In-House

- phantom manifests
- tissue property tables
- benchmark files
- web UI and interaction model
- backend API schemas
- provenance and version tracking
- result normalization for the frontend

### Delegate To TUSX

- transcranial acoustic simulation runs
- skull-aware propagation modeling
- simulation outputs derived from imported CT/MR or normalized phantom data

## Required Adapter Inputs

The TUSX adapter should accept, at minimum:

- phantom version
- anatomy model identifier
- probe pose
- ultrasound parameters
- a normalized simulation representation derived from the project phantom

## Required Adapter Outputs

The TUSX adapter should return normalized outputs compatible with the current API:

- grayscale image output path or reference
- attenuation estimate
- focal depth estimate
- reflection estimate
- path segments if derivable
- region hits if derivable
- engine metadata including engine name and run mode

## Near-Term Implementation Plan

1. Keep the current baseline in-house engine as the fallback.
2. Add a simulation-engine dispatcher in the backend.
3. Add a `tusx` engine option and make it the preferred configured path.
4. Normalize TUSX outputs into the existing `SimulationResponse`.
5. Add `babelbrain` as the next public engine option after the TUSX seam is stable.

## First TUSX Milestones

### Milestone 1

- backend adapter scaffold exists
- engine selection exists
- fallback baseline engine still works

### Milestone 2

- define intermediate file formats for TUSX handoff
- define run directory layout and provenance metadata
- produce first placeholder TUSX-style run artifact

### Milestone 3

- connect real TUSX execution
- compare benchmark outputs against the in-house baseline

## Risks

- MATLAB or environment dependency complexity
- mismatch between TUSX input expectations and our normalized phantom format
- operational difficulty if TUSX is slower or more batch-oriented than the app workflow
- output-shape mismatches that require normalization logic

## Decision Rule

TUSX remains the preferred Path B engine only if it improves benchmark credibility enough to justify integration cost.

BabelBrain remains the next external comparison point once the TUSX adapter contract is stable.

