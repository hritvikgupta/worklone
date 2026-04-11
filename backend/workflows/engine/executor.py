"""
Workflow Executor — DAG-based execution with parallel, loops, and trigger inputs.

Inspired by Sim's execution engine:
- DAG-based topological execution
- Sentinel-based parallel execution
- Variable resolution from upstream outputs
- Trigger input propagation to first block
"""

import time
import json
from datetime import datetime
from typing import Optional
from collections import defaultdict

from backend.workflows.types import (
    Workflow, Block, BlockConfig, BlockType, ExecutionResult, WorkflowStatus, BlockStatus,
    ParallelGroup, ParallelType,
)
from backend.workflows.engine.dag_builder import build_dag, DAG, DAGNode
from backend.workflows.engine.variable_resolver import VariableResolver
from backend.workflows.engine.handlers.registry import handler_registry, register_all_handlers
from backend.workflows.utils import generate_id
from backend.workflows.store import WorkflowStore
from backend.workflows.logger import get_logger

logger = get_logger("executor")

# Parallel branch subscript notation (same as Sim: blockId₍0₎, blockId₍1₎)
BRANCH_PREFIX = "\u208B("  # ₍
BRANCH_SUFFIX = "\u208B)"  # ₎


class ParallelScope:
    """Tracks a parallel execution scope."""
    
    def __init__(self, parallel_id: str, total_branches: int, total_nodes: int):
        self.parallel_id = parallel_id
        self.total_branches = total_branches
        self.total_expected_nodes = total_nodes
        self.completed_count = 0
        self.branch_outputs: dict[int, dict] = {}  # branch_index -> output


class WorkflowExecutor:
    """
    Executes workflows with DAG-based ordering, parallel branches, and trigger inputs.
    """
    
    def __init__(self, store: WorkflowStore):
        self.store = store
        self.resolver: Optional[VariableResolver] = None
        self.parallel_scopes: dict[str, ParallelScope] = {}
        self._handlers_registered = False
    
    def _ensure_handlers(self):
        if not self._handlers_registered:
            register_all_handlers()
            self._handlers_registered = True
    
    async def execute(
        self,
        workflow: Workflow,
        input_data: dict = None,
        trigger_type: str = "manual",
        from_block_id: str = None,
    ) -> ExecutionResult:
        """
        Execute a workflow.
        
        Args:
            workflow: The workflow definition
            input_data: Trigger input data (merged into first block)
            trigger_type: What started this (api, webhook, schedule, manual)
            from_block_id: Resume from a specific block
        """
        self._ensure_handlers()
        
        execution_id = generate_id("exec")
        started_at = datetime.now()
        
        logger.info(f"Executing: {workflow.name} ({execution_id}) trigger={trigger_type}")
        
        # Initialize resolver with workflow variables + trigger input
        self.resolver = VariableResolver(workflow)
        self.resolver.variables.update(workflow.variables)
        if input_data:
            self.resolver.variables["_triggerInput"] = input_data
            self.resolver.variables["_triggerType"] = trigger_type
        
        # Build execution graph
        graph = self._build_execution_graph(workflow)
        
        # Track state
        completed: set[str] = set()
        block_results: dict[str, dict] = {}
        failed = False
        error_msg = ""
        
        # If resuming from a block, mark predecessors
        if from_block_id:
            self._mark_predecessors(graph, from_block_id, completed)
        
        # Execute in order
        for block_id in graph["execution_order"]:
            if block_id in completed:
                continue
            
            block = graph["blocks"].get(block_id)
            if not block:
                continue
            
            # Check if this is a parallel sentinel
            if block_id in graph.get("parallel_start_sentinels", set()):
                await self._handle_parallel_start(block_id, block, graph)
                completed.add(block_id)
                continue
            
            if block_id in graph.get("parallel_end_sentinels", set()):
                await self._handle_parallel_end(block_id, block, graph, block_results)
                completed.add(block_id)
                continue
            
            # Check if this is a parallel branch clone
            original_id = graph.get("clone_map", {}).get(block_id)
            if original_id:
                block = graph["blocks"][original_id]
            
            # Skip if already completed (for resume)
            if block_id in completed:
                continue
            
            # Execute the block
            try:
                block.status = BlockStatus.RUNNING
                logger.info(f"  Executing: {block.config.name} ({block.config.block_type.value})")
                
                handler = handler_registry.get_handler(
                    block.config.block_type,
                    resolver=self.resolver,
                    context=self.resolver.get_context(),
                )
                
                output = await handler.handle(block)
                
                # Store output
                block.outputs = output
                block.status = BlockStatus.COMPLETED if output.get("success", True) else BlockStatus.FAILED
                block.execution_time = output.get("execution_time", 0)
                
                if not output.get("success", True):
                    failed = True
                    error_msg = output.get("error", "Block failed")
                    logger.warning(f"  Block {block_id} failed: {error_msg}")
                
                # Store in resolver
                self.resolver.store_output(block_id, output)
                block_results[block_id] = output
                
                # Track parallel branch completion
                self._track_parallel_branch(block_id, output)
                
                completed.add(block_id)
                
                if failed and block.config.block_type.value not in ("condition", "start", "end"):
                    break
            
            except Exception as e:
                logger.exception(f"Block {block_id} threw exception")
                block.status = BlockStatus.FAILED
                block.error = str(e)
                failed = True
                error_msg = str(e)
                block_results[block_id] = {"success": False, "error": str(e)}
                completed.add(block_id)
                break
        
        # Build result
        completed_at = datetime.now()
        
        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow.id,
            owner_id=workflow.owner_id,
            status=WorkflowStatus.FAILED if failed else WorkflowStatus.COMPLETED,
            trigger_type=trigger_type,
            trigger_input=input_data or {},
            output=self._collect_final_outputs(graph, block_results),
            error=error_msg if failed else "",
            started_at=started_at,
            completed_at=completed_at,
            block_results=block_results,
            execution_time=(completed_at - started_at).total_seconds(),
        )
        
        # Save
        self.store.save_execution(result)
        
        status_str = "FAILED" if failed else "COMPLETED"
        logger.info(f"Execution {execution_id} {status_str} in {result.execution_time:.2f}s")
        
        return result
    
    def _build_execution_graph(self, workflow: Workflow) -> dict:
        """
        Build a complete execution graph from a workflow.
        
        Handles:
        - DAG construction
        - Parallel sentinel injection
        - Branch cloning for parallel groups
        """
        dag = build_dag(workflow)
        
        blocks_by_id = {b.id: b for b in workflow.blocks}
        execution_order = []
        parallel_start_sentinels = set()
        parallel_end_sentinels = set()
        clone_map = {}  # cloned_id -> original_id
        
        # Process parallel groups
        for parallel_id, pg in workflow.parallels.items():
            branch_count = self._resolve_branch_count(pg, workflow)
            if branch_count <= 0:
                continue
            
            # Create sentinel IDs
            start_sentinel = f"parallel-{parallel_id}-sentinel-start"
            end_sentinel = f"parallel-{parallel_id}-sentinel-end"
            parallel_start_sentinels.add(start_sentinel)
            parallel_end_sentinels.add(end_sentinel)
            
            # Create sentinel blocks
            blocks_by_id[start_sentinel] = Block(
                id=start_sentinel,
                config=BlockConfig(block_type=BlockType.START, name=f"Parallel Start: {parallel_id}"),
            )
            blocks_by_id[end_sentinel] = Block(
                id=end_sentinel,
                config=BlockConfig(block_type=BlockType.END, name=f"Parallel End: {parallel_id}"),
            )
            
            # Clone branches for count > 1
            if branch_count > 1 and pg.parallel_type == ParallelType.COUNT:
                for branch_idx in range(1, branch_count):
                    for block_id in pg.block_ids:
                        cloned_id = f"{block_id}{BRANCH_PREFIX}{branch_idx}{BRANCH_SUFFIX}"
                        clone_map[cloned_id] = block_id
                        # Clone the block
                        original = blocks_by_id.get(block_id)
                        if original:
                            blocks_by_id[cloned_id] = Block(
                                id=cloned_id,
                                config=BlockConfig(
                                    block_type=original.config.block_type,
                                    name=f"{original.config.name} (branch {branch_idx})",
                                    params=dict(original.config.params),
                                    body=dict(original.config.body),
                                    tool_name=original.config.tool_name,
                                    model=original.config.model,
                                    system_prompt=original.config.system_prompt,
                                    code=original.config.code,
                                    url=original.config.url,
                                    method=original.config.method,
                                    condition=original.config.condition,
                                ),
                                position=dict(original.position),
                            )
            
            # Add to execution order: start_sentinel → branches → end_sentinel
            execution_order.append(start_sentinel)
            for block_id in pg.block_ids:
                execution_order.append(block_id)
                # Add clones
                for cloned_id, orig_id in clone_map.items():
                    if orig_id == block_id:
                        execution_order.append(cloned_id)
            execution_order.append(end_sentinel)
            
            # Register parallel scope
            nodes_per_branch = len(pg.block_ids)
            self.parallel_scopes[parallel_id] = ParallelScope(
                parallel_id=parallel_id,
                total_branches=branch_count,
                total_nodes=branch_count * nodes_per_branch,
            )
        
        # Add non-parallel blocks
        for block_id in dag.get_execution_order():
            if block_id not in execution_order:
                execution_order.append(block_id)
        
        # Re-order: respect DAG dependencies
        execution_order = self._topological_sort(blocks_by_id, workflow.connections, execution_order)
        
        return {
            "blocks": blocks_by_id,
            "execution_order": execution_order,
            "parallel_start_sentinels": parallel_start_sentinels,
            "parallel_end_sentinels": parallel_end_sentinels,
            "clone_map": clone_map,
            "dag": dag,
        }
    
    def _resolve_branch_count(self, pg: ParallelGroup, workflow: Workflow) -> int:
        """Resolve the number of branches for a parallel group."""
        if pg.parallel_type == ParallelType.COUNT:
            return max(1, pg.count)
        
        # Collection type — use distribution list length
        if pg.distribution:
            try:
                dist = json.loads(pg.distribution) if isinstance(pg.distribution, str) else pg.distribution
                return max(1, len(dist))
            except Exception:
                return 1
        
        # Try to resolve from variables
        if pg.distribution and isinstance(pg.distribution, str):
            resolved = self.resolver.resolve(pg.distribution) if self.resolver else pg.distribution
            try:
                dist = json.loads(resolved) if isinstance(resolved, str) else resolved
                if isinstance(dist, list):
                    return max(1, len(dist))
            except Exception:
                pass
        
        return 1
    
    def _topological_sort(self, blocks, connections, initial_order) -> list[str]:
        """Topological sort respecting connections."""
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        
        all_ids = set(blocks.keys())
        for c in connections:
            adjacency[c.from_block_id].append(c.to_block_id)
            in_degree[c.to_block_id] += 1
            if c.from_block_id not in in_degree:
                in_degree[c.from_block_id] = 0
        
        # Start with nodes that have no incoming edges
        queue = [nid for nid in all_ids if in_degree.get(nid, 0) == 0]
        result = []
        visited = set()
        
        while queue:
            # Prefer nodes from initial_order to maintain user intent
            queue.sort(key=lambda x: initial_order.index(x) if x in initial_order else 999999)
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            result.append(node)
            
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Add any remaining nodes (cycles or disconnected)
        for nid in initial_order:
            if nid not in visited:
                result.append(nid)
        
        return result
    
    async def _handle_parallel_start(self, sentinel_id: str, block: Block, graph: dict) -> None:
        """Handle parallel start sentinel — initialize scope."""
        logger.info(f"Parallel start: {sentinel_id}")
        # The scope was already created in _build_execution_graph
        # This sentinel just marks the entry point
    
    async def _handle_parallel_end(self, sentinel_id: str, block: Block, graph: dict, block_results: dict) -> dict:
        """Handle parallel end sentinel — aggregate branch results."""
        # Extract parallel ID from sentinel
        parallel_id = sentinel_id.replace("parallel-", "").replace("-sentinel-end", "")
        scope = self.parallel_scopes.get(parallel_id)
        
        if not scope:
            return {}
        
        # Collect all branch outputs
        all_branch_outputs = []
        for block_id, output in block_results.items():
            # Check if this block belongs to the parallel
            for pg_block_id in scope.parallel_id.split("-"):
                if block_id.startswith(pg_block_id) or BRANCH_PREFIX in block_id:
                    all_branch_outputs.append(output)
                    break
        
        aggregated = {
            "success": True,
            "parallel_id": parallel_id,
            "total_branches": scope.total_branches,
            "results": all_branch_outputs,
        }
        
        # Store aggregated output
        self.resolver.store_output(sentinel_id, aggregated)
        block_results[sentinel_id] = aggregated
        
        logger.info(f"Parallel end: {sentinel_id} — {len(all_branch_outputs)} branches aggregated")
        return aggregated
    
    def _track_parallel_branch(self, block_id: str, output: dict) -> None:
        """Track completion of a parallel branch node."""
        # Extract parallel scope from block metadata
        for parallel_id, scope in self.parallel_scopes.items():
            scope.completed_count += 1
    
    def _mark_predecessors(self, graph, target_id: str, completed: set) -> None:
        """Mark all predecessors as completed (for resume)."""
        dag = graph.get("dag")
        if not dag:
            return
        node = dag.nodes.get(target_id)
        if not node:
            return
        for dep in node.dependencies:
            if dep not in completed:
                completed.add(dep)
                self._mark_predecessors(graph, dep, completed)
    
    def _collect_final_outputs(self, graph: dict, block_results: dict) -> dict:
        """Collect outputs from terminal blocks."""
        final = {}
        dag = graph.get("dag")
        if not dag:
            return block_results
        
        for block_id, output in block_results.items():
            node = dag.nodes.get(block_id)
            if node and not node.dependents:
                final[block_id] = output
                final[f"block_{block_id}"] = output
        
        return final
    
    async def execute_from_input(
        self,
        workflow_id: str,
        input_data: dict = None,
        owner_id: str = None,
        trigger_type: str = "manual",
    ) -> ExecutionResult:
        """Load and execute a workflow by ID."""
        workflow = self.store.get_workflow(workflow_id, owner_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        return await self.execute(workflow, input_data, trigger_type)
