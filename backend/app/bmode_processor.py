"""
B-mode ultrasound image processing for k-Wave simulation results.

This module processes acoustic pressure field data from k-Wave simulations
into grayscale B-mode ultrasound images suitable for display.
"""

import numpy as np
import scipy.io
import scipy.signal
import matplotlib.pyplot as plt
import os
from pathlib import Path

def process_bmode_image(pressure_field_file: str, output_dir: str) -> str:
    """
    Process k-Wave pressure field into B-mode ultrasound image.

    Args:
        pressure_field_file: Path to MATLAB .mat file with pressure field
        output_dir: Directory to save the output image

    Returns:
        str: Path to the generated B-mode image
    """
    # Load pressure field data
    mat_data = scipy.io.loadmat(pressure_field_file)
    pressure_field = mat_data['pressure_field']

    # For B-mode, we typically want a 2D slice through the focal region
    # Take a central slice in the transducer plane (assuming transducer at z=1)
    if pressure_field.ndim == 3:
        # 3D field, take central x-y slice
        bmode_slice = pressure_field[:, :, pressure_field.shape[2] // 2]
    else:
        # Already 2D
        bmode_slice = pressure_field

    # Apply envelope detection using Hilbert transform
    analytic_signal = scipy.signal.hilbert(bmode_slice, axis=0)
    envelope = np.abs(analytic_signal)

    # Log compression (typical for ultrasound: 40-60 dB dynamic range)
    envelope_db = 20 * np.log10(envelope + 1e-10)  # Add small value to avoid log(0)

    # Normalize to 0-255 range
    # Typical ultrasound display: -60 to 0 dB
    min_db = -60
    max_db = 0
    envelope_normalized = np.clip((envelope_db - min_db) / (max_db - min_db), 0, 1)
    envelope_uint8 = (envelope_normalized * 255).astype(np.uint8)

    # Create output image path
    output_path = os.path.join(output_dir, 'bmode_image.png')

    # Save as grayscale image
    plt.figure(figsize=(8, 6))
    plt.imshow(envelope_uint8, cmap='gray', aspect='auto')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150)
    plt.close()

    return output_path

def create_bmode_from_pressure_field(pressure_field: np.ndarray,
                                   grid_info: dict = None) -> np.ndarray:
    """
    Create B-mode image from pressure field array.

    Args:
        pressure_field: 2D or 3D pressure field from k-Wave
        grid_info: Optional grid information for better processing

    Returns:
        np.ndarray: Grayscale B-mode image (0-255)
    """
    # Extract 2D slice if 3D
    if pressure_field.ndim == 3:
        # Take slice through focal region (middle of depth)
        bmode_slice = pressure_field[:, :, pressure_field.shape[2] // 2]
    else:
        bmode_slice = pressure_field

    # Envelope detection
    analytic_signal = scipy.signal.hilbert(bmode_slice, axis=0)
    envelope = np.abs(analytic_signal)

    # Log compression
    envelope_db = 20 * np.log10(envelope + 1e-12)

    # Dynamic range compression (-60 to 0 dB)
    envelope_compressed = np.clip((envelope_db + 60) / 60, 0, 1)

    # Convert to uint8
    bmode_image = (envelope_compressed * 255).astype(np.uint8)

    return bmode_image