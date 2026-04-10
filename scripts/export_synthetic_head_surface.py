#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import binary_closing, binary_fill_holes
from skimage.measure import marching_cubes


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "backend" / "data" / "synthetic_head.nii.gz"
OBJ_OUTPUT_PATH = ROOT / "frontend" / "public" / "anatomy" / "meshes" / "synthetic-head-outer.obj"
JSON_OUTPUT_PATH = ROOT / "frontend" / "lib" / "generated" / "syntheticHeadSurface.json"

TARGET_MAX_DIMENSION = 3.32
TARGET_TRANSLATION = np.array([0.0, -0.08, 0.0], dtype=np.float64)
MAX_SAMPLE_COUNT = 3200
DOWNSAMPLE_FACTOR = 2


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    lines: list[str] = []
    for vx, vy, vz in vertices:
        lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
    for a, b, c in faces:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    image = nib.load(str(INPUT_PATH))
    volume = image.get_fdata()

    mask = volume > 0
    mask = binary_closing(mask, iterations=1)
    mask = binary_fill_holes(mask)

    if DOWNSAMPLE_FACTOR > 1:
        mask = mask[::DOWNSAMPLE_FACTOR, ::DOWNSAMPLE_FACTOR, ::DOWNSAMPLE_FACTOR]

    spacing = tuple(float(value) * DOWNSAMPLE_FACTOR for value in image.header.get_zooms()[:3])
    vertices, faces, normals, _ = marching_cubes(
        mask.astype(np.float32), level=0.5, spacing=spacing
    )

    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    center = (bbox_min + bbox_max) / 2.0
    extents = bbox_max - bbox_min
    scale = TARGET_MAX_DIMENSION / float(np.max(extents))

    vertices_scene = ((vertices - center) * scale) + TARGET_TRANSLATION
    normals_scene = normals / np.linalg.norm(normals, axis=1, keepdims=True)

    sample_step = max(1, int(np.ceil(len(vertices_scene) / MAX_SAMPLE_COUNT)))
    sample_vertices = vertices_scene[::sample_step]
    sample_normals = normals_scene[::sample_step]

    OBJ_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    write_obj(OBJ_OUTPUT_PATH, vertices_scene, faces)

    payload = {
        "source": str(INPUT_PATH.relative_to(ROOT)),
        "vertexCount": int(len(vertices_scene)),
        "faceCount": int(len(faces)),
        "sampleCount": int(len(sample_vertices)),
        "bboxMin": bbox_min.tolist(),
        "bboxMax": bbox_max.tolist(),
        "scale": scale,
        "translation": TARGET_TRANSLATION.tolist(),
        "samples": [
            {
                "point": point.tolist(),
                "normal": normal.tolist(),
            }
            for point, normal in zip(sample_vertices, sample_normals, strict=True)
        ],
    }
    JSON_OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote OBJ: {OBJ_OUTPUT_PATH}")
    print(f"Wrote samples JSON: {JSON_OUTPUT_PATH}")
    print(f"Mesh vertices: {len(vertices_scene)} faces: {len(faces)} samples: {len(sample_vertices)}")


if __name__ == "__main__":
    main()