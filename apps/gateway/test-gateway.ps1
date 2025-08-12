# Gateway Integration Tests
# ASCII-safe script for validating Kong + Apollo Router configuration

Write-Host "Testing aivo-virtual-brains API Gateway" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

function Wait-ForService {
    param(
        [string]$Url,
        [string]$Name,
        [int]$MaxAttempts = 10
    )

    Write-Host "Waiting for $Name to be ready..." -ForegroundColor Yellow

    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "$Name is ready (200)." -ForegroundColor Green
                return $true
            }
        } catch {
            Write-Host "Attempt $i/$MaxAttempts - $Name not ready yet..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }

    Write-Host "$Name failed after $MaxAttempts attempts" -ForegroundColor Red
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        Write-Host "Last response status: $($resp.StatusCode)" -ForegroundColor Yellow
        if ($resp.Content) { Write-Host "Response body: $($resp.Content)" -ForegroundColor DarkYellow }
    } catch {
        Write-Host "Last error: $($_.Exception.Message)" -ForegroundColor Yellow
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            Write-Host "Last status code: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Yellow
        }
    }
    return $false
}

# Kong Gateway Health
Write-Host "`nTesting Kong Gateway Health" -ForegroundColor Blue
$kongReady = Wait-ForService -Url "http://localhost:8003/gateway/health" -Name "Kong Gateway" -MaxAttempts 10
if ($kongReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8003/gateway/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "Kong Gateway Health Response:" -ForegroundColor Green
        Write-Host $response.Content -ForegroundColor White
    } catch {
        Write-Host "Failed to get Kong health response: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Apollo Router Health
Write-Host "`nTesting Apollo Router Health" -ForegroundColor Blue
$apolloReady = Wait-ForService -Url "http://localhost:4000/health" -Name "Apollo Router" -MaxAttempts 10
if ($apolloReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4000/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "Apollo Router Health Response:" -ForegroundColor Green
        Write-Host $response.Content -ForegroundColor White
    } catch {
        Write-Host "Failed to get Apollo Router health response: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Kong Admin API
Write-Host "`nTesting Kong Admin API" -ForegroundColor Blue
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/status" -UseBasicParsing -TimeoutSec 5
    Write-Host "Kong Admin Status:" -ForegroundColor Green
    Write-Host $response.Content -ForegroundColor White
} catch {
    Write-Host "Failed to get Kong admin status: $($_.Exception.Message)" -ForegroundColor Red
}

# JWT Authentication (should return 401)
Write-Host "`nTesting JWT Authentication (expect 401)" -ForegroundColor Blue
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8003/auth/profile" -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
    Write-Host "Expected 401 but got $($response.StatusCode)" -ForegroundColor Red
} catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode -eq 401) {
        Write-Host "JWT authentication working - returned 401 as expected" -ForegroundColor Green
    } else {
        Write-Host "Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nGateway Testing Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
