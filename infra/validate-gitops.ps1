#!/usr/bin/env powershell

# AIVO Platform Kubernetes GitOps Validation Script
# Tests Helm charts and Kubernetes manifests for syntax and best practices

Write-Host "🚀 AIVO Platform GitOps Validation" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

$ErrorCount = 0

# Function to test YAML syntax
function Test-YamlSyntax {
    param($FilePath)
    
    try {
        $content = Get-Content $FilePath -Raw
        if ($content -match "^\s*$") {
            Write-Host "❌ Empty file: $FilePath" -ForegroundColor Red
            return $false
        }
        
        # Basic YAML validation (check for valid structure)
        if ($content -match "apiVersion:" -and $content -match "kind:" -and $content -match "metadata:") {
            Write-Host "✅ Valid Kubernetes manifest: $FilePath" -ForegroundColor Green
            return $true
        } elseif ($content -match "^[a-zA-Z].*:" -and $content -match "^\s+[a-zA-Z].*:") {
            Write-Host "✅ Valid YAML structure: $FilePath" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Invalid YAML structure: $FilePath" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Error reading file: $FilePath - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to validate Helm Chart.yaml
function Test-HelmChart {
    param($ChartPath)
    
    $chartFile = Join-Path $ChartPath "Chart.yaml"
    $valuesFile = Join-Path $ChartPath "values.yaml"
    
    Write-Host "`n🔍 Testing Helm Chart: $ChartPath" -ForegroundColor Cyan
    
    if (-not (Test-Path $chartFile)) {
        Write-Host "❌ Missing Chart.yaml in $ChartPath" -ForegroundColor Red
        return $false
    }
    
    if (-not (Test-Path $valuesFile)) {
        Write-Host "❌ Missing values.yaml in $ChartPath" -ForegroundColor Red
        return $false
    }
    
    $chartValid = Test-YamlSyntax $chartFile
    $valuesValid = Test-YamlSyntax $valuesFile
    
    # Test Chart.yaml structure
    $chartContent = Get-Content $chartFile -Raw
    if ($chartContent -match "apiVersion:\s*v2" -and 
        $chartContent -match "name:" -and 
        $chartContent -match "version:" -and 
        $chartContent -match "appVersion:") {
        Write-Host "✅ Valid Chart.yaml structure" -ForegroundColor Green
    } else {
        Write-Host "❌ Invalid Chart.yaml structure" -ForegroundColor Red
        $chartValid = $false
    }
    
    return ($chartValid -and $valuesValid)
}

# Function to validate Argo CD applications
function Test-ArgoCDApps {
    param($AppsPath)
    
    Write-Host "`n🔍 Testing Argo CD Applications: $AppsPath" -ForegroundColor Cyan
    
    $appFiles = Get-ChildItem $AppsPath -Filter "*.yaml"
    $allValid = $true
    
    foreach ($file in $appFiles) {
        $isValid = Test-YamlSyntax $file.FullName
        
        if ($isValid) {
            $content = Get-Content $file.FullName -Raw
            if ($content -match "kind:\s*Application" -and 
                $content -match "apiVersion:\s*argoproj.io/v1alpha1" -and
                $content -match "spec:" -and
                $content -match "source:" -and
                $content -match "destination:") {
                Write-Host "✅ Valid Argo CD Application: $($file.Name)" -ForegroundColor Green
            } else {
                Write-Host "❌ Invalid Argo CD Application structure: $($file.Name)" -ForegroundColor Red
                $allValid = $false
            }
        } else {
            $allValid = $false
        }
    }
    
    return $allValid
}

# Function to validate security configurations
function Test-SecurityConfig {
    Write-Host "`n🔍 Testing Security Configurations" -ForegroundColor Cyan
    
    $securityIssues = 0
    
    # Check platform values for security settings
    $platformValues = "infra\helm\platform\values.yaml"
    if (Test-Path $platformValues) {
        $content = Get-Content $platformValues -Raw
        
        if ($content -match "podSecurityStandard:\s*restricted") {
            Write-Host "✅ Pod Security Standard set to restricted" -ForegroundColor Green
        } else {
            Write-Host "❌ Pod Security Standard not set to restricted" -ForegroundColor Red
            $securityIssues++
        }
        
        if ($content -match "runAsNonRoot:\s*true") {
            Write-Host "✅ runAsNonRoot enabled" -ForegroundColor Green
        } else {
            Write-Host "❌ runAsNonRoot not enabled" -ForegroundColor Red
            $securityIssues++
        }
        
        if ($content -match "networkPolicies:\s*\n\s*enabled:\s*true") {
            Write-Host "✅ Network Policies enabled" -ForegroundColor Green
        } else {
            Write-Host "❌ Network Policies not enabled" -ForegroundColor Red
            $securityIssues++
        }
    }
    
    return ($securityIssues -eq 0)
}

# Main validation
Write-Host "`n📋 Starting validation..." -ForegroundColor Yellow

# Test Platform Helm Chart
Write-Host "`n1️⃣ Testing Platform Helm Chart" -ForegroundColor Magenta
$platformValid = Test-HelmChart "infra\helm\platform"
if (-not $platformValid) { $ErrorCount++ }

# Test Service Template
Write-Host "`n2️⃣ Testing Service Template" -ForegroundColor Magenta
$templateValid = Test-HelmChart "infra\helm\services\_template"
if (-not $templateValid) { $ErrorCount++ }

# Test Service Charts
Write-Host "`n3️⃣ Testing Service Helm Charts" -ForegroundColor Magenta
$serviceCharts = @("auth-svc", "user-svc", "inference-gateway-svc")
foreach ($chart in $serviceCharts) {
    $chartPath = "infra\helm\services\$chart"
    if (Test-Path $chartPath) {
        $valid = Test-HelmChart $chartPath
        if (-not $valid) { $ErrorCount++ }
    } else {
        Write-Host "❌ Service chart not found: $chartPath" -ForegroundColor Red
        $ErrorCount++
    }
}

# Test Argo CD Applications
Write-Host "`n4️⃣ Testing Argo CD Applications" -ForegroundColor Magenta
if (Test-Path "infra\argocd\apps") {
    $argoCDValid = Test-ArgoCDApps "infra\argocd\apps"
    if (-not $argoCDValid) { $ErrorCount++ }
} else {
    Write-Host "❌ Argo CD apps directory not found" -ForegroundColor Red
    $ErrorCount++
}

# Test App-of-Apps
Write-Host "`n5️⃣ Testing App-of-Apps" -ForegroundColor Magenta
$appOfApps = "infra\argocd\app-of-apps.yaml"
if (Test-Path $appOfApps) {
    $valid = Test-YamlSyntax $appOfApps
    if (-not $valid) { $ErrorCount++ }
} else {
    Write-Host "❌ App-of-Apps file not found" -ForegroundColor Red
    $ErrorCount++
}

# Test Security Configuration
Write-Host "`n6️⃣ Testing Security Configuration" -ForegroundColor Magenta
$securityValid = Test-SecurityConfig
if (-not $securityValid) { $ErrorCount++ }

# Test Documentation
Write-Host "`n7️⃣ Testing Documentation" -ForegroundColor Magenta
$docs = @("infra\secrets\vault-kv-paths.md", "docs\runbooks\deploy.md")
foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Write-Host "✅ Documentation found: $doc" -ForegroundColor Green
    } else {
        Write-Host "❌ Documentation missing: $doc" -ForegroundColor Red
        $ErrorCount++
    }
}

# Summary
Write-Host "`n📊 Validation Summary" -ForegroundColor Yellow
Write-Host "===================" -ForegroundColor Yellow

if ($ErrorCount -eq 0) {
    Write-Host "🎉 All validations passed! GitOps infrastructure is ready." -ForegroundColor Green
    Write-Host "`n✅ Platform Helm chart validated" -ForegroundColor Green
    Write-Host "✅ Service Helm charts validated" -ForegroundColor Green
    Write-Host "✅ Argo CD applications validated" -ForegroundColor Green
    Write-Host "✅ Security configurations validated" -ForegroundColor Green
    Write-Host "✅ Documentation present" -ForegroundColor Green
    
    Write-Host "`n🚀 Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Commit and push infrastructure code" -ForegroundColor White
    Write-Host "2. Apply app-of-apps to Argo CD: kubectl apply -f infra/argocd/app-of-apps.yaml" -ForegroundColor White
    Write-Host "3. Monitor application sync in Argo CD UI" -ForegroundColor White
    Write-Host "4. Configure Vault secrets per vault-kv-paths.md" -ForegroundColor White
    
    exit 0
} else {
    Write-Host "❌ $ErrorCount validation errors found. Please fix before deployment." -ForegroundColor Red
    exit 1
}
