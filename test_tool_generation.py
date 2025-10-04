"""
Test script for tool generation system

Usage:
    python test_tool_generation.py
"""
from agent_v3.tools import ToolGenerator


def test_tool_generation():
    """Test generating a new SQL tool"""

    gen = ToolGenerator()

    # Example configuration for a pharmacy SQL tool
    config = {
        "tool_name": "text_to_sql_pharmacy_test",
        "class_name": "TextToSQLPharmacyTest",
        "description": "Generate SQL for pharmacy claims data",
        "table_name": "`unique-bonbon-472921-q8.Claims.pharmacy_claims`",
        "key_columns": [
            {
                "name": "PHARMACY_NPI",
                "type": "STRING",
                "description": "National Provider Identifier of the pharmacy"
            },
            {
                "name": "PHARMACY_NAME",
                "type": "STRING",
                "description": "Name of the pharmacy"
            },
            {
                "name": "PHARMACY_STATE",
                "type": "STRING",
                "description": "State where pharmacy is located"
            },
            {
                "name": "FILL_DATE",
                "type": "DATE",
                "description": "Date prescription was filled"
            },
            {
                "name": "PRESCRIPTION_COUNT",
                "type": "INTEGER",
                "description": "Number of prescriptions filled"
            }
        ],
        "column_selection_priority": "- For pharmacy queries: Include ONLY PHARMACY_NPI and requested metrics\n  - NEVER use SELECT *",
        "aggregation_rules": [
            "- For counting pharmacies: COUNT(DISTINCT PHARMACY_NPI)",
            "- For counting prescriptions: SUM(PRESCRIPTION_COUNT)"
        ],
        "date_filtering": "Use FILL_DATE for prescription fill dates\n  - Always use DATE format: '2024-01-01'",
        "item_matching": "Use UPPER() for case-insensitive matching",
        "output_format": "- Return clean, executable BigQuery Standard SQL\n  - Include appropriate GROUP BY when using aggregations\n  - LIMIT results to 1,000,000 (1M) rows",
        "lookup_context": {
            "PHARMACY_STATE": ["CA", "NY", "TX", "FL"],
            "PHARMACY_TYPE": ["Retail", "Mail Order", "Specialty"]
        }
    }

    print("="*80)
    print("TOOL GENERATION TEST")
    print("="*80)

    # Validate configuration
    print("\n1. Validating configuration...")
    error = gen.validate_config("sql", config)
    if error:
        print(f"   ❌ Validation failed: {error}")
        return
    print("   ✅ Configuration valid")

    # Preview generated code
    print("\n2. Generating code preview...")
    tool_code, prompt_yaml, error = gen.preview_tool("sql", config)

    if error:
        print(f"   ❌ Generation failed: {error}")
        return

    print("   ✅ Code generated successfully")
    print(f"\n   Python code: {len(tool_code)} characters")
    print(f"   YAML prompt: {len(prompt_yaml)} characters")

    # Show previews
    print("\n" + "="*80)
    print("PYTHON CODE PREVIEW (first 50 lines)")
    print("="*80)
    lines = tool_code.split('\n')[:50]
    for i, line in enumerate(lines, 1):
        print(f"{i:3}: {line}")

    total_lines = len(tool_code.split('\n'))
    if total_lines > 50:
        remaining = total_lines - 50
        print(f"\n... ({remaining} more lines)")

    print("\n" + "="*80)
    print("YAML PROMPT PREVIEW (first 40 lines)")
    print("="*80)
    lines = prompt_yaml.split('\n')[:40]
    for i, line in enumerate(lines, 1):
        print(f"{i:3}: {line}")

    total_lines = len(prompt_yaml.split('\n'))
    if total_lines > 40:
        remaining = total_lines - 40
        print(f"\n... ({remaining} more lines)")

    print("\n" + "="*80)
    print("TEST OPTIONS")
    print("="*80)
    print("\nTo actually create the tool files, run:")
    print(f'    python -c "from agent_v3.tools import ToolGenerator; gen = ToolGenerator(); gen.create_tool(\'sql\', {config})"')

    print("\nTo delete the test tool files (if created), run:")
    print(f'    python -c "from agent_v3.tools import ToolGenerator; gen = ToolGenerator(); gen.delete_tool(\'{config["tool_name"]}\')"')

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_tool_generation()
