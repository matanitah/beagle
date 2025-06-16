# Beagle

This project implements a self-improving Cypher query generating that optimizes Cypher queries using a Darwinian approach. Given a benchmark of question-answer pairs, and a knowledge graph, the agent will iterate on its own internal workflow to optimize for the best agentic cypher generation performance. This project was inspired by Darwinian Godel Machines, see the paper here: https://arxiv.org/abs/2505.22954

## Features

- Loads question and answer pairs from a benchmark in the benchmarks folder
- Applies workflow mutations to optimize methods to answer
- Only keeps improvements that show better pass@1 performance (i.e. only changes which lead to a greater proportion of cypher queries being generated returning the same results as the ground truth queries are kept)
- Saves and loads state to continue improvement over time
- Uses Neo4j database for query evaluation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Neo4j database credentials:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

3. Ensure your Neo4j database is running and contains the necessary data structure for the benchmark queries.

## Usage

Run the agent:
```bash
python run_agent.py
```

The agent will:
1. Load the benchmark queries
2. Run multiple generations of improvements
3. Save the best performing queries to `improved_queries.json`
4. Print a summary of improvements

## How It Works

The agent uses several mutation strategies to improve queries:
- Adding optimization hints
- Reordering clauses
- Adding index hints
- Simplifying conditions

Each mutation is evaluated against the original query, and only improvements are kept. The evaluation is based on query execution time and correctness.

## Customization

You can modify the agent's behavior by:
- Adjusting the `mutation_rate` in `CypherAgent`
- Adding new mutation strategies
- Changing the evaluation criteria
- Modifying the number of generations in `run_agent.py`

## Output

The agent saves its state to `improved_queries.json`, which contains:
- The best performing queries for each question
- The performance scores achieved 