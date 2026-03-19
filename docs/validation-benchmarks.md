# Validation Benchmarks

This document tracks benchmark cases used to validate simulation behavior and reproducibility.

## Baseline Benchmark Set

### Benchmark 1: Temporal Window

- anatomy model: `baseline-head-phantom-v1`
- probe pose: temporal-window placement with moderate negative rotation
- ultrasound parameters: `2.5 MHz`, `55 mm` focal depth, `18 dB` gain
- expected grayscale image characteristics: coherent central return with visible skull-transition attenuation
- expected semi-quantitative ranges: attenuation estimate `0.8-1.3`, focal depth `50-60 mm`
- acceptance criteria: run completes, phantom version is reported, attenuation falls in range
- source file: [benchmark-temporal-window.json](/home/wwitschey/us-sim/docs/benchmark-temporal-window.json)

### Benchmark 2: Off-Angle Placement

- anatomy model: `baseline-head-phantom-v1`
- probe pose: displaced and steeper off-angle placement
- ultrasound parameters: increased contact angle with slightly reduced coupling
- expected grayscale image characteristics: less centered beam response and lower signal quality than benchmark 1
- expected semi-quantitative ranges: attenuation estimate `1.0-1.6`, focal depth `48-60 mm`
- acceptance criteria: run completes, attenuation is higher than the temporal-window baseline, phantom version is reported
- source file: [benchmark-off-angle.json](/home/wwitschey/us-sim/docs/benchmark-off-angle.json)

### Benchmark 3: Altered Focal Depth

- anatomy model: `baseline-head-phantom-v1`
- probe pose: same baseline temporal-window placement
- ultrasound parameters: deeper focal depth at `72 mm`
- expected grayscale image characteristics: deeper focal emphasis than benchmark 1
- expected semi-quantitative ranges: attenuation estimate `0.95-1.45`, focal depth `68-76 mm`
- acceptance criteria: run completes, reported focal depth follows the requested deeper setting, phantom version is reported
- source file: [benchmark-altered-focal-depth.json](/home/wwitschey/us-sim/docs/benchmark-altered-focal-depth.json)
