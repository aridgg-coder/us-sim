#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import binary_closing, binary_fill_holes, label
from skimage.measure import marching_cubes


TARGET_MAX_DIMENSION = 3.55
TARGET_TRANSLATION = np.array([0.0, -0.02, 0.0], dtype=np.float64)
MAX_SAMPLE_COUNT = 3600


def largest_connected_component(mask: np.ndarray) -> np.ndarray:
    components, count = label(mask)
    if count == 0:
        return mask

    counts = np.bincount(components.ravel())
    counts[0] = 0
    largest = int(np.argmax(counts))
    return components == largest


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    lines: list[str] = []
    for vx, vy, vz in vertices:
        lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")
    for a, b, c in faces:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def world_vertices_from_voxels(
    vertices_zyx: np.ndarray,
    affine_xyz: np.ndarray,
    voxel_step: int,
) -> np.ndarray:
    voxel_xyz = vertices_zyx[:, [2, 1, 0]] * float(voxel_step)
    homogeneous = np.concatenate(
        [voxel_xyz, np.ones((vertices_zyx.shape[0], 1), dtype=np.float64)],
        axis=1,
    )
    return (affine_xyz @ homogeneous.T).T[:, :3]


def world_normals_from_voxels(
    normals_zyx: np.ndarray,
    affine_xyz: np.ndarray,
    voxel_step: int,
) -> np.ndarray:
    normals_xyz = normals_zyx[:, [2, 1, 0]].astype(np.float64)
    linear = affine_xyz[:3, :3] @ np.diag([float(voxel_step)] * 3)
    transformed = normals_xyz @ np.linalg.inv(linear).T
    lengths = np.linalg.norm(transformed, axis=1, keepdims=True)
    lengths[lengths == 0.0] = 1.0
    return transformed / lengths


def extract_surface_assets(
    *,
    mask: np.ndarray,
    affine_xyz: np.ndarray,
    output_obj: Path,
    output_json: Path,
    source: str,
    threshold: float,
    downsample: int = 1,
    samples: int = MAX_SAMPLE_COUNT,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned_mask = largest_connected_component(mask.astype(bool))
    cleaned_mask = binary_closing(cleaned_mask, iterations=2)
    cleaned_mask = binary_fill_holes(cleaned_mask)

    if downsample > 1:
        step = downsample
        cleaned_mask = cleaned_mask[::step, ::step, ::step]
    else:
        step = 1

    vertices, faces, normals, _ = marching_cubes(cleaned_mask.astype(np.float32), level=0.5)

    world_vertices = world_vertices_from_voxels(vertices, affine_xyz, step)
    world_normals = world_normals_from_voxels(normals, affine_xyz, step)

    bbox_min = world_vertices.min(axis=0)
    bbox_max = world_vertices.max(axis=0)
    center = (bbox_min + bbox_max) / 2.0
    extents = bbox_max - bbox_min
    scale = TARGET_MAX_DIMENSION / float(np.max(extents))

    vertices_scene = ((world_vertices - center) * scale) + TARGET_TRANSLATION
    normals_scene = world_normals

    sample_step = max(1, int(np.ceil(len(vertices_scene) / samples)))
    sample_vertices = vertices_scene[::sample_step]
    sample_normals = normals_scene[::sample_step]

    output_obj.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    write_obj(output_obj, vertices_scene, faces)

    payload: dict[str, Any] = {
        "source": source,
        "threshold": threshold,
        "downsample": step,
        "vertexCount": int(len(vertices_scene)),
        "faceCount": int(len(faces)),
        "sampleCount": int(len(sample_vertices)),
        "bboxMin": bbox_min.tolist(),
        "bboxMax": bbox_max.tolist(),
        "scale": scale,
        "translation": TARGET_TRANSLATION.tolist(),
        "samples": [
            {"point": point.tolist(), "normal": normal.tolist()}
            for point, normal in zip(sample_vertices, sample_normals, strict=True)
        ],
    }
    if metadata:
        payload.update(metadata)

    output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload