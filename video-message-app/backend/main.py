from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import uvicorn
import time
import os
from routers import voice, voicevox, unified_voice, voice_clone, background, d_id, websocket, sse, video_generation
from core.config import settings

# Optional: Person Detection (Phase 2 feature - requires YOLO dependencies)
try:
    from routers import person_detection
    PERSON_DETECTION_AVAILABLE = True
except ImportError:
    PERSON_DETECTION_AVAILABLE = False
    logger = None  # Will be set after logging is initialized
from core.logging import setup_logging, get_logger, log_api_request, log_error, log_info
from services.progress_tracker import progress_tracker
from middleware.rate_limiter import limiter, rate_limit_exceeded_handler, check_redis_health

# Setup logging
is_production = os.path.exists('/home/ec2-user')
log_level = "INFO" if is_production else "DEBUG"
setup_logging(level=log_level, json_format=is_production)

# Get logger
logger = get_logger(__name__)

app = FastAPI(title="Video Message API", version="1.0.0")

# Rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Log startup
log_info(
    "Starting Video Message API",
    environment="production" if is_production else "development",
    version="1.0.0"
)

# CORS設定（セキュリティ強化）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Accept-Language",
        "Content-Language",
        "X-Requested-With"
    ],
    max_age=600,  # プリフライトキャッシュ10分
)

# ルーター登録
app.include_router(voice.router, prefix="/api/voices", tags=["voice"])
app.include_router(voicevox.router, prefix="/api", tags=["voicevox"])
app.include_router(unified_voice.router, prefix="/api", tags=["unified_voice"])
app.include_router(voice_clone.router, prefix="/api", tags=["voice_clone"])
app.include_router(background.router, prefix="/api", tags=["background"])
app.include_router(d_id.router, prefix="/api/d-id", tags=["d-id"])

# Optional: Person Detection (Phase 2 - 2025年12月)
if PERSON_DETECTION_AVAILABLE:
    app.include_router(person_detection.router)  # /api/person-detection prefix included in router
    log_info("Person detection router enabled (YOLO dependencies available)")
else:
    logger.warning("Person detection router disabled (YOLO dependencies not installed)")

app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(sse.router, prefix="/api", tags=["sse"])
app.include_router(video_generation.router, tags=["video-generation"])

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # セキュリティヘッダー追加
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests and responses"""
    start_time = time.time()
    
    # Log request
    logger.debug(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    log_api_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration
    )
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging"""
    log_error(
        "Unhandled exception",
        error=exc,
        method=request.method,
        path=request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"error": "サーバーエラーが発生しました", "details": str(exc)}
    )

@app.get("/")
async def root():
    return {"message": "Video Message API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    log_info("Starting up services...")

    # Check Redis health for rate limiting
    redis_healthy = await check_redis_health()
    if redis_healthy:
        log_info("Redis connection healthy - rate limiting enabled")
    else:
        logger.warning("Redis connection failed - rate limiting may not work properly")

    await progress_tracker.start()
    log_info("Progress tracker started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    log_info("Shutting down services...")
    await progress_tracker.stop()
    log_info("Progress tracker stopped")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=55433)