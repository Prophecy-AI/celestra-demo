import os
from openai import OpenAI
from dotenv import load_dotenv
from prompts.planner import SYSTEM_PROMPT

load_dotenv()

class Agent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def process_message(self, message: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    agent = Agent()
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        print("Agent:", agent.process_message(user_input))