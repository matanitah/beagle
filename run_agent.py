import os
from self_improving_agent import SelfImprovingAgent
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the agent
    agent = SelfImprovingAgent(
        benchmark_path='benchmarks/cypher_bench.json',
        db_uri=os.getenv('NEO4J_URI'),
        db_user=os.getenv('NEO4J_USERNAME'),
        db_password=os.getenv('NEO4J_PASSWORD')
    )
    
    try:
        # Run improvement process
        agent.improve(generations=1)
                    
    finally:
        agent.close()

if __name__ == "__main__":
    main() 