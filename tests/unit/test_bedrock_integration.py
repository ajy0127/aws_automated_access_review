import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the lambda directory to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambda"))
)
import bedrock_integration  # noqa: E402


class TestBedrockIntegration(unittest.TestCase):
    """Test the Bedrock integration module."""

    def test_prepare_prompt(self):
        """Test the prepare_prompt function."""
        # Sample findings data
        findings = [
            {
                "id": "finding1",
                "category": "IAM",
                "severity": "High",
                "resource_type": "AWS::IAM::Policy",
                "resource_id": "policy1",
                "description": "Overly permissive IAM policy",
            },
            {
                "id": "finding2",
                "category": "IAM",
                "severity": "Medium",
                "resource_type": "AWS::IAM::Role",
                "resource_id": "role1",
                "description": "Role with unused permissions",
            },
            {
                "id": "finding3",
                "category": "Security Hub",
                "severity": "Critical",
                "resource_type": "AWS::IAM::User",
                "resource_id": "user1",
                "description": "User with console access but no MFA",
            },
        ]

        # Call the function
        prompt = bedrock_integration.prepare_prompt(findings)

        # Assertions
        self.assertIsInstance(prompt, str)
        self.assertIn("AWS Security Findings Summary", prompt)
        self.assertIn("Total findings: 3", prompt)
        self.assertIn("Critical: 1", prompt)
        self.assertIn("High: 1", prompt)
        self.assertIn("Medium: 1", prompt)


class TestClaudeModelIntegration(unittest.TestCase):
    """Test the Claude model integration."""

    @patch("boto3.client")
    def test_invoke_claude_model(self, mock_boto3_client):
        """Test the invoke_claude_model function."""
        # Mock the Bedrock client
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Mock the response from Bedrock using the Messages API shape
        mock_response = {
            "content": [{"type": "text", "text": "This is a test narrative."}],
            "stop_reason": "end_turn",
        }
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(return_value=json.dumps(mock_response).encode())
            )
        }

        # Call the function
        prompt = "Generate a narrative for AWS Access Review"
        response = bedrock_integration.invoke_claude_model(mock_bedrock, prompt)

        # Assertions
        self.assertEqual(response, mock_response)
        mock_bedrock.invoke_model.assert_called_once()

        # Verify the request body uses the Messages API, not legacy completion
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        body = json.loads(call_kwargs["body"])
        self.assertEqual(body["anthropic_version"], "bedrock-2023-05-31")
        self.assertEqual(body["max_tokens"], 4096)
        self.assertIn("messages", body)
        self.assertNotIn("max_tokens_to_sample", body)
        self.assertNotIn("prompt", body)
        # Default model ID should point at some Claude model. Exact ID changes
        # as Bedrock retires versions, so just assert it's an Anthropic Claude.
        self.assertIn("claude", call_kwargs["modelId"])
        self.assertIn("anthropic", call_kwargs["modelId"])


class TestNarrativeExtraction(unittest.TestCase):
    """Test the narrative extraction function."""

    def test_extract_narrative_claude(self):
        """Test the extract_narrative_claude function with the Messages API shape."""
        # Claude 3.x Messages API response
        response = {
            "content": [{"type": "text", "text": "This is a test narrative."}],
            "stop_reason": "end_turn",
        }

        # Call the function
        narrative = bedrock_integration.extract_narrative_claude(response)

        # Assertions
        self.assertEqual(narrative, "This is a test narrative.")

    def test_extract_narrative_claude_legacy_completion(self):
        """Back-compat: legacy text-completion responses still extract cleanly."""
        response = {"completion": "Legacy narrative."}
        self.assertEqual(
            bedrock_integration.extract_narrative_claude(response),
            "Legacy narrative.",
        )


class TestFallbackNarrative(unittest.TestCase):
    """Test the fallback narrative generation."""

    def test_generate_fallback_narrative(self):
        """Test the generate_fallback_narrative function."""
        # Call the function
        narrative = bedrock_integration.generate_fallback_narrative()

        # Assertions
        self.assertIsInstance(narrative, str)
        self.assertIn("AWS Access Review Report", narrative)
        self.assertIn("technical limitations", narrative)


class TestGenerateNarrative(unittest.TestCase):
    """Test the generate_narrative function."""

    @patch("bedrock_integration.get_ai_analysis")
    @patch("boto3.client")
    def test_generate_narrative_success(self, mock_boto3_client, mock_get_ai_analysis):
        """Test the generate_narrative function with successful AI analysis."""
        # Mock the Bedrock client
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Mock the AI analysis
        mock_get_ai_analysis.return_value = "This is a test narrative."

        # Sample findings
        findings = [{"id": "finding1", "severity": "High"}]

        # Call the function
        narrative = bedrock_integration.generate_narrative(findings)

        # Assertions
        self.assertEqual(narrative, "This is a test narrative.")
        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        mock_get_ai_analysis.assert_called_once_with(mock_bedrock, findings)
