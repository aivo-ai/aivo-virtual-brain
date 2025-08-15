#!/usr/bin/env pwsh

Write-Host "🚀 Starting AIVO Virtual Brains Platform - Development Mode" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

# Start infrastructure first
Write-Host "📦 Starting infrastructure services..." -ForegroundColor Blue
docker-compose up -d
Start-Sleep -Seconds 5

# Start all microservices
$services = @(
    @{Name="auth-svc"; Port=3001; Path="services/auth-svc"; MainFile="simple_main.py"},
    @{Name="user-svc"; Port=3002; Path="services/user-svc"; MainFile="simple_main.py"},
    @{Name="assessment-svc"; Port=3004; Path="services/assessment-svc"; MainFile="simple_main.py"},
    @{Name="slp-svc"; Port=3005; Path="services/slp-svc"; MainFile="simple_main.py"},
    @{Name="inference-gateway-svc"; Port=3006; Path="services/inference-gateway-svc"; MainFile="simple_main.py"},
    @{Name="search-svc"; Port=3007; Path="services/search-svc"; MainFile="main.py"}
)

foreach ($service in $services) {
    Write-Host "🔧 Starting $($service.Name) on port $($service.Port)..." -ForegroundColor Yellow
    
    $scriptBlock = "Set-Location 'c:\aivo-virtual-brains\$($service.Path)'; Write-Host 'Starting $($service.Name)...'; c:\aivo-virtual-brains\.venv\Scripts\python.exe -m uvicorn $($service.MainFile.Replace('.py', '')):app --reload --host 0.0.0.0 --port $($service.Port)"
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $scriptBlock
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "⏳ Waiting for services to start up..." -ForegroundColor Blue
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "🩺 Running health checks..." -ForegroundColor Blue

foreach ($service in $services) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$($service.Port)/health" -Method GET -TimeoutSec 5
        Write-Host "✅ $($service.Name): $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($service.Name): Not responding" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🧪 Running Stage-2 verification..." -ForegroundColor Blue
pnpm run verify-stage2

Write-Host ""
Write-Host "🎉 Platform started! Services running on:" -ForegroundColor Green
foreach ($service in $services) {
    Write-Host "   • $($service.Name): http://localhost:$($service.Port)" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "📊 Infrastructure UIs:" -ForegroundColor Green
Write-Host "   • Kong Manager: http://localhost:8002" -ForegroundColor Cyan
Write-Host "   • Grafana: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   • Jaeger: http://localhost:16686" -ForegroundColor Cyan
Write-Host "   • OpenSearch: http://localhost:9200" -ForegroundColor Cyan
