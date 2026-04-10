from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .engine_runs import write_engine_run_artifacts
from .models import EngineMetadata, SimulationRequest, SimulationResponse
from .settings import get_simulation_engine
from .simulation_engines import run_simulation_engine

app = FastAPI(title="US Head Simulation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for simulation results
app.mount("/static", StaticFiles(directory="run_artifacts"), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/simulations", response_model=SimulationResponse)
def create_simulation(request: SimulationRequest) -> SimulationResponse:
    job_id = str(uuid4())
    simulation_engine = get_simulation_engine()
    artifact_metadata = write_engine_run_artifacts(
        job_id=job_id,
        engine=simulation_engine,
        request=request,
        result=run_simulation_engine("baseline", request),
    )
    engine_result = run_simulation_engine(
        simulation_engine,
        request,
        handoff_path=artifact_metadata["handoff_path"],
        run_directory=artifact_metadata["run_directory"],
    )
    artifact_metadata = write_engine_run_artifacts(
        job_id=job_id,
        engine=simulation_engine,
        request=request,
        result=engine_result,
    )

    return SimulationResponse(
        job_id=job_id,
        status="completed",
        simulation_engine=simulation_engine,
        engine_metadata=EngineMetadata(
            engine=simulation_engine,
            adapter_version=artifact_metadata["adapter_version"],
            run_directory=artifact_metadata["run_directory"],
            manifest_path=artifact_metadata["manifest_path"],
            handoff_path=artifact_metadata["handoff_path"],
            tusx_input_path=artifact_metadata["tusx_input_path"],
            pressure_field_path=artifact_metadata["pressure_field_path"],
            receive_channel_data_path=artifact_metadata["receive_channel_data_path"],
            receive_channel_metadata_path=artifact_metadata["receive_channel_metadata_path"],
            reconstruction_metadata_path=artifact_metadata["reconstruction_metadata_path"],
            created_at_utc=artifact_metadata["created_at_utc"],
        ),
        grayscale_image_url=engine_result.grayscale_image_url,
        anatomy_model_id=request.anatomy_model_id,
        phantom_version=request.phantom_version,
        summary=engine_result.summary,
        path_segments=engine_result.path_segments,
        region_hits=engine_result.region_hits,
    )
