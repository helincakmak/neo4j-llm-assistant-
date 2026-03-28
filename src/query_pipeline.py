"""
Query pipeline module.

Orchestrates the full Graph RAG flow:
  User Question → LLM (Cypher Generation) → Neo4j (Execution) → LLM (Answer Formatting)
"""

from dataclasses import dataclass

from neo4j_client import Neo4jClient
from llm_client import LLMClient


@dataclass
class QueryResult:
    """Holds the complete result of a query pipeline execution."""

    question: str
    cypher: str
    raw_results: list[dict]
    answer: str
    success: bool
    error: str | None = None


class QueryPipeline:
    """
    End-to-end pipeline for natural language → graph query → natural answer.

    This is the core Graph RAG implementation:
    1. User asks a question in natural language
    2. LLM generates a Cypher query based on the graph schema
    3. Cypher is executed against Neo4j
    4. LLM formats the results into a human-readable answer
    """

    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.llm = llm_client

    def run(self, question: str) -> QueryResult:
        """
        Execute the full pipeline for a given question.

        Args:
            question: Natural language question from the user.

        Returns:
            QueryResult with all intermediate and final outputs.
        """
        # Step 1: Generate Cypher from natural language
        try:
            cypher = self.llm.generate_cypher(question)
        except Exception as e:
            return QueryResult(
                question=question,
                cypher="",
                raw_results=[],
                answer=f"Cypher oluşturulurken hata: {e}",
                success=False,
                error=str(e),
            )

        # Check if LLM indicated it cannot answer
        if "CANNOT_ANSWER" in cypher:
            return QueryResult(
                question=question,
                cypher=cypher,
                raw_results=[],
                answer="Bu soru mevcut graph şeması ile yanıtlanamıyor. Lütfen farklı bir soru deneyin.",
                success=False,
                error="Question outside schema scope",
            )

        # Step 2: Execute Cypher against Neo4j
        try:
            results = self.neo4j.run_query(cypher)
        except Exception as e:
            return QueryResult(
                question=question,
                cypher=cypher,
                raw_results=[],
                answer=f"Sorgu çalıştırılırken hata oluştu. Cypher geçersiz olabilir.",
                success=False,
                error=str(e),
            )

        # Step 3: Format results into natural language
        try:
            answer = self.llm.format_answer(question, cypher, results)
        except Exception as e:
            # Fallback: return raw results if LLM formatting fails
            answer = f"Sonuçlar: {results}"

        return QueryResult(
            question=question,
            cypher=cypher,
            raw_results=results,
            answer=answer,
            success=True,
        )