# Copyright 2025 LeRobot Training API Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import uuid
import subprocess
import time
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create jobs directory if it doesn't exist
JOBS_DIR = Path("jobs")
JOBS_DIR.mkdir(exist_ok=True)

class JobManager:
    def __init__(self):
        """Initialize the job manager."""
        # Ensure tmux is installed
        try:
            subprocess.run(["tmux", "-V"], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("tmux is not installed. Job persistence may not work correctly.")
        
        # Load existing jobs from disk
        self.jobs = {}
        self._load_existing_jobs()

    def _load_existing_jobs(self):
        """Load existing jobs from disk."""
        for job_file in JOBS_DIR.glob("*.json"):
            try:
                with open(job_file, "r") as f:
                    job_data = json.load(f)
                    job_id = job_data.get("job_id")
                    if job_id:
                        self.jobs[job_id] = job_data
            except Exception as e:
                logger.error(f"Error loading job file {job_file}: {str(e)}")

    def _create_job_data(self, job_id: str, params: Dict[str, Any], status: str = "starting") -> Dict[str, Any]:
        """Create initial job data structure."""
        return {
            "job_id": job_id,
            "status": status,
            "start_time": datetime.now().isoformat(),
            "params": params,
            "progress": 0,
            "logs": [],
        }

    def _save_job_data(self, job_id: str, job_data: Dict[str, Any]):
        """Save job data to disk."""
        job_file = JOBS_DIR / f"{job_id}.json"
        with open(job_file, "w") as f:
            json.dump(job_data, f, indent=2)
        self.jobs[job_id] = job_data

    def _update_job_status(self, job_id: str, status: str, error: Optional[str] = None):
        """Update job status."""
        if job_id in self.jobs:
            job_data = self.jobs[job_id]
            job_data["status"] = status
            if error:
                job_data["error"] = error
            self._save_job_data(job_id, job_data)

    def _parse_progress(self, log_content: str) -> Optional[float]:
        """Parse training progress from log content."""
        # Look for patterns like "Step 1000/20000" or similar
        progress_pattern = r"Step\s+(\d+)/(\d+)"
        matches = re.findall(progress_pattern, log_content)
        
        if matches:
            # Get the last match
            current_step, total_steps = matches[-1]
            try:
                return (int(current_step) / int(total_steps)) * 100
            except (ValueError, ZeroDivisionError):
                return None
        
        return None

    def start_job(self, params: Dict[str, Any]) -> str:
        """Start a new training job in a tmux session."""
        job_id = str(uuid.uuid4())
        session_name = f"lerobot_job_{job_id[:8]}"
        log_file = JOBS_DIR / f"{job_id}.log"
        
        # Create initial job data
        job_data = self._create_job_data(job_id, params)
        self._save_job_data(job_id, job_data)
        
        # Build command for the training script
        cmd = [
            "python", "lerobot/lerobot", "-m", "lerobot.scripts.train",
            f"--policy.path={params.get('policy_path', 'lerobot/smolvla_base')}",
            f"--dataset.repo_id={params.get('dataset_repo_id')}",
            f"--batch_size={params.get('batch_size', 64)}",
            f"--steps={params.get('steps', 20000)}",
            f"--output_dir={params.get('output_dir', 'outputs/train/my_smolvla')}",
            f"--job_name={params.get('job_name', 'my_smolvla_training')}",
            f"--policy.device={params.get('policy_device', 'cuda')}",
            f"--wandb.enable={'true' if params.get('wandb_enable', True) else 'false'}"
        ]
        
        # Add additional arguments if provided
        if params.get('additional_args'):
            for key, value in params['additional_args'].items():
                cmd.append(f"--{key}={value}")
        
        # Create the command string for tmux
        cmd_str = " ".join(cmd)
        
        try:
            # Create a new tmux session
            create_session_cmd = [
                "tmux", "new-session", 
                "-d",  # Detached
                "-s", session_name,  # Session name
                f"cd /app && {cmd_str} | tee {log_file} ; echo 'Job completed with exit code $?' >> {log_file}"
            ]
            
            subprocess.run(create_session_cmd, check=True)
            
            # Update job status to running
            self._update_job_status(job_id, "running")
            
            # Start a background thread to monitor the job
            self._start_monitoring_thread(job_id, session_name, log_file)
            
            return job_id
        
        except Exception as e:
            logger.error(f"Failed to start job: {str(e)}")
            self._update_job_status(job_id, "error", str(e))
            return job_id

    def _start_monitoring_thread(self, job_id: str, session_name: str, log_file: Path):
        """Start a thread to monitor the job."""
        import threading
        
        def monitor_job():
            try:
                while True:
                    # Check if tmux session still exists
                    check_session_cmd = ["tmux", "has-session", "-t", session_name]
                    session_exists = subprocess.run(
                        check_session_cmd, 
                        capture_output=True, 
                        check=False
                    ).returncode == 0
                    
                    # Read logs
                    if log_file.exists():
                        with open(log_file, "r") as f:
                            log_content = f.read()
                        
                        # Parse progress
                        progress = self._parse_progress(log_content)
                        
                        # Update job data
                        if job_id in self.jobs:
                            job_data = self.jobs[job_id]
                            job_data["logs"] = log_content.splitlines()
                            if progress is not None:
                                job_data["progress"] = progress
                            
                            # Check for completion message
                            if "Job completed with exit code" in log_content:
                                exit_code_match = re.search(r"Job completed with exit code (\d+)", log_content)
                                if exit_code_match:
                                    exit_code = int(exit_code_match.group(1))
                                    if exit_code == 0:
                                        job_data["status"] = "completed"
                                    else:
                                        job_data["status"] = "failed"
                                        job_data["error"] = f"Process exited with code {exit_code}"
                                else:
                                    job_data["status"] = "completed"
                            
                            self._save_job_data(job_id, job_data)
                    
                    # If session doesn't exist and job isn't marked as completed/failed, mark as failed
                    if not session_exists and job_id in self.jobs:
                        job_data = self.jobs[job_id]
                        if job_data["status"] not in ["completed", "failed", "cancelled"]:
                            job_data["status"] = "failed"
                            job_data["error"] = "tmux session ended unexpectedly"
                            self._save_job_data(job_id, job_data)
                            break
                    
                    # If job is completed or failed, stop monitoring
                    if job_id in self.jobs and self.jobs[job_id]["status"] in ["completed", "failed", "cancelled"]:
                        break
                    
                    # Sleep to avoid CPU overuse
                    time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error monitoring job {job_id}: {str(e)}")
                if job_id in self.jobs:
                    self._update_job_status(job_id, "error", str(e))
        
        # Start the monitoring thread
        thread = threading.Thread(target=monitor_job, daemon=True)
        thread.start()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        # First check memory
        if job_id in self.jobs:
            return self.jobs[job_id]
        
        # Then check disk
        job_file = JOBS_DIR / f"{job_id}.json"
        if job_file.exists():
            try:
                with open(job_file, "r") as f:
                    job_data = json.load(f)
                    self.jobs[job_id] = job_data
                    return job_data
            except Exception as e:
                logger.error(f"Error reading job file {job_file}: {str(e)}")
        
        return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs."""
        # Refresh job list from disk
        self._load_existing_jobs()
        return list(self.jobs.values())

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job_data = self.get_job(job_id)
        if not job_data:
            return False
        
        if job_data["status"] not in ["running", "starting"]:
            return False
        
        # Get session name
        session_name = f"lerobot_job_{job_id[:8]}"
        
        try:
            # Check if session exists
            check_session_cmd = ["tmux", "has-session", "-t", session_name]
            session_exists = subprocess.run(
                check_session_cmd, 
                capture_output=True, 
                check=False
            ).returncode == 0
            
            if session_exists:
                # Kill the session
                kill_session_cmd = ["tmux", "kill-session", "-t", session_name]
                subprocess.run(kill_session_cmd, check=True)
            
            # Update job status
            self._update_job_status(job_id, "cancelled", "Job cancelled by user")
            return True
        
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {str(e)}")
            return False

# Create a singleton instance
job_manager = JobManager()
