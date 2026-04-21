"""
worklone-employee SDK test suite.
Tests imports, DB provisioning, tool registration, provider routing, evolution toggle.
Live LLM test skipped automatically when no API key is set.
"""

import sys, os, asyncio, unittest, tempfile

sys.path.insert(0, os.path.dirname(__file__))


# ── 1. Imports ────────────────────────────────────────────────────────────────

class TestImports(unittest.TestCase):

    def test_public_surface(self):
        from worklone_employee import Employee, BaseTool, ToolResult
        self.assertTrue(callable(Employee))
        self.assertTrue(callable(BaseTool))

    def test_catalog_loads(self):
        from worklone_employee.tools.catalog import DEFAULT_EMPLOYEE_TOOL_NAMES, create_tool
        self.assertGreater(len(DEFAULT_EMPLOYEE_TOOL_NAMES), 0)
        print(f"  Default tools: {len(DEFAULT_EMPLOYEE_TOOL_NAMES)}")

    def test_providers_import(self):
        from worklone_employee.providers.config import (
            get_provider_config, detect_provider, get_user_provider_config
        )
        self.assertTrue(callable(get_provider_config))

    def test_evolution_imports(self):
        from worklone_employee.evolution.evolution_store import EvolutionStore
        from worklone_employee.evolution.background_review import spawn_memory_review
        self.assertTrue(callable(spawn_memory_review))

    def test_react_agent_imports(self):
        from worklone_employee.agents.react_agent import GenericEmployeeAgent
        self.assertTrue(callable(GenericEmployeeAgent))


# ── 2. Provider / LLM Adapter Routing ────────────────────────────────────────

class TestProviderRouting(unittest.TestCase):

    def test_openai_model_routes_to_openrouter(self):
        from worklone_employee.providers.config import detect_provider
        self.assertEqual(detect_provider("openai/gpt-4o"), "openrouter")

    def test_anthropic_model_routes_to_openrouter(self):
        from worklone_employee.providers.config import detect_provider
        self.assertEqual(detect_provider("anthropic/claude-sonnet-4-5"), "openrouter")

    def test_nvidia_model_routes_to_nvidia(self):
        from worklone_employee.providers.config import detect_provider
        self.assertEqual(detect_provider("minimaxai/minimax-m2.7"), "nvidia")
        self.assertEqual(detect_provider("meta/llama-3.1-405b-instruct"), "nvidia")

    def test_get_provider_config_structure(self):
        from worklone_employee.providers.config import get_provider_config
        cfg = get_provider_config("openai/gpt-4o")
        self.assertIn("provider_name", cfg)
        self.assertIn("api_key", cfg)
        self.assertIn("base_url", cfg)
        self.assertIn("headers", cfg)
        self.assertIn("model", cfg)
        self.assertEqual(cfg["provider_name"], "openrouter")
        self.assertEqual(cfg["base_url"], "https://openrouter.ai/api/v1")

    def test_nvidia_provider_config(self):
        from worklone_employee.providers.config import get_provider_config
        cfg = get_provider_config("meta/llama-3.1-405b-instruct")
        self.assertEqual(cfg["provider_name"], "nvidia")
        self.assertEqual(cfg["base_url"], "https://integrate.api.nvidia.com/v1")
        self.assertEqual(cfg["payload_defaults"].get("top_p"), 0.95)

    def test_user_provider_config_falls_back_to_env(self):
        from worklone_employee.providers.config import get_user_provider_config
        # SDK version always returns env-based config (no DB lookup)
        cfg = get_user_provider_config("any_user", "openai/gpt-4o")
        self.assertEqual(cfg["provider_name"], "openrouter")


# ── 3. Employee DB Provisioning ───────────────────────────────────────────────

class TestEmployeeProvisioning(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_employee_created_in_db(self):
        from worklone_employee import Employee
        emp = Employee(name="Test Bot", model="openai/gpt-4o", db=self.tmp)
        from worklone_employee.db.store import EmployeeStore
        store = EmployeeStore(self.tmp)
        row = store.get_employee(emp._employee_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.name, "Test Bot")
        self.assertEqual(row.model, "openai/gpt-4o")

    def test_idempotent_same_name_same_row(self):
        from worklone_employee import Employee
        emp1 = Employee(name="Bot A", db=self.tmp)
        emp2 = Employee(name="Bot A", db=self.tmp)
        self.assertEqual(emp1._employee_id, emp2._employee_id)

    def test_different_names_different_rows(self):
        from worklone_employee import Employee
        emp1 = Employee(name="Bot X", db=self.tmp)
        emp2 = Employee(name="Bot Y", db=self.tmp)
        self.assertNotEqual(emp1._employee_id, emp2._employee_id)

    def test_config_updates_on_re_init(self):
        from worklone_employee import Employee
        Employee(name="Updatable", model="openai/gpt-4o", db=self.tmp)
        emp2 = Employee(name="Updatable", model="anthropic/claude-sonnet-4-5", db=self.tmp)
        from worklone_employee.db.store import EmployeeStore
        row = EmployeeStore(self.tmp).get_employee(emp2._employee_id)
        self.assertEqual(row.model, "anthropic/claude-sonnet-4-5")


# ── 4. Tool Registration ──────────────────────────────────────────────────────

class TestToolRegistration(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_use_tools_persists_to_db(self):
        from worklone_employee import Employee
        emp = Employee(name="Tool Bot", db=self.tmp)
        emp.use_tools(["web_search", "file_tool"])
        from worklone_employee.db.store import EmployeeStore
        tools = EmployeeStore(self.tmp).get_employee_tools(emp._employee_id)
        names = {t.tool_name for t in tools}
        self.assertIn("web_search", names)
        self.assertIn("file_tool", names)

    def test_use_tools_idempotent_no_duplicates(self):
        from worklone_employee import Employee
        emp = Employee(name="Dupe Bot", db=self.tmp)
        emp.use_tools(["web_search"])
        emp.use_tools(["web_search"])  # second call — should not duplicate
        from worklone_employee.db.store import EmployeeStore
        tools = EmployeeStore(self.tmp).get_employee_tools(emp._employee_id)
        names = [t.tool_name for t in tools if t.tool_name == "web_search"]
        self.assertEqual(len(names), 1)

    def test_custom_function_tool_decorator(self):
        from worklone_employee import Employee
        emp = Employee(name="Custom Bot", db=self.tmp)

        @emp.tool(description="Return a fixed greeting")
        def say_hello(name: str) -> str:
            return f"Hello, {name}!"

        self.assertEqual(len(emp._pending_custom_tools), 1)
        tool = emp._pending_custom_tools[0]
        self.assertEqual(tool.name, "say_hello")
        self.assertEqual(tool.description, "Return a fixed greeting")

    def test_custom_tool_schema_from_annotations(self):
        from worklone_employee import Employee
        emp = Employee(name="Schema Bot", db=self.tmp)

        @emp.tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        schema = emp._pending_custom_tools[0].get_schema()
        self.assertEqual(schema["properties"]["a"]["type"], "integer")
        self.assertEqual(schema["properties"]["b"]["type"], "integer")
        self.assertIn("a", schema["required"])
        self.assertIn("b", schema["required"])

    def test_add_tool_instance(self):
        from worklone_employee import Employee, BaseTool, ToolResult
        emp = Employee(name="Instance Bot", db=self.tmp)

        class PingTool(BaseTool):
            name = "ping"
            description = "Ping test"
            def get_schema(self): return {"type": "object", "properties": {}}
            async def execute(self, parameters, context=None):
                return ToolResult(success=True, output="pong")

        emp.add_tool(PingTool())
        self.assertEqual(emp._pending_custom_tools[0].name, "ping")

    def test_custom_tool_execute(self):
        from worklone_employee.employee import FunctionToolAdapter

        def multiply(x: int, y: int) -> int:
            return x * y

        adapter = FunctionToolAdapter(fn=multiply, description="Multiply two numbers")
        result = asyncio.run(adapter.execute({"x": 3, "y": 4}))
        self.assertTrue(result.success)
        self.assertEqual(result.output, "12")


# ── 5. Evolution Toggle ───────────────────────────────────────────────────────

class TestEvolution(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_evolution_disabled_by_default(self):
        from worklone_employee import Employee
        emp = Employee(name="Evo Bot", db=self.tmp)
        self.assertFalse(emp._evolution_enabled)

    def test_enable_evolution_sets_flag(self):
        from worklone_employee import Employee
        emp = Employee(name="Evo Bot 2", db=self.tmp)
        emp.enable_evolution()
        self.assertTrue(emp._evolution_enabled)

    def test_evolution_store_persists_memory(self):
        from worklone_employee.evolution.evolution_store import EvolutionStore
        store = EvolutionStore(self.tmp)
        store.set_user_memory("emp_1", "user_1", "User prefers short answers.")
        memory = store.get_user_memory("emp_1", "user_1")
        self.assertEqual(memory, "User prefers short answers.")

    def test_evolution_store_persists_skills(self):
        from worklone_employee.evolution.evolution_store import EvolutionStore
        store = EvolutionStore(self.tmp)
        result = store.upsert_skill("emp_1", "Draft Email", "Drafting professional emails",
                                    "1. Open composer\n2. Write subject\n3. Send")
        self.assertIn("action", result)
        skills = store.list_skills("emp_1")
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["title"], "Draft Email")


# ── 6. Live LLM Test (skipped if no API key) ─────────────────────────────────

class TestLiveLLM(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_live_run(self):
        if not self.api_key:
            self.skipTest("OPENROUTER_API_KEY not set — skipping live LLM test")

        from worklone_employee import Employee
        emp = Employee(name="Live Test Bot", model="openai/gpt-4o-mini", db=self.tmp)

        @emp.tool(description="Return 42 as a string")
        def get_answer() -> str:
            return "42"

        response = emp.run("Call the get_answer tool and tell me what it returns.")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"\n  Live response: {response[:200]}")


if __name__ == "__main__":
    print("=" * 60)
    print("worklone-employee SDK Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)
