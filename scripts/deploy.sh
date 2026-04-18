#!/bin/bash
set -e

# Configuration
STACK_NAME="aws-access-review"
REGION="us-east-1"  # Default region
SCHEDULE="rate(30 days)"  # Default: run every 30 days
EMAIL=""
AWS_PROFILE=""  # AWS profile to use
# Default Bedrock model; override with --bedrock-model when you want a different
# Claude generation or region-specific inference profile.
BEDROCK_MODEL_ID="us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --schedule)
      SCHEDULE="$2"
      shift 2
      ;;
    --email)
      EMAIL="$2"
      shift 2
      ;;
    --profile)
      AWS_PROFILE="$2"
      shift 2
      ;;
    --bedrock-model)
      BEDROCK_MODEL_ID="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if email is provided
if [ -z "$EMAIL" ]; then
  echo "Error: Email is required. Please provide it with --email parameter."
  exit 1
fi

# Set AWS profile if specified
AWS_CMD_PROFILE=""
if [ -n "$AWS_PROFILE" ]; then
  AWS_CMD_PROFILE="--profile $AWS_PROFILE"
  echo "Using AWS profile: $AWS_PROFILE"
fi

# Detect the AWS CLI binary. On Windows/WSL it is installed as aws.exe and
# `command -v aws` returns nothing; fall through to aws.exe in that case.
if command -v aws &> /dev/null; then
  AWS_CMD="aws"
elif command -v aws.exe &> /dev/null; then
  AWS_CMD="aws.exe"
else
  echo "Error: AWS CLI is not installed. Please install it first."
  exit 1
fi

# Verify AWS credentials are valid
echo "Verifying AWS credentials..."
if ! $AWS_CMD sts get-caller-identity $AWS_CMD_PROFILE --region "$REGION" &>/dev/null; then
  echo "Error: Unable to validate AWS credentials. Check your AWS configuration or profile."
  exit 1
fi
echo "AWS credentials verified."

# Prepare deployment files
echo "Preparing deployment files..."
rm -rf deployment
mkdir -p deployment

# Copy all Lambda files from src to deployment, then strip compiled artifacts
# so the zip is reproducible and doesn't bundle local interpreter state.
cp -r src/lambda/. deployment/
find deployment -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find deployment -type f -name "*.pyc" -delete 2>/dev/null || true

# Package Lambda function. Remove any stale zip first so `zip -r` does not
# append to an existing archive (which produces a broken Lambda bundle).
echo "Creating Lambda deployment package..."
rm -f lambda_function.zip
cd deployment
zip -r -X ../lambda_function.zip . >/dev/null
cd ..

# Create/Update the CloudFormation stack
echo "Deploying CloudFormation stack '$STACK_NAME' to region '$REGION'..."
$AWS_CMD cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    RecipientEmail="$EMAIL" \
    ScheduleExpression="$SCHEDULE" \
    BedrockModelId="$BEDROCK_MODEL_ID" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --region "$REGION" \
  $AWS_CMD_PROFILE

# Get the bucket name from the stack outputs. Strip trailing \r that Windows
# aws.exe attaches to --output text results — it corrupts the ARN when passed
# to subsequent commands (ValidationException).
echo "Getting S3 bucket name from CloudFormation stack..."
BUCKET_NAME=$($AWS_CMD cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" $AWS_CMD_PROFILE --query "Stacks[0].Outputs[?OutputKey=='AccessReviewS3Bucket'].OutputValue" --output text | tr -d '\r')

echo "Getting Lambda function ARN from CloudFormation stack..."
LAMBDA_ARN=$($AWS_CMD cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" $AWS_CMD_PROFILE --query "Stacks[0].Outputs[?OutputKey=='AccessReviewLambdaArn'].OutputValue" --output text | tr -d '\r')

# Update Lambda function code
echo "Updating Lambda function code..."
$AWS_CMD lambda update-function-code \
  --function-name "$LAMBDA_ARN" \
  --zip-file fileb://lambda_function.zip \
  --region "$REGION" \
  $AWS_CMD_PROFILE

echo "Deployment completed successfully!"
echo "Lambda function: $LAMBDA_ARN"
echo "S3 bucket for reports: $BUCKET_NAME"
echo "Recipient email: $EMAIL"
echo "Schedule: $SCHEDULE"
echo ""
echo "IMPORTANT: If this is a first-time deployment, you will need to verify your email address."
echo "Check your inbox for a verification email from AWS SES and click the verification link."
echo ""
echo "You can run a report immediately with: ./scripts/run_report.sh --stack-name $STACK_NAME --region $REGION $([[ -n \"$AWS_PROFILE\" ]] && echo \"--profile $AWS_PROFILE\")"