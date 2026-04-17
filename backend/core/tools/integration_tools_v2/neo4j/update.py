from typing import Any, Dict
import json
from neo4j import AsyncGraphDatabase
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class Neo4jUpdateTool(BaseTool):
    name = "neo4j_update"
    description = "Execute SET statements to update properties of existing nodes and relationships in Neo4j"
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
                    "description": 'Cypher query with MATCH and SET statements to update properties (e.g., "MATCH (n:Person {name: $name}) SET n.age = $age", "MATCH (n) WHERE n.id = $id SET n += $props")',
                },
                "parameters": {
                    "type": "object",
                    "description": 'Parameters for the Cypher query as a JSON object (e.g., {"name": "Alice", "age": 31, "props": {"city": "NYC"}})',
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        driver = None
        try:
            host: str = parameters["host"]
            port: int = int(parameters["port"])
            database: str = parameters["database"]
            username: str = parameters["username"]
            password: str = parameters["password"]
            encryption: str = parameters.get("encryption", "disabled")
            cypher_query: str = parameters["cypherQuery"]
            query_params: dict = parameters.get("parameters", {})

            uri = f"bolt://{host}:{port}"
            driver = AsyncGraphDatabase.driver(
                uri, auth=(username, password), encrypted=(encryption == "enabled")
            )

            async with driver.session(database=database) as session:
                result = await session.run(cypher_query, **query_params)
                records = []
                async for record in result:
                    rec_dict = {key: record[key] for key in record.keys()}
                    records.append(rec_dict)

                summary = {
                    "resultAvailableAfter": str(result.summary.result_available_after),
                    "resultConsumedAfter": str(result.summary.result_consumed_after),
                    "counters": {
                        "nodesCreated": result.summary.counters.nodes_created,
                        "nodesDeleted": result.summary.counters.nodes_deleted,
                        "relationshipsCreated": result.summary.counters.relationships_created,
                        "relationshipsDeleted": result.summary.counters.relationships_deleted,
                        "propertiesSet": result.summary.counters.properties_set,
                        "labelsAdded": result.summary.counters.labels_added,
                        "labelsRemoved": result.summary.counters.labels_removed,
                        "indexesAdded": result.summary.counters.indexes_added,
                        "indexesRemoved": result.summary.counters.indexes_removed,
                        "constraintsAdded": result.summary.counters.constraints_added,
                        "constraintsRemoved": result.summary.counters.constraints_removed,
                    },
                }

                properties_set = summary["counters"]["propertiesSet"]
                message = f"Updated {properties_set} properties"

                output_data = {
                    "message": message,
                    "summary": summary,
                }

            return ToolResult(
                success=True, output=json.dumps(output_data), data=output_data
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Neo4j update failed: {str(e)}"
            )
        finally:
            if driver is not None:
                await driver.close()