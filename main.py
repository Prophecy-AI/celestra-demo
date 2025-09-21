import sys
import tempfile
import os
import io
import contextlib
from prompts.planner_prompt import PlannerPrompt
from scripts.embeddings import create_providers_with_embeddings

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
            print()
        
        code_to_execute = generated_code.strip()
        if code_to_execute.startswith("```python"):
            code_to_execute = code_to_execute[9:]
        if code_to_execute.endswith("```"):
            code_to_execute = code_to_execute[:-3]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code_to_execute)
            temp_file_path = temp_file.name
        
        try:
            print("Results:")
            print("-" * 40)
            
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec_globals = {'__name__': '__main__'}
                exec(code_to_execute, exec_globals)
            
            output = output_buffer.getvalue()
            if output.strip():
                print(output)
            else:
                print("No output generated")
            
        finally:
            os.unlink(temp_file_path)
            
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

if __name__ == "__main__":
    main()
