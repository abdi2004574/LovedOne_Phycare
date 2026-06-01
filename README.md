# LovedonePsychCare Backend

LovedonePsychCare is a mental health platform for Pakistan. This repository contains the Python-based backend that handles:
- **FastAPI**: Main HTTP server and automatic OpenAPI documentation.
- **Socket.IO**: Real-time websocket chat.
- **Mock Database**: In-memory database for local development (no Supabase required).

## Quick Start (Local Development)

### 1. Start the Backend
```bash
# From the project root
pip install -r requirements.txt
python -m uvicorn app.main:socket_app --reload --port 8000
```

### 2. Start the Frontend
```bash
# From the frontend directory
cd frontend
npm install
npm run dev
```

### 3. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Demo Accounts
| Role | Email | Password |
|------|-------|----------|
| User | demo@lopc.com | demo123 |
| Therapist | dr.sarah@lopc.com | therapist123 |
| Admin | admin@lopc.com | admin123 |

## Deployment with Supabase

For production deployment with a real Supabase database:

### 1. Requirements
Dependencies are specified in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file at the root directory based on `.env.example` with your real Supabase credentials:
```env
# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_KEY=your-service-role-key

# JWT Token Settings
JWT_SECRET=change-this-to-a-random-32-char-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration (Sukoon Assistant)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx

# Application Mode
ENVIRONMENT=development
FRONTEND_URL=https://lovedonepsychcare.vercel.app
```

### 3. Database Schema setup

Run the SQL code located in Step 12 of the setup prompt (or your SQL repository) inside your Supabase project's SQL Editor to set up:
- Table schemas: `profiles`, `patients`, `doctors`, `conversations`, `messages`, `appointments`, and `api_keys`.
- Row Level Security (RLS) policies.
- Realtime publication flags for `messages` and `conversations`.

### 4. Running the Application locally

Start the local server using `uvicorn`:
```bash
uvicorn app.main:socket_app --reload --port 8000
```
Open `http://localhost:8000/docs` to access the interactive FastAPI Swagger documentation.

## Deployment

This repository includes a `Dockerfile` and a `railway.toml` file to easily deploy to platforms like Railway or Render.
- The `Dockerfile` containers the python app and runs using the standard Socket.IO ASGI server.
- The server will run on the port specified by the `$PORT` environment variable under production settings.
