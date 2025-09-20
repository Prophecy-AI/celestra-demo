import json
from agent import Agent
from executor import PlanExecutor

def main():
    agent = Agent()
    executor = PlanExecutor("data/providers.csv")
    
    while True:
        user_input = input("\nQuery: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        try:
            json_plan = agent.process_message(user_input)
            print(f"\nGenerated Plan:\n{json_plan}")
            
            # Extract JSON from markdown code blocks if present
            if "```json" in json_plan:
                json_start = json_plan.find("```json") + 7
                json_end = json_plan.find("```", json_start)
                json_plan = json_plan[json_start:json_end].strip()
            
            plan = json.loads(json_plan)
            result_df = executor.execute_plan(plan)
            print(f"\nResults ({len(result_df)} rows):")
            print(result_df.to_string(index=False))
            
        except json.JSONDecodeError:
            print("Error: Invalid JSON plan generated")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
