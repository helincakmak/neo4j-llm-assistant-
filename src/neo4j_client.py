"""
Neo4j client module

"""

from neo4j import GraphDatabase

from config import Config


class Neo4jClient:
    """Manages the Neo4j driver and provides query execution """

    def __init__(self):
        self._driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
        )

    def close(self):
        """Close the driver connection """
        self._driver.close()

    def verify_connection(self) -> bool:
        """Check if Neo4j is reachable"""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            print(f" Neo4j connection failed: {e}")
            return False

    def run_query(self, cypher: str, parameters: dict = None) -> list[dict]:

        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

    def get_node_count(self) -> int:
        """Return total number of nodes in the database"""
        result = self.run_query("MATCH (n) RETURN count(n) AS count")
        return result[0]["count"] if result else 0

    def get_relationship_count(self) -> int:
        """Return total number of relationships in the database"""
        result = self.run_query("MATCH ()-[r]->() RETURN count(r) AS count")
        return result[0]["count"] if result else 0

    def get_schema_summary(self) -> str:
        """Fetch a live summary of node labels and relationship types."""
        labels = self.run_query("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        rel_types = self.run_query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS types")

        label_list = labels[0]["labels"] if labels else []
        type_list = rel_types[0]["types"] if rel_types else []

        return (
            f"Node labels: {', '.join(label_list)}\n"
            f"Relationship types: {', '.join(type_list)}"
        )

    def clear_database(self):
        """Delete all nodes and relationships. Use with caution"""
        self.run_query("MATCH (n) DETACH DELETE n")