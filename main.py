import os
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from datetime import datetime
from pathlib import Path

# Import the job manager
from job_manager import job_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create jobs directory if it doesn't exist
JOBS_DIR = Path("jobs")
JOBS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="LeRobot Training API")

# Model for training job parameters
class TrainingJobParams(BaseModel):
    policy_path: str = "lerobot/smolvla_base"
    dataset_repo_id: str
    batch_size: int = 64
    steps: int = 20000
    output_dir: str = "outputs/train/my_smolvla"
    job_name: str = "my_smolvla_training"
    policy_device: str = "cuda"
    wandb_enable: bool = True
    hf_user: Optional[str] = None
    additional_args: Optional[Dict[str, Any]] = None

# Model for job status response
class JobStatus(BaseModel):
    job_id: str
    status: str
    start_time: str
    params: Dict[str, Any]
    progress: Optional[float] = None
    logs: Optional[List[str]] = None
    error: Optional[str] = None

@app.post("/jobs", response_model=JobStatus)
async def create_job(params: TrainingJobParams):
    """Start a new training job."""
    # Start the job using the job manager
    job_id = job_manager.start_job(params.dict())
    
    # Get the job data
    job_data = job_manager.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    return job_data

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a job."""
    job_data = job_manager.get_job(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_data

@app.get("/jobs", response_model=List[JobStatus])
async def list_jobs():
    """List all jobs."""
    return job_manager.list_jobs()

@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Failed to cancel job. Job may not exist or is not running.")
    
    return {"message": f"Job {job_id} cancelled successfully"}

@app.get("/")
async def root():
    """API root endpoint."""
    return {"message": "LeRobot Training API", "version": "1.0.0"}
