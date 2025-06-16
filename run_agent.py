import os
from self_improving_agent import SelfImprovingAgent
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the agent
    agent = SelfImprovingAgent(
        benchmark_path='cypher_bench.json',
        db_uri=os.getenv('NEO4J_URI'),
        db_user=os.getenv('NEO4J_USERNAME'),
        db_password=os.getenv('NEO4J_PASSWORD')
    )
    
    try:
        # Run improvement process
        agent.improve(generations=20)
        
        # Print final workflow
        print("\nFinal Workflow:")
        for stage in agent.workflow.stages:
            print(f"\nStage: {stage.name}")
            print(f"Type: {stage.type.value}")
            print(f"Prompt Template: {stage.prompt_template}")
            print(f"Priority: {stage.priority}")
            print(f"Active: {stage.is_active}")
            
    finally:
        agent.close()

if __name__ == "__main__":
    main() 