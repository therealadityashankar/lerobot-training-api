import os
import logging
import httpx
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import socket
from dotenv import load_dotenv

from db import get_db, init_db
from pod_manager import PodManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LeRobot Training Pod Manager",
    description="API for managing RunPod instances running LeRobot training jobs",
    version="0.1.0",
)

# Get RunPod API key from environment
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
if not RUNPOD_API_KEY:
    logger.warning("RUNPOD_API_KEY environment variable not set!")

# Get Docker image path from environment
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "ghcr.io/therealadityashankar/lerobot-training-api:latest")

# Initialize pod manager
pod_manager = PodManager(api_key=RUNPOD_API_KEY, docker_image=DOCKER_IMAGE)

# Models for API requests and responses
class PodCreateRequest(BaseModel):
    name: str = Field(default="LeRobot Training Pod", description="Name for the pod")
    gpu_type_id: str = Field(description="GPU type ID to use for the pod")
    gpu_count: int = Field(default=1, description="Number of GPUs to use")
    volume_in_gb: int = Field(default=50, description="Size of the pod volume in GB")
    container_disk_in_gb: int = Field(default=50, description="Size of the container disk in GB")
    interruptible: bool = Field(default=False, description="Whether to use spot/interruptible instances")
    cloud_type: str = Field(default="SECURE", description="Cloud type (SECURE or COMMUNITY)")
    env_vars: Dict[str, str] = Field(default={}, description="Environment variables to pass to the pod")

class PodResponse(BaseModel):
    pod_id: str
    name: str
    status: str
    public_ip: Optional[str] = None
    ports: Dict[str, int] = {}
    gpu_type: Optional[str] = None
    cost_per_hr: Optional[float] = None

class PodStatusResponse(BaseModel):
    pod_id: str
    status: str
    is_running: bool
    api_accessible: bool
    job_status: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    logs: Optional[str] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LeRobot Training Pod Manager API"}

@app.post("/pods", response_model=PodResponse)
async def create_pod(pod_request: PodCreateRequest):
    """Create a new RunPod pod with the LeRobot training Docker image"""
    try:
        pod = await pod_manager.create_pod(
            name=pod_request.name,
            gpu_type_id=pod_request.gpu_type_id,
            gpu_count=pod_request.gpu_count,
            volume_in_gb=pod_request.volume_in_gb,
            container_disk_in_gb=pod_request.container_disk_in_gb,
            interruptible=pod_request.interruptible,
            cloud_type=pod_request.cloud_type,
            env_vars=pod_request.env_vars
        )
        return pod
    except Exception as e:
        logger.error(f"Error creating pod: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create pod: {str(e)}")

@app.get("/pods/{pod_id}", response_model=PodStatusResponse)
async def get_pod_status(pod_id: str):
    """Get the status of a pod and check if its API is accessible"""
    try:
        status = await pod_manager.get_pod_status(pod_id)
        return status
    except Exception as e:
        logger.error(f"Error getting pod status: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Pod not found or error: {str(e)}")

@app.get("/pods/{pod_id}/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(pod_id: str, job_id: str):
    """Get the status and logs of a specific job running on a pod"""
    try:
        job_status = await pod_manager.get_job_status(pod_id, job_id)
        return job_status
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Job not found or error: {str(e)}")

@app.get("/pods", response_model=List[PodResponse])
async def list_pods():
    """List all pods"""
    try:
        pods = await pod_manager.list_pods()
        return pods
    except Exception as e:
        logger.error(f"Error listing pods: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list pods: {str(e)}")

@app.delete("/pods/{pod_id}")
async def terminate_pod(pod_id: str):
    """Terminate a pod"""
    try:
        result = await pod_manager.terminate_pod(pod_id)
        return {"message": f"Pod {pod_id} terminated successfully"}
    except Exception as e:
        logger.error(f"Error terminating pod: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to terminate pod: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
