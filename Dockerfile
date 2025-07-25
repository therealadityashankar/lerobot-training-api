FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    tmux \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv for faster package installation
RUN pip install uv

# Clone LeRobot repository
RUN git clone https://github.com/huggingface/lerobot.git

# Install LeRobot and its dependencies
RUN cd lerobot && uv pip install -e .
RUN cd lerobot && uv pip install -e ".[smolvla]"

# Copy our API code
COPY . /app/api

# Set working directory to our API
WORKDIR /app/api

# Install API dependencies
RUN uv pip install fastapi uvicorn python-multipart

# Expose port for API
EXPOSE 8000

# Command to run the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
