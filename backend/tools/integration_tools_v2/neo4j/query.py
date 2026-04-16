from typing import Any, Dict, List
import json
import asyncio
from neo4j import GraphDatabase, Node, Relationship, Path
from neo4j.time import Duration, DateTime, Date, Time
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class Neo4jQueryTool(BaseTool):
    name = "neo4j_query"
    description = """Execute MATCH queries to read nodes and relationships from Neo4j graph database. For best performance and to prevent large result sets, include LIMIT in your query (e.g., "MATCH (n:User) RETURN n LIMIT 100") or use LIMIT $limit with a limit parameter."""
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
                    "description": "Cypher query to execute (e.g., \"MATCH (n:Person) RETURN n LIMIT 10\", \"MATCH (a)-[r]->(b) WHERE a.name = $name RETURN a, r, b\")",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the Cypher query as a JSON object. Use for any dynamic values including LIMIT (e.g., query: \"MATCH (n) RETURN n LIMIT $limit\", parameters: {limit: 100}).",
                },
            },
            "required": ["host", "port", "database", "username", "password", "cypherQuery"],
        }

    def _serialize_neo4j_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [self._serialize_neo4j_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_neo4j_value(v) for k, v in value.items()}
        if isinstance(value, (Duration, DateTime, Date, Time)):
            return value.iso_format()
        if isinstance(value, Node):
            props = {k: self._serialize_neo4j_value(v) for k, v in value.properties.items()}
            return {
                "type": "node",
                "elementId": value.element_id,
                "labels": list(value.labels),
                "properties": props,
            }
        if isinstance(value, Relationship):
            props = {k: self._serialize_neo4j_value(v) for k, v in value.properties.items()}
            return {
                "type": "relationship",
                "relType": value.type,
                "elementId": value.element_id,
                "startNodeElementId": value.start_node.element_id,
                "endNodeElementId": value.end_node.element_id,
                "properties": props,
            }
        if isinstance(value, Path):
            return {
                "type": "path",
                "length": len(value.relationships),
                "nodes": [self._serialize_neo4j_value(n) for n in value.nodes],
                "relationships": [self._serialize_neo4j_value(r) for r in value.relationships],
            }
        return str(value)

    def _build_summary(self, summary) -> Dict[str, Any]:
        result_available_after = summary.result_available_after
        result_consumed_after = summary.result_consumed_after
        raa_ms = int(result_available_after.seconds * 1000 + result_available_after.nanoseconds / 1_000_000)
        rca_ms = int(result_consumed_after.seconds * 1000 + result_consumed_after.nanoseconds / 1_000_000)
        counters = summary.counters
        return {
            "resultAvailableAfter": raa_ms,
            "resultConsumedAfter": rca_ms,
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

    def _execute_sync(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        driver = None
        session = None
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
            driver = GraphDatabase.driver(uri, auth=(username, password))
            session = driver.session(database=database)

            result = session.run(cypher_query, **query_params)

            records: List[Dict[str, Any]] = []
            for record in result:
                rec: Dict[str, Any] = {
                    key: self._serialize_neo4j_value(record[key]) for key in record.keys
                }
                records.append(rec)

            summary_dict = self._build_summary(result.summary())
            record_count = len(records)

            return {
                "message": f"Found {record_count} records",
                "records": records,
                "recordCount": record_count,
                "summary": summary_dict,
            }
        except Exception as e:
            raise Exception(f"Neo4j query failed: {str(e)}")
        finally:
            if session is not None:
                session.close()
            if driver is not None:
                driver.close()

    async def execute(self, parameters: Dict[str, Any], context: dict = None) -> ToolResult:
        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, self._execute_sync, parameters)
            return ToolResult(success=True, output=json.dumps(data), data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))