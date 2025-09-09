"""
Module for collecting AWS IAM-related security findings.

This module analyzes AWS Identity and Access Management (IAM) configuration to identify
security risks and compliance issues related to users, roles, policies, and credentials.

Key security checks performed:
1. Users with console access but no MFA enabled
2. Access keys older than 90 days
3. Users with administrator privileges
4. Unused IAM roles
5. Weak or missing password policies

Each finding includes:
- Unique identifier
- Severity rating
- Affected resource details
- Description of the issue
- Recommended remediation steps
- Relevant compliance frameworks (CIS, AWS Well-Architected)

Author: Security Engineering Team
Last Updated: 2025-04-01
"""

import datetime  # For calculating dates and creating timestamps


def collect_iam_findings(iam):
    """
    Collect IAM-related security findings from an AWS account.

    This function performs several important security checks on IAM users, roles,
    and account-level settings to identify potential security risks.

    Args:
        iam (boto3.client): A boto3 IAM client with appropriate permissions

    Returns:
        list: A list of dictionaries, each representing a security finding with
              standardized fields for severity, description, remediation, etc.

    Security Checks Performed:
        - Users with console access but no MFA (high severity)
        - Users with access keys older than 90 days (medium severity)
        - Users with administrator privileges (medium severity)
        - Unused IAM roles that might increase attack surface (low severity)
        - Weak or missing password policies (medium/high severity)

    Compliance Frameworks:
        - CIS AWS Foundations Benchmark
        - AWS Well-Architected Framework Security Pillar
    """
    findings = []
    print("Collecting IAM findings...")

    try:
        # Get all IAM users in the account
        # IAM API returns paginated results, so we need to handle that
        # by continuing to make calls until we get all users
        print("  Retrieving all IAM users...")
        response = iam.list_users()
        users = response["Users"]  # Start with the first page of results

        # If the results are truncated (more pages available), keep fetching
        while response.get("IsTruncated", False):
            response = iam.list_users(
                Marker=response["Marker"]
            )  # Get next page using marker
            users.extend(response["Users"])  # Add these users to our list

        print(f"  Found {len(users)} IAM users")

        # Check each user for security issues
        # We perform multiple security checks on each user
        print("  Starting security checks on each user...")
        for user in users:
            username = user["UserName"]

            # ==== CHECK 1: User has console access but no MFA ====
            # This is a critical security risk - console access should always require MFA
            # First, check if the user has console access by looking for a login profile
            login_profile_exists = False
            try:
                # If this call succeeds, the user has console access
                iam.get_login_profile(UserName=username)
                login_profile_exists = True
            except iam.exceptions.NoSuchEntityException:
                # No login profile means the user can't access the AWS console
                login_profile_exists = False

            if login_profile_exists:
                # User can log in to the console, now check if they have MFA enabled
                mfa_response = iam.list_mfa_devices(UserName=username)

                # If MFADevices list is empty, no MFA devices are registered
                if not mfa_response["MFADevices"]:
                    findings.append(
                        {
                            "id": f"IAM-001-{username}",  # Unique ID for this finding
                            "category": "IAM",  # This is an IAM-related finding
                            "severity": "High",  # High severity - this is a significant risk
                            "resource_type": "IAM User",  # The affected resource type
                            "resource_id": username,  # The specific resource
                            "description": f"User {username} has console access but no MFA enabled",
                            "recommendation": "Enable MFA for all users with console access",
                            "compliance": "CIS 1.2, AWS Well-Architected",  # Compliance frameworks
                            "detection_date": datetime.datetime.now().isoformat(),  # Detection time
                        }
                    )
                    print(
                        f"    FINDING: User {username} has console access without MFA"
                    )

            # ==== CHECK 2: Access keys older than 90 days ====
            # Access keys should be rotated regularly to limit the impact of compromised credentials
            keys_response = iam.list_access_keys(UserName=username)

            # Check each access key for the user
            for key in keys_response["AccessKeyMetadata"]:
                key_id = key[
                    "AccessKeyId"
                ]  # The access key ID (e.g., AKIAIOSFODNN7EXAMPLE)
                key_created = key[
                    "CreateDate"
                ]  # When the key was created (datetime object)

                # Calculate how old the key is in days
                # We need to use timezone-aware datetime objects for correct calculation
                key_age_days = (
                    datetime.datetime.now(datetime.timezone.utc) - key_created
                ).days

                # Keys older than 90 days violate security best practices
                if key_age_days > 90:
                    findings.append(
                        {
                            "id": f"IAM-002-{key_id}",
                            "category": "IAM",
                            "severity": "Medium",  # Medium severity - risk increases with age
                            "resource_type": "IAM Access Key",
                            "resource_id": f"{username}/{key_id}",  # Format: username/key-id
                            "description": f"Access key {key_id} for user {username}"
                            f" is {key_age_days} days old",
                            "recommendation": "Rotate access keys at least every 90 days",
                            "compliance": "CIS 1.4, AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )
                    print(
                        f"    FINDING: Access key {key_id} for {username} is {key_age_days} days"
                    )

            # ==== CHECK 3: Users with wide administrative permissions ====
            # Following the principle of least privilege, users should only have permissions
            # necessary for their job function. Administrator access should be limited.

            # Get policies directly attached to this user (managed policies)
            attached_policies = iam.list_attached_user_policies(UserName=username)[
                "AttachedPolicies"
            ]

            # Look for policy names that suggest administrative privileges
            # This is a simple check that looks for keywords in policy names
            # A more thorough check would analyze policy contents and permissions
            for policy in attached_policies:
                if (
                    "admin" in policy["PolicyName"].lower()
                    or "administrator" in policy["PolicyName"].lower()
                ):
                    findings.append(
                        {
                            "id": f"IAM-003-{username}",
                            "category": "IAM",
                            "severity": "Medium",  # Medium severity - depends on user activity
                            "resource_type": "IAM User",
                            "resource_id": username,
                            "description": f"User {username} has potentially wide privileges"
                            f' via policy {policy["PolicyName"]}',
                            "recommendation": "Apply least privilege principle to IAM users",
                            "compliance": "CIS 1.16, AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )
                    print(
                        f"    FINDING: User {username} has admin policy: {policy['PolicyName']}"
                    )

        # ==== CHECK 4: Unused IAM roles ====
        # Unused roles should be removed to reduce the attack surface
        # First, retrieve all roles in the account (handling pagination)
        print("  Retrieving all IAM roles...")
        response = iam.list_roles()
        roles = response["Roles"]  # Start with the first page of results

        # If more pages exist, continue retrieving them
        while response.get("IsTruncated", False):
            response = iam.list_roles(Marker=response["Marker"])
            roles.extend(response["Roles"])

        print(f"  Found {len(roles)} IAM roles")
        print("  Checking for unused roles...")

        # Examine each role to see if it's been used
        for role in roles:
            role_name = role["RoleName"]

            # Skip AWS service-linked roles
            # These are managed by AWS services and shouldn't be removed manually
            if "service-role/" not in role["Path"] and not role_name.startswith(
                "AWSServiceRole"
            ):
                # Check when the role was last used
                # AWS tracks this information in the RoleLastUsed attribute
                last_used_response = (
                    iam.get_role(RoleName=role_name)
                    .get("Role", {})
                    .get("RoleLastUsed", {})
                )

                # If LastUsedDate is missing, the role has never been used
                if "LastUsedDate" not in last_used_response:
                    findings.append(
                        {
                            "id": f"IAM-004-{role_name}",
                            "category": "IAM",
                            "severity": "Low",  # Low severity - this is more of a hygiene issue
                            "resource_type": "IAM Role",
                            "resource_id": role_name,
                            "description": f"Role {role_name} appears to be unused",
                            "recommendation": (
                                "Consider removing unused roles to reduce attack surface"
                            ),
                            "compliance": "AWS Well-Architected",
                            "detection_date": datetime.datetime.now().isoformat(),
                        }
                    )
                    print(f"    FINDING: Role {role_name} appears to be unused")

        # ==== CHECK 5: Account password policy ====
        # The account should have a strong password policy that meets industry standards
        # This applies to all IAM users who can log in to the AWS Management Console
        print("  Checking account password policy...")
        try:
            # Retrieve the current password policy for the account
            password_policy = iam.get_account_password_policy()["PasswordPolicy"]

            # Check if the policy meets security best practices
            # Based on CIS AWS Foundations Benchmark recommendations
            if (
                not password_policy.get(
                    "RequireUppercaseCharacters", False
                )  # Require uppercase
                or not password_policy.get(
                    "RequireLowercaseCharacters", False
                )  # Require lowercase
                or not password_policy.get("RequireSymbols", False)  # Require symbols
                or not password_policy.get("RequireNumbers", False)  # Require numbers
                or password_policy.get("MinimumPasswordLength", 0) < 14  # Min 14 chars
            ):
                findings.append(
                    {
                        "id": "IAM-005",
                        "category": "IAM",
                        "severity": "Medium",
                        "resource_type": "IAM Password Policy",
                        "resource_id": "account-password-policy",
                        "description": (
                            "IAM password policy does not meet security best practices"
                        ),
                        "recommendation": (
                            "Configure a strong password policy requiring at least 14 "
                            "characters with a mix of character types"
                        ),
                        "compliance": "CIS 1.5-1.11, AWS Well-Architected",
                        "detection_date": datetime.datetime.now().isoformat(),
                    }
                )
                print(
                    "    FINDING: Password policy does not meet security best practices"
                )

        except iam.exceptions.NoSuchEntityException:
            # This exception means no password policy has been set
            # Having no policy at all is a high severity issue
            findings.append(
                {
                    "id": "IAM-006",
                    "category": "IAM",
                    "severity": "High",  # High severity - significant security gap
                    "resource_type": "IAM Password Policy",
                    "resource_id": "account-password-policy",
                    "description": "No IAM password policy is set for the account",
                    "recommendation": "Configure a strong password policy",
                    "compliance": "CIS 1.5-1.11, AWS Well-Architected",
                    "detection_date": datetime.datetime.now().isoformat(),
                }
            )
            print("    FINDING: No password policy is set for the account")

    except Exception as e:
        # Global error handling for the entire module
        # If something goes wrong with IAM checks, we still want to:
        # 1. Log the error for debugging
        # 2. Create a finding so it's visible in the report
        # 3. Continue with the rest of the security checks
        error_msg = str(e)
        print(f"Error collecting IAM findings: {error_msg}")

        # Include a stack trace for better debugging
        import traceback

        print(f"Error stack trace: {traceback.format_exc()}")

        # Add an error finding so it appears in the report
        findings.append(
            {
                "id": "IAM-ERROR",  # Special ID for error findings
                "category": "IAM",
                "severity": "Medium",
                "resource_type": "IAM Service",
                "resource_id": "error",
                "description": f"Error collecting IAM findings: {error_msg}",
                "recommendation": (
                    "Check Lambda execution role permissions for IAM ReadOnly access"
                ),
                "compliance": "N/A",  # Not applicable for errors
                "detection_date": datetime.datetime.now().isoformat(),
            }
        )

    # Module complete - report findings count for logging
    print(f"Collected {len(findings)} IAM findings")
    return findings  # Return all collected findings to the main handler
