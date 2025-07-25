import os
import json
import socket
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
import httpx
from datetime import datetime

from db import get_db, Pod, Job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class PodManager:
    """
    Manager for RunPod pods running LeRobot training jobs
    """
    
    def __init__(self, api_key: str, docker_image: str):
        """
        Initialize the pod manager
        
        Args:
            api_key: RunPod API key
            docker_image: Docker image to use for pods
        """
        self.api_key = api_key
        self.docker_image = docker_image
        self.api_base_url = "https://rest.runpod.io/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make a request to the RunPod API
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            API response as a dictionary
        """
        url = f"{self.api_base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status_code >= 400:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code} - {response.text}")
                
            return response.json()
    
    async def create_pod(self, name: str, gpu_type_id: str, gpu_count: int = 1,
                         volume_in_gb: int = 50, container_disk_in_gb: int = 50,
                         interruptible: bool = False, cloud_type: str = "SECURE",
                         env_vars: Dict[str, str] = {}) -> Dict:
        """
        Create a new RunPod pod
        
        Args:
            name: Name for the pod
            gpu_type_id: GPU type ID
            gpu_count: Number of GPUs
            volume_in_gb: Size of the pod volume in GB
            container_disk_in_gb: Size of the container disk in GB
            interruptible: Whether to use spot/interruptible instances
            cloud_type: Cloud type (SECURE or COMMUNITY)
            env_vars: Environment variables to pass to the pod
            
        Returns:
            Pod information
        """
        payload = {
            "name": name,
            "imageName": self.docker_image,
            "gpuCount": gpu_count,
            "volumeInGb": volume_in_gb,
            "containerDiskInGb": container_disk_in_gb,
            "gpuTypeId": gpu_type_id,
            "cloudType": cloud_type,
            "interruptible": interruptible,
            "ports": ["8000/http", "22/tcp"],  # Expose API port and SSH
            "env": env_vars
        }
        
        response = await self._make_request("POST", "/pods", payload)
        
        # Save pod to database
        async with get_db() as db:
            pod = Pod(
                id=response["id"],
                name=name,
                gpu_type=gpu_type_id,
                gpu_count=gpu_count,
                status="STARTING",
                created_at=datetime.now().isoformat(),
                public_ip=response.get("publicIp"),
                cost_per_hr=response.get("costPerHr")
            )
            await db.execute(
                "INSERT INTO pods (id, name, gpu_type, gpu_count, status, created_at, public_ip, cost_per_hr) "
                "VALUES (:id, :name, :gpu_type, :gpu_count, :status, :created_at, :public_ip, :cost_per_hr)",
                pod.dict()
            )
            await db.commit()
        
        # Format response
        return {
            "pod_id": response["id"],
            "name": name,
            "status": response.get("desiredStatus", "STARTING"),
            "public_ip": response.get("publicIp"),
            "ports": response.get("portMappings", {}),
            "gpu_type": gpu_type_id,
            "cost_per_hr": response.get("costPerHr")
        }
    
    async def get_pod_status(self, pod_id: str) -> Dict:
        """
        Get the status of a pod and check if its API is accessible
        
        Args:
            pod_id: ID of the pod
            
        Returns:
            Pod status information
        """
        response = await self._make_request("GET", f"/pod/{pod_id}")
        
        # Check if the pod's API is accessible
        api_accessible = False
        job_status = None
        
        if response.get("publicIp") and response.get("portMappings", {}).get("8000"):
            # Try to connect to the pod's API
            api_url = f"http://{response['publicIp']}:{response['portMappings']['8000']}"
            try:
                async with httpx.AsyncClient() as client:
                    api_response = await client.get(f"{api_url}/jobs", timeout=5.0)
                    if api_response.status_code == 200:
                        api_accessible = True
                        job_status = api_response.json()
            except Exception as e:
                logger.warning(f"Could not connect to pod API: {str(e)}")
        
        # Update pod status in database
        status = response.get("desiredStatus", "UNKNOWN")
        async with get_db() as db:
            await db.execute(
                "UPDATE pods SET status = ?, public_ip = ?, updated_at = ? WHERE id = ?",
                (status, response.get("publicIp"), datetime.now().isoformat(), pod_id)
            )
            await db.commit()
        
        return {
            "pod_id": pod_id,
            "status": status,
            "is_running": status == "RUNNING",
            "api_accessible": api_accessible,
            "job_status": job_status,
            "logs": None  # We don't have logs from the pod itself
        }
    
    async def get_job_status(self, pod_id: str, job_id: str) -> Dict:
        """
        Get the status and logs of a specific job running on a pod
        
        Args:
            pod_id: ID of the pod
            job_id: ID of the job
            
        Returns:
            Job status information
        """
        # First get the pod status to ensure it's running and get its IP
        pod_status = await self.get_pod_status(pod_id)
        
        if not pod_status["api_accessible"]:
            raise Exception("Pod API is not accessible")
        
        # Get pod IP and port
        pod_info = await self._make_request("GET", f"/pod/{pod_id}")
        pod_ip = pod_info.get("publicIp")
        pod_port = pod_info.get("portMappings", {}).get("8000")
        
        if not pod_ip or not pod_port:
            raise Exception("Pod IP or port not available")
        
        # Query the pod's API for job status
        api_url = f"http://{pod_ip}:{pod_port}"
        async with httpx.AsyncClient() as client:
            job_response = await client.get(f"{api_url}/jobs/{job_id}", timeout=10.0)
            
            if job_response.status_code != 200:
                raise Exception(f"Failed to get job status: {job_response.status_code}")
                
            job_data = job_response.json()
            
            # Update job in database
            async with get_db() as db:
                # Check if job exists
                job = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
                
                if not job:
                    # Create new job record
                    await db.execute(
                        "INSERT INTO jobs (id, pod_id, status, progress, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (job_id, pod_id, job_data.get("status", "UNKNOWN"), 
                         job_data.get("progress", 0.0), datetime.now().isoformat(), 
                         datetime.now().isoformat())
                    )
                else:
                    # Update existing job
                    await db.execute(
                        "UPDATE jobs SET status = ?, progress = ?, updated_at = ? WHERE id = ?",
                        (job_data.get("status", "UNKNOWN"), job_data.get("progress", 0.0),
                         datetime.now().isoformat(), job_id)
                    )
                
                await db.commit()
            
            return {
                "job_id": job_id,
                "status": job_data.get("status", "UNKNOWN"),
                "progress": job_data.get("progress"),
                "logs": job_data.get("logs"),
                "error": job_data.get("error")
            }
    
    async def list_pods(self) -> List[Dict]:
        """
        List all pods
        
        Returns:
            List of pod information
        """
        response = await self._make_request("GET", "/pods")
        pods = []
        
        for pod_data in response.get("pods", []):
            pods.append({
                "pod_id": pod_data["id"],
                "name": pod_data.get("name", "Unknown"),
                "status": pod_data.get("desiredStatus", "UNKNOWN"),
                "public_ip": pod_data.get("publicIp"),
                "ports": pod_data.get("portMappings", {}),
                "gpu_type": pod_data.get("gpu", {}).get("displayName"),
                "cost_per_hr": pod_data.get("costPerHr")
            })
        
        return pods
    
    async def terminate_pod(self, pod_id: str) -> bool:
        """
        Terminate a pod
        
        Args:
            pod_id: ID of the pod
            
        Returns:
            True if successful
        """
        await self._make_request("DELETE", f"/pod/{pod_id}")
        
        # Update pod status in database
        async with get_db() as db:
            await db.execute(
                "UPDATE pods SET status = ?, terminated_at = ? WHERE id = ?",
                ("TERMINATED", datetime.now().isoformat(), pod_id)
            )
            await db.commit()
        
        return True
