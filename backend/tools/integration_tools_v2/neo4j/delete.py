from typing import Any, Dict
from neo4j import AsyncGraphDatabase
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class Neo4jDeleteTool(BaseTool):
    name = "neo4j_delete"
    description = "Execute DELETE or DETACH DELETE statements to remove nodes and relationships from Neo4j"
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
                    "description": "Cypher query with MATCH and DELETE/DETACH DELETE statements (e.g., \"MATCH (n:Person {name: $name}) DELETE n\", \"MATCH (n) DETACH DELETE n\")",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the Cypher query as a JSON object (e.g., {\"name\": \"Alice\", \"id\": 123})",
                },
                "detach": {
                    "type": "boolean",
                    "description": "Whether to use DETACH DELETE to remove relationships before deleting nodes",
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    async def execute(self, parameters: Dict[str, Any], context: dict | None = None) -> ToolResult:
        driver = None
        try:
            host: str = parameters["host"]
            port: int = int(parameters["port"])
            database: str = parameters["database"]
            username: str = parameters["username"]
            password: str = parameters["password"]
            encryption: str = parameters.get("encryption", "disabled")
            cypher_query: str = parameters["cypherQuery"]
            query_params: Dict[str, Any] = parameters.get("parameters", {})

            scheme = "bolt+s" if encryption == "enabled" else "bolt"
            uri = f"{scheme}://{host}:{port}"
            driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

            async with driver.session(database=database) as session:
                result = await session.run(cypher_query, **query_params)
                summary = await result.consume()

            counters = summary.counters
            summary_dict = {
                "resultAvailableAfter": summary.result_available_after.milliseconds,
                "resultConsumedAfter": summary.result_consumed_after.milliseconds,
                "counters": {
                    "nodesCreated": counters.nodes_created,
                    "nodesDeleted": counters.nodes_deleted,
                    "relationshipsCreated": counters.relationships_created,
                    "relationshipsDeleted": counters.relationships_deleted,
                    "propertiesSet": counters.properties_set,
                    "labelsAdded": counters.labels_added,
                    "labelsRemoved": counters.labels_removed,
                    "indexesAdded": counters.indexes_added,
                    "indexesRemoved": counters.indexes_removed,
                    "constraintsAdded": counters.constraints_added,
                    "constraintsRemoved": counters.constraints_removed,
                },
            }
            message = f"Deleted {counters.nodes_deleted} nodes and {counters.relationships_deleted} relationships"
            return ToolResult(
                success=True,
                output=message,
                data={"message": message, "summary": summary_dict},
            )
        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing parameter: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Neo4j delete failed: {str(e)}")
        finally:
            if driver:
                await driver.close()