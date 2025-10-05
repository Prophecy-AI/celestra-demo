"""
Test that all JSON examples in the system prompt are valid
"""
import json
import re
from agent_v3.prompts.system_prompt import get_main_system_prompt


def extract_json_examples(prompt):
    """Extract all JSON tool call examples from the prompt"""
    # Find all JSON blocks that look like tool calls
    # Pattern: starts with { and has "tool": field
    pattern = r'\{\s*"tool":\s*"[^"]+",.*?\n\}'
    matches = re.findall(pattern, prompt, re.DOTALL)
    return matches


def validate_json_example(json_str, index):
    """Validate a single JSON example"""
    try:
        # Parse the JSON
        data = json.loads(json_str)

        # Check required fields
        if "tool" not in data:
            return False, f"Example {index}: Missing 'tool' field"

        if "parameters" not in data:
            return False, f"Example {index}: Missing 'parameters' field"

        if "reasoning_trace" not in data:
            return False, f"Example {index}: Missing 'reasoning_trace' field"

        # Check structure
        if not isinstance(data["parameters"], dict):
            return False, f"Example {index}: 'parameters' is not a dict"

        if not isinstance(data["reasoning_trace"], str):
            return False, f"Example {index}: 'reasoning_trace' is not a string"

        return True, f"Example {index}: Valid ✓"

    except json.JSONDecodeError as e:
        return False, f"Example {index}: JSON decode error: {str(e)}"


def main():
    prompt = get_main_system_prompt()

    print("Extracting JSON examples from system prompt...")
    examples = extract_json_examples(prompt)

    print(f"\nFound {len(examples)} JSON tool call examples\n")

    all_valid = True

    for i, example in enumerate(examples, 1):
        valid, message = validate_json_example(example, i)

        if valid:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            print(f"   Example text:\n{example[:200]}...\n")
            all_valid = False

    print("\n" + "="*80)
    if all_valid:
        print("✅ ALL JSON EXAMPLES ARE VALID")
    else:
        print("❌ SOME JSON EXAMPLES ARE INVALID")
    print("="*80)

    return all_valid


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
