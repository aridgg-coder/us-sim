#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
from skimage.filters import threshold_otsu

from ct_surface_utils import MAX_SAMPLE_COUNT, extract_surface_assets


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_OBJ = ROOT / "frontend" / "public" / "anatomy" / "meshes" / "ct-head-outer.obj"
DEFAULT_OUTPUT_JSON = ROOT / "frontend" / "lib" / "generated" / "ctHeadSurface.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract an outer head mesh and sampled surface set from a CT NIfTI volume."
    )
    parser.add_argument("input", type=Path, help="Path to an input NIfTI CT volume")
    parser.add_argument(
        "--output-obj",
        type=Path,
        default=DEFAULT_OUTPUT_OBJ,
        help="Path to write the extracted OBJ mesh",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Path to write the sampled surface JSON",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Optional intensity threshold. If omitted, Otsu thresholding is used.",
    )
    parser.add_argument(
        "--downsample",
        type=int,
        default=1,
        help="Integer downsample factor before mesh extraction",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=MAX_SAMPLE_COUNT,
        help="Maximum number of sampled surface points to store in JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = nib.load(str(args.input))
    volume = image.get_fdata().astype(np.float32)

    threshold = args.threshold
    if threshold is None:
        sampled = volume[::4, ::4, ::4]
        threshold = float(threshold_otsu(sampled))

    mask = volume > threshold
    payload = extract_surface_assets(
        mask=mask,
        affine_xyz=image.affine,
        output_obj=args.output_obj,
        output_json=args.output_json,
        source=str(args.input),
        threshold=threshold,
        downsample=args.downsample,
        samples=args.samples,
    )

    print(f"Input: {args.input}")
    print(f"Threshold: {threshold:.3f}")
    print(f"OBJ: {args.output_obj}")
    print(f"JSON: {args.output_json}")
    print(
        "Mesh vertices: "
        f"{payload['vertexCount']} faces: {payload['faceCount']} samples: {payload['sampleCount']}"
    )


if __name__ == "__main__":
    main()