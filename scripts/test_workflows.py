"""
Test the workflow engine end-to-end.
"""

import asyncio
import os
from workflows.store import WorkflowStore
from workflows.engine.executor import WorkflowExecutor
from workflows.types import (
    Workflow, Block, BlockConfig, BlockType, Connection,
)
from workflows.utils import generate_id
from workflows.tools.registry import registry
from workflows.tools.llm_tool import LLMTool
from workflows.tools.http_tool import HTTPTool
from workflows.tools.function_tool import FunctionTool


async def test_basic_workflow():
    """Test creating and executing a simple workflow."""
    
    print("\n" + "=" * 60)
    print("TEST: Basic Workflow Execution")
    print("=" * 60 + "\n")
    
    # Register tools
    registry.register(LLMTool())
    registry.register(HTTPTool())
    registry.register(FunctionTool())
    
    print(f"Registered tools: {registry.list_names()}")
    
    # Create store
    store = WorkflowStore(db_path="test_workflows.db")
    
    # Create workflow
    workflow = Workflow(
        id=generate_id("wf"),
        name="test-simple",
        description="A simple test workflow",
    )
    
    # Add blocks
    start_block = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.START,
            name="Start",
        ),
        position={"x": 100, "y": 100},
    )
    workflow.blocks.append(start_block)
    
    function_block = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Generate Data",
            code="result = {'message': 'Hello from workflow!', 'numbers': [1, 2, 3]}",
        ),
        position={"x": 350, "y": 100},
    )
    workflow.blocks.append(function_block)
    
    # Connect blocks
    workflow.connections.append(Connection(
        id=generate_id("conn"),
        from_block_id=start_block.id,
        to_block_id=function_block.id,
    ))
    
    # Save
    store.save_workflow(workflow)
    print(f"Created workflow: {workflow.id} ({workflow.name})")
    print(f"Blocks: {len(workflow.blocks)}")
    print(f"Connections: {len(workflow.connections)}")
    
    # Execute
    executor = WorkflowExecutor(store)
    result = await executor.execute(workflow)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time:.2f}s")
    print(f"  Blocks executed: {len(result.block_results)}")
    
    for block_id, block_result in result.block_results.items():
        print(f"  {block_id}: {block_result.get('output', '')[:100]}")
    
    if result.error:
        print(f"\n  Error: {result.error}")
    
    assert result.status.value == "completed", f"Expected completed, got {result.status.value}"
    print("\n✓ Test passed!")
    
    return result


async def test_agent_block():
    """Test an agent block with LLM call."""
    
    print("\n" + "=" * 60)
    print("TEST: Agent Block (LLM)")
    print("=" * 60 + "\n")
    
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⊘ Skipping — OPENROUTER_API_KEY not set")
        return None
    
    registry.register(LLMTool())
    
    store = WorkflowStore(db_path="test_workflows.db")
    
    workflow = Workflow(
        id=generate_id("wf"),
        name="test-agent",
        description="Test LLM agent block",
    )
    
    agent_block = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.AGENT,
            name="Analyze",
            system_prompt="You are a helpful assistant. Be concise.",
            model="openai/gpt-4o-mini",
        ),
        position={"x": 100, "y": 100},
    )
    # Set prompt via params
    agent_block.config.params["prompt"] = "What is 2+2? Answer in one word."
    
    workflow.blocks.append(agent_block)
    
    store.save_workflow(workflow)
    print(f"Created workflow: {workflow.id}")
    
    executor = WorkflowExecutor(store)
    result = await executor.execute(workflow)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time:.2f}s")
    
    for block_id, block_result in result.block_results.items():
        content = block_result.get("content", block_result.get("output", ""))
        print(f"  {block_id}: {content[:200]}")
    
    if result.error:
        print(f"\n  Error: {result.error}")
    
    print("\n✓ Test complete!")
    return result


async def test_coworker_tools():
    """Test co-worker workflow management tools."""
    
    print("\n" + "=" * 60)
    print("TEST: Co-Worker Tools")
    print("=" * 60 + "\n")
    
    from workflows.coworker_tools import (
        CreateWorkflowTool, AddBlockTool, ConnectBlocksTool,
        ListWorkflowsTool, GetWorkflowTool,
    )
    
    # Create workflow
    create_tool = CreateWorkflowTool()
    result = await create_tool.execute({"name": "test-coworker-wf", "description": "Test"})
    print(f"Create: {result.output}")
    assert result.success
    
    workflow_id = result.data["workflow_id"]
    
    # Add block
    add_tool = AddBlockTool()
    result = await add_tool.execute({
        "workflow_id": workflow_id,
        "block_type": "function",
        "name": "My Function",
        "code": "result = 'Hello!'",
    })
    print(f"Add block: {result.output}")
    assert result.success
    
    block_id = result.data["block_id"]
    
    # Get workflow
    get_tool = GetWorkflowTool()
    result = await get_tool.execute({"workflow_id": workflow_id})
    print(f"Get: {result.output}")
    assert result.success
    
    # List workflows
    list_tool = ListWorkflowsTool()
    result = await list_tool.execute({})
    print(f"List: {result.output}")
    assert result.success
    
    print("\n✓ All co-worker tool tests passed!")


async def main():
    """Run all tests."""
    
    print("\n" + "█" * 60)
    print("WORKFLOW ENGINE TESTS")
    print("█" * 60)
    
    # Test 1: Basic workflow
    await test_basic_workflow()
    
    # Test 2: Co-worker tools
    await test_coworker_tools()
    
    # Test 3: Agent block (if API key available)
    await test_agent_block()
    
    print("\n" + "█" * 60)
    print("ALL TESTS COMPLETE")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
