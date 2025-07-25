# LeRobot Training API

A simple API for running and managing LeRobot training jobs.

## Overview

This project provides:
1. A Dockerfile that sets up the LeRobot environment
2. A FastAPI-based REST API for managing training jobs

## Getting Started

### Building and Running with Docker

```bash
# Build the Docker image
docker build -t lerobot-training-api .

# Run the container
docker run -p 8000:8000 -v /path/to/your/data:/app/data lerobot-training-api
```

### API Endpoints

- `POST /jobs` - Start a new training job
- `GET /jobs/{job_id}` - Get status and logs of a specific job
- `GET /jobs` - List all jobs
- `DELETE /jobs/{job_id}` - Cancel a running job

## API Usage Examples

### Starting a Training Job

```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_repo_id": "your-huggingface-username/mydataset",
    "batch_size": 64,
    "steps": 20000,
    "policy_device": "cuda",
    "wandb_enable": true
  }'
```

### Getting Job Status and Logs

```bash
curl -X GET "http://localhost:8000/jobs/your-job-id"
```

### Listing All Jobs

```bash
curl -X GET "http://localhost:8000/jobs"
```

### Cancelling a Job

```bash
curl -X DELETE "http://localhost:8000/jobs/your-job-id"
```

## Configuration

The API allows customization of all training parameters:

- `policy_path`: Path to the policy (default: "lerobot/smolvla_base")
- `dataset_repo_id`: HuggingFace dataset repository ID (required)
- `batch_size`: Training batch size (default: 64)
- `steps`: Number of training steps (default: 20000)
- `output_dir`: Directory for training outputs (default: "outputs/train/my_smolvla")
- `job_name`: Name for the training job (default: "my_smolvla_training")
- `policy_device`: Device to run training on (default: "cuda")
- `wandb_enable`: Whether to enable Weights & Biases logging (default: true)
- `additional_args`: Any additional arguments to pass to the training script
