# PowerShell script to start both backend and frontend
Write-Host "Starting LovedOne PsyCare development servers..." -ForegroundColor Cyan

# Start backend in background
$backend = Start-Process -FilePath "python" -ArgumentList "-m uvicorn Backend.main:socket_app --reload --port 8000" -WorkingDirectory $PWD -PassThru -WindowStyle Hidden
Write-Host "Backend starting on port 8000..." -ForegroundColor Green

# Wait for backend to be ready
$maxRetries = 30
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Start-Sleep -Seconds 1
        $retry++
    }
}

# Start frontend
Set-Location -Path "frontend"
npm run dev

# Cleanup on exit
Register-EngineEvent -CloseNow -Action {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}