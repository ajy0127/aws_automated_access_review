"""
Module for collecting AWS IAM Access Analyzer findings.
"""

import datetime


def collect_access_analyzer_findings(access_analyzer):
    """
    Collect findings from IAM Access Analyzer.
    Identifies external access to resources that should be private.
    """
    findings = []
    print("Collecting IAM Access Analyzer findings...")

    try:
        # Get all analyzers in the account
        analyzers_response = access_analyzer.list_analyzers(type="ACCOUNT")
        analyzers = analyzers_response.get("analyzers", [])

        if not analyzers:
            findings.append(
                {
                    "id": "AA-001",
                    "category": "Access Analyzer",
                    "severity": "Medium",
                    "resource_type": "IAM Access Analyzer",
                    "resource_id": "none",
                    "description": "No IAM Access Analyzer is configured for this account",
                    "recommendation": (
                        "Enable IAM Access Analyzer to detect resources that are shared "
                        "externally"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )
            return findings

        # For each analyzer, get active findings
        for analyzer in analyzers:
            analyzer_arn = analyzer["arn"]
            analyzer_name = analyzer["name"]

            # List active findings for this analyzer
            list_findings_paginator = access_analyzer.get_paginator("list_findings")
            findings_pages = list_findings_paginator.paginate(
                analyzerArn=analyzer_arn, filter={"status": {"eq": ["ACTIVE"]}}
            )

            aa_findings_count = 0

            for page in findings_pages:
                for finding_id in page.get("findings", []):
                    # Get detailed finding information
                    finding_detail = access_analyzer.get_finding(
                        analyzerArn=analyzer_arn, id=finding_id["id"]
                    )

                    resource_type = finding_detail.get("resourceType", "Unknown")
                    resource = finding_detail.get("resource", "Unknown")

                    # Determine severity based on resource type and access
                    severity = (
                        "High"
                        if resource_type in ["AWS::S3::Bucket", "AWS::KMS::Key"]
                        else "Medium"
                    )

                    # Check if the resource is accessible from the internet
                    is_public = False
                    if "isPublic" in finding_detail and finding_detail["isPublic"]:
                        is_public = True
                        severity = "Critical"

                    findings.append(
                        {
                            "id": f"AA-{finding_id['id']}",
                            "category": "Access Analyzer",
                            "severity": severity,
                            "resource_type": resource_type,
                            "resource_id": resource,
                            "description": (
                                f"{resource_type} {resource} "
                                f"{'public' if is_public else 'has external access'}"
                                " that may not be intended"
                            ),
                            "recommendation": (
                                f"Review the permissions for this {resource_type} "
                                "and restrict access if unintended"
                            ),
                            "compliance": "AWS Well-Architected, CIS AWS Foundations",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )

                    aa_findings_count += 1

            print(
                f"Found {aa_findings_count} Access Analyzer findings for analyzer "
                f"{analyzer_name}"
            )

            # If there were no findings, add a positive finding
            if aa_findings_count == 0:
                findings.append(
                    {
                        "id": f"AA-POSITIVE-{analyzer_name}",
                        "category": "Access Analyzer",
                        "severity": "Informational",
                        "resource_type": "IAM Access Analyzer",
                        "resource_id": analyzer_name,
                        "description": (
                            "No external access findings detected by IAM Access Analyzer"
                        ),
                        "recommendation": "Continue monitoring with IAM Access Analyzer",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

    except Exception as e:
        error_msg = str(e)
        print(f"Error collecting Access Analyzer findings: {error_msg}")
        findings.append(
            {
                "id": "AA-ERROR",
                "category": "Access Analyzer",
                "severity": "Medium",
                "resource_type": "IAM Access Analyzer",
                "resource_id": "error",
                "description": f"Error collecting findings: {error_msg}",
                "recommendation": "Check Lambda role permissions for Access Analyzer",
                "compliance": "N/A",
                "detection_date": datetime.datetime.now().isoformat(),
            }
        )

    print(f"Collected {len(findings)} Access Analyzer findings")
    return findings
