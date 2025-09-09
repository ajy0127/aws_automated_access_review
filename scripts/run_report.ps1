param(
    [string]$StackName = "aws-access-review",
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

# Verify AWS credentials are valid
Write-Host "Verifying AWS credentials..."
try {
    aws sts get-caller-identity --region $Region @awsProfileArgs 2>$null | Out-Null
} catch {
    Write-Host "Error: Unable to validate AWS credentials. Check your AWS configuration or profile." -ForegroundColor Red
    exit 1
}
Write-Host "AWS credentials verified." -ForegroundColor Green

# Get Lambda function name from CloudFormation stack
Write-Host "Getting Lambda function ARN from CloudFormation stack..."
$lambdaArgs = @(
    "cloudformation", "describe-stacks",
    "--stack-name", $StackName,
    "--region", $Region,
    "--query", "Stacks[0].Outputs[?OutputKey=='AccessReviewLambdaArn'].OutputValue",
    "--output", "text"
) + $awsProfileArgs

try {
    $lambdaArn = aws @lambdaArgs
    if (-not $lambdaArn -or $lambdaArn -eq "None") {
        throw "No Lambda ARN found"
    }
} catch {
    Write-Host "Error: Could not retrieve Lambda function ARN from stack outputs." -ForegroundColor Red
    exit 1
}

Write-Host "Found Lambda function: $lambdaArn"

# Invoke Lambda function
Write-Host "Invoking Lambda function to generate access review report..."
$invokeArgs = @(
    "lambda", "invoke",
    "--function-name", $lambdaArn,
    "--invocation-type", "Event",
    "--region", $Region
) + $awsProfileArgs + @("response.json")

aws @invokeArgs

Write-Host "Lambda function invoked successfully!" -ForegroundColor Green
Write-Host "The access review report will be generated and sent to the configured email address."
Write-Host "This process may take several minutes to complete depending on the size of your AWS environment."
Write-Host ""
$functionName = Split-Path $lambdaArn -Leaf
Write-Host "You can check the Lambda function logs in CloudWatch for progress:"
Write-Host "https://$Region.console.aws.amazon.com/cloudwatch/home?region=$Region#logsV2:log-groups/log-group/aws/lambda/$functionName"

# Clean up response file
if (Test-Path "response.json") {
    Remove-Item "response.json"
}
