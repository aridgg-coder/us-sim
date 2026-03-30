#!/usr/bin/env python3
"""
Create a synthetic head model with concentric spheres for TUSX testing.

Generates a NIfTI file with:
- Outer sphere: skull (value 2)
- Middle sphere: brain tissue (value 1)
- Inner sphere: cerebrospinal fluid or core (value 0)
- Background: water/air (value 0)

Dimensions: 256x256x256 voxels
Voxel size: 0.5 mm (total ~12.8 cm cube)
"""

import numpy as np
import nibabel as nib
import os

def create_concentric_spheres(shape=(256, 256, 256), center=None):
    """
    Create a 3D array with concentric spheres.

    Returns:
        np.ndarray: 3D array with tissue labels
    """
    if center is None:
        center = np.array(shape) // 2

    # Create coordinate grids
    x, y, z = np.ogrid[:shape[0], :shape[1], :shape[2]]

    # Calculate distances from center
    distances = np.sqrt((x - center[0])**2 + (y - center[1])**2 + (z - center[2])**2)

    # Define radii (in voxels)
    # Head diameter ~15cm = 300 voxels at 0.5mm, so radius ~150 voxels
    skull_outer_radius = 140  # ~7cm radius
    brain_radius = 120        # ~6cm radius
    csf_radius = 100          # ~5cm radius

    # Create tissue mask
    tissue = np.zeros(shape, dtype=np.uint8)

    # CSF/core (innermost)
    tissue[distances <= csf_radius] = 0

    # Brain tissue
    brain_mask = (distances > csf_radius) & (distances <= brain_radius)
    tissue[brain_mask] = 1

    # Skull
    skull_mask = (distances > brain_radius) & (distances <= skull_outer_radius)
    tissue[skull_mask] = 2

    # Background remains 0 (water/air)

    return tissue

def main():
    # Create the synthetic head volume
    print("Creating synthetic head model...")
    head_volume = create_concentric_spheres()

    # Create affine matrix (0.5mm isotropic voxels)
    voxel_size = 0.5  # mm
    affine = np.eye(4)
    affine[0, 0] = voxel_size
    affine[1, 1] = voxel_size
    affine[2, 2] = voxel_size

    # Create NIfTI image
    nii_img = nib.Nifti1Image(head_volume, affine)

    # Save to file
    output_path = os.path.join(os.path.dirname(__file__), 'data', 'synthetic_head.nii.gz')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    nib.save(nii_img, output_path)
    print(f"Synthetic head model saved to: {output_path}")
    print(f"Shape: {head_volume.shape}")
    print(f"Unique values: {np.unique(head_volume)}")
    print("Value meanings: 0=CSF/water, 1=brain, 2=skull")

if __name__ == "__main__":
    main()