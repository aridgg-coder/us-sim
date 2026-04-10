# Restore Instructions

This project includes a Git submodule (`tusx`) and backend dependencies.
Follow these steps to restore the repository on a new machine.

## Current Restore Point

As of 2026-04-09, the latest validated restore point is on `main` at these commits:

- `0cbeb9d` - auto-start frontend/backend services on workspace open
- `9434d81` - frontend probe/head collision constraints and reduced viewport overlay footprint
- `95c2dca` - automated WSL to Windows MATLAB pipeline, k-Wave source/grid fixes, B-mode URL fixes

The current working codebase already includes:
- frontend probe/transducer placement constraints against the visible head shell
- reduced viewport overlay text footprint
- VS Code tasks plus `scripts/start_services.sh` / `scripts/stop_services.sh`
- real backend simulation pipeline through MATLAB and k-Wave

## 1. Clone Repository With Submodules

```bash
git clone --recurse-submodules https://github.com/wwitschey/us-sim.git
cd us-sim
```

If already cloned without submodules:

```bash
git submodule update --init --recursive
```

## 2. Verify Submodule State

```bash
git submodule status
```

You should see an entry for `tusx` with a commit hash.

## 3. Configure Environment

Copy template env file:

```bash
cp .env.example .env
```

Then edit `.env` with your local paths, including:
- `MATLAB_ROOT`
- `KWAVE_PATH`
- `TUSX_PATH`

## 4. Backend Python Dependencies

From project root:

```bash
cd backend
python3 -m pip install -e . --break-system-packages
```

If your distro supports venv and you prefer isolation:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

If you are restoring the current workspace state, the project root also uses a top-level venv for service startup:

```bash
cd /path/to/us-sim
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend/
```

## 5. Run Backend

```bash
cd /path/to/us-sim/backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 6. Run Frontend And Backend Together

Recommended restore path for the current repo state:

```bash
cd /path/to/us-sim
./scripts/start_services.sh
```

This starts:
- backend on `http://localhost:8000`
- frontend on `http://localhost:3000`

To stop both:

```bash
cd /path/to/us-sim
./scripts/stop_services.sh
```

In VS Code, the workspace also contains an automatic task that runs `./scripts/start_services.sh` on folder open if automatic tasks are allowed.

Health check:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

Frontend check:

```bash
curl -I http://localhost:3000
```

Expected status includes `200`.

## 7. Keep Submodule Up To Date

To pull latest main + submodule pointers:

```bash
git pull
git submodule update --init --recursive
```

To update `tusx` to a newer upstream commit intentionally:

```bash
cd tusx
git fetch origin
git checkout <commit-or-tag>
cd ..
git add tusx
git commit -m "Update tusx submodule"
git push
```
