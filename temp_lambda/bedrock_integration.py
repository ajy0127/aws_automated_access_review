"""
Amazon Bedrock Integration Module for AI-powered Security Analysis

This module provides AI integration with Amazon Bedrock to generate human-readable
security narratives based on technical findings. It transforms raw security data into
actionable insights and recommendations for both technical and business stakeholders.

Key Features:
- Connects to Amazon Bedrock's Claude model for natural language generation
- Formats security findings into structured prompts for optimal AI analysis
- Generates executive summaries, critical findings analysis, and recommendations
- Provides fallback capabilities for resilience when AI service is unavailable

The module follows a modular design pattern for maximum flexibility:
1. prepare_prompt(): Structures data for optimal AI processing
2. invoke_claude_model(): Handles API communication with Bedrock
3. extract_narrative_claude(): Processes the AI response
4. generate_fallback_narrative(): Ensures reliability when AI fails

Author: Security Engineering Team
Last Updated: 2025-04-01
"""

import json  # For parsing and formatting API requests/responses
import boto3  # AWS SDK for Python to interact with Amazon Bedrock


def get_ai_analysis(bedrock_client, findings):
    """
    Main entry point for getting AI analysis of security findings.
    This function is called by the Lambda handler to generate a narrative summary.

    This function orchestrates the entire AI analysis process:
    1. Organizes findings data into an AI-friendly format
    2. Sends the data to the AI model
    3. Processes the AI response
    4. Handles any errors gracefully with fallback content

    Args:
        bedrock_client: Initialized Bedrock client with appropriate permissions
        findings (list): List of security findings in standardized format
                        Each finding should be a dictionary with fields like
                        severity, category, description, resource_type, etc.

    Returns:
        str: AI-generated narrative summary ready for inclusion in email reports
             If AI generation fails, returns a basic fallback narrative
    """
    try:
        # Step 1: Prepare the prompt for Claude model
        # This formats our findings into a structure that helps the AI understand the data
        print("Preparing AI prompt from security findings...")
        prompt = prepare_prompt(findings)

        # Step 2: Call Bedrock with the Claude model
        # This sends our formatted data to Amazon Bedrock and gets a response
        print("Invoking Amazon Bedrock Claude model...")
        response = invoke_claude_model(bedrock_client, prompt)

        # Step 3: Extract and return the generated narrative
        # This processes the raw API response and extracts the useful content
        print("Processing AI response...")
        narrative = extract_narrative_claude(response)
        print("AI narrative generation successful")
        return narrative

    except Exception as e:
        # Error handling - if anything goes wrong, log it and use fallback content
        print(f"Error generating narrative with Bedrock: {str(e)}")

        # Include a stack trace for better debugging
        import traceback

        print(f"Error stack trace: {traceback.format_exc()}")

        # Return a fallback narrative if Bedrock fails
        # This ensures the user still gets a useful report even if AI fails
        print("Using fallback narrative due to error")
        return generate_fallback_narrative()


def generate_narrative(findings):
    """
    Generate a narrative summary of security findings using Amazon Bedrock's Claude model.

    This is a convenience function that handles Bedrock client initialization
    and then calls the main analysis function. Most code should call this function
    rather than working with the lower-level functions directly.

    Args:
        findings (list): List of security findings from various AWS services

    Returns:
        str: AI-generated narrative summary that can be included in reports

    Example usage:
        from bedrock_integration import generate_narrative

        # After collecting security findings
        narrative = generate_narrative(all_findings)

        # Include narrative in email or report
        send_email(recipient, subject, narrative, attachment)
    """
    # Initialize Bedrock client
    # The client is created here so callers don't need to worry about it
    bedrock = boto3.client("bedrock-runtime")

    # Call the main function with the initialized client
    return get_ai_analysis(bedrock, findings)


def prepare_prompt(findings):
    """
    Prepare a prompt for the Claude model based on the security findings.

    This function transforms raw security findings into a structured format that
    helps the AI model understand and analyze the data effectively. The prompt
    includes:
    - Statistical summary (counts by severity)
    - Categorized findings with details
    - XML tags to help the AI identify the findings section

    Args:
        findings (list): List of security findings from various AWS services
                        Each finding should be a dictionary with fields like
                        severity, category, description, resource_type, etc.

    Returns:
        str: Formatted prompt for the Claude model, optimized for security analysis
    """
    # Step 1: Count findings by severity for statistical summary
    # Initialize counters for each severity level
    severity_counts = {
        "Critical": 0,  # Immediate action required
        "High": 0,  # High priority issues
        "Medium": 0,  # Important but less urgent
        "Low": 0,  # Minor issues
        "Informational": 0,  # Awareness only
    }

    # Count findings for each severity level
    for finding in findings:
        if finding.get("severity") in severity_counts:
            severity_counts[finding.get("severity")] += 1

    # Step 2: Group findings by category for better organization
    # e.g., IAM findings, S3 findings, etc.
    findings_by_category = {}
    for finding in findings:
        # Use "Other" as default category if not specified
        category = finding.get("category", "Other")

        # Initialize category list if this is first finding of this type
        if category not in findings_by_category:
            findings_by_category[category] = []

        # Add this finding to its category group
        findings_by_category[category].append(finding)

    # Step 3: Create a formatted summary of findings for the prompt
    # We'll organize them by category, with the most severe findings first
    findings_summary = []

    # Process each category of findings
    for category, category_findings in findings_by_category.items():
        # Add category header
        findings_summary.append(f"\nCategory: {category}")

        # Define severity order for sorting (Critical first)
        severity_order = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
            "Informational": 4,
        }

        # Sort findings within this category by severity
        sorted_findings = sorted(
            category_findings,
            key=lambda x: severity_order.get(x.get("severity", "Low"), 999),
        )

        # Add the 5 most important findings for this category
        # Limiting to 5 per category keeps the prompt manageable in size
        for finding in sorted_findings[:5]:
            summary = (
                f"  - {finding.get('severity')}: {finding.get('description')} "
                f"({finding.get('resource_type')}: {finding.get('resource_id')})"
            )
            findings_summary.append(summary)

        # If there are more findings than we showed, add a count of remaining ones
        if len(category_findings) > 5:
            findings_summary.append(
                f"  - ... and {len(category_findings) - 5} more {category} findings"
            )

    # Step 4: Construct the complete prompt for Claude
    # We use XML tags to help Claude identify the findings section clearly
    # Format is designed to be clear and structured for optimal AI processing
    prompt = f"""<findings>
# AWS Security Findings Summary

Total findings: {len(findings)}
- Critical: {severity_counts['Critical']}
- High: {severity_counts['High']}
- Medium: {severity_counts['Medium']}
- Low: {severity_counts['Low']}
- Informational: {severity_counts['Informational']}

## Findings by Category:
{chr(10).join(findings_summary)}
</findings>
"""

    return prompt


def invoke_claude_model(bedrock, prompt):
    """
    Invoke the Amazon Claude model via Bedrock API.

    This function handles the API communication with Amazon Bedrock,
    configuring the request parameters and processing the response.

    Args:
        bedrock: Initialized Bedrock client with appropriate permissions
        prompt: The structured prompt containing security findings

    Returns:
        dict: The raw model's response as a Python dictionary

    Note:
        This function configures specific parameters for the Claude model:
        - Temperature: Controls randomness (0.7 balances creativity and consistency)
        - Max tokens: Limits response length (4096 provides detailed but concise analysis)
        - Top-p: Controls diversity of responses (0.9 is a balanced setting)
    """
    # Step 1: Select model and set parameters
    # Using Claude v2 for comprehensive text generation capabilities
    model_id = "anthropic.claude-v2"  # Amazon Bedrock model identifier

    # Step 2: Construct the complete prompt with instructions
    # The prompt follows Claude's required Human/Assistant format
    # and includes specific instructions for security report generation
    request_body = {
        "prompt": (
            # Begin with Claude's expected format
            "\n\nHuman: You are a cybersecurity expert analyzing AWS security findings. "
            "Generate a concise, professional security report based on the following "
            f"findings:\n\n{prompt}\n\n"
            # Specific instructions for report structure
            "Your report should include:\n"
            "1. An executive summary of the security posture\n"
            "2. Analysis of the most critical findings\n"
            "3. Clear, actionable recommendations\n"
            "4. Compliance implications\n\n"
            # Style guidance for the report
            "Format the report with clear headings and concise language suitable for both "
            "technical and non-technical stakeholders.\n\n"
            # Claude's expected assistant prefix
            "Assistant: I'll analyze the findings and provide a comprehensive security "
            "report.\n\n"
        ),
        # Model configuration parameters
        "max_tokens_to_sample": 4096,  # Maximum response length (roughly 3000 words)
        "temperature": 0.7,  # Balances creativity and consistency
        "top_p": 0.9,  # Controls diversity of word selection
    }

    # Step 3: Call the Bedrock API
    print(f"Calling Bedrock API with model: {model_id}")
    response = bedrock.invoke_model(
        modelId=model_id,  # Which model to use
        contentType="application/json",  # Format of our request
        accept="application/json",  # Format we want for response
        body=json.dumps(request_body),  # Convert request to JSON string
    )

    # Step 4: Process the response
    # The response body is a stream that needs to be read and parsed
    response_body = json.loads(response.get("body").read())
    print("Successfully received response from Bedrock")

    return response_body


def extract_narrative_claude(response):
    """
    Extract the generated narrative from the Bedrock response.

    This function handles the extraction of the useful narrative text
    from the raw API response and performs any necessary formatting.

    Args:
        response: The raw response from Bedrock API as a Python dictionary

    Returns:
        str: The extracted narrative text, ready for inclusion in reports

    Note:
        If extraction fails for any reason, this function will fall back
        to a basic pre-written narrative to ensure the report generation
        process isn't blocked.
    """
    try:
        # For Claude model, the generated text is in the "completion" field
        # We strip any extra whitespace to ensure clean formatting
        narrative = response.get("completion", "")

        # Apply any additional formatting or post-processing here if needed
        # For example, we might want to add a title, fix formatting issues, etc.

        return narrative.strip()

    except Exception as e:
        # Handle any errors during extraction
        print(f"Error extracting narrative from Bedrock response: {str(e)}")

        # Log the actual response for debugging
        print(f"Problematic response: {response}")

        # Include a stack trace for better debugging
        import traceback

        print(f"Error stack trace: {traceback.format_exc()}")

        # Fall back to a pre-written narrative
        return generate_fallback_narrative()


def generate_fallback_narrative():
    """
    Generate a basic narrative if the AI model fails.

    This function provides a safety net when AI generation fails,
    ensuring that users still receive a useful report even if
    Bedrock is unavailable or returns an error.

    Returns:
        str: A basic narrative summary with general security guidance
    """
    print("Generating fallback narrative due to AI processing failure")

    # Return a professionally formatted basic report
    # This includes general guidance that applies to most AWS environments
    return (
        "# AWS Access Review Report\n\n"
        "## Executive Summary\n\n"
        "Due to technical limitations, a detailed AI analysis could not be generated. "
        "Please refer to the CSV report for a complete list of findings.\n\n"
        "## Key Recommendations\n\n"
        "1. **High Priority:** Review all findings marked as Critical or High priority first\n"
        "2. **Medium Priority:** Address Medium priority findings as part of regular maintenance\n"
        "3. **Low Priority:** Consider Low priority findings for long-term security improvements\n"
        "4. **Ongoing:** Maintain regular security reviews and monitoring\n\n"
        "## Next Steps\n\n"
        "For detailed findings and specific recommendations, please consult the attached CSV"
        " report. Consider scheduling a follow-up security review once the highest priority items"
        " have been addressed.\n\n"
        "---\n"
        "This report was generated by the AWS Access Review Tool. For questions or assistance, "
        "please contact your security team."
    )
