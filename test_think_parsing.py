"""
Test to verify LLM client can parse responses with <think> blocks
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_v3.llm_client import LLMClient


def test_parse_with_think_block():
    """Test that _extract_tool_call can handle <think> blocks before JSON"""

    client = LLMClient()
    available_tools = ["sandbox_exec", "sandbox_write_file", "complete"]

    # Test 1: Simple think block
    response1 = """<think>
I need to create the file first before executing it.
The file doesn't exist yet, so I should use sandbox_write_file.
</think>

{"tool": "sandbox_write_file", "parameters": {"file_path": "/tmp/test.py", "content": "print('hello')"}, "reasoning_trace": "Creating script file"}"""

    result1 = client._extract_tool_call(response1, available_tools)
    print("Test 1 - Simple think block:")
    print(f"  Success: {result1 is not None}")
    if result1:
        print(f"  Tool: {result1.get('tool')}")
        print(f"  Parameters: {result1.get('parameters')}")
        print(f"  Reasoning trace: {result1.get('reasoning_trace')}")
    print()

    # Test 2: Think block with complex nested parameters
    response2 = """<think>
Now I should execute the file I just created.
The file exists at /tmp/test.py.
I'll use a 30 second timeout.
</think>

{"tool": "sandbox_exec", "parameters": {"command": ["python", "/tmp/test.py"], "timeout": 30}, "reasoning_trace": "Executing the test script"}"""

    result2 = client._extract_tool_call(response2, available_tools)
    print("Test 2 - Think block with array in parameters:")
    print(f"  Success: {result2 is not None}")
    if result2:
        print(f"  Tool: {result2.get('tool')}")
        print(f"  Parameters: {result2.get('parameters')}")
        print(f"  Command: {result2.get('parameters', {}).get('command')}")
    print()

    # Test 3: No think block (backward compatibility)
    response3 = """{"tool": "complete", "parameters": {"summary": "Analysis done", "datasets": ["test_data"]}, "reasoning_trace": "Presenting results"}"""

    result3 = client._extract_tool_call(response3, available_tools)
    print("Test 3 - No think block (backward compat):")
    print(f"  Success: {result3 is not None}")
    if result3:
        print(f"  Tool: {result3.get('tool')}")
        print(f"  Datasets: {result3.get('parameters', {}).get('datasets')}")
    print()

    # Test 4: Multiline think with complex reasoning
    response4 = """<think>
Let me verify my assumptions:
1. Did I create the file? Yes, in previous step
2. Does the file path exist? Yes, /tmp/cluster.py
3. Are the column names correct? Need to check schema

Actually, I should inspect the data first before executing.
Let me run a quick schema check.
</think>

{"tool": "sandbox_exec", "parameters": {"command": ["python", "-c", "import polars as pl; df = pl.read_csv('/tmp/data/X.csv'); print(df.schema)"]}, "reasoning_trace": "Checking schema to avoid column name hallucination"}"""

    result4 = client._extract_tool_call(response4, available_tools)
    print("Test 4 - Multiline complex think block:")
    print(f"  Success: {result4 is not None}")
    if result4:
        print(f"  Tool: {result4.get('tool')}")
        print(f"  Command extracted: {len(result4.get('parameters', {}).get('command', [])) > 0}")
    print()

    # Summary
    all_passed = all([result1, result2, result3, result4])
    print("="*60)
    print(f"OVERALL: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    success = test_parse_with_think_block()
    sys.exit(0 if success else 1)
