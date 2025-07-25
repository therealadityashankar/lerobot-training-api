# LeRobot Training API & Pod Manager

This repository contains two main components for managing LeRobot training jobs:

1. **Docker API** - A containerized API for running LeRobot training jobs with persistence
2. **Pod Manager** - A service for creating and managing RunPod instances running the Docker API

## Project Structure

```
lerobot-training-api/
├── docker-api/           # Containerized API for running LeRobot training jobs
│   ├── Dockerfile        # Docker configuration for LeRobot training environment
│   ├── main.py           # FastAPI application for job management
│   ├── job_manager.py    # Module for managing training jobs with tmux
│   ├── LICENSE           # Apache License 2.0
│   └── README.md         # Docker API documentation
│
├── pod-manager/          # Service for managing RunPod instances
│   ├── main.py           # FastAPI application for pod management
│   ├── pod_manager.py    # Module for RunPod API integration
│   ├── db.py             # Database module for persistent storage
│   ├── db/migrations/    # Database migration files
│   ├── .env.example      # Example environment configuration
│   ├── .env.dbmate       # Database migration configuration
│   └── README.md         # Pod Manager documentation
│
└── README.md             # This file
```

## Docker API

The Docker API is a containerized service that:

- Runs LeRobot training jobs in the background using tmux for persistence
- Tracks job progress and logs via JSON files
- Provides REST endpoints for job control and monitoring
- Uses uv for faster package management (instead of conda)
- Includes CUDA support for GPU training

See the [Docker API README](docker-api/README.md) for detailed documentation.

## Pod Manager

The Pod Manager is a service that:

- Creates RunPod instances with the LeRobot training Docker image
- Monitors pod status and checks if they're accessible
- Retrieves job status and logs from running pods
- Manages the lifecycle of pods (listing, terminating)
- Uses SQLite for persistent storage

See the [Pod Manager README](pod-manager/README.md) for detailed documentation.

## Getting Started

### Using the Docker API Directly

1. Build the Docker image:
   ```bash
   cd docker-api
   docker build -t lerobot-training-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 lerobot-training-api
   ```

3. Access the API at http://localhost:8000

### Using the Pod Manager

1. Set up the Pod Manager:
   ```bash
   cd pod-manager
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. Edit the `.env` file to add your RunPod API key and Docker image path.

3. Initialize the database:
   ```bash
   dbmate up
   ```

4. Start the Pod Manager:
   ```bash
   ./run.sh
   ```

5. Access the Pod Manager API at http://localhost:8000

## Workflow

1. Use the Pod Manager to create a RunPod instance with the LeRobot training Docker image
2. The Pod Manager will monitor the pod and check if it's accessible
3. Once the pod is running, use the Docker API endpoints to start and manage training jobs
4. The Pod Manager can retrieve job status and logs from the running pod

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
