[![Tests](https://github.com/ajy0127/aws_automated_access_review/actions/workflows/tests.yml/badge.svg)](https://github.com/ajy0127/aws_automated_access_review/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CFN Lint](https://img.shields.io/badge/CFN-Lint-blue.svg)](https://github.com/aws-cloudformation/cfn-lint)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# AWS Automated Access Review
## A Professional IAM Security Automation Tool

A comprehensive tool for automating AWS IAM security reviews. This project provides security professionals and GRC teams with automated access auditing capabilities to enhance cloud security posture and support compliance requirements. Use this tool to develop your portfolio while gaining practical cloud security skills.

> **⚠️ DISCLAIMER**: This tool is provided as-is without warranty of any kind. While it has been tested in development environments, thorough validation is required before deploying in production. Always review the code, test in a non-production environment first, and ensure it meets your organization's security requirements and compliance standards.

## Key Benefits

- **Enhanced Security Posture**: Systematically identify and remediate IAM security risks.
- **Professional Reporting**: Generate comprehensive reports for stakeholders and auditors.
- **GRC Expertise Development**: Build practical skills in governance, risk, and compliance.
- **Cloud Automation Experience**: Gain hands-on experience with Lambda and Bedrock integration.

## Skills Development Opportunities

1. **IAM Security Expertise**: Understand AWS access controls and identify common misconfigurations.
2. **Compliance Reporting**: Create actionable security reports for stakeholders and auditors.
3. **AI Integration**: Leverage Amazon Bedrock to transform raw security data into actionable insights.
4. **Serverless Architecture**: Deploy and manage cloud-native security automation tools.

## About

AWS Access Review is a comprehensive, zero-configuration security assessment tool that automatically evaluates your AWS environment for potential security risks and compliance gaps. Built for security professionals and GRC teams, it combines findings from multiple AWS security services into a clear, actionable report with AI-powered analysis.

Unlike complex security dashboards that require constant monitoring, AWS Access Review delivers insights directly to stakeholders' inboxes on a scheduled basis. The tool focuses on identifying IAM misconfigurations, overly permissive permissions, missing security controls, and external access risks—the most common sources of cloud security incidents.

With single-click deployment and integration with native AWS services, you can start receiving detailed security reports in minutes without extensive setup or third-party dependencies.

This tool is part of a larger initiative to empower GRC professionals in showcasing their practical AWS GRC engineering implementation skills. Visit the [GRC Portfolio Hub](https://github.com/ajy0127/grc_portfolio/tree/main) for more resources and projects focused on governance, risk, and compliance expertise development.

### Compliance Use Case: SOC 2 Type 2 Audits

Perfect for GRC professionals managing SOC 2 Type 2 and similar compliance frameworks. The tool:

- Runs monthly access reviews automatically (default: every 30 days)
- Creates detailed, timestamped reports for audit evidence
- Integrates with compliance workflows:
  1. Receive monthly reports via email
  2. Store reports as audit evidence
  3. Present to auditors when they sample specific months during assessment

## Core Features

- **IAM Security Auditing**: Identify MFA gaps and excessive permissions through detailed CSV reports.
- **Security Hub Integration**: Consolidate and summarize security findings from AWS Security Hub.
- **External Access Analysis**: Detect public resource exposure using IAM Access Analyzer.
- **AI-Powered Reporting**: Transform raw security data into readable, actionable insights with Amazon Bedrock.
- **Automated Email Delivery**: Receive comprehensive security reports directly to designated inbox.
- **Scheduled Execution**: Configure automatic security assessments at your preferred intervals.

*Note*: This project is under active development with ongoing enhancements planned.

## Key Deliverables

1. **IAM Compliance Report**: Comprehensive CSV listing of security findings with severity ratings.
   - Example: See `examples/sample-access-report.csv`.
2. **Executive Summary**: AI-generated narrative analysis of key security risks and remediation recommendations.
3. **Implementation Documentation**: Technical documentation of deployment architecture and configuration.

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- Python 3.11 or higher
- An AWS account with the following services enabled:
  - AWS Security Hub
  - IAM Access Analyzer
  - Amazon SES (with verified email for receiving reports)
  - Amazon Bedrock (with access to Claude model)

## Deployment Guide

End-to-end deploy takes about 10 minutes. Follow each step in order — don't skip. A PowerShell variant of step 6 is in the [Windows section](#windows-deployment) below.

### Step 1. Check prerequisites

You need:
- **AWS CLI v2** installed and configured with credentials for the target account (run `aws sts get-caller-identity` and confirm the account shown is the one you want).
- **Python 3.11+** (`python3 --version`).
- Permission to create IAM roles, Lambda functions, S3 buckets, CloudFormation stacks, EventBridge rules, and to invoke Bedrock in the target region.

### Step 2. Enable the AWS services the tool depends on

In the AWS console (or via CLI) in the region you'll deploy to:
- **Amazon SES** — the tool sends reports over SES; you'll verify the sender/recipient address in step 4.
- **Amazon Bedrock** — request model access for **Anthropic Claude Haiku 4.5** (or whichever model you plan to use) at **Bedrock → Model access**. Access can take a few minutes to be granted. Without it, the AI narrative falls back to a basic text summary, but the rest of the report still works.
- **AWS Security Hub** — optional but recommended; the tool pulls findings from it if enabled.
- **IAM Access Analyzer** — optional; the tool reads external-access findings if an analyzer exists.

### Step 3. Clone the repo and install dev dependencies

```bash
git clone https://github.com/ajy0127/aws_automated_access_review.git
cd aws_automated_access_review
python3 -m venv .venv
source .venv/bin/activate         # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4. Verify a recipient email in SES

SES will reject sends to unverified addresses while your account is in the SES sandbox.

```bash
aws ses verify-email-identity --email-address you@example.com --region us-east-1
```

Check the inbox of that address and click the **verification link** from AWS. Confirm the status flips to `Success`:

```bash
aws ses get-identity-verification-attributes --identities you@example.com --region us-east-1
```

### Step 5. Check AWS credentials are ready

```bash
./scripts/check_aws_creds.sh --profile your-aws-profile    # optional --profile
```

### Step 6. Pick a Bedrock model (important — read this)

The AI narrative is generated by a Claude model on Bedrock. **Bedrock retires model versions periodically** — if your deployed stack starts returning `ResourceNotFoundException` from Bedrock, the model ID has been retired and you need to redeploy with a current one.

- Default: `us.anthropic.claude-haiku-4-5-20251001-v1:0` (US cross-region inference profile, lowest cost, good enough for the summary workload).
- To pick a different model, find a live one first:
  ```bash
  aws bedrock list-foundation-models --by-provider anthropic \
      --query 'modelSummaries[?modelLifecycle.status==`ACTIVE`].[modelId,modelName]' --output table
  aws bedrock list-inference-profiles \
      --query 'inferenceProfileSummaries[?status==`ACTIVE`].[inferenceProfileId,inferenceProfileName]' --output table
  ```
- Haiku 4.5 and the newer Sonnet/Opus models **require an inference profile ID** (prefixed with `us.` or `global.`) — a bare model ID will fail with `ValidationException: on-demand throughput isn't supported`.

You can change the model at any time by redeploying with `--bedrock-model <id>` (step 7). The value is also stored as a Lambda env var (`BEDROCK_MODEL_ID`) so you can hot-swap it in the console without redeploying.

### Step 7. Deploy the CloudFormation stack

```bash
./scripts/deploy.sh \
  --email you@example.com \
  --region us-east-1 \
  --profile your-aws-profile \
  --bedrock-model us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Available flags:

| Flag | Default | What it sets |
| ---- | ------- | ------------ |
| `--email` | *(required)* | SES-verified recipient address for report emails |
| `--region` | `us-east-1` | AWS region for all resources |
| `--stack-name` | `aws-access-review` | CloudFormation stack name |
| `--schedule` | `rate(30 days)` | How often EventBridge triggers the Lambda (any [schedule expression](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-scheduled-rule-pattern.html)) |
| `--profile` | *(default profile)* | AWS CLI profile |
| `--bedrock-model` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock model ID or inference profile |

The script zips the Lambda code, creates the CloudFormation stack, and uploads the Lambda bundle. Expect 2–4 minutes for first-time deploys.

### Step 8. Generate your first report

```bash
./scripts/run_report.sh --profile your-aws-profile
```

The Lambda runs synchronously, writes a CSV to the report bucket, and emails you the findings with an AI-generated summary. Check your inbox — if the email doesn't arrive within ~1 minute, see [Troubleshooting](#troubleshooting).

### Step 9. (Optional) Tear it all down

```bash
./scripts/cleanup.sh --profile your-aws-profile
```

Deletes the CFN stack, empties the report bucket, and removes the Lambda and EventBridge rule.

---

### Windows deployment

Only `deploy.ps1` is ported. The other helper scripts are bash-only; run them from **WSL** or **Git Bash**.

```powershell
./scripts/deploy.ps1 `
  -Email you@example.com `
  -Region us-east-1 `
  -Profile your-aws-profile `
  -BedrockModelId us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Parameter names mirror the bash flags (PascalCase instead of `--kebab-case`).

## Cost & Scale Estimates

- Expected cost: Approximately $1/month in us-east-1 for a typical account.
- Scale: Successfully tested with AWS accounts containing up to 2000 resources and 500 IAM entities.
- Resource usage: Minimal; Lambda execution typically completes within 2-3 minutes.

## How It Works

1. The Lambda function runs on the configured schedule
2. It collects security findings from multiple AWS services
3. Amazon Bedrock generates a narrative summary of the findings
4. A detailed report is stored in S3 and sent via email
5. The report categorizes findings by severity and provides recommendations

### Sample Report Output

```
## AWS Access Review Summary - March 1, 2025

### Executive Summary
Your AWS environment has 17 security findings across 3 categories. Most critical: 2 IAM users with overly permissive policies and 1 S3 bucket with public access.

### Critical Findings
- Two admin IAM users are missing MFA: `admin-user1`, `dev-admin`
- S3 bucket `customer-data-bucket-prod` allows public read access
- Root account access key is active (should be removed immediately)

### Recommendations
1. Enable MFA for all admin users (priority: HIGH)
2. Remove public access from S3 bucket `customer-data-bucket-prod`
3. Delete root account access key
4. Review and prune unused IAM roles (5 roles unused for >90 days)

Full details in the attached CSV report.
```

The email includes both this readable summary and a detailed CSV with all findings.

## Project Architecture

The project follows a modular architecture to improve maintainability and testability:

```
src/
├── lambda/
│   ├── index.py                # Main Lambda handler
│   └── modules/
│       ├── __init__.py
│       ├── iam_findings.py     # IAM security checks
│       ├── scp_findings.py     # Service Control Policy checks
│       ├── securityhub_findings.py # Security Hub integration
│       ├── access_analyzer_findings.py # IAM Access Analyzer integration
│       ├── cloudtrail_findings.py # CloudTrail configuration checks
│       ├── narrative.py        # AI narrative generation with Bedrock
│       ├── reporting.py        # CSV report generation
│       └── email_utils.py      # Email functionality with SES
├── tests/
│   └── unit/                   # Unit tests for modules
templates/
├── access-review.yaml          # CloudFormation template with embedded Lambda code
└── access-review-real.yaml     # Production template with separate Lambda deployment
scripts/
├── deploy.sh                   # Deployment script
├── run_report.sh               # Run immediate report
└── check_aws_creds.sh          # Verify AWS credentials
```

### CloudFormation Templates

The project includes two CloudFormation templates:

1. **access-review.yaml**: Contains embedded Lambda code directly in the template. This is useful for demonstrations and small tests as it doesn't require a separate build/deploy step.

2. **access-review-real.yaml**: Uses a placeholder Lambda function that will be updated after stack creation. This is the production deployment approach, where the Lambda code is separately packaged and updated using the AWS CLI. The deployment script uses this template.

## Running Reports

The AWS Access Review tool runs automatically according to the schedule you specified during deployment (default: monthly). However, you can also trigger a report manually:

1. Using the provided script:
   ```
   ./scripts/run_report.sh --profile your-aws-profile
   ```
   
   This script will:
   - Find your Lambda function from the CloudFormation stack
   - Invoke it with an empty event payload
   - Provide a link to CloudWatch logs for monitoring progress

2. Using the AWS Console:
   - Navigate to the Lambda console
   - Find the function named `<stack-name>-access-review`
   - Click "Test" and use an empty event `{}`
   
3. Using the AWS CLI directly:
   ```
   aws lambda invoke --function-name <stack-name>-access-review --payload '{}' response.json --profile your-aws-profile
   ```

Reports are sent to the email address you specified during deployment and are also stored in the S3 bucket created by the CloudFormation stack.

## Development Guide

### Local Development Environment

1. Set up a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run unit tests:
   ```
   python -m pytest tests/unit
   ```

3. For local development, you can use the following environment variables:
   ```
   export REPORT_BUCKET=your-bucket-name
   export RECIPIENT_EMAIL=your.email@example.com
   ```

### Adding New Functionality

To add a new security check or feature:

1. Create a new module in `src/lambda/modules/`
2. Implement your functionality in the new module
3. Update `src/lambda/index.py` to import and use your new module
4. Add unit tests in `tests/unit/`
5. Run the tests to ensure your changes don't break existing functionality
6. Update documentation as needed

### Deployment

The deployment process is handled by `scripts/deploy.sh`, which:

1. Prepares the deployment files
2. Creates a Lambda deployment package
3. Deploys the CloudFormation stack
4. Updates the Lambda function code

## Troubleshooting

### AWS Credentials

- **"Unable to locate credentials"**: Configure your AWS credentials using `aws configure` or specify a profile with `--profile`
- **"The config profile could not be found"**: Check available profiles with `aws configure list-profiles`
- **"Access denied"**: Ensure your AWS credentials have the necessary permissions

### Email Verification

- **Email not received**: Verify that your email address is verified in Amazon SES
  - Check your CloudFormation stack outputs for the recipient email
  - Verify the email in the SES console: https://console.aws.amazon.com/ses/home#verified-senders-email
  - Check your spam folder for the verification email

### Lambda Function

- **Lambda function timeout**: The default timeout is 5 minutes. If your AWS environment is large, you might need to increase this by modifying the CloudFormation template.
- **Memory issues**: If you see out-of-memory errors, increase the Lambda function memory in the CloudFormation template.

## Contributing

We welcome contributions to improve AWS Access Review! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Version

Current version: See the [VERSION](VERSION) file.
