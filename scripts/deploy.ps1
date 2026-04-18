# PowerShell port of scripts/deploy.sh for Windows users.
# Requires: AWS CLI v2, PowerShell 5.1+ (or PowerShell 7+), Compress-Archive (built-in).

[CmdletBinding()]
param(
    [string]$StackName = "aws-access-review",
    [string]$Region = "us-east-1",
    [string]$Schedule = "rate(30 days)",
    [Parameter(Mandatory = $true)]
    [string]$Email,
    [string]$Profile = ""
)

$ErrorActionPreference = "Stop"

$awsCommonArgs = @("--region", $Region)
if ($Profile) {
    $awsCommonArgs += @("--profile", $Profile)
    Write-Host "Using AWS profile: $Profile"
}

Write-Host "Verifying AWS credentials..."
& aws sts get-caller-identity @awsCommonArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Unable to validate AWS credentials. Check your AWS configuration or profile."
}
Write-Host "AWS credentials verified."

Write-Host "Preparing deployment files..."
if (Test-Path "deployment") { Remove-Item -Recurse -Force "deployment" }
New-Item -ItemType Directory -Path "deployment" | Out-Null

Copy-Item -Path "src/lambda/*" -Destination "deployment/" -Recurse -Force

# Strip compiled artifacts so the zip is reproducible
Get-ChildItem -Path "deployment" -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "deployment" -Recurse -Filter "*.pyc" |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Creating Lambda deployment package..."
if (Test-Path "lambda_function.zip") { Remove-Item -Force "lambda_function.zip" }
Compress-Archive -Path "deployment/*" -DestinationPath "lambda_function.zip" -Force

Write-Host "Deploying CloudFormation stack '$StackName' to region '$Region'..."
$deployArgs = @(
    "cloudformation", "deploy",
    "--template-file", "templates/access-review-real.yaml",
    "--stack-name", $StackName,
    "--parameter-overrides", "RecipientEmail=$Email", "ScheduleExpression=$Schedule",
    "--capabilities", "CAPABILITY_IAM",
    "--no-fail-on-empty-changeset"
) + $awsCommonArgs
& aws @deployArgs
if ($LASTEXITCODE -ne 0) { throw "CloudFormation deploy failed." }

Write-Host "Getting S3 bucket name from CloudFormation stack..."
$bucketName = & aws cloudformation describe-stacks `
    --stack-name $StackName @awsCommonArgs `
    --query "Stacks[0].Outputs[?OutputKey=='AccessReviewS3Bucket'].OutputValue" `
    --output text

Write-Host "Getting Lambda function ARN from CloudFormation stack..."
$lambdaArn = & aws cloudformation describe-stacks `
    --stack-name $StackName @awsCommonArgs `
    --query "Stacks[0].Outputs[?OutputKey=='AccessReviewLambdaArn'].OutputValue" `
    --output text

Write-Host "Updating Lambda function code..."
& aws lambda update-function-code `
    --function-name $lambdaArn `
    --zip-file fileb://lambda_function.zip `
    @awsCommonArgs | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Lambda update-function-code failed." }

Write-Host ""
Write-Host "Deployment completed successfully!"
Write-Host "Lambda function: $lambdaArn"
Write-Host "S3 bucket for reports: $bucketName"
Write-Host "Recipient email: $Email"
Write-Host "Schedule: $Schedule"
Write-Host ""
Write-Host "IMPORTANT: If this is a first-time deployment, verify your email address via the SES verification email."
