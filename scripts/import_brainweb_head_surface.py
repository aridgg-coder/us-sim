#!/usr/bin/env python3

from __future__ import annotations

import gzip
import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import binary_closing, binary_fill_holes, label
from skimage.measure import marching_cubes


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_URL = "https://brainweb.bic.mni.mcgill.ca/cgi/brainweb1"
DOWNLOAD_FORM = {
    "do_download_alias": "phantom_1.0mm_normal_crisp",
    "format_value": "minc",
    "zip_value": "gnuzip",
    "who_name": "us-sim",
    "who_institution": "local-research",
    "who_email": "local@example.com",
    "download_for_real": "[Start download!]",
}

RAW_OUTPUT_PATH = ROOT / "backend" / "data" / "brainweb_normal_crisp.mnc.gz"
OBJ_OUTPUT_PATH = ROOT / "frontend" / "public" / "anatomy" / "meshes" / "brainweb-head-outer.obj"
JSON_OUTPUT_PATH = ROOT / "frontend" / "lib" / "generated" / "brainwebHeadSurface.json"

TARGET_MAX_DIMENSION = 3.55
TARGET_TRANSLATION = np.array([0.0, -0.02, 0.0], dtype=np.float64)
MAX_SAMPLE_COUNT = 3600
MESH_DOWNSAMPLE_FACTOR = 1
OUTER_HEAD_LABELS = (4, 5, 6, 7, 9)


def largest_connected_component(mask: np.ndarray) -> np.ndarray:
    components, count = label(mask)
    if count == 0:
        return mask

    counts = np.bincount(components.ravel())
    counts[0] = 0
    largest = int(np.argmax(counts))
    return components == largest


def download_brainweb() -> None:
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.parse.urlencode(DOWNLOAD_FORM).encode("utf-8")
    request = urllib.request.Request(DOWNLOAD_URL, data=data, method="POST")
    with urllib.request.urlopen(request) as response, RAW_OUTPUT_PATH.open("wb") as output:
        shutil.copyfileobj(response, output)


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    lines: list[str] = []
    for vx, vy, vz in vertices:
        lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
    for a, b, c in faces:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    download_brainweb()

    image = nib.load(str(RAW_OUTPUT_PATH))
    volume = image.get_fdata().astype(np.int16)

    mask = np.isin(volume, OUTER_HEAD_LABELS)
    mask = largest_connected_component(mask)
    mask = binary_closing(mask, iterations=2)
    mask = binary_fill_holes(mask)

    if MESH_DOWNSAMPLE_FACTOR > 1:
      mask = mask[::MESH_DOWNSAMPLE_FACTOR, ::MESH_DOWNSAMPLE_FACTOR, ::MESH_DOWNSAMPLE_FACTOR]

    spacing = tuple(
        float(value) * MESH_DOWNSAMPLE_FACTOR for value in image.header.get_zooms()[:3]
    )
    vertices, faces, normals, _ = marching_cubes(
        mask.astype(np.float32), level=0.5, spacing=spacing
    )

    affine = image.affine
    homogeneous = np.concatenate(
        [vertices[:, [2, 1, 0]], np.ones((vertices.shape[0], 1), dtype=np.float64)],
        axis=1,
    )
    world_vertices = (affine @ homogeneous.T).T[:, :3]

    bbox_min = world_vertices.min(axis=0)
    bbox_max = world_vertices.max(axis=0)
    center = (bbox_min + bbox_max) / 2.0
    extents = bbox_max - bbox_min
    scale = TARGET_MAX_DIMENSION / float(np.max(extents))

    vertices_scene = ((world_vertices - center) * scale) + TARGET_TRANSLATION
    normals_scene = normals / np.linalg.norm(normals, axis=1, keepdims=True)

    sample_step = max(1, int(np.ceil(len(vertices_scene) / MAX_SAMPLE_COUNT)))
    sample_vertices = vertices_scene[::sample_step]
    sample_normals = normals_scene[::sample_step]

    OBJ_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    write_obj(OBJ_OUTPUT_PATH, vertices_scene, faces)

    payload = {
        "source": str(RAW_OUTPUT_PATH.relative_to(ROOT)),
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

    print(f"Downloaded: {RAW_OUTPUT_PATH}")
    print(f"Wrote OBJ: {OBJ_OUTPUT_PATH}")
    print(f"Wrote samples JSON: {JSON_OUTPUT_PATH}")
    print(f"Mesh vertices: {len(vertices_scene)} faces: {len(faces)} samples: {len(sample_vertices)}")


if __name__ == "__main__":
    main()