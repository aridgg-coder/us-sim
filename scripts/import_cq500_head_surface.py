#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path
from urllib.error import HTTPError

import nibabel as nib
import numpy as np
import pydicom

from ct_surface_utils import MAX_SAMPLE_COUNT, extract_surface_assets


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK_DIR = ROOT / "backend" / "data" / "cq500"
DEFAULT_OUTPUT_OBJ = ROOT / "frontend" / "public" / "anatomy" / "meshes" / "cq500-head-outer.obj"
DEFAULT_OUTPUT_JSON = ROOT / "frontend" / "lib" / "generated" / "cq500HeadSurface.json"
CQ500_ARCHIVE_URL = "https://s3.ap-south-1.amazonaws.com/qure.headct.study/CQ500-CT-{case}.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a CQ500 case, reconstruct its DICOM CT volume, and extract a head surface mesh."
    )
    parser.add_argument(
        "case",
        type=int,
        nargs="?",
        default=0,
        help="CQ500 case index to download, such as 0 for CQ500-CT-0.zip",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="Directory used for downloaded archives and extracted DICOM files",
    )
    parser.add_argument(
        "--archive-path",
        type=Path,
        default=None,
        help="Optional path to an existing CQ500 ZIP archive",
    )
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=None,
        help="Optional extraction directory for the archive contents",
    )
    parser.add_argument(
        "--series-dir",
        type=Path,
        default=None,
        help="Optional explicit DICOM series directory to use after extraction",
    )
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
        "--output-nifti",
        type=Path,
        default=None,
        help="Optional path to write the reconstructed CT volume as a NIfTI file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=-300.0,
        help="HU threshold used to separate head tissue from air",
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
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Require an existing archive instead of downloading it",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Delete any existing extracted directory before unzipping the archive again",
    )
    return parser.parse_args()


def archive_path_for_case(case_index: int, work_dir: Path) -> Path:
    return work_dir / f"CQ500-CT-{case_index}.zip"


def extract_dir_for_case(case_index: int, work_dir: Path) -> Path:
    return work_dir / f"CQ500-CT-{case_index}"


def remote_size(url: str) -> int | None:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=120) as response:
        content_length = response.headers.get("Content-Length")
    return int(content_length) if content_length is not None else None


def download_archive(url: str, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = remote_size(url)
    existing_bytes = archive_path.stat().st_size if archive_path.exists() else 0

    if total_bytes is not None and existing_bytes >= total_bytes and zipfile.is_zipfile(archive_path):
        return

    use_resume = existing_bytes > 0 and total_bytes is not None and existing_bytes < total_bytes
    headers = {"Range": f"bytes={existing_bytes}-"} if use_resume else {}
    request = urllib.request.Request(url, headers=headers)

    try:
        response = urllib.request.urlopen(request, timeout=120)
    except HTTPError as error:
        if use_resume and error.code == 416:
            if zipfile.is_zipfile(archive_path):
                return
            archive_path.unlink(missing_ok=True)
            existing_bytes = 0
            response = urllib.request.urlopen(url, timeout=120)
        else:
            raise

    with response:
        if use_resume and getattr(response, "status", None) == 206:
            mode = "ab"
            downloaded = existing_bytes
        else:
            mode = "wb"
            downloaded = 0

        with archive_path.open(mode) as output_file:
            chunk_size = 1024 * 1024
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                output_file.write(chunk)
                downloaded += len(chunk)
                if total_bytes is not None and total_bytes > 0:
                    percent = downloaded * 100.0 / total_bytes
                    print(
                        f"Downloaded {downloaded / (1024 * 1024):.1f} MiB / "
                        f"{total_bytes / (1024 * 1024):.1f} MiB ({percent:.1f}%)"
                    )
                else:
                    print(f"Downloaded {downloaded / (1024 * 1024):.1f} MiB")


def ensure_archive(case_index: int, archive_path: Path, skip_download: bool) -> Path:
    if archive_path.exists() and zipfile.is_zipfile(archive_path):
        return archive_path

    if skip_download:
        raise FileNotFoundError(f"Valid CQ500 archive not found at {archive_path}")

    url = CQ500_ARCHIVE_URL.format(case=case_index)
    print(f"Downloading {url}")
    download_archive(url, archive_path)

    if not zipfile.is_zipfile(archive_path):
        raise RuntimeError(f"Downloaded file is not a valid ZIP archive: {archive_path}")
    return archive_path


def ensure_extracted(archive_path: Path, extract_dir: Path, force_extract: bool) -> Path:
    if force_extract and extract_dir.exists():
        shutil.rmtree(extract_dir)

    if extract_dir.exists() and any(extract_dir.rglob("*.dcm")):
        return extract_dir

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zip_file:
        zip_file.extractall(extract_dir)
    return extract_dir


def find_series_directories(root: Path) -> list[Path]:
    grouped: dict[Path, int] = {}
    for dicom_file in root.rglob("*.dcm"):
        grouped[dicom_file.parent] = grouped.get(dicom_file.parent, 0) + 1
    return [path for path, _count in sorted(grouped.items(), key=lambda item: item[1], reverse=True)]


def select_series_directory(extract_dir: Path, series_dir: Path | None) -> Path:
    if series_dir is not None:
        if not series_dir.exists():
            raise FileNotFoundError(f"Series directory does not exist: {series_dir}")
        return series_dir

    candidates = find_series_directories(extract_dir)
    if not candidates:
        raise FileNotFoundError(f"No DICOM files found under {extract_dir}")

    selected = candidates[0]
    print(f"Selected series: {selected}")
    return selected


def dicom_sort_keys(dataset: pydicom.dataset.FileDataset) -> tuple[float, float, str]:
    if hasattr(dataset, "ImageOrientationPatient") and hasattr(dataset, "ImagePositionPatient"):
        orientation = np.asarray(dataset.ImageOrientationPatient, dtype=np.float64)
        position = np.asarray(dataset.ImagePositionPatient, dtype=np.float64)
        slice_normal = np.cross(orientation[:3], orientation[3:])
        projection = float(np.dot(position, slice_normal))
    else:
        projection = float(getattr(dataset, "InstanceNumber", 0))

    instance_number = float(getattr(dataset, "InstanceNumber", 0))
    sop_instance_uid = str(getattr(dataset, "SOPInstanceUID", ""))
    return projection, instance_number, sop_instance_uid


def load_dicom_series(series_dir: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    datasets: list[pydicom.dataset.FileDataset] = []
    for dicom_path in sorted(series_dir.glob("*.dcm")):
        dataset = pydicom.dcmread(str(dicom_path), force=True)
        if not hasattr(dataset, "PixelData"):
            continue
        if int(getattr(dataset, "Rows", 0)) == 0 or int(getattr(dataset, "Columns", 0)) == 0:
            continue
        datasets.append(dataset)

    if not datasets:
        raise RuntimeError(f"No image slices found in {series_dir}")

    datasets.sort(key=dicom_sort_keys)
    first = datasets[0]
    rows = int(first.Rows)
    cols = int(first.Columns)

    volume_slices: list[np.ndarray] = []
    slice_positions: list[float] = []
    slice_normal: np.ndarray | None = None
    row_direction = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    column_direction = np.array([0.0, 1.0, 0.0], dtype=np.float64)

    if hasattr(first, "ImageOrientationPatient"):
        orientation = np.asarray(first.ImageOrientationPatient, dtype=np.float64)
        row_direction = orientation[:3]
        column_direction = orientation[3:]
        slice_normal = np.cross(row_direction, column_direction)
        normal_length = np.linalg.norm(slice_normal)
        if normal_length > 0:
            slice_normal = slice_normal / normal_length
        else:
            slice_normal = None

    for dataset in datasets:
        if int(dataset.Rows) != rows or int(dataset.Columns) != cols:
            raise RuntimeError("Encountered mixed slice dimensions within the selected CQ500 series")

        pixel_array = dataset.pixel_array.astype(np.float32)
        slope = float(getattr(dataset, "RescaleSlope", 1.0))
        intercept = float(getattr(dataset, "RescaleIntercept", 0.0))
        volume_slices.append((pixel_array * slope) + intercept)

        if slice_normal is not None and hasattr(dataset, "ImagePositionPatient"):
            position = np.asarray(dataset.ImagePositionPatient, dtype=np.float64)
            slice_positions.append(float(np.dot(position, slice_normal)))

    volume = np.stack(volume_slices, axis=0)

    pixel_spacing = getattr(first, "PixelSpacing", [1.0, 1.0])
    row_spacing = float(pixel_spacing[0])
    col_spacing = float(pixel_spacing[1])

    if len(slice_positions) >= 2:
        slice_spacing = float(np.median(np.diff(slice_positions)))
    else:
        slice_spacing = float(
            getattr(first, "SpacingBetweenSlices", getattr(first, "SliceThickness", 1.0))
        )
    slice_spacing = abs(slice_spacing) if slice_spacing != 0 else 1.0

    origin = np.asarray(getattr(first, "ImagePositionPatient", [0.0, 0.0, 0.0]), dtype=np.float64)
    if slice_normal is None:
        slice_normal = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    affine_xyz = np.eye(4, dtype=np.float64)
    affine_xyz[:3, 0] = row_direction * col_spacing
    affine_xyz[:3, 1] = column_direction * row_spacing
    affine_xyz[:3, 2] = slice_normal * slice_spacing
    affine_xyz[:3, 3] = origin

    metadata: dict[str, object] = {
        "seriesDir": str(series_dir),
        "sliceCount": int(len(datasets)),
        "rows": rows,
        "cols": cols,
        "spacingMm": [col_spacing, row_spacing, slice_spacing],
        "seriesDescription": str(getattr(first, "SeriesDescription", "")),
        "studyDescription": str(getattr(first, "StudyDescription", "")),
    }
    return volume, affine_xyz, metadata


def summarize_volume_qc(volume_zyx: np.ndarray, metadata: dict[str, object]) -> dict[str, object]:
    spacing_x_mm, spacing_y_mm, spacing_z_mm = [float(value) for value in metadata["spacingMm"]]
    extent_x_mm = float(volume_zyx.shape[2]) * spacing_x_mm
    extent_y_mm = float(volume_zyx.shape[1]) * spacing_y_mm
    extent_z_mm = float(volume_zyx.shape[0]) * spacing_z_mm

    hu_min = float(np.min(volume_zyx))
    hu_max = float(np.max(volume_zyx))
    hu_p01 = float(np.percentile(volume_zyx, 1.0))
    hu_p99 = float(np.percentile(volume_zyx, 99.0))

    likely_full_head = extent_x_mm >= 150.0 and extent_y_mm >= 180.0 and extent_z_mm >= 160.0
    coverage_assessment = "likely_full_head" if likely_full_head else "possibly_cropped_or_limited_fov"

    return {
        "shapeZYX": [int(value) for value in volume_zyx.shape],
        "extentMm": [extent_x_mm, extent_y_mm, extent_z_mm],
        "huRange": [hu_min, hu_max],
        "huPercentiles": [hu_p01, hu_p99],
        "coverageAssessment": coverage_assessment,
    }


def maybe_write_nifti(output_path: Path | None, volume_zyx: np.ndarray, affine_xyz: np.ndarray) -> None:
    if output_path is None:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    nifti_volume = np.transpose(volume_zyx, (2, 1, 0))
    nib.save(nib.Nifti1Image(nifti_volume, affine_xyz), str(output_path))


def main() -> None:
    args = parse_args()
    work_dir = args.work_dir
    archive_path = args.archive_path or archive_path_for_case(args.case, work_dir)
    extract_dir = args.extract_dir or extract_dir_for_case(args.case, work_dir)

    archive_path = ensure_archive(args.case, archive_path, args.skip_download)
    extract_dir = ensure_extracted(archive_path, extract_dir, args.force_extract)
    series_dir = select_series_directory(extract_dir, args.series_dir)

    volume_zyx, affine_xyz, metadata = load_dicom_series(series_dir)
    qc_summary = summarize_volume_qc(volume_zyx, metadata)
    maybe_write_nifti(args.output_nifti, volume_zyx, affine_xyz)

    payload = extract_surface_assets(
        mask=volume_zyx > args.threshold,
        affine_xyz=affine_xyz,
        output_obj=args.output_obj,
        output_json=args.output_json,
        source=str(series_dir),
        threshold=args.threshold,
        downsample=args.downsample,
        samples=args.samples,
        metadata={
            "case": args.case,
            "archive": str(archive_path),
            **metadata,
            "qcSummary": qc_summary,
        },
    )

    print(f"Case: CQ500-CT-{args.case}")
    print(f"Archive: {archive_path}")
    print(f"Series: {series_dir}")
    print(
        "QC: "
        f"shapeZYX={qc_summary['shapeZYX']} "
        f"extentMm={[round(value, 1) for value in qc_summary['extentMm']]} "
        f"huRange={[round(value, 1) for value in qc_summary['huRange']]} "
        f"huP01P99={[round(value, 1) for value in qc_summary['huPercentiles']]} "
        f"assessment={qc_summary['coverageAssessment']}"
    )
    if args.output_nifti is not None:
        print(f"NIfTI: {args.output_nifti}")
    print(f"OBJ: {args.output_obj}")
    print(f"JSON: {args.output_json}")
    print(
        "Mesh vertices: "
        f"{payload['vertexCount']} faces: {payload['faceCount']} samples: {payload['sampleCount']}"
    )


if __name__ == "__main__":
    main()