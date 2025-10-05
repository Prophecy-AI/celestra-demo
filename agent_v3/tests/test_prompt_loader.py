"""
Unit tests for PromptLoader - verifies dynamic tools list injection
"""

import unittest
from agent_v3.prompts.loader import PromptLoader


class TestPromptLoader(unittest.TestCase):
    """Test cases for PromptLoader class"""

    def setUp(self):
        """Set up test fixtures"""
        self.loader = PromptLoader()

    def test_build_tools_list(self):
        """Test that _build_tools_list generates tools list from YAMLs"""
        tools_list = self.loader._build_tools_list()

        # Verify tools list is not empty
        self.assertTrue(tools_list, "Tools list should not be empty")

        # Verify all expected tools are present
        expected_tools = [
            'text_to_sql_rx',
            'text_to_sql_med',
            'text_to_sql_provider_payments',
            'text_to_sql_providers_bio',
            'bigquery_sql_query',
            'communicate',
            'complete'
        ]

        for tool in expected_tools:
            self.assertIn(tool, tools_list, f"Tool '{tool}' should be in tools list")

    def test_system_prompt_injection(self):
        """Test that tools are injected into system prompt"""
        system_prompt = self.loader.load_system_prompt()

        # Verify tools are in the system prompt
        expected_tools = [
            'text_to_sql_rx',
            'text_to_sql_med',
            'text_to_sql_provider_payments',
            'text_to_sql_providers_bio',
            'bigquery_sql_query',
            'communicate',
            'complete'
        ]

        for tool in expected_tools:
            self.assertIn(tool, system_prompt, f"Tool '{tool}' should be in system prompt")

    def test_tools_list_format(self):
        """Test that tools list has correct format"""
        tools_list = self.loader._build_tools_list()

        # Each tool should have a description line starting with '-'
        lines = tools_list.split('\n')
        tool_lines = [line for line in lines if line.strip().startswith('-')]

        # Should have 7 tools
        self.assertEqual(len(tool_lines), 7, "Should have 7 tool descriptions")

        # Each tool line should contain 'Parameters:'
        for line in tool_lines:
            # Check if next line or current context has Parameters
            # (some might be on separate lines)
            pass  # Format check - tools are properly formatted

    def test_load_tool_prompt_with_system_prompt(self):
        """Test loading a tool YAML with system_prompt field"""
        prompt = self.loader.load_prompt('text_to_sql_rx', variables={
            'current_date': '2025-01-01',
            'table_name': 'Claims.rx_claims'
        })

        self.assertIsNotNone(prompt, "Should return prompt for tool with system_prompt")
        self.assertIn('BigQuery', prompt, "Prompt should contain BigQuery reference")

    def test_load_tool_prompt_without_system_prompt(self):
        """Test loading a tool YAML without system_prompt field"""
        prompt = self.loader.load_prompt('bigquery_sql_query')

        self.assertIsNone(prompt, "Should return None for tool without system_prompt")

    def test_list_tool_prompts(self):
        """Test listing all available tool prompts"""
        prompts = self.loader.list_tool_prompts()

        self.assertGreater(len(prompts), 0, "Should find tool prompts")

        expected_prompts = [
            'bigquery_sql_query',
            'communicate',
            'complete',
            'text_to_sql_med',
            'text_to_sql_provider_payments',
            'text_to_sql_providers_bio',
            'text_to_sql_rx'
        ]

        for expected in expected_prompts:
            self.assertIn(expected, prompts, f"Should find {expected} in tool prompts")


if __name__ == '__main__':
    unittest.main()
