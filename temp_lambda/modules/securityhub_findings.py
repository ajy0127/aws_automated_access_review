"""
Module for collecting AWS Security Hub findings.
"""

import datetime


def collect_securityhub_findings(securityhub):
    """
    Collect IAM-related findings from Security Hub.
    Focuses on high and critical findings related to identity and access management.
    """
    findings = []
    print("Collecting AWS Security Hub findings...")

    try:
        # Check if Security Hub is enabled by retrieving enabled standards
        enabled_standards = securityhub.get_enabled_standards().get(
            "StandardsSubscriptions", []
        )

        if not enabled_standards:
            findings.append(
                {
                    "id": "SECHUB-NOT-ENABLED",
                    "category": "SecurityHub",
                    "severity": "High",
                    "resource_type": "AWS Security Hub",
                    "resource_id": "none",
                    "description": "Security Hub is not enabled in this account",
                    "recommendation": (
                        "Enable Security Hub and at least the CIS AWS Foundations standard"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )
            return findings

        # Get findings paginator
        paginator = securityhub.get_paginator("get_findings")

        # Filter for IAM-related findings with high/critical severity
        filters = {
            "ProductName": [{"Value": "Security Hub", "Comparison": "EQUALS"}],
            "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
            "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}],
            "SeverityLabel": [
                {"Value": "HIGH", "Comparison": "EQUALS"},
                {"Value": "CRITICAL", "Comparison": "EQUALS"},
            ],
            "ResourceType": [{"Value": "AwsIam", "Comparison": "PREFIX"}],
        }

        # Get findings pages
        findings_pages = paginator.paginate(Filters=filters)

        # Process findings
        for page in findings_pages:
            for finding in page.get("Findings", [])[:50]:  # Limit to first 50
                findings.append(
                    {
                        "id": finding.get("Id", "")[-12:],
                        "category": "SecurityHub",
                        "severity": finding.get("Severity", {}).get("Label", "MEDIUM"),
                        "resource_type": finding.get("Resources", [{}])[0].get(
                            "Type", ""
                        ),
                        "resource_id": finding.get("Resources", [{}])[0].get("Id", ""),
                        "description": finding.get("Description", ""),
                        "recommendation": finding.get("Remediation", {})
                        .get("Recommendation", {})
                        .get("Text", "Review finding in Security Hub console"),
                        "compliance": finding.get("Compliance", {}).get("Status", ""),
                        "detection_date": finding.get("FirstObservedAt", ""),
                    }
                )

        # If no findings detected, add a positive note
        if not findings:
            findings.append(
                {
                    "id": "SECHUB-POSITIVE-001",
                    "category": "SecurityHub",
                    "severity": "Informational",
                    "resource_type": "AWS Security Hub",
                    "resource_id": "none",
                    "description": "No high/critical IAM-related findings detected",
                    "recommendation": "Continue monitoring Security Hub findings",
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )

    except Exception as e:
        error_msg = str(e)
        print(f"Error collecting Security Hub findings: {error_msg}")
        findings.append(
            {
                "id": "SECHUB-ERROR",
                "category": "SecurityHub",
                "severity": "Medium",
                "resource_type": "AWS Security Hub",
                "resource_id": "error",
                "description": f"Error collecting findings: {error_msg}",
                "recommendation": "Check Lambda role permissions for Security Hub",
                "compliance": "N/A",
                "detection_date": datetime.datetime.now().isoformat(),
            }
        )

    print(f"Collected {len(findings)} Security Hub findings")
    return findings
