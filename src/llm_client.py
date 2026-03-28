"""
LLM client module.

Supports two providers:
- Groq API (cloud, free tier) — default, no GPU needed
- Ollama (local) — fallback for offline use
"""

import json
import requests

from config import Config
from schema import GRAPH_SCHEMA, SAMPLE_QUERIES


class LLMClient:
    """LLM integration for Graph RAG pipeline."""

    def __init__(self):
        self.provider = Config.LLM_PROVIDER

        if self.provider == "groq":
            self.api_key = Config.GROQ_API_KEY
            self.model = Config.GROQ_MODEL
            self.base_url = "https://api.groq.com/openai/v1"
        else:
            self.model = Config.OLLAMA_MODEL
            self.base_url = Config.OLLAMA_BASE_URL

    def verify_connection(self) -> bool:
        """Check if the LLM provider is reachable."""
        if self.provider == "groq":
            return self._verify_groq()
        return self._verify_ollama()

    def _verify_groq(self) -> bool:
        """Check Groq API connectivity."""
        if not self.api_key:
            print("❌ GROQ_API_KEY is not set in .env")
            return False
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                return True
            print(f"❌ Groq API error: {response.status_code}")
            return False
        except requests.ConnectionError:
            print("❌ Cannot connect to Groq API.")
            return False

    def _verify_ollama(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print("❌ Ollama is not responding.")
                return False

            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]

            if self.model not in model_names and f"{self.model}:latest" not in model_names:
                print(f"❌ Model '{self.model}' not found. Available: {model_names}")
                print(f"   Run: ollama pull {self.model}")
                return False
            return True
        except requests.ConnectionError:
            print("❌ Cannot connect to Ollama. Is it running?")
            print("   Start with: ollama serve")
            return False

    def _chat(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request to the configured provider."""
        if self.provider == "groq":
            return self._chat_groq(system_prompt, user_message)
        return self._chat_ollama(system_prompt, user_message)

    def _chat_groq(self, system_prompt: str, user_message: str) -> str:
        """Send request to Groq API (OpenAI-compatible)."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    def _chat_ollama(self, system_prompt: str, user_message: str) -> str:
        """Send request to Ollama API."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        return response.json()["message"]["content"]

    def generate_cypher(self, question: str) -> str:
        """
        Convert a natural language question into a Cypher query.

        Args:
            question: The user's question in natural language.

        Returns:
            A Cypher query string.
        """
        system_prompt = f"""You are a Neo4j Cypher query expert. Your job is to convert natural language questions into valid Cypher queries.

## Graph Schema
{GRAPH_SCHEMA}

## Example Queries
{SAMPLE_QUERIES}

## Rules
1. Return ONLY the Cypher query — no explanations, no markdown, no code blocks.
2. Use the exact node labels, relationship types, and property names from the schema.
3. For name matching, use CONTAINS for partial matches (e.g., WHERE p.name CONTAINS "Ahmet").
4. Always alias return values with AS for readability.
5. If the question cannot be answered with the given schema, return: // CANNOT_ANSWER
6. Use case-insensitive matching where appropriate with toLower().
"""

        user_message = f"Convert this question to a Cypher query:\n{question}"

        cypher = self._chat(system_prompt, user_message).strip()

        # Clean up common LLM formatting artifacts
        import re

        # Remove markdown code blocks
        code_block = re.search(r'```(?:cypher)?\s*\n?(.*?)```', cypher, re.DOTALL)
        if code_block:
            cypher = code_block.group(1).strip()

        # Remove backticks
        cypher = cypher.strip("`").strip()

        # If there's text before the actual query, find the first line
        # that starts with a Cypher keyword
        lines = cypher.split('\n')
        cypher_keywords = ['MATCH', 'RETURN', 'WITH', 'CALL', 'CREATE', 'MERGE', 'OPTIONAL', 'UNWIND']
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip().upper()
            for keyword in cypher_keywords:
                if stripped.startswith(keyword):
                    start_idx = i
                    break
            else:
                continue
            break

        cypher = '\n'.join(lines[start_idx:]).strip()

        return cypher

    def format_answer(self, question: str, cypher: str, results: list[dict]) -> str:
        """
        Generate a natural language answer from query results.

        Args:
            question: The original user question.
            cypher: The Cypher query that was executed.
            results: The query results as a list of dicts.

        Returns:
            A human-readable answer string.
        """
        if not results:
            return "Bu soruyla eşleşen bir sonuç bulunamadı. Soruyu farklı şekilde sormayı deneyebilirsiniz."

        system_prompt = """You are a helpful assistant that explains database query results in a natural, conversational way.

## Rules
1. Answer in the SAME LANGUAGE as the question (Turkish or English).
2. Be concise but informative.
3. Present the data clearly — use names and values from the results.
4. If there are multiple results, summarize them naturally.
5. Do not mention Cypher, queries, or databases in your answer.
6. Do not make up information — only use what is in the results.
"""

        user_message = (
            f"Question: {question}\n\n"
            f"Data:\n{json.dumps(results, ensure_ascii=False, indent=2)}\n\n"
            f"Provide a natural language answer based on this data."
        )

        return self._chat(system_prompt, user_message).strip()