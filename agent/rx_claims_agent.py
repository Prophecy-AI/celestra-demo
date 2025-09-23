import os
import sys
import time
import polars as pl
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from google.cloud import bigquery
# from openai import OpenAI
import anthropic
from prompts.rx_claims_prompt import SYSTEM_PROMPT

# Import debug function from main_agent
DEBUG = os.getenv('DEBUG', '0') == '1'

def debug_log(message: str, agent: str = "RX_CLAIMS"):
    """Centralized debug logging with timestamps"""
    if DEBUG:
        timestamp = time.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        print(f"[{timestamp}] [{agent}] {message}")

load_dotenv()

class RXClaimsAgent:
    def __init__(self):
        debug_log("Initializing RXClaimsAgent")
        self.bq_client = bigquery.Client(project="unique-bonbon-472921-q8")
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        debug_log("RXClaimsAgent initialized")
        
    def execute_sql_query(self, sql: str):
        clean_sql = sql.strip()
        if clean_sql.startswith("```sql"):
            clean_sql = clean_sql[6:]
        if clean_sql.startswith("```"):
            clean_sql = clean_sql[3:]
        if clean_sql.endswith("```"):
            clean_sql = clean_sql[:-3]
            
        debug_log(f"Executing SQL query: {clean_sql[:100]}...")
        query_job = self.bq_client.query(clean_sql)
        debug_log(f"BigQuery job started: {query_job.job_id}")
        results = query_job.result()
        debug_log(f"BigQuery job completed, converting to Polars")
        # Convert BigQuery result to Arrow then to Polars
        arrow_table = results.to_arrow()
        df = pl.from_arrow(arrow_table)
        debug_log(f"Conversion complete, result shape: {df.shape}")

        return df
    
    def generate_sql(self, query: str) -> str:
        debug_log(f"Generating SQL for query: {query}")
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": query}
            ]
        )
        generated_sql = response.content[0].text
        debug_log(f"Claude generated SQL ({len(generated_sql)} chars)")
        return generated_sql
    
    def get_data(self, query: str, save_output: bool = False):
        generated_sql = ""
        result_df = None
        error_msg = ""
        
        try:
            debug_log(f"Processing query: {query}")
            generated_sql = self.generate_sql(query)
            debug_log(f"Executing generated SQL")
            result_df = self.execute_sql_query(generated_sql)
            debug_log(f"Query completed, result shape: {result_df.shape if hasattr(result_df, 'shape') else 'N/A'}")
        except Exception as e:
            error_msg = f"Error fetching RX claims data: {str(e)}"
            result_df = pl.DataFrame()
        
        if save_output:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"output/rx_claims_query_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(f"RX Claims Query: {query}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Generated SQL:\n")
                f.write("-" * 40 + "\n")
                f.write(generated_sql + "\n")
                f.write("-" * 40 + "\n\n")
                f.write("Results:\n")
                f.write("-" * 40 + "\n")
                if error_msg:
                    f.write(error_msg + "\n\n")
                elif result_df.is_empty():
                    f.write("No results found\n\n")
                else:
                    f.write(f"Found {len(result_df)} rows\n\n{str(result_df)}\n\n")
                f.write(f"Timestamp: {timestamp}\n")
            
            debug_log(f"Results saved to {filename}")
            print(f"Results saved to {filename}")
        
        if error_msg:
            return error_msg
        return result_df

def main():
    agent = RXClaimsAgent()
    print("RX Claims Agent - Enter queries to test data fetching")
    
    while True:
        try:
            user_input = input("\nRX Query: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
                
            result = agent.get_data(user_input)
            print(f"\nResult: {result}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
