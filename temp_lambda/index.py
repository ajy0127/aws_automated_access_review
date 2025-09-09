"""
AWS Access Review Lambda function for automated security auditing.
This lambda collects security findings from various AWS services and generates a comprehensive
report.

The main workflow:
1. Collect findings from multiple AWS services (IAM, Organizations, Security Hub, etc.)
2. Analyze and compile findings into a structured format
3. Generate a CSV report with detailed findings
4. Create an AI-powered narrative summary using Amazon Bedrock
5. Email the report to specified recipients

This modular architecture allows easy extension with new security checks.

Version: 1.0.0
Author: Security Engineering Team
Last Updated: 2025-04-01
"""

import json  # For JSON serialization/deserialization
import boto3  # AWS SDK for Python
import os  # For environment variable access
import datetime  # For timestamps and date formatting

# Import modules for specific functionality
# Each module handles a different aspect of security findings collection
from modules.iam_findings import (
    collect_iam_findings,
)  # IAM user and role security checks
from modules.scp_findings import collect_scp_findings  # Service Control Policy analysis
from modules.securityhub_findings import (
    collect_securityhub_findings,
)  # AWS Security Hub integration
from modules.access_analyzer_findings import (
    collect_access_analyzer_findings,
)  # External access findings
from modules.cloudtrail_findings import (
    collect_cloudtrail_findings,
)  # Audit log analysis
from modules.narrative import (
    generate_ai_narrative,
)  # AI summary generation with Bedrock
from modules.reporting import (
    generate_csv_report,
    upload_to_s3,
)  # Report generation and storage
from modules.email_utils import (
    send_email_with_attachment,
    verify_email_for_ses,
)  # Email delivery


def handler(event, context):
    """
    Main handler for the AWS Access Review Lambda function.

    This is the entry point when the Lambda is triggered either by:
    1. CloudWatch scheduled events (for regular reports)
    2. Manual invocation (for on-demand reports)
    3. CLI testing (via the test_lambda.py script)

    Args:
        event (dict): The event data that triggered this Lambda function
            - Can contain 'force_real_execution' flag for testing
            - Can override recipient_email for testing
        context (LambdaContext): Runtime information provided by AWS Lambda

    Returns:
        dict: Response with status code and execution result message
    """
    print("Starting AWS Access Review")

    # Check if this is a forced real execution (useful for testing)
    # When true, this will actually send emails even in test environments
    force_real_execution = event.get("force_real_execution", False)
    if force_real_execution:
        print("Forcing real execution with email delivery")

    # Get environment variables set during deployment
    # The S3 bucket where we'll store the report files
    report_bucket = os.environ["REPORT_BUCKET"]

    # The email address can be overridden in the event (for testing)
    # Otherwise, use the one set during deployment
    recipient_email = event.get("recipient_email", os.environ["RECIPIENT_EMAIL"])
    print(f"Will send report to: {recipient_email}")

    # Initialize all AWS service clients we'll need
    # Using boto3 clients is the recommended AWS SDK approach for Lambda functions

    # IAM client for checking users, roles, and policies
    iam = boto3.client("iam")

    # Organizations client for checking SCPs - wrapped in try/except because
    # Organizations service might not be enabled in all accounts
    try:
        org = boto3.client("organizations")
    except Exception as e:
        error_msg = str(e)
        print(f"Warning: Unable to initialize Organizations client: {error_msg}")
        org = None  # Set to None so we can check later if it's available

    # Security Hub client - wrapped in try/except because
    # Security Hub might not be enabled in the account
    try:
        securityhub = boto3.client("securityhub")
    except Exception as e:
        error_msg = str(e)
        print(f"Warning: Unable to initialize Security Hub client: {error_msg}")
        securityhub = None  # Set to None so we can check later if it's available

    # IAM Access Analyzer client - wrapped in try/except because
    # Access Analyzer might not be enabled in the account
    try:
        access_analyzer = boto3.client("accessanalyzer")
    except Exception as e:
        error_msg = str(e)
        print(f"Warning: Unable to initialize Access Analyzer client: {error_msg}")
        access_analyzer = None  # Set to None so we can check later if it's available

    # These services should always be available in all accounts
    cloudtrail = boto3.client("cloudtrail")  # For audit trail analysis
    bedrock = boto3.client("bedrock-runtime")  # For AI narrative generation
    s3 = boto3.client("s3")  # For storing report files
    ses = boto3.client("ses")  # For sending email reports

    # Verify the recipient email in SES if needed
    # Amazon SES requires email verification before sending
    try:
        verify_email_for_ses(ses, recipient_email)
    except Exception as e:
        error_msg = str(e)
        print(f"Warning: Could not verify email in SES: {error_msg}")

    # This list will hold all findings from different security services
    findings = []

    try:
        # ===== STEP 1: Collect findings from multiple AWS security services =====

        # Collect IAM findings (users, roles, policies)
        # This should always work since IAM is a core service
        print("Collecting IAM findings...")
        iam_findings = collect_iam_findings(iam)
        findings.extend(iam_findings)
        print(f"Found {len(iam_findings)} IAM findings")

        # Collect Service Control Policy findings if Organizations is available
        # Some accounts may not be part of an organization
        if org:
            print("Collecting SCP findings...")
            scp_findings = collect_scp_findings(org)
            findings.extend(scp_findings)
            print(f"Found {len(scp_findings)} SCP findings")
        else:
            print("Organizations service not available - skipping SCP analysis")

        # Collect Security Hub findings if available
        # Security Hub is an optional service that may not be enabled
        if securityhub:
            print("Collecting Security Hub findings...")
            securityhub_findings = collect_securityhub_findings(securityhub)
            findings.extend(securityhub_findings)
            print(f"Found {len(securityhub_findings)} Security Hub findings")
        else:
            print("Security Hub not available - skipping Security Hub analysis")

        # Collect IAM Access Analyzer findings if available
        # Access Analyzer is an optional service that may not be enabled
        if access_analyzer:
            print("Collecting IAM Access Analyzer findings...")
            access_analyzer_findings = collect_access_analyzer_findings(access_analyzer)
            findings.extend(access_analyzer_findings)
            print(f"Found {len(access_analyzer_findings)} Access Analyzer findings")
        else:
            print("Access Analyzer not available - skipping external access analysis")

        # Collect CloudTrail findings
        # CloudTrail should always be available as it's a core service
        print("Collecting CloudTrail findings...")
        cloudtrail_findings = collect_cloudtrail_findings(cloudtrail, s3)
        findings.extend(cloudtrail_findings)
        print(f"Found {len(cloudtrail_findings)} CloudTrail findings")

        print(f"Total findings collected: {len(findings)}")

        # ===== STEP 2: Generate CSV report with all findings =====
        print("Generating CSV report...")
        csv_content, csv_filename = generate_csv_report(findings)

        # ===== STEP 3: Upload CSV to S3 for persistence =====
        # Create a timestamp for unique filename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        csv_key = f"reports/aws-access-review-{timestamp}.csv"
        print(f"Uploading report to S3 bucket: {report_bucket}, key: {csv_key}")
        upload_to_s3(s3, report_bucket, csv_content, csv_key)

        # ===== STEP 4: Generate AI narrative using Amazon Bedrock =====
        # This creates a human-readable summary of the findings
        print("Generating AI narrative summary...")
        narrative = generate_ai_narrative(bedrock, findings)

        # ===== STEP 5: Send email with narrative and CSV attachment =====
        print(f"Sending email report to {recipient_email}...")
        send_email_with_attachment(
            ses, recipient_email, narrative, csv_content, csv_filename
        )

        print("AWS Access Review completed successfully")
        return {
            "statusCode": 200,
            "body": json.dumps("AWS Access Review completed successfully"),
            "reportDetails": {
                "timestamp": timestamp,
                "bucket": report_bucket,
                "key": csv_key,
                "findingsCount": len(findings),
            },
        }

    except Exception as e:
        # Comprehensive error handling
        error_msg = str(e)
        print(f"Error in AWS Access Review: {error_msg}")

        # Log the error stack trace for debugging
        import traceback

        print(f"Error stack trace: {traceback.format_exc()}")

        return {
            "statusCode": 500,
            "body": json.dumps(f"Error: {error_msg}"),
            "errorDetails": {"message": error_msg, "type": type(e).__name__},
        }
