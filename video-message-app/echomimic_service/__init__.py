"""
EchoMimic Service - Audio-driven portrait animation

This service provides audio-driven portrait animation using the EchoMimic model.
It takes a reference face image and audio file to generate a video where the
face appears to speak the audio.

Components:
- config.py: Service configuration and paths
- models.py: Pydantic models for API
- inference.py: EchoMimic model wrapper
- face_utils.py: Face detection utilities
- main.py: FastAPI application

Usage:
    # Start the service
    python main.py

    # Or with uvicorn
    uvicorn main:app --host 0.0.0.0 --port 8005

API Endpoints:
    GET  /           - Root endpoint with service info
    GET  /health     - Health check with model status
    POST /generate-video - Generate video from image + audio
    GET  /job-status/{job_id} - Get job status
    GET  /result/{job_id} - Download result video
    POST /models/load - Manually load models
    POST /models/unload - Unload models to free VRAM
"""

__version__ = "1.0.0"
__service__ = "EchoMimic Service"
