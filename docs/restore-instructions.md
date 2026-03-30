# Restore Instructions

This project includes a Git submodule (`tusx`) and backend dependencies.
Follow these steps to restore the repository on a new machine.

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

## 5. Run Backend

```bash
cd /path/to/us-sim/backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

## 6. Keep Submodule Up To Date

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
