# Implementation Roadmap

## Milestone 1: Project Bootstrap

- Initialize git and CI.
- Install Next.js frontend dependencies.
- Install FastAPI backend dependencies.
- Add environment configuration for local development.
- Add formatting and linting for TypeScript and Python.

## Milestone 2: Core Research UI

- Build the simulation workspace layout.
- Add a 3D viewport for the head model and probe.
- Add direct manipulation controls for probe position and orientation.
- Add a parameter panel for focal depth, gain, frequency, power, contact angle, and coupling quality.
- Add a grayscale image panel and semi-quantitative result cards.

## Milestone 3: Simulation Service

- Define simulation job request and response schemas.
- Add job creation, status polling, and result retrieval endpoints.
- Add a simulation-engine dispatcher with `tusx`, `baseline`, and later `babelbrain` options.
- Add a TUSX-first adapter that normalizes external-engine outputs into the API response shape.
- Keep a baseline in-house adapter as fallback and benchmark reference.
- Persist scenarios and job metadata.

## Milestone 4: Data Integration

- Define the import pipeline for XCAT and other public anatomy sources.
- Normalize source metadata and geometry formats.
- Add model versioning and provenance tracking.
- Prepare one canonical development head model for repeatable local testing.
- Replace the current frontend anatomy adapter with imported volumetric or mesh data.

## Milestone 5: Baseline Validation

- Define 3 to 5 benchmark scenarios.
- Record expected output ranges and qualitative checks.
- Add reproducibility checks for repeated runs.
- Review assumptions and outputs with a domain expert.

## Milestone 6: Higher Fidelity

- Add longer-running simulation modes.
- Improve material property handling and skull heterogeneity.
- Evaluate AI-assisted acceleration against baseline quality.
- Introduce GPU-backed workers if runtime requires it.
- Add BabelBrain as the second public engine integration for comparison against TUSX and the fallback baseline path.
