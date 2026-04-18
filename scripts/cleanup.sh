#!/bin/bash
set -e

# Configuration
STACK_NAME="aws-access-review"
REGION="us-east-1"  # Change to your preferred region
AWS_PROFILE=""      # AWS profile to use
SKIP_CONFIRM=false  # Skip the interactive prompt for automation

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
    --profile)
      AWS_PROFILE="$2"
      shift 2
      ;;
    --yes|-y)
      SKIP_CONFIRM=true
      shift
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

# Confirm deletion (unless --yes was passed)
if [ "$SKIP_CONFIRM" != true ]; then
  echo "This will delete the CloudFormation stack '$STACK_NAME' and all associated resources."
  echo "This action cannot be undone."
  read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
  fi
fi

# Look up the report bucket name from the stack output BEFORE deleting the stack.
# The CloudFormation template exposes this as output key "AccessReviewS3Bucket".
echo "Looking up report bucket name from stack outputs..."
REPORT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" $AWS_CMD_PROFILE \
  --query "Stacks[0].Outputs[?OutputKey=='AccessReviewS3Bucket'].OutputValue" \
  --output text 2>/dev/null || true)

# Empty the S3 bucket first. CloudFormation can't delete a non-empty S3 bucket,
# so the stack delete will fail with "BucketNotEmpty" if we skip this step.
if [ -n "$REPORT_BUCKET" ] && [ "$REPORT_BUCKET" != "None" ]; then
  echo "Emptying report bucket: $REPORT_BUCKET"
  aws s3 rm "s3://$REPORT_BUCKET" --recursive --region "$REGION" $AWS_CMD_PROFILE
else
  echo "No report bucket found in stack outputs (already deleted or never created); skipping empty step."
fi

# Delete the CloudFormation stack. The stack itself owns the bucket, so once it
# is empty the delete-stack call cleans up the bucket + Lambda + IAM role +
# EventBridge rule + Lambda permission in one operation.
echo "Deleting CloudFormation stack: $STACK_NAME"
aws cloudformation delete-stack \
  --stack-name "$STACK_NAME" \
  --region "$REGION" $AWS_CMD_PROFILE

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION" $AWS_CMD_PROFILE

echo "Cleanup completed successfully!"
