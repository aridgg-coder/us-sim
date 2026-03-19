# US Head Simulation

Research-oriented web application for simulating ultrasound probe application to the human head with 3D anatomical models, manipulable probe placement, grayscale image output, and semi-quantitative simulation results.

## Workspace Layout

- `frontend/`: Next.js web client for 3D interaction, controls, and visualization
- `backend/`: FastAPI service for simulation orchestration and job execution
- `docs/`: physics assumptions, validation notes, and implementation roadmap
- `development-plan.md`: product and technical development plan

## Initial Priorities

- build the 3D interaction shell
- stand up the simulation API
- define physics assumptions and validation cases
- establish benchmark scenarios before adding complexity

## Next Steps

1. Install frontend dependencies and run the Next.js app.
2. Create a Python virtual environment and install backend dependencies.
3. Replace the stylized 3D head with anatomical source data from XCAT or another public dataset.
4. Replace the placeholder backend math with the first baseline 3D simulation job.
5. Populate the benchmark and assumptions docs with concrete references and test cases.

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
SIMULATION_ENGINE=tusx uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

As of March 19, 2026, the frontend is pinned to `next@16.2.0`.

## Engine Selection

The backend supports:

- `tusx`: active Path B default
- `baseline`: in-house fallback adapter
- `babelbrain`: placeholder comparison adapter for the next public integration

Set the engine with:

```bash
SIMULATION_ENGINE=tusx
```
