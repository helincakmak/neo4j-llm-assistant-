"""graph schema and example queries for LLM context"""

GRAPH_SCHEMA = """
## Node Labels and Properties

- Person: name (string), role (string), email (string)
- Project: name (string), status (string: "active" | "completed" | "planned"), description (string), start_date (string)
- Technology: name (string), category (string: "language" | "framework" | "database" | "tool" | "cloud")
- Department: name (string), budget (integer)

## Relationship Types

- (Person)-[:WORKS_ON {since: string, role: string}]->(Project)
- (Project)-[:USES {purpose: string}]->(Technology)
- (Person)-[:HAS_SKILL {level: string: "beginner" | "intermediate" | "expert"}]->(Technology)
- (Person)-[:REPORTS_TO]->(Person)
- (Project)-[:BELONGS_TO]->(Department)

## Important Notes

- All Person names are Turkish (e.g., "Ahmet Yılmaz", "Elif Demir")
- Technology names use their standard casing (e.g., "Python", "React", "Neo4j")
- Department names are in English (e.g., "Engineering", "Data Science")
- Project statuses are lowercase English ("active", "completed", "planned")
- Skill levels are lowercase English ("beginner", "intermediate", "expert")
"""


SAMPLE_QUERIES = """
## Example Cypher Queries

Q: Python kullanan projelerde kimler çalışıyor?
Cypher: MATCH (p:Person)-[:WORKS_ON]->(pr:Project)-[:USES]->(t:Technology {name: "Python"}) RETURN p.name AS person, pr.name AS project

Q: Which department has the most projects?
Cypher: MATCH (p:Project)-[:BELONGS_TO]->(d:Department) RETURN d.name AS department, count(p) AS project_count ORDER BY project_count DESC LIMIT 1

Q: Ahmet'in yöneticisi kim?
Cypher: MATCH (p:Person)-[:REPORTS_TO]->(manager:Person) WHERE p.name CONTAINS "Ahmet" RETURN p.name AS person, manager.name AS manager

Q: Expert seviyesinde React bilen kimler var?
Cypher: MATCH (p:Person)-[:HAS_SKILL {level: "expert"}]->(t:Technology {name: "React"}) RETURN p.name AS person

Q: Hangi teknolojiler en çok projede kullanılıyor?
Cypher: MATCH (pr:Project)-[:USES]->(t:Technology) RETURN t.name AS technology, count(pr) AS usage_count ORDER BY usage_count DESC

Q: Engineering departmanının bütçesi ne kadar?
Cypher: MATCH (d:Department {name: "Engineering"}) RETURN d.name AS department, d.budget AS budget

Q: Aktif projelerde hangi teknolojiler kullanılıyor?
Cypher: MATCH (pr:Project {status: "active"})-[:USES]->(t:Technology) RETURN pr.name AS project, collect(t.name) AS technologies

Q: Who works on more than one project?
Cypher: MATCH (p:Person)-[:WORKS_ON]->(pr:Project) WITH p, count(pr) AS project_count WHERE project_count > 1 RETURN p.name AS person, project_count ORDER BY project_count DESC
"""