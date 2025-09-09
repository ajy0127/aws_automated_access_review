"""
Module for collecting AWS CloudTrail-related security findings.
"""

import datetime


def collect_cloudtrail_findings(cloudtrail, s3):
    """
    Collect CloudTrail-related security findings.
    Checks if CloudTrail is enabled and properly configured.
    """
    findings = []
    print("Collecting AWS CloudTrail findings...")

    try:
        # Get list of trails
        trails = cloudtrail.describe_trails().get("trailList", [])

        if not trails:
            findings.append(
                {
                    "id": "CT-NOT-ENABLED",
                    "category": "CloudTrail",
                    "severity": "High",
                    "resource_type": "AWS CloudTrail",
                    "resource_id": "none",
                    "description": "CloudTrail is not enabled in this account",
                    "recommendation": (
                        "Enable CloudTrail to track API activity across your AWS account"
                    ),
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )
            return findings

        # Check each trail's configuration
        for trail in trails:
            trail_name = trail.get("Name", "")
            trail_arn = trail.get("TrailARN", "")
            s3_bucket = trail.get("S3BucketName", "")

            # Check if logging is enabled
            status = cloudtrail.get_trail_status(Name=trail_name)
            if not status.get("IsLogging", False):
                findings.append(
                    {
                        "id": f"CT-LOGGING-{trail_name[:8]}",
                        "category": "CloudTrail",
                        "severity": "High",
                        "resource_type": "AWS CloudTrail",
                        "resource_id": trail_arn,
                        "description": f"CloudTrail {trail_name} is not actively logging",
                        "recommendation": "Enable logging for the CloudTrail trail",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

            # Check multi-region logging
            if not trail.get("IsMultiRegionTrail", False):
                findings.append(
                    {
                        "id": f"CT-REGION-{trail_name[:8]}",
                        "category": "CloudTrail",
                        "severity": "Medium",
                        "resource_type": "AWS CloudTrail",
                        "resource_id": trail_arn,
                        "description": (
                            f"CloudTrail {trail_name} is not configured for multi-region"
                        ),
                        "recommendation": "Enable multi-region logging for complete coverage",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

            # Check management events
            selectors = cloudtrail.get_event_selectors(TrailName=trail_name).get(
                "EventSelectors", []
            )

            management_events_enabled = False
            for selector in selectors:
                if selector.get("ReadWriteType") == "All" and selector.get(
                    "IncludeManagementEvents", False
                ):
                    management_events_enabled = True
                    break

            if not management_events_enabled:
                findings.append(
                    {
                        "id": f"CT-MGMT-{trail_name[:8]}",
                        "category": "CloudTrail",
                        "severity": "Medium",
                        "resource_type": "AWS CloudTrail",
                        "resource_id": trail_arn,
                        "description": (
                            f"CloudTrail {trail_name} is not logging all management events"
                        ),
                        "recommendation": "Enable logging of all management events",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

            # Check log file validation
            if not trail.get("LogFileValidationEnabled", False):
                findings.append(
                    {
                        "id": f"CT-VALID-{trail_name[:8]}",
                        "category": "CloudTrail",
                        "severity": "Low",
                        "resource_type": "AWS CloudTrail",
                        "resource_id": trail_arn,
                        "description": (
                            f"CloudTrail {trail_name} does not have log validation enabled"
                        ),
                        "recommendation": "Enable log file validation for integrity",
                        "compliance": "AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )

            # Check S3 bucket encryption
            try:
                s3.get_bucket_encryption(Bucket=s3_bucket)
            except Exception as e:
                if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                    findings.append(
                        {
                            "id": f"CT-ENC-{trail_name[:8]}",
                            "category": "CloudTrail",
                            "severity": "Medium",
                            "resource_type": "AWS CloudTrail",
                            "resource_id": trail_arn,
                            "description": (
                                f"S3 bucket {s3_bucket} for CloudTrail {trail_name} "
                                "is not encrypted"
                            ),
                            "recommendation": "Enable encryption for CloudTrail S3 bucket",
                            "compliance": "AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )

        # If no findings detected, add a positive note
        if not findings:
            findings.append(
                {
                    "id": "CT-POSITIVE-001",
                    "category": "CloudTrail",
                    "severity": "Informational",
                    "resource_type": "AWS CloudTrail",
                    "resource_id": "account",
                    "description": "CloudTrail is properly configured",
                    "recommendation": "Continue monitoring CloudTrail configuration",
                    "compliance": "AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )

    except Exception as e:
        error_msg = str(e)
        print(f"Error collecting CloudTrail findings: {error_msg}")
        findings.append(
            {
                "id": "CT-ERROR",
                "category": "CloudTrail",
                "severity": "Medium",
                "resource_type": "AWS CloudTrail",
                "resource_id": "error",
                "description": f"Error collecting findings: {error_msg}",
                "recommendation": "Check Lambda role permissions for CloudTrail",
                "compliance": "N/A",
                "detection_date": datetime.datetime.now().isoformat(),
            }
        )

    print(f"Collected {len(findings)} CloudTrail findings")
    return findings
