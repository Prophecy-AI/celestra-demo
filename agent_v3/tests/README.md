# Agent v3 Tests

Unit tests for the agent_v3 package.

## Running Tests

Run all tests:
```bash
python -m unittest discover agent_v3/tests -v
```

Run specific test file:
```bash
python -m unittest agent_v3.tests.test_prompt_loader -v
```

Run specific test case:
```bash
python -m unittest agent_v3.tests.test_prompt_loader.TestPromptLoader.test_build_tools_list -v
```

## Test Files

- `test_prompt_loader.py` - Tests for PromptLoader class and dynamic tools list injection

## Test Coverage

Current tests cover:
- Dynamic tools list building from YAML files
- System prompt injection with tools
- Loading tool prompts with/without system_prompt field
- Tool prompts listing functionality
