# LeRobot Training Pod Manager

A service that manages RunPod instances running LeRobot training jobs. This pod manager allows you to:

1. Create RunPod pods with the LeRobot training Docker image
2. Check if a pod is running and accessible
3. Get job status and logs from running pods
4. Manage pods (list, terminate)

## Requirements

- Python 3.10+
- RunPod API key
- Docker image with LeRobot training API

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file based on the example:

```bash
cp .env.example .env
```

3. Edit the `.env` file and add your RunPod API key and Docker image path:

```
RUNPOD_API_KEY=your_runpod_api_key_here
DOCKER_IMAGE=ghcr.io/therealadityashankar/lerobot-training-api:latest
```

4. Initialize the database with dbmate:

```bash
mkdir -p db/migrations
dbmate up
```

## Running the Service

Start the API server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Create a Pod

```
POST /pods
```

Request body:

```json
{
  "name": "LeRobot Training Pod",
  "gpu_type_id": "NVIDIA GeForce RTX 4090",
  "gpu_count": 1,
  "volume_in_gb": 50,
  "container_disk_in_gb": 50,
  "interruptible": false,
  "cloud_type": "SECURE",
  "env_vars": {
    "SOME_ENV_VAR": "value"
  }
}
```

### Get Pod Status

```
GET /pods/{pod_id}
```

### Get Job Status

```
GET /pods/{pod_id}/jobs/{job_id}
```

### List Pods

```
GET /pods
```

### Terminate Pod

```
DELETE /pods/{pod_id}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RUNPOD_API_KEY` | RunPod API key | (required) |
| `DOCKER_IMAGE` | Docker image path | `ghcr.io/therealadityashankar/lerobot-training-api:latest` |
| `DB_PATH` | SQLite database path | `pod_manager.db` |

## Database Schema

The pod manager uses SQLite with the following schema:

### Pods Table

- `id`: Pod ID from RunPod
- `name`: User-defined name for the pod
- `gpu_type`: GPU type ID
- `gpu_count`: Number of GPUs
- `status`: Pod status (STARTING, RUNNING, TERMINATED)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `terminated_at`: Termination timestamp (if applicable)
- `public_ip`: Public IP address of the pod
- `cost_per_hr`: Hourly cost of the pod

### Jobs Table

- `id`: Job ID
- `pod_id`: Associated pod ID
- `status`: Job status
- `progress`: Training progress (0-100%)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `completed_at`: Completion timestamp (if applicable)
- `error`: Error message (if applicable)
