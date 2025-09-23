import sys
import time
from dotenv import load_dotenv
from google.cloud import bigquery
from prompts.sql_planner_prompt import SQLPlannerPrompt

load_dotenv()

class BigQueryAgent:
    def __init__(self):
        print("DEBUG: Initializing BigQuery client...")
        self.client = bigquery.Client(project="unique-bonbon-472921-q8")
        self.planner = SQLPlannerPrompt()
        print("DEBUG: BigQuery client initialized")
        
    def execute_query(self, user_query: str, show_sql: bool = True):
        total_start = time.time()
        print("=" * 60)
        print(f"DEBUG: Processing query: {user_query}")
        
        try:
            print("DEBUG: Generating SQL...")
            sql_start = time.time()
            generated_sql = self.planner.generate_sql(user_query)
            sql_gen_time = time.time() - sql_start
            print(f"DEBUG: SQL generation took {sql_gen_time:.2f} seconds")
            
            clean_sql = generated_sql.strip()
            if clean_sql.startswith("```sql"):
                clean_sql = clean_sql[6:]
            if clean_sql.startswith("```"):
                clean_sql = clean_sql[3:]
            if clean_sql.endswith("```"):
                clean_sql = clean_sql[:-3]
            
            if show_sql:
                print("Generated SQL:")
                print("-" * 40)
                print(clean_sql)
                print("-" * 40)
            
            print("DEBUG: Executing BigQuery...")
            query_start = time.time()
            query_job = self.client.query(clean_sql)
            results = query_job.result()
            query_time = time.time() - query_start
            print(f"DEBUG: BigQuery execution took {query_time:.2f} seconds")
            
            print("DEBUG: Converting to DataFrame...")
            df_start = time.time()
            df = results.to_dataframe()
            df_time = time.time() - df_start
            print(f"DEBUG: DataFrame conversion took {df_time:.2f} seconds")
            
            total_time = time.time() - total_start
            print(f"DEBUG: Total execution time: {total_time:.2f} seconds")
            
            print("Results:")
            print("-" * 40)
            if df.empty:
                print("No results found")
                result_text = "No results found"
            else:
                print(f"Found {len(df)} rows")
                print(df.to_string(index=False))
                result_text = f"Found {len(df)} rows\n\n{df.to_string(index=False)}"
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"query_results_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(f"Query: {user_query}\n")
                f.write("=" * 60 + "\n\n")
                if show_sql:
                    f.write("Generated SQL:\n")
                    f.write("-" * 40 + "\n")
                    f.write(clean_sql + "\n")
                    f.write("-" * 40 + "\n\n")
                f.write("Results:\n")
                f.write("-" * 40 + "\n")
                f.write(result_text + "\n\n")
                f.write(f"Execution Time: {total_time:.2f} seconds\n")
            
            print(f"Results saved to {filename}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            total_time = time.time() - total_start
            print(f"DEBUG: Total time before error: {total_time:.2f} seconds")

def main():
    print("DEBUG: Starting SQL Agent...")
    agent = BigQueryAgent()
    
    show_sql = True
    if len(sys.argv) > 1 and '--no-sql' in sys.argv:
        show_sql = False
        print("DEBUG: SQL display disabled")
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
            agent.execute_query(user_input, show_sql)
            print()
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"ERROR: {e}")
            print()

if __name__ == "__main__":
    main()
