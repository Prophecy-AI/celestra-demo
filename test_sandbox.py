"""
Test script for sandbox code execution tools
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_v3.context import Context
from agent_v3.tools.code_execution.sandbox_write_file import SandboxWriteFile
from agent_v3.tools.code_execution.sandbox_edit_file import SandboxEditFile
from agent_v3.tools.code_execution.sandbox_exec import SandboxExec


def test_simple_exec():
    """Test 1: Simple Python script execution"""
    print("\n" + "="*60)
    print("TEST 1: Simple sandbox_exec with Python script")
    print("="*60 + "\n")

    context = Context(session_id="test_session_1")
    exec_tool = SandboxExec()

    # Test simple Python command
    params = {
        "command": ["python", "-c", "import sys; print(f'Python {sys.version}'); print('Hello from sandbox!')"],
        "timeout": 30
    }

    print("Executing command:", " ".join(params["command"]))
    result = exec_tool.execute(params, context)

    print(f"\nSuccess: {result.success}")
    if result.success:
        print(f"Exit code: {result.data.get('exit_code')}")
        print(f"Stdout:\n{result.data.get('stdout')}")
        if result.data.get('stderr'):
            print(f"Stderr:\n{result.data.get('stderr')}")
    else:
        print(f"Error: {result.error}")

    # Cleanup
    context.cleanup()
    return result.success


def test_full_workflow():
    """Test 2: Full workflow - write → edit → execute → retrieve"""
    print("\n" + "="*60)
    print("TEST 2: Full workflow (write → edit → execute → retrieve)")
    print("="*60 + "\n")

    context = Context(session_id="test_session_2")
    write_tool = SandboxWriteFile()
    edit_tool = SandboxEditFile()
    exec_tool = SandboxExec()

    # Step 1: Write a Python script
    print("STEP 1: Writing Python script...")
    script_content = """import polars as pl

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': [85, 90, 95]
}

df = pl.DataFrame(data)
print("Original DataFrame:")
print(df)

# Calculate mean age
mean_age = df['age'].mean()
print(f"\\nMean age: {mean_age}")

# Save to output
df.write_csv('/tmp/output/results.csv')
print("\\nResults saved to /tmp/output/results.csv")
"""

    write_params = {
        "file_path": "/tmp/analysis.py",
        "content": script_content
    }

    write_result = write_tool.execute(write_params, context)
    print(f"Write success: {write_result.success}")
    if not write_result.success:
        print(f"Write error: {write_result.error}")
        context.cleanup()
        return False

    # Step 2: Edit the script (change mean_age to also calculate max)
    print("\nSTEP 2: Editing script to add max calculation...")
    edit_params = {
        "file_path": "/tmp/analysis.py",
        "old_string": "# Calculate mean age\nmean_age = df['age'].mean()\nprint(f\"\\nMean age: {mean_age}\")",
        "new_string": "# Calculate mean age and max age\nmean_age = df['age'].mean()\nmax_age = df['age'].max()\nprint(f\"\\nMean age: {mean_age}\")\nprint(f\"Max age: {max_age}\")"
    }

    edit_result = edit_tool.execute(edit_params, context)
    print(f"Edit success: {edit_result.success}")
    if not edit_result.success:
        print(f"Edit error: {edit_result.error}")
        context.cleanup()
        return False

    # Step 3: Execute the script
    print("\nSTEP 3: Executing script...")
    exec_params = {
        "command": ["python", "/tmp/analysis.py"],
        "timeout": 30
    }

    exec_result = exec_tool.execute(exec_params, context)
    print(f"Exec success: {exec_result.success}")
    if exec_result.success:
        print(f"Exit code: {exec_result.data.get('exit_code')}")
        print(f"\nScript output:\n{exec_result.data.get('stdout')}")

        # Step 4: Check retrieved files
        output_files = exec_result.data.get('output_files', [])
        print(f"\nSTEP 4: Retrieved output files: {output_files}")

        if output_files:
            print(f"Total files retrieved: {len(output_files)}")
            for f in output_files:
                print(f"  - {f}")
    else:
        print(f"Exec error: {exec_result.error}")

    # Cleanup
    context.cleanup()
    return exec_result.success and exec_result.data.get('exit_code') == 0


if __name__ == "__main__":
    print("\nSTARTING SANDBOX TOOLS TESTS")
    print("This will test the sandbox_exec, sandbox_write_file, and sandbox_edit_file tools")

    # Run tests
    test1_pass = test_simple_exec()
    test2_pass = test_full_workflow()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Test 1 (Simple exec): {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Test 2 (Full workflow): {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if (test1_pass and test2_pass) else '✗ SOME TESTS FAILED'}")

    sys.exit(0 if (test1_pass and test2_pass) else 1)
