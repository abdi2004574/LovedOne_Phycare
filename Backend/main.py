import socketio
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from Backend.config import settings
from Backend.database import supabase
from Backend.middleware.auth import get_current_user
from Backend.websockets.chat import sio

# Import all routers
from Backend.routers import (
    auth, patients, doctors,
    conversations, messages,
    appointments, admin, webhooks,
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="LovedonePsychCare API",
    version="2.0.0",
    description="Backend for LovedonePsychCare — live Supabase-backed mental health platform for Pakistan.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers under /api/v1
PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(patients.router,      prefix=PREFIX)
app.include_router(doctors.router,       prefix=PREFIX)
app.include_router(conversations.router, prefix=PREFIX)
app.include_router(messages.router,      prefix=PREFIX)
app.include_router(appointments.router,  prefix=PREFIX)
app.include_router(admin.router,         prefix=PREFIX)
app.include_router(webhooks.router,      prefix=PREFIX)


@app.get("/auth/me", tags=["Auth"])
def auth_me(current_user: dict = Depends(get_current_user)):
    profile = supabase.table("profiles").select("*").eq("id", current_user["sub"]).single().execute()
    if not profile.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.data


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "environment": settings.environment}

# Wrap FastAPI inside Socket.IO ASGI app
# This enables both HTTP (FastAPI) and WebSocket (Socket.IO) on the same server
socket_app = socketio.ASGIApp(sio, app)

# ─── Run ─────────────────────────────────────────────────────────────────────
# Development:  uvicorn Backend.main:socket_app --reload --port 8000
# Production:   uvicorn Backend.main:socket_app --host 0.0.0.0 --port $PORT
