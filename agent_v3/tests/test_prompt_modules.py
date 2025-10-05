"""
Unit tests for prompt modules - verifies each tool's prompt functions
"""

import unittest


class TestPromptModules(unittest.TestCase):
    """Test cases for prompt modules"""

    def test_text_to_sql_rx_module(self):
        """Test text_to_sql_rx prompt module"""
        from agent_v3.prompts import text_to_sql_rx

        # Test orchestrator_info
        info = text_to_sql_rx.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_rx', info)
        self.assertIn('Parameters:', info)

        # Test system_prompt
        prompt = text_to_sql_rx.get_system_prompt(
            current_date='2025-01-01',
            table_name='test_table'
        )
        self.assertIsInstance(prompt, str)
        self.assertIn('BigQuery', prompt)
        self.assertIn('2025-01-01', prompt)
        self.assertIn('test_table', prompt)

    def test_text_to_sql_med_module(self):
        """Test text_to_sql_med prompt module"""
        from agent_v3.prompts import text_to_sql_med

        info = text_to_sql_med.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_med', info)

        prompt = text_to_sql_med.get_system_prompt(
            current_date='2025-01-01',
            table_name='test_table'
        )
        self.assertIsInstance(prompt, str)
        self.assertIn('medical claims', prompt)

    def test_text_to_sql_provider_payments_module(self):
        """Test text_to_sql_provider_payments prompt module"""
        from agent_v3.prompts import text_to_sql_provider_payments

        info = text_to_sql_provider_payments.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_provider_payments', info)

        prompt = text_to_sql_provider_payments.get_system_prompt(table_name='test_table')
        self.assertIsInstance(prompt, str)
        self.assertIn('payments', prompt.lower())
        self.assertIn('npi_number', prompt.lower())

    def test_text_to_sql_providers_bio_module(self):
        """Test text_to_sql_providers_bio prompt module"""
        from agent_v3.prompts import text_to_sql_providers_bio

        info = text_to_sql_providers_bio.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('text_to_sql_providers_bio', info)

        prompt = text_to_sql_providers_bio.get_system_prompt(table_name='test_table')
        self.assertIsInstance(prompt, str)
        self.assertIn('biographical', prompt.lower())
        self.assertIn('specialty', prompt.lower())

    def test_bigquery_sql_query_module(self):
        """Test bigquery_sql_query prompt module (non-LLM tool)"""
        from agent_v3.prompts import bigquery_sql_query

        info = bigquery_sql_query.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('bigquery_sql_query', info)

        # Non-LLM tool should return None for system_prompt
        prompt = bigquery_sql_query.get_system_prompt()
        self.assertIsNone(prompt)

    def test_communicate_module(self):
        """Test communicate prompt module (non-LLM tool)"""
        from agent_v3.prompts import communicate

        info = communicate.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('communicate', info)

        prompt = communicate.get_system_prompt()
        self.assertIsNone(prompt)

    def test_complete_module(self):
        """Test complete prompt module (non-LLM tool)"""
        from agent_v3.prompts import complete

        info = complete.get_orchestrator_info()
        self.assertIsInstance(info, str)
        self.assertIn('complete', info)

        prompt = complete.get_system_prompt()
        self.assertIsNone(prompt)

    def test_all_modules_have_required_functions(self):
        """Test that all prompt modules have required functions"""
        modules = [
            'text_to_sql_rx',
            'text_to_sql_med',
            'text_to_sql_provider_payments',
            'text_to_sql_providers_bio',
            'bigquery_sql_query',
            'communicate',
            'complete'
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                module = __import__(f'agent_v3.prompts.{module_name}', fromlist=[''])

                # Check required functions exist
                self.assertTrue(
                    hasattr(module, 'get_orchestrator_info'),
                    f"{module_name} must have get_orchestrator_info()"
                )
                self.assertTrue(
                    hasattr(module, 'get_system_prompt'),
                    f"{module_name} must have get_system_prompt()"
                )


if __name__ == '__main__':
    unittest.main()
