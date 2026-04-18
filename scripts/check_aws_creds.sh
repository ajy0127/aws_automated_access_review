#!/bin/bash
set -e

# Configuration
REGION="us-east-1"  # Default region
AWS_PROFILE=""  # AWS profile to use

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      REGION="$2"
      shift 2
      ;;
    --profile)
      AWS_PROFILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set AWS profile if specified
AWS_CMD_PROFILE=""
if [ -n "$AWS_PROFILE" ]; then
  AWS_CMD_PROFILE="--profile $AWS_PROFILE"
  echo "Using AWS profile: $AWS_PROFILE"
fi

echo "Checking AWS credentials..."
echo "Region: $REGION"

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

# Check AWS credentials
echo "Checking AWS identity..."
if ! $AWS_CMD sts get-caller-identity $AWS_CMD_PROFILE --region "$REGION"; then
  echo "Error: Failed to get AWS identity. Please check your credentials."
  exit 1
fi

echo "AWS credentials are valid!"

# Check required services
echo -e "\nChecking required AWS services..."

# Check Security Hub
echo "Checking Security Hub..."
if $AWS_CMD securityhub get-enabled-standards $AWS_CMD_PROFILE --region "$REGION" &> /dev/null; then
  echo "✅ Security Hub is accessible"
else
  echo "⚠️ Security Hub may not be enabled or accessible"
fi

# Check IAM Access Analyzer
echo "Checking IAM Access Analyzer..."
if $AWS_CMD accessanalyzer list-analyzers $AWS_CMD_PROFILE --region "$REGION" &> /dev/null; then
  echo "✅ IAM Access Analyzer is accessible"
else
  echo "⚠️ IAM Access Analyzer may not be enabled or accessible"
fi

# Check Amazon SES
echo "Checking Amazon SES..."
if $AWS_CMD ses get-send-quota $AWS_CMD_PROFILE --region "$REGION" &> /dev/null; then
  echo "✅ Amazon SES is accessible"
else
  echo "⚠️ Amazon SES may not be enabled or accessible in this region"
fi

# Check Amazon Bedrock
echo "Checking Amazon Bedrock..."
if $AWS_CMD bedrock list-foundation-models $AWS_CMD_PROFILE --region "$REGION" &> /dev/null; then
  echo "✅ Amazon Bedrock is accessible"
else
  echo "⚠️ Amazon Bedrock may not be enabled or accessible in this region"
fi

echo -e "\nCredential check completed!"
echo "If any services show warnings, you may need to enable them or check permissions."
echo "You can now proceed with deployment using the same profile:"
echo "./deploy.sh --email your.email@example.com --profile $AWS_PROFILE" 