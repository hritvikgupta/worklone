from typing import Any, Dict
from datetime import datetime, date, time, timedelta
from neo4j import GraphDatabase
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class Neo4jMergeTool(BaseTool):
    name = "neo4j_merge"
    description = "Execute MERGE statements to find or create nodes and relationships in Neo4j (upsert operation)"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
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
                    "description": "Cypher MERGE statement to execute (e.g., \"MERGE (n:Person {name: $name}) ON CREATE SET n.created = timestamp()\", \"MERGE (a)-[r:KNOWS]->(b)\")",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the Cypher query as a JSON object (e.g., {\"name\": \"Alice\", \"email\": \"alice@example.com\"})",
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    def _serialize_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (int, float, str, bool)):
            return value
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, timedelta):
            return int(value.total_seconds() * 1000)
        return str(value)

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host: str = parameters["host"]
            if not host:
                raise ValueError("Host is required")
            port: int = int(parameters["port"])
            if port <= 0:
                raise ValueError("Port must be a positive integer")
            database: str = parameters["database"]
            if not database:
                raise ValueError("Database name is required")
            username: str = parameters["username"]
            if not username:
                raise ValueError("Username is required")
            password: str = parameters["password"]
            if not password:
                raise ValueError("Password is required")
            encryption: str = parameters.get("encryption", "disabled")
            if encryption not in ["enabled", "disabled"]:
                raise ValueError("Encryption must be 'enabled' or 'disabled'")
            cypher_query: str = parameters["cypherQuery"]
            if not cypher_query:
                raise ValueError("Cypher query is required")
            if not cypher_query.strip().upper().startswith("MERGE"):
                raise ValueError("Query validation failed: Cypher MERGE statement expected")
            query_params: dict = parameters.get("parameters", {})

            scheme = "bolt+s" if encryption == "enabled" else "bolt"
            uri = f"{scheme}://{host}:{port}"
            driver = GraphDatabase.driver(uri, auth=(username, password))

            try:
                with driver.session(database=database) as session:
                    result = session.run(cypher_query, **query_params)
                    records = [
                        {k: self._serialize_value(v) for k, v in record.items()}
                        for record in result
                    ]
                    summary_obj = result.consume()

                    def duration_to_ms(dur: Any) -> int:
                        if dur is None:
                            return 0
                        try:
                            return int(dur.total_seconds() * 1000)
                        except AttributeError:
                            return int(dur.seconds * 1000 + dur.nanoseconds / 1000000.0)

                    summary = {
                        "resultAvailableAfter": duration_to_ms(summary_obj.result_available_after),
                        "resultConsumedAfter": duration_to_ms(summary_obj.result_consumed_after),
                        "counters": {
                            "nodesCreated": summary_obj.counters.nodes_created,
                            "nodesDeleted": summary_obj.counters.nodes_deleted,
                            "relationshipsCreated": summary_obj.counters.relationships_created,
                            "relationshipsDeleted": summary_obj.counters.relationships_deleted,
                            "propertiesSet": summary_obj.counters.properties_set,
                            "labelsAdded": summary_obj.counters.labels_added,
                            "labelsRemoved": summary_obj.counters.labels_removed,
                            "indexesAdded": summary_obj.counters.indexes_added,
                            "indexesRemoved": summary_obj.counters.indexes_removed,
                            "constraintsAdded": summary_obj.counters.constraints_added,
                            "constraintsRemoved": summary_obj.counters.constraints_removed,
                        },
                    }
                    counters = summary["counters"]
                    message = (
                        f"Merge completed: {counters['nodesCreated']} nodes created, "
                        f"{counters['relationshipsCreated']} relationships created"
                    )
                    output_data = {
                        "message": message,
                        "records": records,
                        "recordCount": len(records),
                        "summary": summary,
                    }
                    return ToolResult(
                        success=True, output=message, data=output_data
                    )
            finally:
                driver.close()
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Neo4j merge failed: {str(e)}"
            )