param(
    [string]$Region = "us-east-1",
    [string]$Profile = ""
)

$ErrorActionPreference = "Stop"

# Set AWS profile if specified
$awsProfileArgs = @()
if ($Profile) {
    $awsProfileArgs += "--profile", $Profile
    Write-Host "Using AWS profile: $Profile"
}

Write-Host "Checking AWS credentials..."
Write-Host "Region: $Region"

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
} catch {
    Write-Host "Error: AWS CLI is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "Checking AWS identity..."
try {
    aws sts get-caller-identity --region $Region @awsProfileArgs
} catch {
    Write-Host "Error: Failed to get AWS identity. Please check your credentials." -ForegroundColor Red
    exit 1
}

Write-Host "AWS credentials are valid!" -ForegroundColor Green

# Check required services
Write-Host "`nChecking required AWS services..."

# Check Security Hub
Write-Host "Checking Security Hub..."
try {
    aws securityhub get-enabled-standards --region $Region @awsProfileArgs 2>$null | Out-Null
    Write-Host "✅ Security Hub is accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Security Hub may not be enabled or accessible" -ForegroundColor Yellow
}

# Check IAM Access Analyzer
Write-Host "Checking IAM Access Analyzer..."
try {
    aws accessanalyzer list-analyzers --region $Region @awsProfileArgs 2>$null | Out-Null
    Write-Host "✅ IAM Access Analyzer is accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️ IAM Access Analyzer may not be enabled or accessible" -ForegroundColor Yellow
}

# Check Amazon SES
Write-Host "Checking Amazon SES..."
try {
    aws ses get-send-quota --region $Region @awsProfileArgs 2>$null | Out-Null
    Write-Host "✅ Amazon SES is accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Amazon SES may not be enabled or accessible in this region" -ForegroundColor Yellow
}

# Check Amazon Bedrock
Write-Host "Checking Amazon Bedrock..."
try {
    aws bedrock list-foundation-models --region $Region @awsProfileArgs 2>$null | Out-Null
    Write-Host "✅ Amazon Bedrock is accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Amazon Bedrock may not be enabled or accessible in this region" -ForegroundColor Yellow
}

Write-Host "`nCredential check completed!" -ForegroundColor Green
Write-Host "If any services show warnings, you may need to enable them or check permissions."
Write-Host "You can now proceed with deployment using the same profile:"
if ($Profile) {
    Write-Host ".\scripts\deploy.ps1 -Email your.email@example.com -Profile $Profile"
} else {
    Write-Host ".\scripts\deploy.ps1 -Email your.email@example.com"
}
