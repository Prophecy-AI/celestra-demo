"""
Unit tests for tool modules - verifies each tool's prompt functions
"""

import unittest


class TestToolModules(unittest.TestCase):
    """Test cases for tool modules"""

    def test_text_to_sql_rx_module(self):
        """Test text_to_sql_rx tool module"""
        from agent_v3.tools.text_to_sql_rx import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_rx', info)
        self.assertIn('Parameters:', info)

        prompt = prompts.get_system_prompt(
            current_date='2025-01-01',
            table_name='test_table'
        )
        self.assertIsInstance(prompt, str)
        self.assertIn('BigQuery', prompt)
        self.assertIn('2025-01-01', prompt)
        self.assertIn('test_table', prompt)

    def test_text_to_sql_med_module(self):
        """Test text_to_sql_med tool module"""
        from agent_v3.tools.text_to_sql_med import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_med', info)

        prompt = prompts.get_system_prompt(
            current_date='2025-01-01',
            table_name='test_table'
        )
        self.assertIsInstance(prompt, str)
        self.assertIn('medical claims', prompt)

    def test_text_to_sql_provider_payments_module(self):
        """Test text_to_sql_provider_payments tool module"""
        from agent_v3.tools.text_to_sql_provider_payments import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_provider_payments', info)

        prompt = prompts.get_system_prompt(table_name='test_table')
        self.assertIsInstance(prompt, str)
        self.assertIn('payments', prompt.lower())
        self.assertIn('npi_number', prompt.lower())

    def test_text_to_sql_providers_bio_module(self):
        """Test text_to_sql_providers_bio tool module"""
        from agent_v3.tools.text_to_sql_providers_bio import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_providers_bio', info)

        prompt = prompts.get_system_prompt(table_name='test_table')
        self.assertIsInstance(prompt, str)
        self.assertIn('biographical', prompt.lower())
        self.assertIn('specialty', prompt.lower())

    def test_bigquery_sql_query_module(self):
        """Test bigquery_sql_query tool module (non-LLM tool)"""
        from agent_v3.tools.bigquery_sql_query import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('bigquery_sql_query', info)

        prompt = prompts.get_system_prompt()
        self.assertIsNone(prompt)

    def test_communicate_module(self):
        """Test communicate tool module (non-LLM tool)"""
        from agent_v3.tools.communicate import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('communicate', info)

        prompt = prompts.get_system_prompt()
        self.assertIsNone(prompt)

    def test_complete_module(self):
        """Test complete tool module (non-LLM tool)"""
        from agent_v3.tools.complete import prompts

        info = prompts.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('complete', info)

        prompt = prompts.get_system_prompt()
        self.assertIsNone(prompt)

    def test_all_tool_classes_have_required_methods(self):
        """Test that all tool classes have required class methods"""
        from agent_v3.tools import (
            TextToSQLRx,
            TextToSQLMed,
            TextToSQLProviderPayments,
            TextToSQLProvidersBio,
            BigQuerySQLQuery,
            Communicate,
            Complete
        )

        tool_classes = [
            TextToSQLRx,
            TextToSQLMed,
            TextToSQLProviderPayments,
            TextToSQLProvidersBio,
            BigQuerySQLQuery,
            Communicate,
            Complete
        ]

        for tool_class in tool_classes:
            with self.subTest(tool=tool_class.__name__):
                self.assertTrue(
                    hasattr(tool_class, 'get_orchestrator_info'),
                    f"{tool_class.__name__} must have get_orchestrator_info()"
                )
                self.assertTrue(
                    hasattr(tool_class, 'get_system_prompt'),
                    f"{tool_class.__name__} must have get_system_prompt()"
                )

    def test_system_prompt_generation(self):
        """Test that main system prompt generates correctly with dynamic tools"""
        from agent_v3.prompts import get_main_system_prompt

        prompt = get_main_system_prompt()

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 1000, "System prompt should be substantial")

        # Verify all tools are in the prompt
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
            self.assertIn(tool, prompt, f"Tool '{tool}' should be in system prompt")


if __name__ == '__main__':
    unittest.main()
