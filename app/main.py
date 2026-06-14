import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import socketio

from app.config import settings
from app.database import supabase
from app.middleware.auth import get_current_user
from app.websockets.chat import sio

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    print(f"[{request.method}] {request.url.path} -> {response.status_code} ({duration}ms)")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] {request.url.path} - {exc}")
    return JSONResponse(status_code=500, content={"success": False, "detail": "Internal server error"})

PREFIX = f"/api/{settings.api_version}"
from app.routers import auth, patients, doctors, conversations, messages, appointments, admin, webhooks
for r in [auth, patients, doctors, conversations, messages, appointments, admin, webhooks]:
    app.include_router(r.router, prefix=PREFIX)

@app.get(f"{PREFIX}/health")
def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.api_version,
        "time": datetime.now(timezone.utc).isoformat(),
    }

socket_app = socketio.ASGIApp(sio, app)