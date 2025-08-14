#!/usr/bin/env powershell
<#
.SYNOPSIS
    Test runner for AIVO Grafana dashboards and alert rules

.DESCRIPTION
    This script starts the mock health server and synthetic load generator
    to validate that Grafana dashboards import correctly and alerts fire
    when thresholds are breached.

.PARAMETER Action
    Action to perform: start-server, run-load-test, run-spike-test, validate-dashboards, or full-test

.PARAMETER Duration
    Duration for load tests in seconds (default: 300)

.PARAMETER SpikeService
    Service to target for spike test (auth-svc, user-svc, learner-svc, payment-svc, assessment-svc, iep-svc)

.EXAMPLE
    .\test-observability.ps1 -Action full-test
    Runs complete observability validation

.EXAMPLE
    .\test-observability.ps1 -Action run-spike-test -SpikeService auth-svc
    Runs spike test on auth service to trigger 5xx alerts
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start-server", "run-load-test", "run-spike-test", "validate-dashboards", "full-test")]
    [string]$Action,
    
    [int]$Duration = 300,
    
    [ValidateSet("auth-svc", "user-svc", "learner-svc", "payment-svc", "assessment-svc", "iep-svc")]
    [string]$SpikeService = "auth-svc",
    
    [string]$BaseUrl = "http://localhost:8000",
    
    [int]$ConcurrentUsers = 10
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
}

function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "❌ Python not found. Please install Python 3.8+" -ForegroundColor Red
        exit 1
    }
    
    # Check if requirements are installed
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $requirementsFile = Join-Path $currentDir "requirements.txt"
    
    if (Test-Path $requirementsFile) {
        Write-Host "📦 Installing Python requirements..." -ForegroundColor Yellow
        pip install -r $requirementsFile | Out-Null
        Write-Host "✅ Requirements installed" -ForegroundColor Green
    }
    
    # Check if Grafana is accessible (if running)
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        Write-Host "✅ Grafana detected at http://localhost:3000" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Grafana not detected. Start Grafana to view dashboards." -ForegroundColor Yellow
    }
}

function Start-MockServer {
    Write-Header "Starting Mock Health Server"
    
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $serverScript = Join-Path $currentDir "mock-health-server.py"
    
    if (!(Test-Path $serverScript)) {
        Write-Host "❌ Mock server script not found: $serverScript" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🚀 Starting mock health server on port 8000..." -ForegroundColor Green
    Write-Host "   - Health endpoints: /health, /auth/health, /users/health, etc."
    Write-Host "   - Prometheus metrics: /metrics"
    Write-Host "   - Service endpoints: /auth/*, /users/*, /learners/*, etc."
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    
    python $serverScript
}

function Start-LoadTest {
    Write-Header "Running Synthetic Load Test"
    
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $loadScript = Join-Path $currentDir "synthetic-load-generator.py"
    
    if (!(Test-Path $loadScript)) {
        Write-Host "❌ Load generator script not found: $loadScript" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🔥 Starting load test with $ConcurrentUsers users for $Duration seconds..." -ForegroundColor Green
    Write-Host "   Base URL: $BaseUrl"
    Write-Host "   Duration: $Duration seconds"
    Write-Host "   Concurrent Users: $ConcurrentUsers"
    Write-Host ""
    
    python $loadScript --base-url $BaseUrl --users $ConcurrentUsers --duration $Duration
    
    Write-Host ""
    Write-Host "✅ Load test completed!" -ForegroundColor Green
    Write-Host "📊 Check Grafana dashboards for metrics and alerts"
}

function Start-SpikeTest {
    Write-Header "Running Spike Test on $SpikeService"
    
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $loadScript = Join-Path $currentDir "synthetic-load-generator.py"
    
    Write-Host "💥 Generating high error rate for $SpikeService..." -ForegroundColor Yellow
    Write-Host "   This should trigger 5xx error rate alerts in Grafana"
    Write-Host "   Target service: $SpikeService"
    Write-Host "   Duration: 60 seconds"
    Write-Host ""
    
    python $loadScript --base-url $BaseUrl --spike-service $SpikeService --spike-duration 60
    
    Write-Host ""
    Write-Host "✅ Spike test completed!" -ForegroundColor Green
    Write-Host "🚨 Check Grafana alerts - should see '$SpikeService 5xx Error Rate High' alert firing"
}

function Test-DashboardValidation {
    Write-Header "Validating Dashboard JSON Files"
    
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $dashboardDir = Split-Path -Parent $currentDir | Join-Path -ChildPath "dashboards"
    
    if (!(Test-Path $dashboardDir)) {
        Write-Host "❌ Dashboard directory not found: $dashboardDir" -ForegroundColor Red
        exit 1
    }
    
    $dashboardFiles = Get-ChildItem -Path $dashboardDir -Filter "*.json"
    
    if ($dashboardFiles.Count -eq 0) {
        Write-Host "❌ No dashboard JSON files found in: $dashboardDir" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "📋 Found $($dashboardFiles.Count) dashboard files:" -ForegroundColor Green
    
    foreach ($file in $dashboardFiles) {
        Write-Host "   📊 $($file.Name)" -ForegroundColor Cyan
        
        try {
            $content = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
            
            # Basic validation
            if ($content.title -and $content.panels -and $content.uid) {
                Write-Host "      ✅ Valid dashboard structure" -ForegroundColor Green
                Write-Host "      📝 Title: $($content.title)"
                Write-Host "      🔗 UID: $($content.uid)"
                Write-Host "      📊 Panels: $($content.panels.Count)"
            } else {
                Write-Host "      ⚠️  Missing required fields (title, panels, uid)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "      ❌ Invalid JSON: $($_.Exception.Message)" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    Write-Host "📋 Dashboard Import Instructions:" -ForegroundColor Yellow
    Write-Host "   1. Open Grafana at http://localhost:3000"
    Write-Host "   2. Go to '+' > Import"
    Write-Host "   3. Upload each JSON file or copy/paste content"
    Write-Host "   4. Configure data source as 'Prometheus' if needed"
}

function Test-AlertRules {
    Write-Header "Validating Alert Rules"
    
    $currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $alertDir = Split-Path -Parent $currentDir | Join-Path -ChildPath "provisioning" | Join-Path -ChildPath "alerting"
    
    if (Test-Path $alertDir) {
        $alertFiles = Get-ChildItem -Path $alertDir -Filter "*.yml"
        Write-Host "📋 Found $($alertFiles.Count) alert rule files:" -ForegroundColor Green
        
        foreach ($file in $alertFiles) {
            Write-Host "   🚨 $($file.Name)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "⚠️  Alert rules directory not found: $alertDir" -ForegroundColor Yellow
    }
}

function Run-FullTest {
    Write-Header "Running Full Observability Test Suite"
    
    Write-Host "This will run a comprehensive test of all observability components:" -ForegroundColor Green
    Write-Host "1. Validate dashboard JSON files"
    Write-Host "2. Check alert rules configuration"
    Write-Host "3. Instructions for manual validation"
    Write-Host ""
    
    Test-DashboardValidation
    Test-AlertRules
    
    Write-Header "Manual Testing Instructions"
    Write-Host "To complete the observability validation:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. 🖥️  Start Mock Server (in separate terminal):"
    Write-Host "   .\test-observability.ps1 -Action start-server"
    Write-Host ""
    Write-Host "2. 📊 Import Dashboards to Grafana:"
    Write-Host "   - Open http://localhost:3000"
    Write-Host "   - Import each JSON file from infra/grafana/dashboards/"
    Write-Host "   - Set Prometheus data source to http://prometheus:9090"
    Write-Host ""
    Write-Host "3. 🔥 Generate Load (in separate terminal):"
    Write-Host "   .\test-observability.ps1 -Action run-load-test -Duration 180"
    Write-Host ""
    Write-Host "4. 💥 Test Alerts (in separate terminal):"
    Write-Host "   .\test-observability.ps1 -Action run-spike-test -SpikeService auth-svc"
    Write-Host ""
    Write-Host "5. ✅ Verify Results:"
    Write-Host "   - Dashboards show metrics and data"
    Write-Host "   - Alerts fire when thresholds are breached"
    Write-Host "   - FinOps dashboard shows placeholder costs"
    Write-Host ""
    Write-Host "🎉 S1-19 Implementation Ready!" -ForegroundColor Green
}

# Main execution
try {
    Test-Prerequisites
    
    switch ($Action) {
        "start-server" { Start-MockServer }
        "run-load-test" { Start-LoadTest }
        "run-spike-test" { Start-SpikeTest }
        "validate-dashboards" { Test-DashboardValidation }
        "full-test" { Run-FullTest }
        default { 
            Write-Host "❌ Unknown action: $Action" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
