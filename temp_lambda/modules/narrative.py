"""
Module for generating narrative summaries of AWS access review findings.
"""

import datetime


def generate_ai_narrative(bedrock, findings):
    """
    Generate a narrative summary of findings using Amazon Bedrock.
    Uses AI to create a comprehensive analysis of security findings.
    """
    print("Generating AI narrative summary using Amazon Bedrock...")

    try:
        # Import from bedrock_integration.py
        from bedrock_integration import get_ai_analysis

        # If the import succeeded, use the real function
        return get_ai_analysis(bedrock, findings)
    except Exception as e:
        error_msg = str(e)
        print(f"Error using Bedrock integration: {error_msg}")
        print("Falling back to local narrative generation")

        # Fall back to a locally generated narrative if Bedrock fails
        return generate_fallback_narrative(findings)


def generate_fallback_narrative(findings):
    """
    Generate a basic narrative summary without using AI services.
    Used as a fallback when Bedrock is unavailable.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count findings by severity
    severity_counts = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Informational": 0,
    }

    # Count findings by category
    category_counts = {}

    # Track key issues
    key_issues = []
    positives = []

    for finding in findings:
        # Count by severity
        severity = finding.get("severity", "Medium")
        if severity in severity_counts:
            severity_counts[severity] += 1

        # Count by category
        category = finding.get("category", "Other")
        if category not in category_counts:
            category_counts[category] = 0
        category_counts[category] += 1

        # Track critical and high findings as key issues
        if severity in ["Critical", "High"]:
            key_issues.append(
                f"- {finding.get('description')} "
                f"({finding.get('resource_type')}: {finding.get('resource_id')})"
            )

        # Track positive findings
        if (
            severity == "Informational"
            and "no " in finding.get("description", "").lower()
            or "positive" in finding.get("id", "").lower()
        ):
            positives.append(f"- {finding.get('description')}")

    # Sort categories by count
    sorted_categories = sorted(
        category_counts.items(), key=lambda x: x[1], reverse=True
    )

    # Build the narrative
    narrative = (
        f"\nAWS Access Review Report - {timestamp}\n\n"
        "EXECUTIVE SUMMARY\n"
        "This automated security review has analyzed your AWS environment across "
        f"multiple security dimensions and identified {len(findings)} findings.\n\n"
        "FINDINGS SUMMARY\n"
        f"Total findings: {len(findings)}\n"
        f"Critical: {severity_counts['Critical']} - Requires immediate attention\n"
        f"High: {severity_counts['High']} - Should be addressed soon\n"
        f"Medium: {severity_counts['Medium']} - Should be planned for remediation\n"
        f"Low: {severity_counts['Low']} - Consider addressing when convenient\n"
        f"Informational: {severity_counts['Informational']} - No action needed\n\n"
        "FINDINGS BY CATEGORY\n"
    )

    for category, count in sorted_categories:
        narrative += f"{category}: {count} findings\n"

    if key_issues:
        narrative += (
            "\nKEY ISSUES REQUIRING ATTENTION\n"
            "The following critical or high severity issues were identified:\n"
            f"{chr(10).join(key_issues[:5])}\n"
        )
        if len(key_issues) > 5:
            narrative += (
                f"...and {len(key_issues) - 5} more critical or high severity "
                "issues.\n"
            )

    if positives:
        narrative += (
            "\nPOSITIVE SECURITY FINDINGS\n"
            "The following security best practices were detected:\n"
            f"{chr(10).join(positives[:3])}\n"
        )
        if len(positives) > 3:
            narrative += f"...and {len(positives) - 3} more positive findings.\n"

    narrative += (
        "\nRECOMMENDATIONS\n"
        "1. Address all Critical and High findings as soon as possible\n"
        "2. Create a remediation plan for Medium findings\n"
        "3. Schedule regular security reviews using this tool\n"
        "4. For detailed findings, please see the attached CSV report\n"
    )

    return narrative
