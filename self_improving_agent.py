import json
import time
from typing import Dict, List, Any
from neo4j import GraphDatabase
from agent_workflow import AgentWorkflow, WorkflowStage, StageType
import os
from dotenv import load_dotenv
from tqdm import tqdm

class SelfImprovingAgent:
    def __init__(self, benchmark_path: str, db_uri: str = None, db_user: str = None, db_password: str = None):
        """Initialize the self-improving agent."""
        self.benchmark = self._load_benchmark(benchmark_path)
        self.workflow = AgentWorkflow()
        self.best_performance = 0.0
        self.generation = 0
        
        # Load database credentials
        load_dotenv()
        self.db_uri = db_uri or os.getenv('NEO4J_URI')
        self.db_user = db_user or os.getenv('NEO4J_USERNAME')
        self.db_password = db_password or os.getenv('NEO4J_PASSWORD')
        
        if not all([self.db_uri, self.db_user, self.db_password]):
            raise ValueError("Database credentials must be provided either directly or through environment variables")
        
        self.driver = GraphDatabase.driver(self.db_uri, auth=(self.db_user, self.db_password))

    def _load_benchmark(self, path: str) -> List[Dict]:
        """Load the benchmark data from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _execute_workflow(self, query: str) -> Dict[str, Any]:
        """Execute the current workflow on a query."""
        current_query = query
        results = {}
        
        # Execute each stage in order of priority
        for stage in sorted(self.workflow.stages, key=lambda x: x.priority):
            if not stage.is_active:
                continue
                
            # Format the prompt with the current query
            prompt = stage.prompt_template.format(query=current_query)
            
            # Execute the stage's function
            result = stage.function(current_query)
            
            # Update the query if the stage returns a new one
            if isinstance(result, str):
                current_query = result
                
            results[stage.name] = result
            
        return results

    def _evaluate_workflow(self) -> float:
        """Evaluate the current workflow on the benchmark."""
        total_score = 0.0
        
        for item in self.benchmark:
            query = item['cypher']
            
            try:
                # Execute the workflow
                start_time = time.time()
                workflow_results = self._execute_workflow(query)
                execution_time = time.time() - start_time
                
                # Calculate score based on execution time and correctness
                score = 1.0 / (execution_time + 1e-6)
                total_score += score
                
            except Exception as e:
                print(f"Error evaluating query: {e}")
                continue
                
        return total_score / len(self.benchmark)

    def improve(self, generations: int = 10):
        """Run the self-improvement process for a specified number of generations."""
        for generation in tqdm(range(generations), desc="Improving agent"):
            self.generation = generation
            
            # Create a mutated version of the workflow
            mutated_workflow = self.workflow.mutate_workflow()
            
            # Evaluate both workflows
            current_score = self._evaluate_workflow()
            self.workflow = mutated_workflow
            mutated_score = self._evaluate_workflow()
            
            # Keep the better performing workflow
            if mutated_score > current_score:
                self.best_performance = mutated_score
                print(f"\nGeneration {generation}: Improved workflow")
                print(f"New score: {mutated_score:.4f} (was {current_score:.4f})")
                print("Current workflow stages:")
                for stage in self.workflow.stages:
                    print(f"- {stage.name} (Priority: {stage.priority})")
            else:
                # Revert to the previous workflow
                self.workflow = mutated_workflow
                
            # Save the current state
            self.save_state(f"states/agent_state_gen_{generation}.json")

    def save_state(self, path: str):
        """Save the current state of the agent."""
        state = {
            "generation": self.generation,
            "best_performance": self.best_performance,
            "workflow": {
                "stages": [
                    {
                        "name": stage.name,
                        "type": stage.type.value,
                        "prompt_template": stage.prompt_template,
                        "is_active": stage.is_active,
                        "priority": stage.priority
                    }
                    for stage in self.workflow.stages
                ]
            }
        }
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, path: str):
        """Load a previously saved state."""
        with open(path, 'r') as f:
            state = json.load(f)
            self.generation = state["generation"]
            self.best_performance = state["best_performance"]
            
            # Reconstruct the workflow
            self.workflow = AgentWorkflow()
            self.workflow.stages = [
                WorkflowStage(
                    name=stage["name"],
                    type=StageType(stage["type"]),
                    prompt_template=stage["prompt_template"],
                    function=getattr(self.workflow, f"_{stage['name'].lower().replace(' ', '_')}"),
                    is_active=stage["is_active"],
                    priority=stage["priority"]
                )
                for stage in state["workflow"]["stages"]
            ]

    def close(self):
        """Close the database connection."""
        self.driver.close() 