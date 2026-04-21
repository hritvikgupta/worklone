# BaseTool Reference

`BaseTool` is the base class for all tools in the SDK. Subclass it to create custom tools with full control over schema, execution, and error handling.

## Interface

```python
from worklone_employee import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "What this tool does — shown to the LLM"
    category = "custom"

    def get_schema(self) -> dict:
        """Return a JSON Schema object describing the tool's parameters."""
        ...

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        """Execute the tool and return a ToolResult."""
        ...
```

## Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Tool identifier — must be unique within an employee |
| `description` | `str` | What the tool does — the LLM reads this to decide when to call it |
| `category` | `str` | Optional grouping label (`"general"`, `"integration"`, `"data"`, etc.) |

## Methods to Implement

### get_schema

```python
def get_schema(self) -> dict:
```

Returns a JSON Schema `object` describing the tool's input parameters. This is passed directly to the LLM.

```python
def get_schema(self) -> dict:
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default: 10)"
            }
        },
        "required": ["query"]
    }
```

### execute

```python
async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
```

Called by the SDK when the LLM decides to use this tool. `parameters` is validated against your schema. `context` contains metadata like `user_id`, `owner_id`, `employee_id`.

```python
async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
    query = parameters["query"]
    limit = parameters.get("limit", 10)
    try:
        results = await my_search_api(query, limit)
        return ToolResult(success=True, output=str(results), data=results)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))
```

## ToolResult

```python
from worklone_employee import ToolResult

ToolResult(
    success: bool,
    output: str,
    error: str = "",
    data: Any = None,
)
```

| Field | Description |
|-------|-------------|
| `success` | Whether the call succeeded |
| `output` | String shown to the LLM as the observation — keep it concise |
| `error` | Error message when `success=False` |
| `data` | Optional structured data — not shown to the LLM directly, available in callbacks |

## Full Example

```python
from worklone_employee import BaseTool, ToolResult
import httpx

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a city"
    category = "data"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name (e.g. 'New York', 'London')"
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units: 'metric' or 'imperial'"
                }
            },
            "required": ["city"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        city = parameters["city"]
        units = parameters.get("units", "metric")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": city, "units": units, "appid": self.api_key}
                )
                resp.raise_for_status()
                data = resp.json()
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                output = f"{city}: {temp}° — {desc}"
                return ToolResult(success=True, output=output, data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

# Register
emp.add_tool(WeatherTool(api_key="your_key"))
```
