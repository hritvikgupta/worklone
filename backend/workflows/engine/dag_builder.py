"""
DAG Builder — converts a workflow into an execution graph.
"""

from collections import defaultdict
from backend.workflows.types import Workflow, Block, Connection
from backend.workflows.logger import get_logger

logger = get_logger("dag_builder")


class DAGNode:
    """A node in the execution DAG."""
    
    def __init__(self, block: Block):
        self.block = block
        self.dependencies: list[str] = []  # Block IDs this node depends on
        self.dependents: list[str] = []  # Block IDs that depend on this node
        self.condition: str = ""  # Optional condition to execute this node
    
    @property
    def id(self) -> str:
        return self.block.id
    
    def is_ready(self, completed: set[str]) -> bool:
        """Check if all dependencies are met."""
        return all(dep in completed for dep in self.dependencies)
    
    def should_execute(self, variables: dict) -> bool:
        """Check if condition is met."""
        if not self.condition:
            return True
        from backend.workflows.utils import evaluate_condition
        return evaluate_condition(self.condition, variables)


class DAG:
    """Directed Acyclic Graph for workflow execution."""
    
    def __init__(self):
        self.nodes: dict[str, DAGNode] = {}
        self.order: list[str] = []  # Topological order
    
    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.id] = node
    
    def add_edge(self, from_id: str, to_id: str, condition: str = "") -> None:
        if to_id in self.nodes:
            self.nodes[to_id].dependencies.append(from_id)
            self.nodes[to_id].condition = condition
        if from_id in self.nodes:
            self.nodes[from_id].dependents.append(to_id)
    
    def get_ready_nodes(self, completed: set[str]) -> list[DAGNode]:
        """Get nodes that are ready to execute."""
        return [
            node for node in self.nodes.values()
            if node.id not in completed and node.is_ready(completed)
        ]
    
    def get_execution_order(self) -> list[str]:
        """Get topological execution order."""
        if self.order:
            return self.order
        
        # Kahn's algorithm
        in_degree = defaultdict(int)
        for node in self.nodes.values():
            if node.id not in in_degree:
                in_degree[node.id] = 0
            for dep in node.dependents:
                in_degree[dep] += 1
        
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            node = self.nodes.get(node_id)
            if node:
                for dep in node.dependents:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        self.order = order
        return order


def build_dag(workflow: Workflow) -> DAG:
    """
    Build a DAG from a workflow definition.
    
    Creates execution nodes and edges based on workflow connections.
    """
    dag = DAG()
    
    # Create nodes
    for block in workflow.blocks:
        dag.add_node(DAGNode(block))
        logger.debug(f"Added DAG node: {block.id} ({block.config.block_type.value})")
    
    # Create edges
    for connection in workflow.connections:
        dag.add_edge(
            connection.from_block_id,
            connection.to_block_id,
            connection.condition,
        )
        logger.debug(f"Added DAG edge: {connection.from_block_id} → {connection.to_block_id}")
    
    # Validate no cycles
    order = dag.get_execution_order()
    if len(order) != len(dag.nodes):
        logger.warning(
            f"DAG has {len(order)} nodes but workflow has {len(dag.nodes)}. "
            "Possible cycle detected — execution may be incomplete."
        )
    
    logger.info(f"Built DAG: {len(dag.nodes)} nodes, {len(workflow.connections)} edges")
    return dag
