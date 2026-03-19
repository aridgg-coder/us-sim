# Development Plan: Web-Based Ultrasound Probe / Human Head Simulation Tool

## 1. Purpose

Build a web-based application that simulates an ultrasound (`US`) probe being applied to the human head, allowing users to change probe, tissue, and positioning parameters and observe resulting outputs.

Assumption: `US probe` means `ultrasound probe`. If `US` means something else, this plan should be revised before implementation begins.

## 2. Product Goals

- Provide an interactive browser-based simulation of probe placement and behavior.
- Let users adjust key parameters in real time.
- Visualize the relationship between probe settings, head geometry, and simulated output.
- Support research use with scientifically grounded, semi-quantitative outputs and a path to even higher accuracy over time.

## 3. Non-Goals

- Real-time clinical diagnosis.
- Regulatory-grade medical device software in the first version.
- Consumer-focused educational visualization as the primary use case.
- Direct treatment guidance without separate validation and domain expert review.

## 4. Core User Experience

Users should be able to:

- Choose or load a head model.
- Manipulate probe placement directly in the simulation, including position and orientation on the scalp, and immediately see the effect on outputs.
- Change simulation parameters such as:
  - probe frequency
  - intensity / power
  - focal depth
  - gain
  - contact angle
  - coupling quality
  - scan position
  - tissue assumptions
- Manipulate all major ultrasound parameters interactively and see how those changes affect the simulated outputs.
- Run or scrub through the simulation.
- View outputs such as:
  - grayscale ultrasound image output
  - probe placement
  - beam path
  - attenuation estimates
  - reflected signal approximations
  - heat or energy deposition estimates, if included
  - 3D slice or volume visualization
- Save and compare parameter sets.

## 5. Key Product Questions To Resolve Early

- This is a research tool.
- The first version must be accurate, with a roadmap for even higher accuracy through longer simulation time, improved modeling, and potentially AI-assisted acceleration or refinement.
- Head models will come from XCAT and other public data sources.
- The simulation should be true 3D from day one.
- A short compute delay is acceptable.
- Outputs should be semi-quantitative.
- No disclaimers are required in the current plan.

## 6. Recommended MVP

Start with a constrained MVP:

- Browser UI with parameter controls.
- 3D head model based on XCAT and other public data sources.
- Probe placement and orientation controls.
- Accurate acoustic propagation model for the first research version.
- Immediate or near-immediate visual feedback after parameter changes, with short compute delays allowed.
- Scenario save/load.
- Grayscale ultrasound image output with supporting semi-quantitative views.

This keeps the first release research-focused while establishing a path for higher-fidelity simulation as compute time, modeling sophistication, or AI-assisted methods improve.

## 7. Proposed Architecture

### Frontend

- Framework: Next.js or React-based SPA.
- UI responsibilities:
  - parameter controls
  - simulation setup
  - result panels
  - scenario management
- Visualization:
  - WebGL / Three.js or vtk.js for 3D rendering from day one
  - multiplanar slice views
  - grayscale ultrasound image view
  - probe pose manipulation directly in the 3D scene

### Backend

- API service for simulation orchestration, scenario persistence, and heavier compute jobs.
- Good candidates:
  - Python with FastAPI for scientific computing integration
  - background workers for simulation jobs with short asynchronous delays
  - object storage for volumetric datasets and derived outputs if needed

### Simulation Engine

- Active path:
  - `Path B` is the first integration track
  - `TUSX` is the first external simulation engine target
  - `BabelBrain` is the next public integration target after the TUSX adapter is stable
- In-house responsibilities that remain regardless of engine:
  - phantom manifests and tissue-property tables
  - benchmark scenarios and validation workflows
  - API normalization and frontend-facing outputs
- Engine adapter responsibilities:
  - transcranial acoustic propagation
  - skull-aware focusing, attenuation, and reflection modeling
  - grayscale image synthesis and semi-quantitative output generation
- Accuracy roadmap:
  - longer-running higher-fidelity simulation modes
  - improved anatomical segmentation and material calibration
  - optional AI-assisted acceleration, denoising, surrogate modeling, or inverse estimation where scientifically justified

### Persistence

- PostgreSQL initially for:
  - saved scenarios
  - model metadata
  - run history
  - parameter presets
  - validation experiment records

### Deployment

- Web app hosted separately from simulation workers.
- Containerized services for reproducible scientific environments.
- GPU-capable worker deployment as an option for higher-fidelity or accelerated modes.

## 8. Suggested Technical Stack

- Frontend: Next.js, TypeScript, Three.js or vtk.js, a focused UI component layer
- Backend: Python, FastAPI, Pydantic
- Scientific stack: NumPy, SciPy, nibabel / VTK-compatible tooling, possibly PyTorch and specialized acoustic libraries
- Jobs: Celery / RQ / background worker if long-running simulations emerge
- Storage: PostgreSQL
- Infra: Docker, CI pipeline, cloud deployment, optional GPU workers

## 9. Simulation Strategy

### Phase A: Accurate Baseline 3D Model

Use anatomically informed 3D geometry from XCAT and other public sources:

- voxel or mesh-based head representation
- skull, scalp, fluid, and brain-region material properties
- probe placement and orientation mapped directly into the 3D scene
- support for focal depth, gain, frequency, and related acquisition parameters

Compute:

- beam path and focal geometry
- attenuation and reflection effects
- grayscale ultrasound image output
- semi-quantitative field summaries and signal-derived measures

### Phase B: Higher-Fidelity Simulation Modes

- increase spatial resolution
- incorporate better skull heterogeneity and curvature effects
- add more computationally expensive propagation models
- support longer-running jobs for improved accuracy

### Phase C: AI-Assisted and Optimized Modes

- use AI only where it improves speed or reconstruction without weakening scientific traceability
- explore learned surrogates for faster parameter sweeps
- evaluate AI-assisted denoising, interpolation, or inverse estimation against non-AI baselines

### Validation Strategy

- compare simulated outputs against published references, phantom data, and expert review where available
- maintain benchmark cases with fixed inputs and expected ranges
- document assumptions, calibration choices, and known error bounds internally for the research team

## 10. Safety, Ethics, and Regulatory Positioning

This project touches medical and biological simulation, so the plan should include:

- involvement of subject-matter experts in acoustics / neuroimaging / biomedical engineering
- audit of claims shown in the UI and documentation
- traceable assumptions for every simulation output
- avoidance of overstating accuracy
- careful handling of public anatomical data sources and licensing obligations

If the product may guide real procedures, regulatory, legal, and clinical review must become a formal workstream.

## 11. Development Phases

### Phase 0: Discovery and Specification

Deliverables:

- product brief
- list of user personas
- success metrics
- physics scope definition
- risk register
- source-data acquisition plan
- validation plan

Tasks:

- define the research workflow and target use cases
- identify required first-version accuracy targets
- confirm XCAT and other public-source ingestion strategy
- define the first semi-quantitative outputs and grayscale image outputs
- choose the initial external simulation integration strategy
- define the TUSX adapter boundary and TUSX-to-API normalization layer
- keep BabelBrain as the next comparison integration after TUSX
- define benchmark and validation cases

### Phase 1: Prototype

Deliverables:

- web UI scaffold
- 3D scene with manipulable probe
- loaded anatomical head model
- baseline simulation pipeline
- grayscale image rendering path

Tasks:

- build frontend scaffold
- create parameter panel
- render 3D head and probe
- implement direct manipulation for probe pose
- implement the first TUSX-oriented simulation adapter and fallback baseline adapter
- display grayscale image and supporting output panels
- connect parameter changes to rerunnable simulation jobs

### Phase 2: MVP

Deliverables:

- stable web app
- saved scenarios
- backend API
- short-delay job execution
- semi-quantitative output suite
- internal validation report

Tasks:

- add persistence
- improve state management
- support repeatable simulation runs
- add validation checks on inputs
- implement scenario comparison
- integrate XCAT and other public-source head data cleanly
- tune simulation performance to acceptable short-delay latency

### Phase 3: Scientific Improvement

Deliverables:

- higher-fidelity simulation modes
- better material modeling and calibration
- benchmark suite
- AI-assisted acceleration experiments

Tasks:

- improve propagation model
- increase anatomical realism
- compare outputs across known cases
- tune performance
- evaluate AI-assisted approaches against benchmark quality and runtime

### Phase 4: Hardening and Release

Deliverables:

- deployment pipeline
- monitoring
- user documentation
- reproducible compute environments
- internal release package

Tasks:

- load testing
- security review
- logging and observability
- packaging and release process
- reproducibility checks across environments

## 12. Team Roles

Recommended contributors:

- frontend engineer
- backend / platform engineer
- simulation / scientific computing engineer
- UX designer
- biomedical or ultrasound domain expert
- QA engineer

For a very small team, one full-stack engineer plus one scientific advisor can get an MVP moving, but validation work still requires expert involvement.

## 13. Major Risks

- ambiguous product scope
- difficulty achieving required first-version accuracy within acceptable runtime
- scientific inaccuracies undermining research usefulness
- compute cost for higher-fidelity simulation
- difficulty sourcing anatomical or validation data
- performance bottlenecks in browser rendering
- mismatch between AI-assisted acceleration and scientific traceability requirements

## 14. Success Metrics

- users can configure and run scenarios without assistance
- simulation updates within acceptable latency for the chosen scope
- outputs are internally consistent and documented
- early expert reviewers find the controls and visuals credible
- team can add new probe or tissue parameters without major redesign
- benchmark cases remain stable and reproducible across environments

## 15. Initial Backlog

1. Confirm research workflow and intended use.
2. Write product requirements for MVP.
3. Define the first 3D rendering and interaction approach.
4. Create UI wireframes for probe placement and parameter editing.
5. Define the accurate baseline 3D head and acoustic model.
6. Stand up frontend application scaffold.
7. Stand up backend API scaffold.
8. Implement the first 3D simulation endpoint and job flow.
9. Add visualization for probe, head volume, beam path, and grayscale output.
10. Add save/load for scenarios.
11. Add assumptions, benchmark, and validation views.
12. Review with a domain expert.

## 16. Recommendation

The best path is to start with a research-oriented MVP built around an accurate baseline 3D model, manipulable probe placement, grayscale image generation, and semi-quantitative outputs, then layer in slower higher-fidelity and AI-assisted modes only where they can be benchmarked against that baseline. That keeps the system scientifically grounded while still leaving room for meaningful performance and accuracy improvements.
