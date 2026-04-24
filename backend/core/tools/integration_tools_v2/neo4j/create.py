from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
try:
    from neo4j import AsyncGraphDatabase
except ImportError:
    AsyncGraphDatabase = None

class Neo4jCreateTool(BaseTool):
    name = "neo4j_create"
    description = "Execute CREATE statements to add new nodes and relationships to Neo4j graph database"
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
                    "description": 'Database name to connect to (e.g., "neo4j", "movies", "social")',
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
                    "description": 'Cypher CREATE statement to execute (e.g., "CREATE (n:Person {name: $name, age: $age})", "CREATE (a)-[:KNOWS]->(b)")',
                },
                "parameters": {
                    "type": "object",
                    "description": 'Parameters for the Cypher query as a JSON object (e.g., {"name": "Alice", "age": 30})',
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    def _convert_neo4j_to_json(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "__neo4j_type_name__"):
            type_name = value.__neo4j_type_name__
            if type_name == "Node":
                return {
                    "element_id": value.element_id,
                    "id": int(value.id),
                    "labels": list(value.labels),
                    "properties": dict(value),
                }
            elif type_name == "Relationship":
                return {
                    "element_id": value.element_id,
                    "id": int(value.id),
                    "type": value.type,
                    "start": self._convert_neo4j_to_json(value.start_node),
                    "end": self._convert_neo4j_to_json(value.end_node),
                    "properties": dict(value),
                }
            else:
                if hasattr(value, "iso_format"):
                    return value.iso_format()
                return str(value)
        if isinstance(value, list):
            return [self._convert_neo4j_to_json(v) for v in value]
        if isinstance(value, dict):
            return {k: self._convert_neo4j_to_json(v) for k, v in value.items()}
        return value

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if AsyncGraphDatabase is None:
            return ToolResult(success=False, output="", error="neo4j is not installed. Install it to use Neo4j tools.")

        try:
            host = parameters["host"]
            port = int(parameters["port"])
            database = parameters["database"]
            username = parameters["username"]
            password = parameters["password"]
            encryption = parameters.get("encryption", "disabled")
            if encryption not in ("enabled", "disabled"):
                encryption = "disabled"
            cypher_query = parameters["cypherQuery"].strip()
            query_params = parameters.get("parameters", {})

            if not cypher_query.upper().startswith("CREATE"):
                return ToolResult(
                    success=False,
                    output="",
                    error="Cypher query validation failed: must start with CREATE",
                )

            scheme = "bolt+s" if encryption == "enabled" else "bolt"
            uri = f"{scheme}://{host}:{port}"

            driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
            try:
                async with driver.session(database=database) as session:
                    result = await session.run(cypher_query, **query_params)
                    records = []
                    async for record in result:
                        record_dict = {}
                        for key in record.keys:
                            record_dict[key] = self._convert_neo4j_to_json(record[key])
                        records.append(record_dict)

                    result_summary = result.summary()
                    summary = {
                        "result_available_after": result_summary.result_available_after.milliseconds,
                        "result_consumed_after": result_summary.result_consumed_after.milliseconds,
                        "counters": {
                            "nodesCreated": result_summary.counters.nodes_created,
                            "nodesDeleted": result_summary.counters.nodes_deleted,
                            "relationshipsCreated": result_summary.counters.relationships_created,
                            "relationshipsDeleted": result_summary.counters.relationships_deleted,
                            "propertiesSet": result_summary.counters.properties_set,
                            "labelsAdded": result_summary.counters.labels_added,
                            "labelsRemoved": result_summary.counters.labels_removed,
                            "indexesAdded": result_summary.counters.indexes_added,
                            "indexesRemoved": result_summary.counters.indexes_removed,
                            "constraintsAdded": result_summary.counters.constraints_added,
                            "constraintsRemoved": result_summary.counters.constraints_removed,
                        },
                    }

                nodes_created = summary["counters"]["nodesCreated"]
                relationships_created = summary["counters"]["relationshipsCreated"]
                message = f"Created {nodes_created} nodes and {relationships_created} relationships"

                output_data = {
                    "message": message,
                    "records": records,
                    "recordCount": len(records),
                    "summary": summary,
                }

                return ToolResult(success=True, output=message, data=output_data)

            finally:
                await driver.close()

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Neo4j create failed: {str(e)}"
            )
