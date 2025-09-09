param(
    [Parameter(Mandatory=$true)]
    [string]$Email,
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

Write-Host "=== TESTING DEPLOYMENT READINESS ===" -ForegroundColor Cyan
Write-Host "This will attempt to validate the CloudFormation template and check if services are accessible."
Write-Host ""

# Test CloudFormation template validation
Write-Host "1. Validating CloudFormation template..." -ForegroundColor Yellow
try {
    $validateArgs = @(
        "cloudformation", "validate-template",
        "--template-body", "file://templates/access-review-real.yaml",
        "--region", $Region
    ) + $awsProfileArgs
    
    aws @validateArgs
    Write-Host "✅ CloudFormation template is valid" -ForegroundColor Green
} catch {
    Write-Host "❌ CloudFormation template validation failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test if we can create a change set (this will show if services are accessible)
Write-Host "2. Testing CloudFormation deployment permissions..." -ForegroundColor Yellow
$testStackName = "aws-access-review-test-$(Get-Random -Maximum 9999)"

try {
    $changeSetArgs = @(
        "cloudformation", "create-change-set",
        "--stack-name", $testStackName,
        "--template-body", "file://templates/access-review-real.yaml",
        "--change-set-name", "test-change-set",
        "--parameters", "ParameterKey=RecipientEmail,ParameterValue=$Email", "ParameterKey=ScheduleExpression,ParameterValue=rate(30 days)",
        "--capabilities", "CAPABILITY_IAM",
        "--region", $Region
    ) + $awsProfileArgs
    
    aws @changeSetArgs
    Write-Host "✅ CloudFormation change set created successfully" -ForegroundColor Green
    
    # Clean up the change set
    Write-Host "Cleaning up test change set..." -ForegroundColor Gray
    $deleteArgs = @(
        "cloudformation", "delete-change-set",
        "--stack-name", $testStackName,
        "--change-set-name", "test-change-set",
        "--region", $Region
    ) + $awsProfileArgs
    aws @deleteArgs
    
} catch {
    Write-Host "❌ CloudFormation deployment test failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "This could mean:" -ForegroundColor Yellow
    Write-Host "- Required AWS services are not enabled" -ForegroundColor Yellow
    Write-Host "- Your user lacks necessary permissions" -ForegroundColor Yellow
    Write-Host "- There's an issue with the template parameters" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🎉 DEPLOYMENT READINESS TEST PASSED!" -ForegroundColor Green
Write-Host "Your AWS environment appears to be properly configured." -ForegroundColor Green
Write-Host ""
Write-Host "Ready to deploy with:" -ForegroundColor Cyan
if ($Profile) {
    Write-Host ".\scripts\deploy.ps1 -Email $Email -Profile $Profile" -ForegroundColor White
} else {
    Write-Host ".\scripts\deploy.ps1 -Email $Email" -ForegroundColor White
}
