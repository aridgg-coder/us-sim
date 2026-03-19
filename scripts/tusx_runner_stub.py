#!/usr/bin/env python3

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--run-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handoff_path = Path(args.handoff)
    run_dir = Path(args.run_dir)
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    params = payload["ultrasound_parameters"]

    frequency = float(params["frequency_mhz"])
    focal_depth = float(params["focal_depth_mm"])
    gain = float(params["gain_db"])
    intensity = float(params["intensity"])
    contact_angle = float(params["contact_angle_deg"])
    coupling_quality = float(params["coupling_quality"])

    attenuation = round(
        (frequency * 0.22)
        + (focal_depth * 0.009)
        + (contact_angle * 0.014)
        + ((1 - coupling_quality) * 0.9),
        3,
    )
    reflection = round(
        0.28 + (contact_angle * 0.011) + ((1 - coupling_quality) * 0.3),
        3,
    )
    latency = 1650 + int(max(gain, 0) * 10)

    result = {
        "grayscale_image_url": "/static/tusx-placeholder-grayscale.png",
        "summary": {
            "attenuation_estimate": attenuation,
            "focal_region_depth_mm": focal_depth,
            "estimated_latency_ms": latency,
            "reflection_estimate": reflection,
        },
        "path_segments": [
            {
                "structure_id": "scalp",
                "tissue_id": "scalp",
                "length_mm": round(6.2 + contact_angle * 0.05, 2),
                "attenuation_contribution": round(frequency * 0.09, 3),
            },
            {
                "structure_id": "skull",
                "tissue_id": "skull",
                "length_mm": round(7.4 + abs(contact_angle) * 0.04, 2),
                "attenuation_contribution": round(frequency * 0.42, 3),
            },
            {
                "structure_id": "csf",
                "tissue_id": "csf",
                "length_mm": 2.1,
                "attenuation_contribution": 0.008,
            },
            {
                "structure_id": "brain",
                "tissue_id": "brain",
                "length_mm": round(max(22.0, focal_depth - 12.0), 2),
                "attenuation_contribution": round(frequency * 0.11, 3),
            },
            {
                "structure_id": "ventricles",
                "tissue_id": "ventricular_fluid",
                "length_mm": round(max(2.0, min(8.0, (focal_depth - 40.0) * 0.22)), 2),
                "attenuation_contribution": 0.01,
            },
        ],
        "region_hits": [
            {
                "structure_id": "scalp",
                "label": "Scalp / Superficial Soft Tissue",
                "hit_strength": round(0.55 * intensity * coupling_quality, 3),
            },
            {
                "structure_id": "skull",
                "label": "Skull",
                "hit_strength": round(0.42 * intensity * coupling_quality, 3),
            },
            {
                "structure_id": "csf",
                "label": "Cerebrospinal Fluid",
                "hit_strength": round(0.68 * intensity * coupling_quality, 3),
            },
            {
                "structure_id": "brain",
                "label": "Brain Parenchyma",
                "hit_strength": round(0.74 * intensity * coupling_quality, 3),
            },
            {
                "structure_id": "ventricles",
                "label": "Ventricles",
                "hit_strength": round(0.49 * intensity * coupling_quality, 3),
            },
        ],
    }

    (run_dir / "tusx_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
