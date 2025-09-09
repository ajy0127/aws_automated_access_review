param(
    [string]$StackName = "aws-access-review",
    [string]$Region = "us-east-1",
    [string]$Schedule = "rate(30 days)",
    [Parameter(Mandatory=$true)]
    [string]$Email,
    [string]$Profile = ""
)

$ErrorActionPreference = "Stop"

# Set AWS profile if specified
$awsProfileArgs = @()
if ($Profile) {
    $awsProfileArgs += "--profile", $Profile
    Write-Host "Using AWS profile: $Profile"
}

# Verify AWS credentials are valid
Write-Host "Verifying AWS credentials..."
try {
    aws sts get-caller-identity --region $Region @awsProfileArgs 2>$null | Out-Null
} catch {
    Write-Host "Error: Unable to validate AWS credentials. Check your AWS configuration or profile." -ForegroundColor Red
    exit 1
}
Write-Host "AWS credentials verified." -ForegroundColor Green

# Prepare deployment files
Write-Host "Preparing deployment files..."
if (Test-Path "deployment") {
    Remove-Item -Recurse -Force "deployment"
}
New-Item -ItemType Directory -Path "deployment" | Out-Null

# Copy all Lambda files from src to deployment
Copy-Item -Recurse "src\lambda\*" "deployment\"

# Package Lambda function
Write-Host "Creating Lambda deployment package..."
Push-Location "deployment"
try {
    Compress-Archive -Path "*" -DestinationPath "..\lambda_function.zip" -Force
} finally {
    Pop-Location
}

# Create/Update the CloudFormation stack
Write-Host "Deploying CloudFormation stack '$StackName' to region '$Region'..."
$deployArgs = @(
    "cloudformation", "deploy",
    "--template-file", "templates\access-review-real.yaml",
    "--stack-name", $StackName,
    "--parameter-overrides",
    "RecipientEmail=$Email",
    "ScheduleExpression=$Schedule",
    "--capabilities", "CAPABILITY_IAM",
    "--region", $Region
) + $awsProfileArgs

aws @deployArgs

# Get the bucket name from the stack outputs
Write-Host "Getting S3 bucket name from CloudFormation stack..."
$bucketArgs = @(
    "cloudformation", "describe-stacks",
    "--stack-name", $StackName,
    "--region", $Region,
    "--query", "Stacks[0].Outputs[?OutputKey=='AccessReviewS3Bucket'].OutputValue",
    "--output", "text"
) + $awsProfileArgs
$bucketName = aws @bucketArgs

Write-Host "Getting Lambda function ARN from CloudFormation stack..."
$lambdaArgs = @(
    "cloudformation", "describe-stacks",
    "--stack-name", $StackName,
    "--region", $Region,
    "--query", "Stacks[0].Outputs[?OutputKey=='AccessReviewLambdaArn'].OutputValue",
    "--output", "text"
) + $awsProfileArgs
$lambdaArn = aws @lambdaArgs

# Update Lambda function code
Write-Host "Updating Lambda function code..."
$updateArgs = @(
    "lambda", "update-function-code",
    "--function-name", $lambdaArn,
    "--zip-file", "fileb://lambda_function.zip",
    "--region", $Region
) + $awsProfileArgs
aws @updateArgs

Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "Lambda function: $lambdaArn"
Write-Host "S3 bucket for reports: $bucketName"
Write-Host "Recipient email: $Email"
Write-Host "Schedule: $Schedule"
Write-Host ""
Write-Host "IMPORTANT: If this is a first-time deployment, you will need to verify your email address." -ForegroundColor Yellow
Write-Host "Check your inbox for a verification email from AWS SES and click the verification link."
Write-Host ""
if ($Profile) {
    Write-Host "You can run a report immediately with: .\scripts\run_report.ps1 -StackName $StackName -Region $Region -Profile $Profile"
} else {
    Write-Host "You can run a report immediately with: .\scripts\run_report.ps1 -StackName $StackName -Region $Region"
}
