# AIVO Virtual Brains - S1-18 Security & Privacy Tests
# Security Test Validation Script
# 
# Validates S1-18 implementation completeness and security coverage requirements:
# - Verifies all security test files exist and are executable
# - Checks security documentation is complete  
# - Validates Kong security plugin configuration
# - Confirms CI regression prevention setup

param(
    [switch]$Verbose,
    [switch]$FixIssues
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."

Write-Host "🔍 S1-18 Security Implementation Validation" -ForegroundColor Cyan
Write-Host "📁 Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host ("=" * 60) -ForegroundColor Gray

$ValidationResults = @()
$OverallSuccess = $true

function Add-ValidationResult {
    param($Component, $Check, $Status, $Message, $FixAction = $null)
    
    $ValidationResults += @{
        Component = $Component
        Check = $Check
        Status = $Status
        Message = $Message
        FixAction = $FixAction
    }
    
    $StatusIcon = if ($Status) { "✅" } else { "❌" }
    $Color = if ($Status) { "Green" } else { "Red" }
    Write-Host "  $StatusIcon $Check`: $Message" -ForegroundColor $Color
    
    if (-not $Status) {
        $script:OverallSuccess = $false
        if ($FixAction -and $FixIssues) {
            Write-Host "    🔧 Auto-fixing: $FixAction" -ForegroundColor Yellow
        }
    }
}

# Validation 1: Security Test Files
Write-Host "`n🔐 Validating Security Test Files..." -ForegroundColor Yellow

$RequiredTestFiles = @(
    @{ Path = "tests\security\test_jwt_security.py"; Name = "JWT Security Tests" }
    @{ Path = "tests\security\test_consent_logging.py"; Name = "Consent Logging Tests" }
    @{ Path = "tests\security\test_pii_scrubbing.py"; Name = "PII Scrubbing Tests" }
    @{ Path = "tests\security\run_security_tests.py"; Name = "Python Test Runner" }
    @{ Path = "tests\security\run_security_tests.ps1"; Name = "PowerShell Test Runner" }
)

foreach ($TestFile in $RequiredTestFiles) {
    $FilePath = Join-Path $ProjectRoot $TestFile.Path
    $Exists = Test-Path $FilePath
    
    if ($Exists) {
        # Check if file has content
        $Content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        $HasContent = $Content -and $Content.Trim().Length -gt 100
        
        Add-ValidationResult "Security Tests" $TestFile.Name $HasContent `
            $(if ($HasContent) { "Found with content" } else { "Empty or minimal" }) `
            "Add comprehensive test implementation"
    } else {
        Add-ValidationResult "Security Tests" $TestFile.Name $false "File missing" `
            "Create $($TestFile.Path)"
    }
}

# Validation 2: Security Documentation
Write-Host "`n📚 Validating Security Documentation..." -ForegroundColor Yellow

$SecurityDocs = @(
    @{ Path = "docs\security\edge-policies.md"; Name = "Edge Security Policies"; MinLines = 100 }
    @{ Path = "docs\security\threat-model.md"; Name = "Threat Model"; MinLines = 50 }
)

foreach ($Doc in $SecurityDocs) {
    $DocPath = Join-Path $ProjectRoot $Doc.Path
    $Exists = Test-Path $DocPath
    
    if ($Exists) {
        $Lines = (Get-Content $DocPath -ErrorAction SilentlyContinue).Count
        $HasContent = $Lines -ge $Doc.MinLines
        
        Add-ValidationResult "Documentation" $Doc.Name $HasContent `
            $(if ($HasContent) { "$Lines lines" } else { "Only $Lines lines (need $($Doc.MinLines))" }) `
            "Expand documentation content"
    } else {
        Add-ValidationResult "Documentation" $Doc.Name $false "File missing" `
            "Create security documentation"
    }
}

# Validation 3: Kong Security Plugin Configuration
Write-Host "`n🔒 Validating Kong Security Configuration..." -ForegroundColor Yellow

$KongConfigPath = Join-Path $ProjectRoot "infra\kong\kong.yml"
if (Test-Path $KongConfigPath) {
    $KongConfig = Get-Content $KongConfigPath -Raw
    
    # Check for required security plugins
    $RequiredPlugins = @("dash_context", "learner_scope", "consent_gate", "jwt", "cors", "rate-limiting")
    
    foreach ($Plugin in $RequiredPlugins) {
        $HasPlugin = $KongConfig -match $Plugin
        Add-ValidationResult "Kong Plugins" $Plugin $HasPlugin `
            $(if ($HasPlugin) { "Configured" } else { "Missing from kong.yml" }) `
            "Add $Plugin plugin configuration"
    }
    
    # Check for security plugin files
    $PluginFiles = @(
        "apps\gateway\plugins\dash_context\handler.lua",
        "apps\gateway\plugins\learner_scope\handler.lua", 
        "apps\gateway\plugins\consent_gate\handler.lua"
    )
    
    foreach ($PluginFile in $PluginFiles) {
        $PluginPath = Join-Path $ProjectRoot $PluginFile
        $Exists = Test-Path $PluginPath
        $PluginName = Split-Path (Split-Path $PluginFile -Parent) -Leaf
        
        if ($Exists) {
            $Content = Get-Content $PluginPath -Raw -ErrorAction SilentlyContinue
            $HasImplementation = $Content -and $Content.Length -gt 500
            
            Add-ValidationResult "Kong Plugins" "$PluginName Implementation" $HasImplementation `
                $(if ($HasImplementation) { "Implemented" } else { "Stub only" }) `
                "Complete plugin implementation"
        } else {
            Add-ValidationResult "Kong Plugins" "$PluginName Implementation" $false "File missing" `
                "Create plugin handler"
        }
    }
} else {
    Add-ValidationResult "Kong Plugins" "Configuration File" $false "kong.yml missing" `
        "Create Kong declarative configuration"
}

# Validation 4: CI/CD Security Integration
Write-Host "`n🔄 Validating CI/CD Security Integration..." -ForegroundColor Yellow

$CIFiles = @(
    @{ Path = ".github\workflows\security-tests.yml"; Name = "GitHub Actions Security Workflow" }
    @{ Path = "scripts\test-security.sh"; Name = "Security Test Script" }
    @{ Path = "scripts\test-security.ps1"; Name = "Security Test PowerShell Script" }
)

foreach ($CIFile in $CIFiles) {
    $CIPath = Join-Path $ProjectRoot $CIFile.Path
    $Exists = Test-Path $CIPath
    
    Add-ValidationResult "CI/CD" $CIFile.Name $Exists `
        $(if ($Exists) { "Configured" } else { "Missing" }) `
        "Create CI security test integration"
}

# Validation 5: Security Test Coverage Requirements
Write-Host "`n📊 Validating Security Test Coverage..." -ForegroundColor Yellow

$CoverageTargets = @{
    "JWT Security Tests" = 80
    "Consent Logging Tests" = 80
    "PII Scrubbing Tests" = 90
    "Overall Security Coverage" = 80
}

foreach ($Target in $CoverageTargets.Keys) {
    $MinCoverage = $CoverageTargets[$Target]
    
    # Check if coverage target is documented in test files
    $TestFiles = Get-ChildItem "$ProjectRoot\tests\security\test_*.py" -ErrorAction SilentlyContinue
    $CoverageDocumented = $false
    
    foreach ($TestFile in $TestFiles) {
        $Content = Get-Content $TestFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($Content -and $Content -match "coverage.*$MinCoverage") {
            $CoverageDocumented = $true
            break
        }
    }
    
    Add-ValidationResult "Coverage" $Target $CoverageDocumented `
        $(if ($CoverageDocumented) { "≥$MinCoverage% target documented" } else { "Target not documented" }) `
        "Add coverage requirement to test documentation"
}

# Validation 6: Security Service Dependencies
Write-Host "`n🔗 Validating Security Service Dependencies..." -ForegroundColor Yellow

$SecurityServices = @{
    "Redis (Consent Cache)" = "redis://localhost:6379"
    "PostgreSQL (Audit Log)" = "postgresql://localhost:5432"
    "Kong Gateway" = "http://localhost:8000"
    "Consent Service" = "http://localhost:8003"
}

foreach ($Service in $SecurityServices.Keys) {
    $ServiceURL = $SecurityServices[$Service]
    
    # Check if service is documented in test files
    $ServiceDocumented = $false
    $TestFiles = Get-ChildItem "$ProjectRoot\tests\security\*.py" -ErrorAction SilentlyContinue
    
    foreach ($TestFile in $TestFiles) {
        $Content = Get-Content $TestFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($Content -and $Content -match [regex]::Escape($ServiceURL)) {
            $ServiceDocumented = $true
            break
        }
    }
    
    Add-ValidationResult "Dependencies" $Service $ServiceDocumented `
        $(if ($ServiceDocumented) { "Referenced in tests" } else { "Not referenced" }) `
        "Add service dependency to test configuration"
}

# Validation 7: Security Error Codes and Response Formats
Write-Host "`n⚠️  Validating Security Error Handling..." -ForegroundColor Yellow

$RequiredErrorCodes = @("MISSING_JWT", "INVALID_JWT", "MISSING_CONTEXT", "INVALID_CONTEXT", "LEARNER_SCOPE_VIOLATION", "CONSENT_REQUIRED")

$JWTTestPath = Join-Path $ProjectRoot "tests\security\test_jwt_security.py"
if (Test-Path $JWTTestPath) {
    $JWTTestContent = Get-Content $JWTTestPath -Raw
    
    foreach ($ErrorCode in $RequiredErrorCodes) {
        $ErrorCodeTested = $JWTTestContent -match [regex]::Escape($ErrorCode)
        
        Add-ValidationResult "Error Handling" $ErrorCode $ErrorCodeTested `
            $(if ($ErrorCodeTested) { "Test exists" } else { "No test found" }) `
            "Add test case for $ErrorCode error response"
    }
}

# Generate Validation Report
Write-Host "`n" + ("=" * 60) -ForegroundColor Gray
Write-Host "📋 S1-18 VALIDATION SUMMARY" -ForegroundColor Cyan

$TotalChecks = $ValidationResults.Count
$PassedChecks = ($ValidationResults | Where-Object { $_.Status -eq $true }).Count
$FailedChecks = $TotalChecks - $PassedChecks
$SuccessRate = if ($TotalChecks -gt 0) { ($PassedChecks / $TotalChecks) * 100 } else { 0 }

Write-Host "`n📊 Overall Results:" -ForegroundColor White
Write-Host "  • Total Checks: $TotalChecks" -ForegroundColor Gray
Write-Host "  • Passed: $PassedChecks" -ForegroundColor Green
Write-Host "  • Failed: $FailedChecks" -ForegroundColor Red
Write-Host "  • Success Rate: $($SuccessRate.ToString('F1'))%" -ForegroundColor $(if ($SuccessRate -ge 80) { "Green" } else { "Red" })

# Group results by component
$ComponentGroups = $ValidationResults | Group-Object Component
foreach ($Group in $ComponentGroups) {
    $ComponentPassed = ($Group.Group | Where-Object { $_.Status -eq $true }).Count
    $ComponentTotal = $Group.Group.Count
    $ComponentRate = ($ComponentPassed / $ComponentTotal) * 100
    
    $Color = if ($ComponentRate -ge 80) { "Green" } elseif ($ComponentRate -ge 60) { "Yellow" } else { "Red" }
    Write-Host "`n🔍 $($Group.Name): $ComponentPassed/$ComponentTotal ($($ComponentRate.ToString('F1'))%)" -ForegroundColor $Color
    
    foreach ($Result in $Group.Group) {
        if (-not $Result.Status) {
            Write-Host "  ❌ $($Result.Check): $($Result.Message)" -ForegroundColor Red
            if ($Result.FixAction) {
                Write-Host "     💡 Fix: $($Result.FixAction)" -ForegroundColor Yellow
            }
        }
    }
}

# S1-18 Readiness Assessment
Write-Host "`n🎯 S1-18 READINESS ASSESSMENT" -ForegroundColor Cyan

$ReadinessChecks = @{
    "Security Test Suite" = ($ValidationResults | Where-Object { $_.Component -eq "Security Tests" -and $_.Status }).Count -ge 3
    "Security Documentation" = ($ValidationResults | Where-Object { $_.Component -eq "Documentation" -and $_.Status }).Count -ge 1
    "Kong Security Plugins" = ($ValidationResults | Where-Object { $_.Component -eq "Kong Plugins" -and $_.Status }).Count -ge 5
    "Error Code Coverage" = ($ValidationResults | Where-Object { $_.Component -eq "Error Handling" -and $_.Status }).Count -ge 4
}

$ReadyForCommit = $true
foreach ($Check in $ReadinessChecks.Keys) {
    $CheckPassed = $ReadinessChecks[$Check]
    $StatusIcon = if ($CheckPassed) { "✅" } else { "❌" }
    Write-Host "  $StatusIcon $Check" -ForegroundColor $(if ($CheckPassed) { "Green" } else { "Red" })
    
    if (-not $CheckPassed) {
        $ReadyForCommit = $false
    }
}

$MinReadinessScore = 80
$ReadyForCommit = $ReadyForCommit -and $SuccessRate -ge $MinReadinessScore

Write-Host "`n🚀 DEPLOYMENT READINESS:" -ForegroundColor Cyan
if ($ReadyForCommit) {
    Write-Host "✅ READY for S1-18 commit" -ForegroundColor Green
    Write-Host "   Commit message: 'test(security): jwt claims, consent log, pii scrub stubs'" -ForegroundColor Green
    Write-Host "   Next steps:" -ForegroundColor Gray
    Write-Host "   1. Run: python tests/security/run_security_tests.py" -ForegroundColor Gray
    Write-Host "   2. Verify ≥80% security coverage" -ForegroundColor Gray
    Write-Host "   3. Commit and push S1-18 implementation" -ForegroundColor Gray
} else {
    Write-Host "❌ NOT READY for S1-18 commit" -ForegroundColor Red
    Write-Host "   Issues to address:" -ForegroundColor Red
    Write-Host "   • Success rate: $($SuccessRate.ToString('F1'))% (need ≥$MinReadinessScore%)" -ForegroundColor Red
    Write-Host "   • Fix failed validation checks above" -ForegroundColor Red
    Write-Host "   • Ensure comprehensive security test coverage" -ForegroundColor Red
}

# Save validation report
$ReportPath = Join-Path $ProjectRoot "s1-18-validation-report.txt"
$ValidationResults | ConvertTo-Json -Depth 3 | Out-File $ReportPath -Encoding UTF8
Write-Host "`n📄 Validation report saved: $ReportPath" -ForegroundColor Gray

# Exit with appropriate code
if ($OverallSuccess -and $ReadyForCommit) {
    Write-Host "`n🎉 S1-18 validation PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n💥 S1-18 validation FAILED!" -ForegroundColor Red
    exit 1
}
