"""
Function Tool — Execute custom Python code.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.workflows.tools.base import BaseTool, ToolResult


class FunctionTool(BaseTool):
    """Execute custom Python code within a workflow."""
    
    name = "run_function"
    description = "Execute a Python code snippet. Use for data transformation, calculations, or custom logic."
    category = "core"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use 'result' variable for output.",
                },
                "variables": {
                    "type": "object",
                    "description": "Variables to inject into the code context",
                },
            },
            "required": ["code"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        code = parameters.get("code")
        variables = parameters.get("variables", {})
        
        if not code:
            return ToolResult(
                success=False,
                output="",
                error="Code is required",
            )
        
        # Build execution namespace
        namespace = {
            "context": context or {},
            "result": None,
        }
        namespace.update(variables)
        
        try:
            # Execute code in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(
                    executor,
                    self._execute_code,
                    code,
                    namespace,
                )
                await future
            
            output = str(namespace.get("result", "Code executed successfully"))
            
            return ToolResult(
                success=True,
                output=output,
                data=namespace.get("result"),
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Code execution failed: {str(e)}",
            )
    
    def _execute_code(self, code: str, namespace: dict):
        """Execute code in the given namespace."""
        exec(code, namespace)
