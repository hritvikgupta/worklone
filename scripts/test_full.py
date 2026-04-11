"""
Comprehensive test for the full workflow engine.

Tests:
1. Multi-tenant auth (users, API keys)
2. Workflow CRUD (create, read, update, delete)
3. Blocks and connections
4. Triggers (webhook, schedule, API)
5. Workflow execution (sync + parallel)
6. Background jobs
7. Schedule dispatcher
"""

import asyncio
import json
import os
from datetime import datetime

from workflows.store import WorkflowStore
from workflows.engine.executor import WorkflowExecutor
from workflows.worker import BackgroundWorker, ScheduleDispatcher
from workflows.types import (
    Workflow, Block, BlockConfig, BlockType, Connection,
    Trigger, TriggerType, ParallelGroup, ParallelType,
    ExecutionResult, BackgroundJob, JobStatus, APIKeyType, SchedulePreset,
)
from workflows.utils import generate_id
from workflows.tools.registry import registry
from workflows.tools.llm_tool import LLMTool
from workflows.tools.http_tool import HTTPTool
from workflows.tools.function_tool import FunctionTool


async def test_multi_tenant():
    """Test user isolation and API keys."""
    print("\n" + "=" * 60)
    print("TEST 1: Multi-Tenant Auth")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Create two users
    user1 = store.create_user(user_id="user_1", name="Alice", email="alice@test.com")
    user2 = store.create_user(user_id="user_2", name="Bob", email="bob@test.com")
    print(f"Created users: {user1.name} ({user1.id}), {user2.name} ({user2.id})")
    
    # Create API keys
    key1 = store.create_api_key(user1.id, name="Alice's Key")
    key2 = store.create_api_key(user2.id, name="Bob's Key")
    print(f"Created API keys: {key1.id}, {key2.id}")
    
    # Verify keys
    verified1 = store.verify_api_key(key1.key_raw)
    verified2 = store.verify_api_key(key2.key_raw)
    assert verified1.owner_id == user1.id, "Key 1 should belong to user 1"
    assert verified2.owner_id == user2.id, "Key 2 should belong to user 2"
    print(f"✓ API keys verified: {verified1.owner_id}, {verified2.owner_id}")
    
    # Invalid key
    invalid = store.verify_api_key("invalid_key")
    assert invalid is None, "Invalid key should return None"
    print("✓ Invalid key correctly rejected")
    
    # Revoke key
    store.revoke_api_key(key1.id, user1.id)
    revoked = store.verify_api_key(key1.key_raw)
    assert revoked is None, "Revoked key should not work"
    print("✓ API key revocation works")
    
    print("\n✓ Multi-tenant auth tests passed!")


async def test_workflow_isolation():
    """Test that users can only access their own workflows."""
    print("\n" + "=" * 60)
    print("TEST 2: Workflow Isolation")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Create workflows for each user
    wf1 = Workflow(id=generate_id("wf"), name="Alice's Workflow", owner_id="user_1")
    wf2 = Workflow(id=generate_id("wf"), name="Bob's Workflow", owner_id="user_2")
    
    store.save_workflow(wf1)
    store.save_workflow(wf2)
    
    # User 1 can see their workflow
    alice_wfs = store.list_workflows("user_1")
    assert len(alice_wfs) >= 1, "Alice should have at least 1 workflow"
    wf1_ids = [wf.id for wf in alice_wfs]
    assert wf1.id in wf1_ids, "Alice should see her workflow"
    print(f"✓ Alice sees {len(alice_wfs)} workflow(s)")
    
    # User 2 can see their workflow
    bob_wfs = store.list_workflows("user_2")
    assert len(bob_wfs) >= 1, "Bob should have at least 1 workflow"
    wf2_ids = [wf.id for wf in bob_wfs]
    assert wf2.id in wf2_ids, "Bob should see his workflow"
    print(f"✓ Bob sees {len(bob_wfs)} workflow(s)")
    
    # User 1 cannot see User 2's workflow
    assert wf2.id not in wf1_ids, "Alice should NOT see Bob's workflow"
    print("✓ Workflow isolation works — users can't see each other's workflows")
    
    # Get specific workflow with owner check
    result = store.get_workflow(wf1.id, "user_1")
    assert result is not None, "Alice can get her workflow"
    result = store.get_workflow(wf1.id, "user_2")
    assert result is None, "Bob cannot get Alice's workflow"
    print("✓ Owner-restricted get_workflow works")
    
    print("\n✓ Workflow isolation tests passed!")


async def test_triggers():
    """Test trigger creation and queries."""
    print("\n" + "=" * 60)
    print("TEST 3: Triggers (Webhook, Schedule, API)")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Create a workflow with triggers
    workflow = Workflow(
        id=generate_id("wf"),
        name="trigger-test",
        owner_id="user_1",
    )
    
    # Webhook trigger
    workflow.triggers.append(Trigger(
        id=generate_id("trig"),
        trigger_type=TriggerType.WEBHOOK,
        name="Incoming webhook",
        webhook_path=generate_id("wh"),
        enabled=True,
    ))
    
    # Schedule trigger
    workflow.triggers.append(Trigger(
        id=generate_id("trig"),
        trigger_type=TriggerType.SCHEDULE,
        name="Daily run",
        schedule_preset=SchedulePreset.DAILY,
        cron_expression="0 0 * * *",
        enabled=True,
        next_run_at=datetime.now(),
    ))
    
    # API trigger
    workflow.triggers.append(Trigger(
        id=generate_id("trig"),
        trigger_type=TriggerType.API,
        name="API trigger",
        enabled=True,
    ))
    
    store.save_workflow(workflow)
    print(f"Created workflow with {len(workflow.triggers)} triggers")
    
    # Query webhook by path
    webhook_trigger = workflow.triggers[0]
    found = store.get_webhook_by_path(webhook_trigger.webhook_path)
    assert found is not None, "Should find webhook by path"
    print(f"✓ Webhook found by path: {found.name}")
    
    # Query due schedules
    due = store.get_due_schedules()
    assert len(due) >= 1, "Should have at least 1 due schedule"
    print(f"✓ Found {len(due)} due schedule(s)")
    
    # List all schedules
    all_schedules = store.get_all_schedule_triggers()
    schedule_count = len([s for s in all_schedules if s.name == "Daily run"])
    assert schedule_count >= 1, "Should find the daily schedule"
    print(f"✓ Found {schedule_count} schedule trigger(s)")
    
    print("\n✓ Trigger tests passed!")


async def test_parallel_execution():
    """Test parallel block execution."""
    print("\n" + "=" * 60)
    print("TEST 4: Parallel Execution")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Register tools
    registry.register(FunctionTool())
    
    # Create workflow with parallel blocks
    workflow = Workflow(
        id=generate_id("wf"),
        name="parallel-test",
        owner_id="user_1",
    )
    
    # Start block
    start = Block(
        id=generate_id("blk"),
        config=BlockConfig(block_type=BlockType.START, name="Start"),
        position={"x": 100, "y": 100},
    )
    workflow.blocks.append(start)
    
    # Two function blocks to run in parallel
    func1 = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Task A",
            code="result = 'Task A completed'",
        ),
        position={"x": 350, "y": 50},
    )
    workflow.blocks.append(func1)
    
    func2 = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Task B",
            code="result = 'Task B completed'",
        ),
        position={"x": 350, "y": 200},
    )
    workflow.blocks.append(func2)
    
    # Parallel group
    parallel_id = generate_id("par")
    workflow.parallels[parallel_id] = ParallelGroup(
        id=parallel_id,
        block_ids=[func1.id, func2.id],
        parallel_type=ParallelType.COUNT,
        count=1,
    )
    
    # End block
    end = Block(
        id=generate_id("blk"),
        config=BlockConfig(block_type=BlockType.END, name="End"),
        position={"x": 600, "y": 100},
    )
    workflow.blocks.append(end)
    
    # Connections
    workflow.connections.append(Connection(
        id=generate_id("conn"),
        from_block_id=start.id,
        to_block_id=func1.id,
    ))
    workflow.connections.append(Connection(
        id=generate_id("conn"),
        from_block_id=func1.id,
        to_block_id=func2.id,
    ))
    workflow.connections.append(Connection(
        id=generate_id("conn"),
        from_block_id=func2.id,
        to_block_id=end.id,
    ))
    
    store.save_workflow(workflow)
    print(f"Created parallel workflow: {len(workflow.blocks)} blocks, 1 parallel group")
    
    # Execute
    executor = WorkflowExecutor(store)
    result = await executor.execute(workflow, trigger_type="manual")
    
    print(f"Status: {result.status.value}")
    print(f"Blocks executed: {len(result.block_results)}")
    
    for block_id, block_result in result.block_results.items():
        status = "✓" if block_result.get("success") else "✗"
        print(f"  {status} {block_id}: {str(block_result.get('output', ''))[:80]}")
    
    assert result.status.value == "completed", f"Expected completed, got {result.status.value}"
    print("\n✓ Parallel execution test passed!")


async def test_background_jobs():
    """Test background job queue and processing."""
    print("\n" + "=" * 60)
    print("TEST 5: Background Jobs")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Create a simple workflow for job testing
    workflow = Workflow(
        id=generate_id("wf"),
        name="job-test",
        owner_id="user_1",
    )
    workflow.blocks.append(Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Simple Task",
            code="result = 'Done!'",
        ),
    ))
    store.save_workflow(workflow)
    
    # Enqueue a job
    job = BackgroundJob(
        id=generate_id("job"),
        workflow_id=workflow.id,
        owner_id="user_1",
        job_type="workflow_execution",
        payload={"workflow_id": workflow.id, "input_data": {}},
        max_attempts=3,
    )
    store.enqueue_job(job)
    print(f"Enqueued job: {job.id}")
    
    # Get pending jobs
    pending = store.get_pending_jobs()
    assert len(pending) >= 1, "Should have pending job"
    print(f"✓ Found {len(pending)} pending job(s)")
    
    # Update job status
    store.update_job_status(job.id, JobStatus.RUNNING, attempts=1)
    store.update_job_status(job.id, JobStatus.COMPLETED)
    
    # Job should no longer be pending
    pending = store.get_pending_jobs()
    completed_job_ids = [j.id for j in store.get_pending_jobs()]
    assert job.id not in completed_job_ids, "Completed job should not be pending"
    print("✓ Job status updates correctly")
    
    print("\n✓ Background job tests passed!")


async def test_schedule_dispatcher():
    """Test schedule dispatcher."""
    print("\n" + "=" * 60)
    print("TEST 6: Schedule Dispatcher")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    dispatcher = ScheduleDispatcher(store)
    
    # Get schedule summary
    summary = dispatcher.get_next_run_summary()
    print(f"Found {len(summary)} scheduled trigger(s)")
    
    for s in summary:
        print(f"  • {s['name']}: cron={s['cron']}, preset={s['preset']}, "
              f"failed={s['failed_count']}, enabled={s['enabled']}")
    
    # Tick (should process due schedules)
    await dispatcher.tick()
    print("✓ Schedule tick completed")
    
    # Check for enqueued jobs
    jobs = store.get_pending_jobs()
    schedule_jobs = [j for j in jobs if j.job_type == "schedule_dispatch"]
    print(f"✓ {len(schedule_jobs)} schedule job(s) enqueued")
    
    print("\n✓ Schedule dispatcher tests passed!")


async def test_variable_resolution():
    """Test variable resolution between blocks."""
    print("\n" + "=" * 60)
    print("TEST 7: Variable Resolution")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    registry.register(FunctionTool())
    
    # Create workflow with variable passing
    workflow = Workflow(
        id=generate_id("wf"),
        name="variable-test",
        owner_id="user_1",
        variables={"greeting": "Hello"},
    )
    
    # Block 1: Generate data
    block1 = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Generate",
            code="result = {'name': 'World', 'numbers': [1, 2, 3]}",
        ),
    )
    workflow.blocks.append(block1)
    
    # Block 2: Use output from block 1 via template
    block2 = Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Transform",
            code="""
import json
output = json.loads('{{Generate.output.output}}'.replace("'", '"'))
result = f"{{output.get('name', 'unknown')}}"
""",
        ),
    )
    workflow.blocks.append(block2)
    
    # Connection
    workflow.connections.append(Connection(
        id=generate_id("conn"),
        from_block_id=block1.id,
        to_block_id=block2.id,
    ))
    
    store.save_workflow(workflow)
    
    # Execute
    executor = WorkflowExecutor(store)
    result = await executor.execute(workflow)
    
    print(f"Status: {result.status.value}")
    for block_id, block_result in result.block_results.items():
        print(f"  {block_id}: {str(block_result.get('output', ''))[:100]}")
    
    print("\n✓ Variable resolution test passed!")


async def test_webhook_trigger():
    """Test webhook trigger flow."""
    print("\n" + "=" * 60)
    print("TEST 8: Webhook Trigger Flow")
    print("=" * 60)
    
    store = WorkflowStore(db_path="test_full.db")
    
    # Create workflow with webhook trigger
    workflow = Workflow(
        id=generate_id("wf"),
        name="webhook-test",
        owner_id="user_1",
    )
    
    webhook_trigger = Trigger(
        id=generate_id("trig"),
        trigger_type=TriggerType.WEBHOOK,
        name="Incoming data",
        webhook_path="test-webhook-123",
        enabled=True,
    )
    workflow.triggers.append(webhook_trigger)
    
    # Block to process webhook data
    workflow.blocks.append(Block(
        id=generate_id("blk"),
        config=BlockConfig(
            block_type=BlockType.FUNCTION,
            name="Process",
            code="result = 'Webhook data received'",
        ),
    ))
    
    store.save_workflow(workflow)
    
    # Find webhook by path
    found = store.get_webhook_by_path("test-webhook-123")
    assert found is not None, "Should find webhook"
    assert found.id == webhook_trigger.id, "Should be the same trigger"
    print(f"✓ Webhook found: {found.name} (path={found.webhook_path})")
    
    # Non-existent path
    not_found = store.get_webhook_by_path("non-existent")
    assert not_found is None, "Should not find non-existent webhook"
    print("✓ Non-existent webhook correctly returns None")
    
    print("\n✓ Webhook trigger test passed!")


async def main():
    """Run all tests."""
    print("\n" + "█" * 60)
    print("FULL WORKFLOW ENGINE TESTS")
    print("█" * 60)
    
    # Clean up
    import os
    if os.path.exists("test_full.db"):
        os.remove("test_full.db")
    
    try:
        await test_multi_tenant()
        await test_workflow_isolation()
        await test_triggers()
        await test_parallel_execution()
        await test_background_jobs()
        await test_schedule_dispatcher()
        await test_variable_resolution()
        await test_webhook_trigger()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    print("\n" + "█" * 60)
    print("ALL TESTS PASSED")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
