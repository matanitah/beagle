# Self-Improving Cypher Query Agent

This project implements a self-improving agent that optimizes Cypher queries using a Darwinian approach. The agent continuously evolves and improves its query performance based on execution time and correctness.

## Features

- Loads and evaluates Cypher queries from a benchmark
- Applies various mutations to optimize queries
- Only keeps improvements that show better performance
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