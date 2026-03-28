"""
Graph RAG — Interactive Q&A System

Main entry point. Starts an interactive loop where users can ask
natural language questions that are answered via the Knowledge Graph.

Usage:
    python src/main.py
"""

import sys

from neo4j_client import Neo4jClient
from llm_client import LLMClient
from query_pipeline import QueryPipeline
from config import Config


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║              🔗 Graph RAG — Knowledge Graph Q&A              ║
║                                                              ║
║  Ask questions in natural language (Turkish or English).     ║
║  Type 'quit' to exit, 'schema' to see the graph schema,     ║
║  or 'stats' to see database statistics.                      ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_result(result):
    """Pretty-print a query pipeline result."""
    print()
    if result.cypher and "CANNOT_ANSWER" not in result.cypher:
        print(f"  🔍 Cypher:  {result.cypher}")
    if result.raw_results:
        print(f"  📊 Results: {len(result.raw_results)} record(s)")
    if result.error:
        print(f"  ⚠️  Error:   {result.error}")
    print(f"\n  💬 {result.answer}")
    print()


def main():
    # --- Initialize clients ---
    neo4j = Neo4jClient()
    llm = LLMClient()

    print("\n⏳ Checking connections...")

    if not neo4j.verify_connection():
        print("\n💡 Check your NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env")
        sys.exit(1)
    print("  ✅ Neo4j connected")

    if not llm.verify_connection():
        if Config.LLM_PROVIDER == "groq":
            print("\n💡 Check your GROQ_API_KEY in .env")
        else:
            print("\n💡 Start Ollama: ollama serve")
            print(f"💡 Pull model:  ollama pull {llm.model}")
        sys.exit(1)
    print(f"  ✅ LLM connected ({Config.LLM_PROVIDER}: {llm.model})")

    # --- Check if data exists ---
    node_count = neo4j.get_node_count()
    if node_count == 0:
        print("\n⚠️  Database is empty. Load sample data first:")
        print("   python src/seed_data.py")
        neo4j.close()
        sys.exit(1)
    print(f"  ✅ Database has {node_count} nodes")

    # --- Create pipeline ---
    pipeline = QueryPipeline(neo4j, llm)

    print(BANNER)

    # --- Interactive loop ---
    try:
        while True:
            try:
                question = input("You: ").strip()
            except EOFError:
                break

            if not question:
                continue

            if question.lower() in ("quit", "exit", "q", "çıkış"):
                print("\n👋 Goodbye!\n")
                break

            if question.lower() == "schema":
                print(f"\n  {neo4j.get_schema_summary()}\n")
                continue

            if question.lower() == "stats":
                nodes = neo4j.get_node_count()
                rels = neo4j.get_relationship_count()
                print(f"\n  📊 Nodes: {nodes} | Relationships: {rels}\n")
                continue

            # Run the Graph RAG pipeline
            result = pipeline.run(question)
            print_result(result)

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()