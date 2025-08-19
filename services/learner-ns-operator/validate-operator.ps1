# Learner Namespace Operator Validation Script
# Validates the operator deployment and functionality

param(
    [switch]$SkipE2E,
    [string]$Namespace = "aivo-system"
)

Write-Host "🔍 Validating Learner Namespace Operator Deployment" -ForegroundColor Cyan
Write-Host "=" * 60

# Function to check command availability
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to run kubectl and capture output
function Invoke-Kubectl {
    param([string]$Args)
    try {
        $result = Invoke-Expression "kubectl $Args" 2>&1
        if ($LASTEXITCODE -eq 0) {
            return @{ Success = $true; Output = $result }
        } else {
            return @{ Success = $false; Output = $result }
        }
    } catch {
        return @{ Success = $false; Output = $_.Exception.Message }
    }
}

# Function to wait for condition
function Wait-ForCondition {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds = 300,
        [int]$IntervalSeconds = 5,
        [string]$Description = "condition"
    )
    
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        if (& $Condition) {
            return $true
        }
        Start-Sleep -Seconds $IntervalSeconds
        $elapsed += $IntervalSeconds
        Write-Host "." -NoNewline
    }
    Write-Host ""
    Write-Host "❌ Timeout waiting for $Description" -ForegroundColor Red
    return $false
}

# Validation functions
function Test-Prerequisites {
    Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow
    
    $checks = @()
    
    # Check kubectl
    if (Test-Command "kubectl") {
        $checks += "✅ kubectl available"
        
        # Check cluster connectivity
        $result = Invoke-Kubectl "cluster-info --request-timeout=10s"
        if ($result.Success) {
            $checks += "✅ Kubernetes cluster accessible"
        } else {
            $checks += "❌ Cannot connect to Kubernetes cluster"
            return $false
        }
    } else {
        $checks += "❌ kubectl not found"
        return $false
    }
    
    # Check if namespace exists
    $result = Invoke-Kubectl "get namespace $Namespace"
    if ($result.Success) {
        $checks += "✅ Namespace $Namespace exists"
    } else {
        $checks += "❌ Namespace $Namespace not found"
        return $false
    }
    
    $checks | ForEach-Object { Write-Host $_ }
    return $true
}

function Test-CRDInstallation {
    Write-Host "📋 Checking CRD installation..." -ForegroundColor Yellow
    
    $result = Invoke-Kubectl "get crd learnerspaces.aivo.dev"
    if ($result.Success) {
        Write-Host "✅ LearnerSpace CRD installed"
        
        # Check CRD version
        $crdInfo = Invoke-Kubectl "get crd learnerspaces.aivo.dev -o jsonpath='{.spec.versions[*].name}'"
        if ($crdInfo.Success) {
            Write-Host "✅ CRD versions: $($crdInfo.Output)"
        }
        return $true
    } else {
        Write-Host "❌ LearnerSpace CRD not found" -ForegroundColor Red
        Write-Host "Run: kubectl apply -f services/learner-ns-operator/crd.yaml" -ForegroundColor Yellow
        return $false
    }
}

function Test-RBACConfiguration {
    Write-Host "🔐 Checking RBAC configuration..." -ForegroundColor Yellow
    
    $checks = @()
    
    # Check ServiceAccount
    $result = Invoke-Kubectl "get serviceaccount learner-ns-operator -n $Namespace"
    if ($result.Success) {
        $checks += "✅ ServiceAccount exists"
    } else {
        $checks += "❌ ServiceAccount missing"
    }
    
    # Check ClusterRole
    $result = Invoke-Kubectl "get clusterrole learner-ns-operator"
    if ($result.Success) {
        $checks += "✅ ClusterRole exists"
    } else {
        $checks += "❌ ClusterRole missing"
    }
    
    # Check ClusterRoleBinding
    $result = Invoke-Kubectl "get clusterrolebinding learner-ns-operator"
    if ($result.Success) {
        $checks += "✅ ClusterRoleBinding exists"
    } else {
        $checks += "❌ ClusterRoleBinding missing"
    }
    
    $checks | ForEach-Object { Write-Host $_ }
    
    $failures = $checks | Where-Object { $_ -like "❌*" }
    return $failures.Count -eq 0
}

function Test-OperatorDeployment {
    Write-Host "🚀 Checking operator deployment..." -ForegroundColor Yellow
    
    # Check if deployment exists
    $result = Invoke-Kubectl "get deployment learner-ns-operator -n $Namespace"
    if (-not $result.Success) {
        Write-Host "❌ Operator deployment not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "✅ Deployment exists"
    
    # Check deployment status
    $result = Invoke-Kubectl "get deployment learner-ns-operator -n $Namespace -o jsonpath='{.status.conditions[?(@.type==\"Available\")].status}'"
    if ($result.Success -and $result.Output -eq "True") {
        Write-Host "✅ Deployment is available"
    } else {
        Write-Host "❌ Deployment not available" -ForegroundColor Red
        
        # Show deployment details
        Write-Host "Deployment status:" -ForegroundColor Yellow
        Invoke-Kubectl "describe deployment learner-ns-operator -n $Namespace"
        return $false
    }
    
    # Check pod status
    $result = Invoke-Kubectl "get pods -l app.kubernetes.io/name=learner-ns-operator -n $Namespace -o jsonpath='{.items[*].status.phase}'"
    if ($result.Success -and $result.Output -eq "Running") {
        Write-Host "✅ Pod is running"
    } else {
        Write-Host "❌ Pod not running" -ForegroundColor Red
        
        # Show pod details
        Write-Host "Pod status:" -ForegroundColor Yellow
        Invoke-Kubectl "get pods -l app.kubernetes.io/name=learner-ns-operator -n $Namespace"
        Invoke-Kubectl "describe pods -l app.kubernetes.io/name=learner-ns-operator -n $Namespace"
        return $false
    }
    
    return $true
}

function Test-HealthEndpoint {
    Write-Host "🏥 Testing health endpoint..." -ForegroundColor Yellow
    
    # Get pod name
    $result = Invoke-Kubectl "get pods -l app.kubernetes.io/name=learner-ns-operator -n $Namespace -o jsonpath='{.items[0].metadata.name}'"
    if (-not $result.Success) {
        Write-Host "❌ Cannot find operator pod" -ForegroundColor Red
        return $false
    }
    
    $podName = $result.Output
    Write-Host "Testing health endpoint on pod: $podName"
    
    # Test health endpoint
    $result = Invoke-Kubectl "exec -n $Namespace $podName -- wget -q -O- --timeout=5 http://localhost:8080/healthz"
    if ($result.Success) {
        Write-Host "✅ Health endpoint responding"
        return $true
    } else {
        Write-Host "❌ Health endpoint not responding" -ForegroundColor Red
        Write-Host "Error: $($result.Output)" -ForegroundColor Red
        return $false
    }
}

function Test-OperatorLogs {
    Write-Host "📝 Checking operator logs..." -ForegroundColor Yellow
    
    $result = Invoke-Kubectl "logs -l app.kubernetes.io/name=learner-ns-operator -n $Namespace --tail=20"
    if ($result.Success) {
        Write-Host "✅ Operator logs accessible"
        Write-Host "Recent logs:" -ForegroundColor Cyan
        $result.Output | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        
        # Check for error patterns
        $errors = $result.Output | Where-Object { $_ -match "ERROR|Exception|Failed" }
        if ($errors.Count -gt 0) {
            Write-Host "⚠️  Found errors in logs:" -ForegroundColor Yellow
            $errors | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        }
        
        return $true
    } else {
        Write-Host "❌ Cannot access operator logs" -ForegroundColor Red
        return $false
    }
}

function Test-BasicFunctionality {
    Write-Host "🧪 Testing basic LearnerSpace functionality..." -ForegroundColor Yellow
    
    $testLearnerSpace = @"
apiVersion: aivo.dev/v1
kind: LearnerSpace
metadata:
  name: test-validation-$(Get-Random -Minimum 1000 -Maximum 9999)
  namespace: $Namespace
spec:
  learnerId: "validation-test-$(Get-Random -Minimum 1000 -Maximum 9999)"
  subjects: ["test-subject"]
  resourceQuota:
    cpu: "100m"
    memory: "256Mi"
    storage: "1Gi"
    pods: 2
  networkPolicy:
    egressDeny: true
    allowedNamespaces: ["aivo-system"]
  vaultRole: "learner-test"
"@
    
    # Apply test LearnerSpace
    try {
        $testFile = New-TemporaryFile
        $testLearnerSpace | Set-Content -Path $testFile.FullName
        
        $result = Invoke-Kubectl "apply -f $($testFile.FullName)"
        if (-not $result.Success) {
            Write-Host "❌ Failed to create test LearnerSpace" -ForegroundColor Red
            return $false
        }
        
        $learnerSpaceName = ($testLearnerSpace | ConvertFrom-Yaml).metadata.name
        Write-Host "✅ Created test LearnerSpace: $learnerSpaceName"
        
        # Wait for namespace creation
        Write-Host "Waiting for namespace creation..." -NoNewline
        $namespaceCreated = Wait-ForCondition -Condition {
            $statusResult = Invoke-Kubectl "get learnerspace $learnerSpaceName -n $Namespace -o jsonpath='{.status.phase}'"
            return $statusResult.Success -and $statusResult.Output -eq "Ready"
        } -TimeoutSeconds 120 -Description "LearnerSpace Ready"
        
        if ($namespaceCreated) {
            Write-Host "✅ LearnerSpace reached Ready state"
            
            # Get created namespace name
            $nsResult = Invoke-Kubectl "get learnerspace $learnerSpaceName -n $Namespace -o jsonpath='{.status.namespace}'"
            if ($nsResult.Success) {
                $createdNamespace = $nsResult.Output
                Write-Host "✅ Created namespace: $createdNamespace"
                
                # Verify namespace exists
                $nsCheckResult = Invoke-Kubectl "get namespace $createdNamespace"
                if ($nsCheckResult.Success) {
                    Write-Host "✅ Namespace exists and is accessible"
                } else {
                    Write-Host "❌ Created namespace not found" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "❌ LearnerSpace did not reach Ready state" -ForegroundColor Red
            
            # Show status for debugging
            Write-Host "LearnerSpace status:" -ForegroundColor Yellow
            Invoke-Kubectl "get learnerspace $learnerSpaceName -n $Namespace -o yaml"
        }
        
        # Cleanup
        Write-Host "Cleaning up test resources..."
        Invoke-Kubectl "delete learnerspace $learnerSpaceName -n $Namespace" | Out-Null
        
        return $namespaceCreated
        
    } catch {
        Write-Host "❌ Error during functionality test: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        if ($testFile) {
            Remove-Item $testFile.FullName -Force -ErrorAction SilentlyContinue
        }
    }
}

function Test-E2ETests {
    if ($SkipE2E) {
        Write-Host "⏭️  Skipping E2E tests (--SkipE2E specified)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "🧪 Running E2E tests..." -ForegroundColor Yellow
    
    $e2eScript = "services/learner-ns-operator/tests/test_e2e.py"
    if (-not (Test-Path $e2eScript)) {
        Write-Host "⚠️  E2E test script not found at $e2eScript" -ForegroundColor Yellow
        return $true
    }
    
    # Check if Python is available
    if (-not (Test-Command "python")) {
        Write-Host "⚠️  Python not found, skipping E2E tests" -ForegroundColor Yellow
        return $true
    }
    
    try {
        # Run E2E tests
        $result = Start-Process -FilePath "python" -ArgumentList $e2eScript -Wait -PassThru -WindowStyle Hidden
        if ($result.ExitCode -eq 0) {
            Write-Host "✅ E2E tests passed"
            return $true
        } else {
            Write-Host "❌ E2E tests failed with exit code $($result.ExitCode)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Error running E2E tests: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main validation flow
function Start-Validation {
    Write-Host "Starting validation..." -ForegroundColor Green
    
    $allPassed = $true
    $tests = @(
        @{ Name = "Prerequisites"; Function = { Test-Prerequisites } },
        @{ Name = "CRD Installation"; Function = { Test-CRDInstallation } },
        @{ Name = "RBAC Configuration"; Function = { Test-RBACConfiguration } },
        @{ Name = "Operator Deployment"; Function = { Test-OperatorDeployment } },
        @{ Name = "Health Endpoint"; Function = { Test-HealthEndpoint } },
        @{ Name = "Operator Logs"; Function = { Test-OperatorLogs } },
        @{ Name = "Basic Functionality"; Function = { Test-BasicFunctionality } },
        @{ Name = "E2E Tests"; Function = { Test-E2ETests } }
    )
    
    foreach ($test in $tests) {
        Write-Host ""
        try {
            $passed = & $test.Function
            if ($passed) {
                Write-Host "✅ $($test.Name) - PASSED" -ForegroundColor Green
            } else {
                Write-Host "❌ $($test.Name) - FAILED" -ForegroundColor Red
                $allPassed = $false
            }
        } catch {
            Write-Host "❌ $($test.Name) - ERROR: $($_.Exception.Message)" -ForegroundColor Red
            $allPassed = $false
        }
    }
    
    Write-Host ""
    Write-Host "=" * 60
    if ($allPassed) {
        Write-Host "🎉 All validations passed! Learner Namespace Operator is ready." -ForegroundColor Green
    } else {
        Write-Host "❌ Some validations failed. Please check the errors above." -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
        Write-Host "- Check operator logs: kubectl logs -l app.kubernetes.io/name=learner-ns-operator -n $Namespace" -ForegroundColor Cyan
        Write-Host "- Verify RBAC: kubectl auth can-i '*' '*' --as=system:serviceaccount:$Namespace:learner-ns-operator" -ForegroundColor Cyan
        Write-Host "- Check CRD: kubectl get crd learnerspaces.aivo.dev" -ForegroundColor Cyan
        Write-Host "- View events: kubectl get events -n $Namespace --sort-by='.lastTimestamp'" -ForegroundColor Cyan
    }
    
    return $allPassed
}

# Run validation
$success = Start-Validation
exit $(if ($success) { 0 } else { 1 })
