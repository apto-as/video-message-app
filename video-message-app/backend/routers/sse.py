"""
Server-Sent Events (SSE) Router for Progress Tracking

Provides SSE endpoint as fallback for clients that don't support WebSocket.
SSE is simpler, HTTP-based, and works through most firewalls/proxies.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from services.progress_tracker import progress_tracker, EventType
from core.logging import get_logger
import asyncio

logger = get_logger(__name__)

router = APIRouter(prefix="/sse", tags=["sse"])


async def event_stream(task_id: str, request: Request):
    """
    Generate SSE event stream for a task

    Yields:
        SSE-formatted progress updates
    """
    logger.info(f"SSE connection established for task {task_id}")

    try:
        # Subscribe to progress updates
        async for event in progress_tracker.subscribe(task_id):
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected from task {task_id}")
                break

            # Send event in SSE format
            yield event.to_sse()

            # If complete or error, close stream
            if event.event_type in (EventType.COMPLETE, EventType.ERROR):
                logger.info(f"Task {task_id} completed/errored, closing SSE stream")
                break

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for task {task_id}")
    except Exception as e:
        logger.error(f"SSE stream error for task {task_id}: {e}")
        # Send error event
        error_event = f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        yield error_event


@router.get("/progress/{task_id}")
async def sse_progress(task_id: str, request: Request):
    """
    SSE endpoint for real-time progress updates

    Usage:
        const eventSource = new EventSource('/api/sse/progress/task-uuid');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };

    Returns:
        StreamingResponse with text/event-stream content type
    """
    return StreamingResponse(
        event_stream(task_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/health")
async def sse_health():
    """Health check for SSE service"""
    active_tasks = progress_tracker.get_active_tasks()

    return {
        "status": "healthy",
        "service": "SSE Progress Tracker",
        "active_tasks": len(active_tasks)
    }
