# Agent v3 Tests

Unit tests for the agent_v3 package.

## Running Tests

Run all tests:
```bash
python -m unittest discover agent_v3/tests -v
```

Run specific test file:
```bash
python -m unittest agent_v3.tests.test_prompt_modules -v
```

Run specific test case:
```bash
python -m unittest agent_v3.tests.test_prompt_modules.TestToolModules.test_system_prompt_generation -v
```

## Test Files

- `test_prompt_modules.py` - Tests for tool modules and system prompt generation

## Test Coverage

Current tests cover:
- Tool prompt modules (get_orchestrator_info() and get_system_prompt() for all 7 tools)
- Tool class methods verification
- System prompt dynamic generation with tools injection
- LLM vs non-LLM tool behavior
