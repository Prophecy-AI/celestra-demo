"""
Test TOOL-CALL tag extraction
"""
import os
os.environ["DEBUG"] = "1"

from agent_v3.llm_client import LLMClient


def test_with_tool_call_tags():
    """Test that TOOL-CALL tags are properly extracted"""
    client = LLMClient()

    response = """
<think>
I should explore the data first
</think>

<TOOL-CALL>
{
  "tool": "sandbox_exec",
  "parameters": {
    "command": ["python", "-c", "print('hello')"]
  },
  "reasoning_trace": "Testing"
}
</TOOL-CALL>
"""

    result = client._extract_tool_call(response, ["sandbox_exec"])

    print("\n" + "="*80)
    print("TEST 1: With TOOL-CALL tags (should succeed)")
    print("="*80)
    if result and result.get('tool') == 'sandbox_exec':
        print("✅ PASS: Tool call correctly extracted from TOOL-CALL tags")
    else:
        print(f"❌ FAIL: Could not extract from TOOL-CALL tags")

    return result is not None


def test_without_tool_call_tags():
    """Test backward compatibility - still works without tags"""
    client = LLMClient()

    response = """
{
  "tool": "sandbox_write_file",
  "parameters": {
    "file_path": "/tmp/test.py",
    "content": "print('test')"
  },
  "reasoning_trace": "Creating file"
}
"""

    result = client._extract_tool_call(response, ["sandbox_write_file"])

    print("\n" + "="*80)
    print("TEST 2: Without TOOL-CALL tags (backward compat)")
    print("="*80)
    if result and result.get('tool') == 'sandbox_write_file':
        print("✅ PASS: Tool call still works without tags (backward compat)")
    else:
        print(f"❌ FAIL: Backward compatibility broken")

    return result is not None


def test_multiple_tool_calls_with_tags():
    """Test that multiple tool calls are rejected even with tags"""
    client = LLMClient()

    response = """
<TOOL-CALL>
{
  "tool": "sandbox_write_file",
  "parameters": {
    "file_path": "/tmp/test.py",
    "content": "print('test')"
  },
  "reasoning_trace": "Creating file"
}
</TOOL-CALL>

<TOOL-CALL>
{
  "tool": "sandbox_exec",
  "parameters": {
    "command": ["python", "/tmp/test.py"]
  },
  "reasoning_trace": "Executing"
}
</TOOL-CALL>
"""

    result = client._extract_tool_call(response, ["sandbox_write_file", "sandbox_exec"])

    print("\n" + "="*80)
    print("TEST 3: Multiple TOOL-CALL tags (should be REJECTED)")
    print("="*80)
    if result is None:
        print("✅ PASS: Multiple tool calls correctly rejected")
    else:
        print(f"❌ FAIL: Multiple tool calls not rejected")
        print(f"   Tool selected: {result.get('tool')}")

    return result is None


if __name__ == "__main__":
    import sys

    print("\n" + "="*80)
    print("TOOL-CALL TAG EXTRACTION TESTS")
    print("="*80)

    test1 = test_with_tool_call_tags()
    test2 = test_without_tool_call_tags()
    test3 = test_multiple_tool_calls_with_tags()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Test 1 (With tags):       {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (Without tags):    {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 (Multiple tags):   {'✅ PASS' if test3 else '❌ FAIL'}")

    all_pass = test1 and test2 and test3
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print("="*80 + "\n")

    sys.exit(0 if all_pass else 1)
