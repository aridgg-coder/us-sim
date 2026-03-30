# K-Wave Integration Setup Guide

## Overview

This guide explains how to set up k-Wave and TUTX integration for the transcranial ultrasound simulator backend.

## Architecture

The integration works as follows:

```
Frontend (Next.js) → Backend API (FastAPI) → TUSX Wrapper (Python)
                                                    ↓
                                          MATLAB Launcher (MATLAB)
                                                    ↓
                                          k-Wave Simulation (k-Wave Toolbox)
                                                    ↓
                                          Results → JSON → Backend → Frontend
```

### Key Components

- **[tusx_matlab_launcher.m](../scripts/tusx_matlab_launcher.m)** - MATLAB entry point that orchestrates TUSX + k-Wave
- **[run_tusx_wrapper.py](../scripts/run_tusx_wrapper.py)** - Python wrapper that finds and invokes MATLAB
- **[matlab_config.py](../backend/app/matlab_config.py)** - MATLAB executable discovery and configuration
- **tusx_input.json** - Handoff package from backend to MATLAB
- **tusx_result.json** - Results returned from MATLAB to backend

## Installation Steps

### 1. Install MATLAB

Download and install MATLAB from [mathworks.com](https://www.mathworks.com/products/matlab.html).

Make note of your installation path:
- **Windows**: `C:\Program Files\MATLAB\R2023b` (or your version)
- **Linux**: `/usr/local/MATLAB/R2023b` (or your version)
- **macOS**: `/Applications/MATLAB_R2023b.app`
- **WSL/Windows Subsystem for Linux**: `/mnt/c/Program Files/MATLAB/R2023b`

### 2. Install Required Toolboxes

In MATLAB, run:

```matlab
% Verify or install required toolboxes
ver

% Required: Signal Processing Toolbox, Image Processing Toolbox, Statistics and Machine Learning Toolbox
% These are typically installed by default but verify with 'ver' command
```

### 3. Install k-Wave

Download k-Wave from [k-Wave.org](http://k-wave.org):

1. Go to [k-Wave download page](http://k-wave.org/download.html)
2. Download the latest version (currently supports MATLAB R2014b and later)
3. Extract to a location on your filesystem
4. Add k-Wave to your MATLAB path

In MATLAB:
```matlab
% Add k-Wave to path (adjust path as needed)
addpath('/path/to/k-Wave');

% Verify installation
kWaveCheck

% Save the path for future sessions
savepath
```

### 4. Install TUSX

```bash
# Clone TUSX (if not already in the repo)
cd /home/aridgg/us-sim
git clone https://github.com/ianheimbuch/tusx.git tusx

# Or if already present in tusx/ directory, verify structure:
ls tusx/sim/tusx_sim_setup.m  # Should exist
```

Add TUSX to MATLAB path:

```matlab
% In MATLAB
addpath('/path/to/us-sim/tusx');
addpath('/path/to/us-sim/tusx/sim');
addpath('/path/to/us-sim/tusx/gen');
% ... add other TUSX subdirectories

% Save path
savepath
```

### 5. Configure Environment Variables

Copy `.env.example` to `.env` and set the paths:

```bash
cp .env.example .env
```

Edit `.env` and set `MATLAB_ROOT` if MATLAB is not automatically detected:

```bash
# For Windows WSL:
MATLAB_ROOT=/mnt/c/Program Files/MATLAB/R2023b

# For Windows native:
# MATLAB_ROOT=C:\Program Files\MATLAB\R2023b

# For Linux:
# MATLAB_ROOT=/usr/local/MATLAB/R2023b

# For macOS:
# MATLAB_ROOT=/Applications/MATLAB_R2023b.app
```

### 6. Test MATLAB Detection

Run this Python command to verify MATLAB is found:

```bash
cd /home/aridgg/us-sim/backend

# Test MATLAB detection
python3 -c "
from app.matlab_config import MATLABConfig
exe = MATLABConfig.find_matlab_executable()
print(f'MATLAB found at: {exe}')
"
```

If MATLAB is not found:
- Verify MATLAB is installed at the expected path
- Set `MATLAB_ROOT` environment variable
- Ensure MATLAB is on your system PATH

### 7. Test Simulation Pipeline

```bash
# Run a test simulation through the backend
cd /home/aridgg/us-sim/backend

# Start the backend (if not already running)
python3 -m uvicorn app.main:app --reload

# In another terminal, run a simulation
curl -X POST http://localhost:8000/api/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "tusx",
    "anatomy_model_id": "xcat-proxy",
    "phantom_version": "1.0",
    "probe_pose": {
      "position_mm": [0, 0, 0],
      "orientation_deg": [0, 0, 0]
    },
    "ultrasound_parameters": {
      "frequency_mhz": 0.5,
      "focal_depth_mm": 30,
      "gain_db": 20,
      "intensity": 1.0,
      "contact_angle_deg": 0,
      "coupling_quality": 0.8
    }
  }'
```

Check the run artifacts directory to see logs:

```bash
ls -la backend/run_artifacts/20260330/tusx-*/

# View wrapper log to see what happened
cat backend/run_artifacts/20260330/tusx-*/tusx_wrapper.log
```

## Troubleshooting

### MATLAB not found

```python
# Check if MATLAB is on the system
import os
result = os.system("which matlab")  # Unix/Linux
# or
result = os.system("where matlab")  # Windows
```

If not found, set `MATLAB_ROOT`:

```bash
# Linux/macOS
export MATLAB_ROOT=/usr/local/MATLAB/R2023b

# Windows (cmd)
set MATLAB_ROOT=C:\Program Files\MATLAB\R2023b

# Windows (PowerShell)
$env:MATLAB_ROOT = "C:\Program Files\MATLAB\R2023b"
```

### MATLAB times out

The default timeout is 5 minutes (300 seconds). For slower systems or higher-fidelity simulations:

```bash
# In .env
SIMULATION_TIMEOUT=600  # 10 minutes
```

### k-Wave not found by MATLAB

In MATLAB, verify k-Wave is on the path:

```matlab
which kWaveCheck
% Should return the path to k-Wave's kWaveCheck.m

% If not found, add it:
addpath('/path/to/k-Wave');
addpath(genpath('/path/to/k-Wave'));  % Add all subdirectories
savepath
```

### TUSX errors

Verify TUSX is properly installed:

```matlab
which tusx_sim_setup
% Should return the path to tusx_sim_setup.m from the tusx/sim directory

% If not found, add it:
addpath('/path/to/us-sim/tusx');
addpath(genpath('/path/to/us-sim/tusx'));
```

### Fallback to Stub Mode

If you want to test the backend without MATLAB:

```python
# Call wrapper with --use-stub flag
python scripts/run_tusx_wrapper.py --handoff tusx_input.json --run-dir ./run_dir --use-stub

# Or set environment variable
export USE_STUB_MODE=true
```

## MVP vs. Full Integration

### MVP (Current)

- Stub MATLAB launcher returns semi-analytical results
- No actual k-Wave simulation yet
- Useful for testing frontend and API workflows
- Run artifacts show expected JSON structure

### Full Integration (Phase 3)

- Real TUSX + k-Wave simulation
- High-fidelity acoustic propagation
- Actual grayscale ultrasound image synthesis
- Longer compute time acceptable

To enable full TUSX integration once complete, update `tusx_matlab_launcher.m` to call the real simulation functions instead of using the analytical approximation.

## Next Steps

1. **Verify MATLAB/k-Wave work**: Run `tusx_sim_setup` directly in MATLAB with test data
2. **Profile simulation time**: Understand how long k-Wave takes for typical simulation parameters
3. **Implement full launcher**: Replace analytical model in `tusx_matlab_launcher.m` with actual TUSX calls
4. **Add result post-processing**: Convert k-Wave output to grayscale ultrasound images
5. **Validate outputs**: Compare against published benchmarks and phantom data

## References

- [k-Wave Toolbox](http://k-wave.org)
- [TUSX GitHub Repository](https://github.com/ianheimbuch/tusx)
- [Transcranial Ultrasound](https://en.wikipedia.org/wiki/Focused_ultrasound)

