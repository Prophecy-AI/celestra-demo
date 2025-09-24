import sys 
import base64
from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox
from prompts.planner_prompt import PlannerPrompt
from scripts.embeddings import create_providers_with_embeddings

load_dotenv()

sbx = Sandbox.create()

with open("data/providers.csv", "rb") as f:
    providers_path = sbx.files.write("providers.csv", f)

with open("data/Mounjaro Claim Sample.csv", "rb") as f:
    claims_path = sbx.files.write("claims.csv", f)

def run_code(code: str):
    execution = sbx.run_code(code)
    
    if execution.error:
        print("ERROR:")
        print(execution.error.name)
        print(execution.error.value)
        return
    
    if execution.logs:
        print(execution.logs)
    
    for i, result in enumerate(execution.results):
        if result.png:
            with open(f'chart-{i}.png', 'wb') as f:
                f.write(base64.b64decode(result.png))
            print(f'Chart saved to chart-{i}.png')
        if result.text:
            print(result.text)

def execute_query(query: str, show_code: bool = True):
    planner = PlannerPrompt()
    
    print("=" * 60)
    
    try:
        generated_code = planner.generate_code(query)
        
        if show_code:
            print("Generated Code:")
            print("-" * 40)
            print(generated_code)
            print("-" * 40)
        
        code_to_execute = generated_code.strip()
        if code_to_execute.startswith("```python"):
            code_to_execute = code_to_execute[9:]
        if code_to_execute.endswith("```"):
            code_to_execute = code_to_execute[:-3]
        
        code_to_execute = code_to_execute.replace('data/providers.csv', providers_path.path)
        code_to_execute = code_to_execute.replace('data/Mounjaro Claim Sample.csv', claims_path.path)
        
        # Add explicit execution to ensure E2B captures output
        if "if __name__ ==" in code_to_execute:
            code_to_execute = code_to_execute.replace('if __name__ == "__main__":', 'if True:  # Force execution')
        
        print("Results:")
        print("-" * 40)
        run_code(code_to_execute)
            
    except Exception as e:
        print(f"Error: {e}")

def main():

    show_code = True
    if len(sys.argv) > 1 and '--no-code' in sys.argv:
        show_code = False
        print("Code display disabled")
        print()
    
    while True:
        try:
            user_input = input("Query: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
                
            print()
            execute_query(user_input, show_code)
            print()
            
         except KeyboardInterrupt:
             print("\nGoodbye! 👋")
             break
         except Exception as e:
             print(f"Error: {e}")
             print()
    
    sbx.kill()

if __name__ == "__main__":
    try:
        main()
    finally:
        sbx.kill()