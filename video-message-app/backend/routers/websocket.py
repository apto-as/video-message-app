"""
WebSocket Router for Real-time Progress Tracking

Provides WebSocket endpoint for clients to subscribe to task progress updates.
Supports multiple concurrent connections with automatic cleanup.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from services.progress_tracker import progress_tracker, EventType
from core.logging import get_logger
import asyncio
import json

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time progress updates

    Protocol:
    - Client connects to /ws/progress/{task_id}
    - Server sends JSON messages with progress updates
    - Server sends heartbeat every 30 seconds
    - Connection closes when task completes or client disconnects

    Message Format:
    {
        "task_id": "uuid",
        "event_type": "stage_update|progress_update|error|complete|heartbeat",
        "data": {...},
        "timestamp": "2025-11-07T12:34:56.789Z"
    }
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for task {task_id}")

    try:
        # Subscribe to progress updates
        async for event in progress_tracker.subscribe(task_id):
            try:
                # Send event as JSON
                await websocket.send_text(event.to_json())

                # If complete or error, close connection gracefully
                if event.event_type in (EventType.COMPLETE, EventType.ERROR):
                    logger.info(f"Task {task_id} completed/errored, closing WebSocket")
                    break

            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected from task {task_id}")
                break
            except Exception as e:
                logger.error(f"Error sending WebSocket message for {task_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.get("/progress/{task_id}/history")
async def get_progress_history(task_id: str):
    """
    Get historical progress events for a task (HTTP fallback)

    Returns:
        List of progress events with timestamps
    """
    history = progress_tracker.get_progress_history(task_id)

    return {
        "task_id": task_id,
        "event_count": len(history),
        "events": [json.loads(event.to_json()) for event in history]
    }


@router.get("/progress/{task_id}/latest")
async def get_latest_progress(task_id: str):
    """
    Get latest progress event for a task (HTTP polling fallback)

    Returns:
        Latest progress event or null if no events
    """
    latest = progress_tracker.get_latest_progress(task_id)

    if latest is None:
        return {
            "task_id": task_id,
            "event": None,
            "message": "No progress events found for this task"
        }

    return {
        "task_id": task_id,
        "event": json.loads(latest.to_json())
    }


@router.get("/active-tasks")
async def get_active_tasks():
    """
    Get list of tasks with active subscribers

    Returns:
        List of task IDs with subscriber counts
    """
    active_tasks = progress_tracker.get_active_tasks()

    return {
        "active_task_count": len(active_tasks),
        "tasks": [
            {
                "task_id": task_id,
                "subscriber_count": progress_tracker.get_subscriber_count(task_id)
            }
            for task_id in active_tasks
        ]
    }


@router.get("/health")
async def websocket_health():
    """Health check for WebSocket service"""
    active_tasks = progress_tracker.get_active_tasks()

    return {
        "status": "healthy",
        "service": "WebSocket Progress Tracker",
        "active_tasks": len(active_tasks),
        "max_connections": 100  # Configurable
    }
