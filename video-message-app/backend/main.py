from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from routers import voice, voicevox, unified_voice, voice_clone, background, d_id
from core.config import settings

app = FastAPI(title="Video Message API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(voice.router, prefix="/api/voices", tags=["voice"])
app.include_router(voicevox.router, prefix="/api", tags=["voicevox"])
app.include_router(unified_voice.router, prefix="/api", tags=["unified_voice"])
app.include_router(voice_clone.router, prefix="/api", tags=["voice_clone"])
app.include_router(background.router, prefix="/api", tags=["background"])
app.include_router(d_id.router, prefix="/api/d-id", tags=["d-id"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=55433)