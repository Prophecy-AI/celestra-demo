"""
Test strict validation: reject responses with multiple tool calls
"""
import os
os.environ["DEBUG"] = "1"

from agent_v3.llm_client import LLMClient


def test_single_tool_call():
    """Test that single tool call passes"""
    client = LLMClient()

    # Single tool call should PASS
    response = """
<think>
I should explore the data first
</think>

{
  "tool": "sandbox_exec",
  "parameters": {
    "command": ["python", "-c", "print('hello')"]
  },
  "reasoning_trace": "Testing"
}
"""

    result = client._extract_tool_call(response, ["sandbox_exec", "sandbox_write_file"])

    print("\n" + "="*80)
    print("TEST 1: Single tool call")
    print("="*80)
    if result:
        print(f"✅ PASS: Single tool call accepted")
        print(f"   Tool: {result.get('tool')}")
    else:
        print(f"❌ FAIL: Single tool call rejected")

    return result is not None


def test_multiple_tool_calls():
    """Test that multiple tool calls are REJECTED"""
    client = LLMClient()

    # Multiple tool calls should be REJECTED
    response = """
{
  "tool": "sandbox_write_file",
  "parameters": {
    "file_path": "/tmp/test.py",
    "content": "print('test')"
  },
  "reasoning_trace": "Creating file"
}

{
  "tool": "sandbox_exec",
  "parameters": {
    "command": ["python", "/tmp/test.py"]
  },
  "reasoning_trace": "Executing file"
}
"""

    result = client._extract_tool_call(response, ["sandbox_exec", "sandbox_write_file"])

    print("\n" + "="*80)
    print("TEST 2: Multiple tool calls (should be REJECTED)")
    print("="*80)
    if result is None:
        print(f"✅ PASS: Multiple tool calls correctly REJECTED")
    else:
        print(f"❌ FAIL: Multiple tool calls were NOT rejected")
        print(f"   Tool selected: {result.get('tool')}")

    return result is None


def test_three_tool_calls():
    """Test that three tool calls are REJECTED"""
    client = LLMClient()

    # Three tool calls should be REJECTED
    response = """
{
  "tool": "sandbox_write_file",
  "parameters": {
    "file_path": "/tmp/test.py",
    "content": "print('test')"
  },
  "reasoning_trace": "Creating file"
}

{
  "tool": "sandbox_exec",
  "parameters": {
    "command": ["python", "/tmp/test.py"]
  },
  "reasoning_trace": "Executing file"
}

{
  "tool": "complete",
  "parameters": {
    "summary": "Done",
    "datasets": []
  },
  "reasoning_trace": "Finishing"
}
"""

    result = client._extract_tool_call(response, ["sandbox_exec", "sandbox_write_file", "complete"])

    print("\n" + "="*80)
    print("TEST 3: Three tool calls (should be REJECTED)")
    print("="*80)
    if result is None:
        print(f"✅ PASS: Three tool calls correctly REJECTED")
    else:
        print(f"❌ FAIL: Three tool calls were NOT rejected")
        print(f"   Tool selected: {result.get('tool')}")

    return result is None


if __name__ == "__main__":
    import sys

    print("\n" + "="*80)
    print("STRICT VALIDATION TESTS")
    print("="*80)

    test1 = test_single_tool_call()
    test2 = test_multiple_tool_calls()
    test3 = test_three_tool_calls()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Test 1 (Single tool): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (Two tools):   {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 (Three tools): {'✅ PASS' if test3 else '❌ FAIL'}")

    all_pass = test1 and test2 and test3
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print("="*80 + "\n")

    sys.exit(0 if all_pass else 1)
