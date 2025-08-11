# Gateway Integration Tests
# Test script for validating Kong + Apollo Router configuration

Write-Host "🔧 Testing aivo-virtual-brains API Gateway" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Wait for services to be ready
function Wait-ForService {
    param($Url, $Name, $MaxAttempts = 30)
    
    Write-Host "⏳ Waiting for $Name to be ready..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ $Name is ready!" -ForegroundColor Green
                return $true
            }
        } catch {
            Write-Host "⏱️  Attempt $i/$MaxAttempts - $Name not ready yet..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
    
    Write-Host "❌ $Name failed to become ready after $MaxAttempts attempts" -ForegroundColor Red
    return $false
}

# Test Kong Gateway Health
Write-Host "`n🌐 Testing Kong Gateway Health" -ForegroundColor Blue
$kongReady = Wait-ForService -Url "http://localhost:8003/gateway/health" -Name "Kong Gateway"

if ($kongReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8003/gateway/health" -UseBasicParsing
        Write-Host "📊 Kong Gateway Health Response:" -ForegroundColor Green
        Write-Host $response.Content -ForegroundColor White
    } catch {
        Write-Host "❌ Failed to get Kong health response: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test Apollo Router Health
Write-Host "`n🚀 Testing Apollo Router Health" -ForegroundColor Blue
$apolloReady = Wait-ForService -Url "http://localhost:4000/health" -Name "Apollo Router"

if ($apolloReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4000/health" -UseBasicParsing
        Write-Host "📊 Apollo Router Health Response:" -ForegroundColor Green
        Write-Host $response.Content -ForegroundColor White
    } catch {
        Write-Host "❌ Failed to get Apollo Router health response: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test Kong Admin API
Write-Host "`n🔧 Testing Kong Admin API" -ForegroundColor Blue
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/status" -UseBasicParsing
    Write-Host "📊 Kong Admin Status:" -ForegroundColor Green
    Write-Host $response.Content -ForegroundColor White
} catch {
    Write-Host "❌ Failed to get Kong admin status: $($_.Exception.Message)" -ForegroundColor Red
}

# Test JWT Authentication (should return 401)
Write-Host "`n🔐 Testing JWT Authentication (expect 401)" -ForegroundColor Blue
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8003/auth/profile" -UseBasicParsing -ErrorAction Stop
    Write-Host "❌ Expected 401 but got $($response.StatusCode)" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ JWT authentication working - returned 401 as expected" -ForegroundColor Green
    } else {
        Write-Host "❌ Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n🏁 Gateway Testing Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
