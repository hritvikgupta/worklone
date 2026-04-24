from typing import Any, Dict
from collections import defaultdict
import json
try:
    from neo4j import AsyncGraphDatabase
except ImportError:
    AsyncGraphDatabase = None

from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement


class Neo4jIntrospectTool(BaseTool):
    name = "neo4j_introspect"
    description = "Introspect a Neo4j database to discover its schema including node labels, relationship types, properties, constraints, and indexes."
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
            },
            "required": ["host", "port", "database", "username", "password"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if AsyncGraphDatabase is None:
            return ToolResult(success=False, output="", error="neo4j is not installed. Install it to use Neo4j tools.")

        driver = None
        try:
            host: str = parameters["host"]
            port: int = parameters["port"]
            database: str = parameters["database"]
            username: str = parameters["username"]
            password: str = parameters["password"]
            encryption: str = parameters.get("encryption", "disabled")

            scheme = "bolts" if encryption == "enabled" else "bolt"
            uri = f"{scheme}://{host}:{port}"

            driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

            async with driver.session(database=database) as session:
                # Labels
                result = await session.run(
                    "CALL db.labels() YIELD label RETURN label ORDER BY label"
                )
                labels = [record["label"] async for record in result]

                # Relationship types
                result = await session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType"
                )
                relationship_types = [record["relationshipType"] async for record in result]

                # Node schemas
                node_schemas = []
                try:
                    result = await session.run(
                        "CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes RETURN nodeLabels, propertyName, propertyTypes"
                    )
                    node_properties_map = defaultdict(list)
                    async for record in result:
                        node_labels = record["nodeLabels"]
                        property_name = record["propertyName"]
                        property_types = record["propertyTypes"]
                        label_key = ":".join(node_labels)
                        node_properties_map[label_key].append(
                            {"name": property_name, "types": property_types}
                        )
                    node_schemas = [
                        {"label": k, "properties": v} for k, v in node_properties_map.items()
                    ]
                except Exception:
                    pass

                # Relationship schemas
                relationship_schemas = []
                try:
                    result = await session.run(
                        "CALL db.schema.relTypeProperties() YIELD relationshipType, propertyName, propertyTypes RETURN relationshipType, propertyName, propertyTypes"
                    )
                    rel_properties_map = defaultdict(list)
                    async for record in result:
                        rel_type = record["relationshipType"]
                        property_name = record["propertyName"]
                        property_types = record["propertyTypes"]
                        if property_name:
                            rel_properties_map[rel_type].append(
                                {"name": property_name, "types": property_types}
                            )
                    relationship_schemas = [
                        {"type": k, "properties": v} for k, v in rel_properties_map.items()
                    ]
                except Exception:
                    pass

                # Constraints
                constraints = []
                try:
                    result = await session.run("SHOW CONSTRAINTS")
                    async for record in result:
                        constraints.append(
                            {
                                "name": record["name"],
                                "type": record["type"],
                                "entityType": record["entityType"],
                                "properties": record.get("properties", []),
                            }
                        )
                except Exception:
                    pass

                # Indexes
                indexes = []
                try:
                    result = await session.run("SHOW INDEXES")
                    async for record in result:
                        indexes.append(
                            {
                                "name": record["name"],
                                "type": record["type"],
                                "entityType": record["entityType"],
                                "properties": record.get("properties", []),
                            }
                        )
                except Exception:
                    pass

            message = (
                f"Database introspection completed: found {len(labels)} labels, "
                f"{len(relationship_types)} relationship types, {len(node_schemas)} node schemas, "
                f"{len(relationship_schemas)} relationship schemas, {len(constraints)} constraints, "
                f"{len(indexes)} indexes"
            )
            data = {
                "message": message,
                "labels": labels,
                "relationshipTypes": relationship_types,
                "nodeSchemas": node_schemas,
                "relationshipSchemas": relationship_schemas,
                "constraints": constraints,
                "indexes": indexes,
            }
            return ToolResult(success=True, output=json.dumps(data), data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Neo4j introspection failed: {str(e)}")
        finally:
            if driver:
                await driver.close()
