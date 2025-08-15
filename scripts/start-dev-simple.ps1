Write-Host "Starting AIVO Virtual Brains Platform - Development Mode" -ForegroundColor Green

# Start infrastructure first
Write-Host "Starting infrastructure services..." -ForegroundColor Blue
docker-compose up -d
Start-Sleep -Seconds 5

# Start all microservices
Write-Host "Starting auth-svc on port 3001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\auth-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn simple_main:app --reload --host 0.0.0.0 --port 3001"
Start-Sleep -Seconds 2

Write-Host "Starting user-svc on port 3002..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\user-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn simple_main:app --reload --host 0.0.0.0 --port 3002"
Start-Sleep -Seconds 2

Write-Host "Starting assessment-svc on port 3004..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\assessment-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn simple_main:app --reload --host 0.0.0.0 --port 3004"
Start-Sleep -Seconds 2

Write-Host "Starting slp-svc on port 3005..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\slp-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn simple_main:app --reload --host 0.0.0.0 --port 3005"
Start-Sleep -Seconds 2

Write-Host "Starting inference-gateway-svc on port 3006..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\inference-gateway-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn simple_main:app --reload --host 0.0.0.0 --port 3006"
Start-Sleep -Seconds 2

Write-Host "Starting search-svc on port 3007..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\aivo-virtual-brains\services\search-svc'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 3007"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Waiting for services to start up..." -ForegroundColor Blue
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Running health checks..." -ForegroundColor Blue

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/health" -Method GET -TimeoutSec 5
    Write-Host "✅ auth-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ auth-svc: Not responding" -ForegroundColor Red
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3002/health" -Method GET -TimeoutSec 5
    Write-Host "✅ user-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ user-svc: Not responding" -ForegroundColor Red
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3004/health" -Method GET -TimeoutSec 5
    Write-Host "✅ assessment-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ assessment-svc: Not responding" -ForegroundColor Red
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3005/health" -Method GET -TimeoutSec 5
    Write-Host "✅ slp-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ slp-svc: Not responding" -ForegroundColor Red
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3006/health" -Method GET -TimeoutSec 5
    Write-Host "✅ inference-gateway-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ inference-gateway-svc: Not responding" -ForegroundColor Red
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3007/health" -Method GET -TimeoutSec 5
    Write-Host "✅ search-svc: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ search-svc: Not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "Running Stage-2 verification..." -ForegroundColor Blue
pnpm run verify-stage2

Write-Host ""
Write-Host "Platform started! Services running on:" -ForegroundColor Green
Write-Host "   • auth-svc: http://localhost:3001" -ForegroundColor Cyan
Write-Host "   • user-svc: http://localhost:3002" -ForegroundColor Cyan
Write-Host "   • assessment-svc: http://localhost:3004" -ForegroundColor Cyan
Write-Host "   • slp-svc: http://localhost:3005" -ForegroundColor Cyan
Write-Host "   • inference-gateway-svc: http://localhost:3006" -ForegroundColor Cyan
Write-Host "   • search-svc: http://localhost:3007" -ForegroundColor Cyan
