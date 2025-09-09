"""
Module for collecting AWS Organizations Service Control Policy (SCP) findings.
"""

import json
import datetime


def collect_scp_findings(org):
    """
    Collect SCP-related security findings.
    Analyzes Service Control Policies for potential security gaps.
    """
    findings = []
    print("Collecting AWS Organizations SCP findings...")

    try:
        # Check if Organizations is in use
        organization = org.describe_organization().get("Organization", {})

        if not organization:
            findings.append(
                {
                    "id": "SCP-NOT-USED",
                    "category": "SCP",
                    "severity": "Informational",
                    "resource_type": "AWS Organizations",
                    "resource_id": "none",
                    "description": (
                        "AWS Organizations is not being used or the Lambda role lacks "
                        "permissions"
                    ),
                    "recommendation": (
                        "Consider using AWS Organizations with SCPs to enforce security "
                        "guardrails"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )
            return findings

        # Get organization roots
        roots = org.list_roots().get("Roots", [])
        if not roots:
            return findings

        # List all policies in the organization
        paginator = org.get_paginator("list_policies")
        policy_pages = paginator.paginate(Filter="SERVICE_CONTROL_POLICY")

        policies = []
        for page in policy_pages:
            policies.extend(page.get("Policies", []))

        # If there are no SCPs (beyond the default FullAWSAccess), flag it
        if len(policies) <= 1:
            findings.append(
                {
                    "id": "SCP-001",
                    "category": "SCP",
                    "severity": "Medium",
                    "resource_type": "Service Control Policy",
                    "resource_id": "none",
                    "description": "No custom SCPs detected in the organization",
                    "recommendation": (
                        "Implement SCPs to enforce security guardrails across the "
                        "organization"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )

        # Analyze each policy
        for policy in policies:
            policy_id = policy["Id"]
            policy_name = policy["Name"]

            # Skip the default FullAWSAccess policy
            if policy_name == "FullAWSAccess":
                continue

            # Get detailed policy content
            policy_detail = org.describe_policy(PolicyId=policy_id)
            policy_content = policy_detail.get("Policy", {}).get("Content", "{}")

            # Parse the policy content as JSON
            try:
                policy_doc = json.loads(policy_content)
                statements = policy_doc.get("Statement", [])

                # Check for common security best practices in SCPs
                has_deny_root = False
                has_security_services = False

                for statement in statements:
                    action = statement.get("Action", [])
                    if not isinstance(action, list):
                        action = [action]

                    # Check for root user restrictions
                    if (
                        "aws:PrincipalArn" in json.dumps(statement)
                        and "root" in json.dumps(statement).lower()
                    ):
                        has_deny_root = True

                    # Check for security services protections
                    if any(
                        service in json.dumps(statement).lower()
                        for service in [
                            "cloudtrail",
                            "config",
                            "guardduty",
                            "securityhub",
                            "macie",
                            "iam",
                        ]
                    ):
                        has_security_services = True

                # Add findings based on policy analysis
                if not has_deny_root:
                    findings.append(
                        {
                            "id": f"SCP-ROOT-{policy_id[-6:]}",
                            "category": "SCP",
                            "severity": "Medium",
                            "resource_type": "Service Control Policy",
                            "resource_id": policy_name,
                            "description": (
                                f'SCP "{policy_name}" does not appear to restrict root user '
                                "activities"
                            ),
                            "recommendation": (
                                "Add statements to deny actions for root users in member "
                                "accounts"
                            ),
                            "compliance": "AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )

                if not has_security_services:
                    findings.append(
                        {
                            "id": f"SCP-SECURITY-{policy_id[-6:]}",
                            "category": "SCP",
                            "severity": "Low",
                            "resource_type": "Service Control Policy",
                            "resource_id": policy_name,
                            "description": (
                                f'SCP "{policy_name}" does not appear to protect security '
                                "services"
                            ),
                            "recommendation": (
                                "Add statements to prevent disabling of security services"
                            ),
                            "compliance": "AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )

            except json.JSONDecodeError:
                findings.append(
                    {
                        "id": f"SCP-FORMAT-{policy_id[-6:]}",
                        "category": "SCP",
                        "severity": "Low",
                        "resource_type": "Service Control Policy",
                        "resource_id": policy_name,
                        "description": f'SCP "{policy_name}" has invalid JSON format',
                        "recommendation": "Review and correct the SCP JSON format",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

        # If we've analyzed SCPs but found no issues, add a positive note
        if policies and len(findings) == 0:
            findings.append(
                {
                    "id": "SCP-POSITIVE-001",
                    "category": "SCP",
                    "severity": "Informational",
                    "resource_type": "Service Control Policy",
                    "resource_id": "organization",
                    "description": "Organization SCPs follow security best practices",
                    "recommendation": (
                        "Continue to maintain SCPs in line with evolving security needs"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )

    except Exception as e:
        error_msg = str(e)
        print(f"Error collecting SCP findings: {error_msg}")
        findings.append(
            {
                "id": "SCP-ERROR",
                "category": "SCP",
                "severity": "Medium",
                "resource_type": "Organizations Service",
                "resource_id": "error",
                "description": f"Error analyzing SCPs: {error_msg}",
                "recommendation": (
                    "Check Lambda execution role permissions for Organizations ReadOnly "
                    "access"
                ),
                "compliance": "N/A",
                "detection_date": datetime.datetime.now().isoformat(),
            }
        )

    print(f"Collected {len(findings)} SCP findings")
    return findings
