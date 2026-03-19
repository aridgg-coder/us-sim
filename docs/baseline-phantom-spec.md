# Baseline Phantom Specification

## Purpose

This document defines the first realistic head phantom and simulation target for the research prototype described in [development-plan.md](/home/wwitschey/us-sim/development-plan.md).

It is the main Phase 0 specification artifact for:

- the first anatomically grounded head phantom
- the first baseline 3D simulation mode
- the first validation-oriented benchmark set

The goal is to make the next implementation phase concrete enough that engineering, data ingestion, visualization, and validation work can proceed against one shared target.

## Scope

This baseline spec covers:

- phantom contents for the first research version
- accepted anatomy sources
- coordinate and unit conventions
- required tissue property tables
- first supported probe and simulation parameters
- required outputs
- validation expectations
- performance targets for the baseline mode
- the external engine integration boundary for Path B

This document does not yet define:

- higher-fidelity skull microstructure modeling
- patient-specific personalized phantoms
- regulatory or clinical-use claims
- full inverse reconstruction or AI-assisted modes

## 1. Intended Use

The baseline phantom is for a research tool that simulates ultrasound probe placement on the human head and produces:

- grayscale image output
- beam-path and focal-region visualizations
- semi-quantitative signal and propagation summaries

The baseline phantom must support interactive research exploration with short compute delays and scientifically interpretable outputs.

## 2. Baseline Phantom Contents

The first phantom must include the following structures as distinct simulation regions:

1. scalp / superficial soft tissue
2. skull
3. cerebrospinal fluid
4. brain parenchyma
5. ventricles

The first phantom may optionally include, if source data quality is sufficient:

1. major intracranial vessels
2. temporal acoustic window landmarks
3. coarse regional brain subdivisions

The first phantom does not require:

1. fine cortical folding resolution as a hard requirement
2. cranial nerve segmentation
3. lesion-specific pathology models

## 3. Source Data Policy

### Primary Source Strategy

The baseline phantom will combine:

- licensed XCAT-derived geometry when available
- public-source anatomical data for bootstrap and comparison

### Accepted Source Categories

- XCAT-derived anatomical exports
- BodyParts3D metadata and mesh assets where licensing and structure quality are acceptable
- other public anatomy sources with clear licensing, provenance, and coordinate information

### Source Requirements

Every imported structure must record:

- source name
- source version or release identifier if available
- license or usage restriction
- import date
- original file format
- transformation or preprocessing steps

### Source Priority

1. XCAT for the primary research phantom when licensed and available
2. public-source data for bootstrap, comparison, or missing structures
3. hand-authored proxy geometry only as a temporary fallback

## 4. Phantom Representation

The project must support two linked representations of the same phantom:

### Display Representation

- lightweight mesh or simplified geometry for interactive rendering in the browser
- suitable for probe placement, visualization, and fast UI updates

### Simulation Representation

- voxel grid or simulation-oriented mesh
- suitable for acoustic property lookup and propagation calculations
- may have higher spatial resolution than the display representation

Both representations must map back to the same structure IDs and coordinate system.

## 5. Coordinate System and Units

The baseline phantom will use:

- millimeters for spatial units
- degrees for orientation angles
- a right-handed 3D world coordinate system

The implementation must document:

- origin definition
- anatomical axes mapping
- head orientation convention
- probe pose convention relative to the phantom

Initial engineering convention:

- `x`: left-right
- `y`: anterior-posterior
- `z`: inferior-superior

If imported source data uses a different convention, the import pipeline must normalize it.

## 6. Tissue Classes and Required Properties

The first baseline simulation requires a tissue-property table with at least:

- sound speed
- density
- attenuation coefficient
- acoustic impedance

The minimum required tissue classes are:

- scalp / soft tissue
- skull
- cerebrospinal fluid
- brain tissue
- ventricular fluid

The first implementation may use literature-derived homogeneous values per tissue class, but the table must be externalized and versioned so later calibration is possible.

## 7. Initial Probe and Simulation Parameters

The baseline mode must support the following user-controlled parameters:

- probe position
- probe orientation
- frequency
- focal depth
- gain
- intensity
- contact angle
- coupling quality

The baseline mode should support these as direct inputs to both:

- visualization
- simulation request payloads

## 8. Baseline Simulation Behavior

The first baseline simulation mode must:

- operate in true 3D
- use the phantom representation to determine tissue traversal
- account for skull and fluid transitions at a coarse but explicit level
- produce a grayscale image output
- produce semi-quantitative summaries from the same simulated run

The baseline mode does not need to be the most computationally accurate future model, but it must be:

- anatomically grounded
- internally consistent
- benchmarkable
- extensible to higher-fidelity modes

## 8A. Path B Integration Strategy

The active engine strategy is:

1. first external integration: `TUSX`
2. next public comparison integration: `BabelBrain`
3. in-house baseline engine retained as fallback and normalization reference

The project should expose one stable simulation response shape even when multiple engines exist behind it.

That means:

- phantom and tissue inputs remain project-owned
- engine-specific run logic stays behind adapters
- frontend contracts should not depend directly on MATLAB or engine-specific files

## 9. Required Outputs

Each simulation run in baseline mode must produce:

1. grayscale image output
2. beam-path visualization
3. focal-region visualization or coordinates
4. attenuation estimate
5. focal depth estimate
6. estimated run latency
7. metadata identifying phantom source and version

Recommended additional outputs:

1. reflection summary at major interfaces
2. tissue path-length summary
3. region-hit summary for the beam path

## 10. Baseline Validation Requirements

The baseline phantom is not accepted until it supports repeatable benchmark cases.

The first validation set must include at least:

1. temporal-window placement case
2. off-angle placement case
3. altered focal-depth case

Each benchmark must define:

- anatomy model and version
- probe pose
- ultrasound parameters
- expected grayscale image characteristics
- expected semi-quantitative output ranges
- acceptance criteria

## 11. Performance Targets

The baseline mode should target:

- interactive parameter changes reflected in the UI immediately
- simulation rerun latency that feels like a short compute delay

Initial target:

- under 3 seconds for the default baseline scenario on a normal local development machine

Stretch target:

- under 1.5 seconds for the same scenario once the baseline pipeline is stable

If higher-fidelity modes exceed this, they should be explicitly labeled as slower modes rather than replacing the baseline mode.

## 12. File and Data Requirements

The implementation should introduce:

- a phantom manifest file
- a tissue-property table file
- provenance metadata for imported anatomy sources
- benchmark scenario files

Required file concepts:

- `phantom.manifest.json`
- `tissue-properties.json`
- `benchmark-*.json`

Exact filenames can change, but the separation of concerns should remain.

## 13. Acceptance Criteria For Phase 0 Completion

Phase 0 is considered complete when the team has:

1. chosen the first baseline phantom structures
2. defined the first accepted source-data policy
3. defined coordinate and unit conventions
4. defined the first tissue-property table shape
5. defined the required baseline outputs
6. defined at least three benchmark scenarios
7. defined the target baseline runtime

## 14. Immediate Next Implementation Tasks

1. Create `tissue-properties.json` for the five required tissue classes.
2. Create `phantom.manifest.json` for the first baseline head phantom.
3. Extend the anatomy import pipeline to map imported sources into the phantom manifest.
4. Update the frontend viewer to display phantom provenance and structure IDs.
5. Add a TUSX-first simulation adapter boundary in the backend.
6. Keep an in-house fallback adapter for comparison and local development.
7. Fill in the benchmark scenarios in [validation-benchmarks.md](/home/wwitschey/us-sim/docs/validation-benchmarks.md).
8. Add BabelBrain as the next public engine option after the TUSX seam is stable.

## 15. Relationship To Existing Docs

- [development-plan.md](/home/wwitschey/us-sim/development-plan.md): program-level roadmap
- [physics-assumptions.md](/home/wwitschey/us-sim/docs/physics-assumptions.md): physics-model details to be filled in next
- [validation-benchmarks.md](/home/wwitschey/us-sim/docs/validation-benchmarks.md): benchmark definitions that should now be made concrete
