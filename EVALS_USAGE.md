# Evals Usage Guide

The `evals_v5` system provides automated quality checks using OpenAI o3. Evals were implemented but not yet integrated into the agent.

## Prerequisites

```bash
# In your .env file
EVALS_ENABLED=1
OPENAI_API_KEY=sk-...
```

---

## Option 1: Manual Eval Usage (Quick)

Run evals manually from Python:

```python
from evals_v5.runner import EvalRunner

# Initialize runner for a session
runner = EvalRunner(
    session_id="abc123",
    workspace_dir="./workspace/abc123"
)

# Submit evals (fire-and-forget, async)
runner.submit("sql", {
    "sql": "SELECT * FROM rx_claims WHERE ...",
    "context": "Querying prescription data for diabetes medications"
})

runner.submit("hallucination", {
    "answer": "The top prescriber is Dr. Smith with 1,234 prescriptions",
    "data": "csv content or query results here"
})

runner.submit("answer", {
    "question": "What are the top diabetes medications?",
    "answer": "The top 3 medications are...",
    "context": "Based on RX_CLAIMS data"
})

runner.submit("code", {
    "code": "import polars as pl\ndf = pl.read_csv('data.csv')",
    "task": "Load and analyze prescription data"
})

runner.submit("retrieval", {
    "query": "diabetes medications",
    "retrieved_data": "Query results here",
    "context": "BigQuery rx_claims table"
})

runner.submit("objective", {
    "objective": "Find top prescribers for ozempic",
    "actions": "Queried RX_CLAIMS, filtered by drug name, grouped by NPI",
    "outcome": "Found top 10 prescribers with counts"
})
```

### Results Location

Results are stored in `workspace/{session_id}/.evals/`:
```
.evals/
  sql_1234567890.json
  hallucination_1234567891.json
  answer_1234567892.json
```

Each result JSON contains:
```json
{
  "eval_type": "sql",
  "data": { /* input data */ },
  "result": {
    "score": 85,
    "passed": true,
    "issues": [],
    "reasoning": "Query is well-structured..."
  },
  "timestamp": 1234567890
}
```

---

## Option 2: Integrate into Agent (Proper)

Modify `agent_v5/agent.py` to automatically run evals during execution.

### Implementation (~20 LOC)

```python
# In agent_v5/agent.py

class ResearchAgent:
    def __init__(self, session_id: str, workspace_dir: str, system_prompt: str):
        # ... existing code ...

        # Add eval runner
        from evals_v5.runner import EvalRunner
        self.evals = EvalRunner(session_id, workspace_dir)

    async def run(self, user_message: str) -> AsyncGenerator[Dict, None]:
        # ... existing agentic loop ...

        # After tool execution, submit relevant evals
        for tool_use in tool_uses:
            result = await self.tools.execute(tool_use["name"], tool_use["input"])

            # Submit SQL eval for BigQuery queries
            if tool_use["name"] == "mcp__bigquery__bigquery_query":
                self.evals.submit("sql", {
                    "sql": tool_use["input"]["sql"],
                    "context": f"Session {self.session_id}"
                })

            # Continue with existing code...

        # After final response, submit answer eval
        if not tool_uses:
            final_text = "".join([
                block["text"] for block in response_content
                if block.get("type") == "text"
            ])

            self.evals.submit("answer", {
                "question": user_message,
                "answer": final_text,
                "context": f"Conversation turn {len(self.conversation_history)//2}"
            })

            self.evals.submit("objective", {
                "objective": user_message,
                "actions": "Agent actions summary here",
                "outcome": final_text
            })
```

### Integration Points

1. **SQL Eval**: After every `mcp__bigquery__bigquery_query` tool use
   - Validates SQL syntax and logic
   - Checks for performance issues

2. **Hallucination Eval**: After BigQuery results are processed
   - Compares agent claims against actual data
   - Detects invented statistics

3. **Answer Eval**: On final response before loop exit
   - Scores answer quality
   - Checks if question was addressed

4. **Code Eval**: After Bash tool executes Python scripts
   - Validates Python code correctness
   - Checks for errors

5. **Retrieval Eval**: After data is retrieved from BigQuery
   - Checks if retrieved data is relevant to query
   - Validates data quality

6. **Objective Eval**: On conversation completion
   - Evaluates if user's goal was achieved
   - Assesses overall task completion

### Benefits of Integration

- ✅ Automatic quality monitoring
- ✅ No manual eval submission needed
- ✅ Fire-and-forget (doesn't block agent)
- ✅ Results available for analysis
- ✅ Can catch issues early

### Drawbacks

- Requires OPENAI_API_KEY (additional cost)
- Adds complexity to agent loop
- o3 model may be slow/expensive

---

## Viewing Eval Results

```python
import json
from pathlib import Path

# Load all evals for a session
evals_dir = Path("./workspace/abc123/.evals")

for eval_file in evals_dir.glob("*.json"):
    data = json.loads(eval_file.read_text())
    print(f"\n{data['eval_type'].upper()}")
    print(f"Score: {data['result'].get('score', 'N/A')}/100")
    print(f"Passed: {data['result'].get('passed', 'N/A')}")
    print(f"Reasoning: {data['result'].get('reasoning', 'N/A')}")
```

---

## Recommendation

**For now**: Use Option 1 (manual) to test evals and understand their behavior.

**Later**: Implement Option 2 (integrated) once you're confident in the eval quality and want automated monitoring.

The evals are most valuable when:
- You have complex SQL queries that need validation
- You're concerned about hallucination in data analysis
- You want automated quality metrics over time
