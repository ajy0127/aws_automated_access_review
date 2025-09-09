param(
    [string]$Region = "us-east-1",
    [string]$Profile = ""
)

$ErrorActionPreference = "Continue"

# Set AWS profile if specified
$awsProfileArgs = @()
if ($Profile) {
    $awsProfileArgs += "--profile", $Profile
    Write-Host "Using AWS profile: $Profile"
}

Write-Host "Verifying AWS services setup..." -ForegroundColor Cyan
Write-Host "Region: $Region"
Write-Host ""

$allGood = $true

# Check Security Hub
Write-Host "Checking Security Hub..." -NoNewline
try {
    $result = aws securityhub get-enabled-standards --region $Region @awsProfileArgs 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅ ENABLED" -ForegroundColor Green
    } else {
        Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
    $allGood = $false
}

# Check IAM Access Analyzer
Write-Host "Checking IAM Access Analyzer..." -NoNewline
try {
    $result = aws accessanalyzer list-analyzers --region $Region @awsProfileArgs 2>$null
    if ($LASTEXITCODE -eq 0) {
        $analyzers = $result | ConvertFrom-Json
        if ($analyzers.analyzers.Count -gt 0) {
            Write-Host " ✅ ENABLED" -ForegroundColor Green
        } else {
            Write-Host " ❌ NO ANALYZERS FOUND" -ForegroundColor Red
            $allGood = $false
        }
    } else {
        Write-Host " ❌ NOT ACCESSIBLE" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ❌ NOT ACCESSIBLE" -ForegroundColor Red
    $allGood = $false
}

# Check Amazon SES
Write-Host "Checking Amazon SES..." -NoNewline
try {
    $result = aws ses get-send-quota --region $Region @awsProfileArgs 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅ ENABLED" -ForegroundColor Green
    } else {
        Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
    $allGood = $false
}

# Check Amazon Bedrock
Write-Host "Checking Amazon Bedrock..." -NoNewline
try {
    $result = aws bedrock list-foundation-models --region $Region @awsProfileArgs 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅ ENABLED" -ForegroundColor Green
    } else {
        Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host " ❌ NOT ENABLED" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""
if ($allGood) {
    Write-Host "🎉 All services are properly configured!" -ForegroundColor Green
    Write-Host "You can now proceed with deployment:" -ForegroundColor Green
    if ($Profile) {
        Write-Host ".\scripts\deploy.ps1 -Email your.email@example.com -Profile $Profile" -ForegroundColor Cyan
    } else {
        Write-Host ".\scripts\deploy.ps1 -Email your.email@example.com" -ForegroundColor Cyan
    }
} else {
    Write-Host "❌ Some services need to be enabled. Please follow the setup guide." -ForegroundColor Red
    Write-Host "After enabling services, run this script again to verify." -ForegroundColor Yellow
}
