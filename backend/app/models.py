from typing import Literal

from pydantic import BaseModel, Field


class Vector3(BaseModel):
    x: float
    y: float
    z: float


class ProbePose(BaseModel):
    position_mm: Vector3
    rotation_deg: Vector3


class UltrasoundParameters(BaseModel):
    frequency_mhz: float = Field(gt=0)
    focal_depth_mm: float = Field(gt=0)
    gain_db: float
    intensity: float = Field(ge=0)
    contact_angle_deg: float
    coupling_quality: float = Field(ge=0, le=1)


class SimulationRequest(BaseModel):
    anatomy_model_id: str
    phantom_version: str = "baseline-v1"
    probe_pose: ProbePose
    ultrasound_parameters: UltrasoundParameters
    output_mode: Literal["baseline", "high_fidelity"] = "baseline"


class SimulationSummary(BaseModel):
    attenuation_estimate: float
    focal_region_depth_mm: float
    estimated_latency_ms: int
    reflection_estimate: float


class PathSegment(BaseModel):
    structure_id: str
    tissue_id: str
    length_mm: float
    attenuation_contribution: float


class RegionHit(BaseModel):
    structure_id: str
    label: str
    hit_strength: float


class EngineMetadata(BaseModel):
    engine: Literal["baseline", "tusx", "babelbrain"]
    adapter_version: str
    run_directory: str
    manifest_path: str
    handoff_path: str
    tusx_input_path: str = ""
    pressure_field_path: str = ""
    receive_channel_data_path: str = ""
    receive_channel_metadata_path: str = ""
    reconstruction_metadata_path: str = ""
    created_at_utc: str


class SimulationResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed"]
    simulation_engine: Literal["baseline", "tusx", "babelbrain"]
    engine_metadata: EngineMetadata
    grayscale_image_url: str
    anatomy_model_id: str
    phantom_version: str
    summary: SimulationSummary
    path_segments: list[PathSegment]
    region_hits: list[RegionHit]
