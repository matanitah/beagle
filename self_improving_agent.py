import json
from neo4j import GraphDatabase
from typing import List, Dict, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import Neo4jGraph
import re

class AgentState(TypedDict):
    question: str
    schema: str
    generated_query: str
    ground_truth_query: str
    performance: float

class SelfImprovingAgent:
    def __init__(self, benchmark_path, db_uri, db_user, db_password):
        self.benchmark_path = benchmark_path
        self.db_uri = db_uri
        self.db_user = db_user
        self.db_password = db_password
        self.driver = GraphDatabase.driver(self.db_uri, auth=(self.db_user, self.db_password))
        self.graph = Neo4jGraph()
        self.schema = self.graph.schema
        
        self.best_performance = 0.0
        self.current_queries = {}
        
        self.llm = ChatOllama(model="mistral")
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a Cypher query expert. Generate a valid Cypher query to answer the question.

Database Schema:
{schema}

Rules:
1. Return ONLY the Cypher query, nothing else
2. Do not include explanations, comments, or markdown
3. Ensure the query is syntactically correct
4. Use proper Cypher syntax with MATCH, WHERE, RETURN clauses
5. Do not add any text before or after the query

Examples:
Question: How many patients are there?
MATCH (p:Patient) RETURN count(p) as count

Question: What are the names of all providers?
MATCH (pr:Provider) RETURN pr.provider_name"""),
            ("user", "Question: {question}")
        ])
        
        # Create workflow
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create a simple workflow with just query generation and evaluation."""
        workflow = StateGraph(AgentState)
        
        # Single node for query generation
        workflow.add_node("generate_query", self._generate_query)
        workflow.add_node("evaluate_query", self._evaluate_query)
        
        # Simple linear flow
        workflow.add_edge("generate_query", "evaluate_query")
        workflow.add_edge("evaluate_query", END)
        
        workflow.set_entry_point("generate_query")
        
        return workflow.compile()

    def _generate_query(self, state: AgentState) -> AgentState:
        """Generate a Cypher query using the simple prompt template."""
        try:
            messages = self.prompt_template.format_messages(
                schema=state["schema"],
                question=state["question"]
            )
            response = self.llm.invoke(messages)
            state["generated_query"] = self._clean_query(response.content)
            print(f"Generated: {state['generated_query']}")
        except Exception as e:
            print(f"Error generating query: {e}")
            state["generated_query"] = ""
        return state

    def _evaluate_query(self, state: AgentState) -> AgentState:
        """Evaluate the generated query against ground truth."""
        try:
            if self._compare_results(state["generated_query"], state["ground_truth_query"]):
                state["performance"] = 1.0
                print("✓ Query matches ground truth")
            else:
                state["performance"] = 0.0
                print("✗ Query does not match ground truth")
                print(f"Generated: {state['generated_query']}")
                print(f"Expected: {state['ground_truth_query']}")
        except Exception as e:
            print(f"Error evaluating query: {e}")
            state["performance"] = 0.0
        return state

    def _clean_query(self, query: str) -> str:
        """Clean the query by removing markdown formatting and extra text."""
        # Remove markdown code blocks
        query = re.sub(r'```cypher\n?', '', query)
        query = re.sub(r'```\n?', '', query)
        
        # Split by lines and find the actual query
        lines = query.strip().split('\n')
        query_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines and explanatory text
            if not line:
                continue
            # Look for lines that start with Cypher keywords
            if any(line.upper().startswith(keyword) for keyword in 
                   ['MATCH', 'CREATE', 'MERGE', 'WITH', 'CALL', 'RETURN', 'WHERE', 'ORDER', 'LIMIT', 'SKIP']):
                query_lines.append(line)
            # If we already have query lines, stop at explanatory text
            elif query_lines and any(word in line.lower() for word in 
                                   ['this query', 'will return', 'explanation', 'note:']):
                break
            # Continue building the query if it looks like a continuation
            elif query_lines and (line.startswith('WHERE') or line.startswith('RETURN') or 
                                line.startswith('ORDER') or line.startswith('LIMIT')):
                query_lines.append(line)
        
        # Join the query lines
        cleaned_query = ' '.join(query_lines) if query_lines else query.strip()
        
        # Remove any trailing explanatory text
        if 'This query' in cleaned_query:
            cleaned_query = cleaned_query.split('This query')[0].strip()
        
        return cleaned_query

    def _execute_query(self, query: str) -> List[Dict]:
        """Execute a Cypher query and return results."""
        if not query.strip():
            return []
        try:
            results = self.graph.query(query)
            return results
        except Exception as e:
            print(f"Error executing query '{query}': {e}")
            return []

    def _compare_results(self, query1: str, query2: str) -> bool:
        """Compare results of two queries."""
        if not query1 or not query2:
            return False
        
        results1 = self._execute_query(query1)
        results2 = self._execute_query(query2)
        
        # Handle empty results
        if not results1 and not results2:
            return True
        if not results1 or not results2:
            return False
            
        return results1 == results2

    def run_benchmark(self, max_questions: int = None):
        """Run the agent on the benchmark questions."""
        output = ""
        # Load benchmark
        with open(self.benchmark_path, 'r') as f:
            benchmark = json.load(f)
        
        if max_questions:
            benchmark = benchmark[:max_questions]
        
        total_correct = 0
        total_questions = len(benchmark)
        
        print(f"Running benchmark on {total_questions} questions...")
        
        for i, qa_pair in enumerate(benchmark, 1):
            print(f"\n--- Question {i}/{total_questions} ---")
            output += f"\n--- Question {i}/{total_questions} ---"
            print(f"Question: {qa_pair['question']}")
            output += f"Question: {qa_pair['question']} \n"
            print(f"Ground truth: {qa_pair['answer']}")
            output += f"Ground truth: {qa_pair['answer']} \n"
            
            # Create state for this question
            state = AgentState(
                question=qa_pair["question"],
                schema=self.schema,
                generated_query="",
                ground_truth_query=qa_pair["answer"],
                performance=0.0
            )
            
            # Run workflow
            final_state = self.workflow.invoke(state)
            
            # Track performance
            if final_state["performance"] == 1.0:
                total_correct += 1
                self.current_queries[qa_pair["question"]] = final_state["generated_query"]
        
        # Calculate overall performance
        overall_performance = total_correct / total_questions
        print(f"\n=== RESULTS ===")
        print(f"Correct: {total_correct}/{total_questions}")
        print(f"Performance: {overall_performance:.2%}")
        
        if overall_performance > self.best_performance:
            self.best_performance = overall_performance
            self._save_state()
        
        return output, overall_performance

    def diagnose_problem(self, output):
        # Create diagnostic prompt
        diagnostic_prompt = f"""
            You are a Neo4j Cypher expert. Analyze the following benchmark run output and identify the key problems 
            with how the queries are being generated. Focus on patterns of errors and areas for improvement.

            Benchmark output:
            {output}

            Provide a concise diagnosis of the main issues in query generation.
            """

        # Get diagnosis from LLM
        response = self.llm.invoke(diagnostic_prompt)
        
        print("\n=== DIAGNOSIS ===")
        print(response)
        
        return response
    
    def improve_workflow(self, diagnosis):
        # Create improvement prompt
        improvement_prompt = f"""
            You are a Neo4j Cypher expert. Based on the following diagnosis of query generation issues,
            suggest a specific improvement to the workflow that would address these problems.
            
            Diagnosis:
            {diagnosis}
            
            Current workflow stages:
            {self.workflow}
            
            Suggest a new workflow stage that would help improve query accuracy. Format as:
            STAGE NAME: <name>
            DESCRIPTION: <what the stage does>
            PROMPT: <prompt template for the stage>
            """
            
        # Get improvement suggestion from LLM
        response = self.llm.invoke(improvement_prompt).content
        
        print("\n=== SUGGESTED IMPROVEMENT ===")
        print(response)
        
        # Parse response to extract stage details
        # try:
        #     lines = response.split('\n')
        #     stage_name = next(l for l in lines if l.startswith('STAGE NAME:')).split(':')[1].strip()
        #     stage_prompt = next(l for l in lines if l.startswith('PROMPT:')).split(':')[1].strip()
            
        #     # Create temporary workflow with new stage
        #     temp_workflow = self.workflow.copy()
        #     temp_workflow.add_stage(stage_name, stage_prompt)

        #     return temp_workflow
        # except Exception as e:
        #     print(f"Error parsing workflow improvement: {e}")

    def improve(self, generations=10):
        """Run improvement iterations."""
        for generation in range(generations):
            print(f"\n=== Generation {generation + 1}/{generations} ===")
            output, performance = self.run_benchmark(max_questions=5)  # Start with small subset
            
            diagnosis = self.diagnose_problem(output)
            new_workflow = self.improve_workflow(diagnosis)
            
        print(f"\nBest performance achieved: {self.best_performance:.2%}")

    def _save_state(self):
        """Save current state."""
        state = {
            "queries": self.current_queries,
            "performance": self.best_performance,
            "prompt_template": self.prompt_template.messages[0].prompt.template
        }
        with open("improved_queries.json", "w") as f:
            json.dump(state, f, indent=2)
        print("State saved to improved_queries.json")

    def close(self):
        """Close connections."""
        self.driver.close()
