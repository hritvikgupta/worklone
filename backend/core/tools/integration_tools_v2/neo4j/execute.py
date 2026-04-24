from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


class Neo4jExecuteTool(BaseTool):
    name = "neo4j_execute"
    description = "Execute arbitrary Cypher queries on Neo4j graph database for complex operations"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Neo4j server hostname or IP address",
                },
                "port": {
                    "type": "number",
                    "description": "Neo4j server port (default: 7687 for Bolt protocol)",
                },
                "database": {
                    "type": "string",
                    "description": "Database name to connect to (e.g., \"neo4j\", \"movies\", \"social\")",
                },
                "username": {
                    "type": "string",
                    "description": "Neo4j username",
                },
                "password": {
                    "type": "string",
                    "description": "Neo4j password",
                },
                "encryption": {
                    "type": "string",
                    "description": "Connection encryption mode (enabled, disabled)",
                },
                "cypherQuery": {
                    "type": "string",
                    "description": "Cypher query to execute (e.g., \"CALL db.labels()\", \"MATCH (n) RETURN count(n)\", \"CREATE INDEX FOR (n:Person) ON (n.name)\")",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the Cypher query as a JSON object (e.g., {\"name\": \"Alice\", \"limit\": 100})",
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    def _build_summary(self, result) -> dict[str, Any]:
        raa = result.summary.result_available_after
        rca = result.summary.result_consumed_after
        counters = result.summary.counters
        return {
            "resultAvailableAfter": int(raa.seconds * 1000 + raa.nanoseconds / 1000000),
            "resultConsumedAfter": int(rca.seconds * 1000 + rca.nanoseconds / 1000000),
            "counters": {
                "nodesCreated": getattr(counters, "nodes_created", 0),
                "nodesDeleted": getattr(counters, "nodes_deleted", 0),
                "relationshipsCreated": getattr(counters, "relationships_created", 0),
                "relationshipsDeleted": getattr(counters, "relationships_deleted", 0),
                "propertiesSet": getattr(counters, "properties_set", 0),
                "labelsAdded": getattr(counters, "labels_added", 0),
                "labelsRemoved": getattr(counters, "labels_removed", 0),
                "indexesAdded": getattr(counters, "indexes_added", 0),
                "indexesRemoved": getattr(counters, "indexes_removed", 0),
                "constraintsAdded": getattr(counters, "constraints_added", 0),
                "constraintsRemoved": getattr(counters, "constraints_removed", 0),
            },
        }

    async def execute(self, parameters: dict[str, Any], context: dict | None = None) -> ToolResult:
        if GraphDatabase is None:
            return ToolResult(success=False, output="", error="neo4j is not installed. Install it to use Neo4j tools.")

        host: str = parameters["host"]
        port: int = int(parameters["port"])
        database: str = parameters["database"]
        username: str = parameters["username"]
        password: str = parameters["password"]
        encryption_enabled: bool = parameters.get("encryption", "disabled") == "enabled"
        cypher_query: str = parameters["cypherQuery"]
        query_params: dict[str, Any] = parameters.get("parameters", {})

        uri = f"bolt://{host}:{port}"
        driver = GraphDatabase.driver(uri, auth=(username, password), encrypted=encryption_enabled)

        try:
            async with driver.session(database=database) as session:
                result = await session.run(cypher_query, **query_params)
                records = []
                async for record in result:
                    records.append(dict(record))
                summary = self._build_summary(result)
                message = f"Query executed successfully, returned {len(records)} records"
                data = {
                    "message": message,
                    "records": records,
                    "recordCount": len(records),
                    "summary": summary,
                }
                return ToolResult(success=True, output=message, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Neo4j execute failed: {str(e)}")
        finally:
            await driver.close()
