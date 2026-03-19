"""
    python src/seed_data.py
"""

import json
import sys
from pathlib import Path

from neo4j_client import Neo4jClient


DATA_FILE = Path(__file__).parent.parent / "data" / "sample_data.json"


def load_data(client: Neo4jClient):
    """Load all sample data into Neo4j."""

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("  Clearing existing data...")
    client.clear_database()

    # create constraints for data integrity
    print(" Creating constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:Project) REQUIRE pr.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Department) REQUIRE d.name IS UNIQUE",
    ]
    for c in constraints:
        client.run_query(c)

    # create Department nodes
    print(" Creating departments...")
    for dept in data["departments"]:
        client.run_query(
            "CREATE (d:Department {name: $name, budget: $budget})",
            dept,
        )

    # create Technology nodes
    print(" Creating technologies...")
    for tech in data["technologies"]:
        client.run_query(
            "CREATE (t:Technology {name: $name, category: $category})",
            tech,
        )

    # create Person nodes
    print(" Creating persons...")
    for person in data["persons"]:
        client.run_query(
            "CREATE (p:Person {name: $name, role: $role, email: $email})",
            person,
        )

    # create Project nodes + BELONGS_TO + USES relationships
    print(" Creating projects and relationships...")
    for project in data["projects"]:
        # Create project node
        client.run_query(
            """
            CREATE (pr:Project {
                name: $name,
                status: $status,
                description: $description,
                start_date: $start_date
            })
            """,
            {
                "name": project["name"],
                "status": project["status"],
                "description": project["description"],
                "start_date": project["start_date"],
            },
        )

        # BELONGS_TO department
        client.run_query(
            """
            MATCH (pr:Project {name: $project}), (d:Department {name: $dept})
            CREATE (pr)-[:BELONGS_TO]->(d)
            """,
            {"project": project["name"], "dept": project["department"]},
        )

        # USES technologies
        for tech in project["technologies"]:
            client.run_query(
                """
                MATCH (pr:Project {name: $project}), (t:Technology {name: $tech})
                CREATE (pr)-[:USES {purpose: $purpose}]->(t)
                """,
                {
                    "project": project["name"],
                    "tech": tech["name"],
                    "purpose": tech["purpose"],
                },
            )

    # create WORKS_ON relationships
    print(" Creating WORKS_ON relationships...")
    for wo in data["works_on"]:
        client.run_query(
            """
            MATCH (p:Person {name: $person}), (pr:Project {name: $project})
            CREATE (p)-[:WORKS_ON {since: $since, role: $role}]->(pr)
            """,
            wo,
        )

    # create REPORTS_TO relationships 
    print(" Creating REPORTS_TO relationships...")
    for rt in data["reports_to"]:
        client.run_query(
            """
            MATCH (p:Person {name: $person}), (m:Person {name: $manager})
            CREATE (p)-[:REPORTS_TO]->(m)
            """,
            rt,
        )

    # create HAS_SKILL relationships
    print(" Creating HAS_SKILL relationships...")
    for hs in data["has_skill"]:
        client.run_query(
            """
            MATCH (p:Person {name: $person}), (t:Technology {name: $technology})
            CREATE (p)-[:HAS_SKILL {level: $level}]->(t)
            """,
            hs,
        )

    # --- Summary ---
    node_count = client.get_node_count()
    rel_count = client.get_relationship_count()
    print(f"\n Data loaded successfully!")
    print(f"   Nodes: {node_count}")
    print(f"   Relationships: {rel_count}")
    print(f"   Schema: {client.get_schema_summary()}")


def main():
    client = Neo4jClient()

    if not client.verify_connection():
        print("\n💡 Make sure Neo4j is running: docker-compose up -d")
        sys.exit(1)

    try:
        load_data(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()