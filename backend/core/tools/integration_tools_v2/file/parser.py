from typing import Any, Dict, List, Union
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FileParserTool(BaseTool):
    name = "file_parser"
    description = "Parse one or more uploaded files or files from URLs (text, PDF, CSV, images, etc.)"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filePath": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Path to the file(s). Can be a single path, URL, or an array of paths."
                },
                "file": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Uploaded file(s) to parse"
                },
                "fileType": {
                    "type": "string",
                    "description": "Type of file to parse (auto-detected if not specified)"
                }
            },
            "required": []
        }

    def _resolve_file_path(self, file_input: Any) -> str | None:
        if not isinstance(file_input, dict):
            return None
        path = file_input.get("path")
        if isinstance(path, str):
            return path
        url = file_input.get("url")
        if isinstance(url, str):
            return url
        key = file_input.get("key")
        if isinstance(key, str):
            ctx = file_input.get("context")
            if not isinstance(ctx, str):
                ctx = None
            serve_path = f"/api/files/serve/{urllib.parse.quote(key)}"
            if ctx:
                serve_path += f"?context={urllib.parse.quote(ctx)}"
            return serve_path
        return None

    def _prepare_body(self, parameters: Dict[str, Any], context: Dict[str, Any] | None) -> Dict[str, Any]:
        if not parameters:
            raise ValueError("No parameters provided to tool body")
        determined_file_path: Union[str, List[str], None] = None
        determined_file_type: str | None = parameters.get("fileType")
        # 1. direct filePath
        file_path_param = parameters.get("filePath")
        if file_path_param is not None:
            determined_file_path = file_path_param
        # 2. file array or single
        elif "file" in parameters:
            files_input = parameters["file"]
            if isinstance(files_input, list) and len(files_input) > 0:
                file_paths: List[str] = []
                for f in files_input:
                    p = self._resolve_file_path(f)
                    if p is None:
                        raise ValueError("Invalid file input: One or more files are missing path or URL")
                    file_paths.append(p)
                determined_file_path = file_paths
            elif isinstance(files_input, dict):
                resolved_path = self._resolve_file_path(files_input)
                if resolved_path is None:
                    raise ValueError("Invalid file input: Missing path or URL")
                determined_file_path = resolved_path
        # 3. legacy files
        elif "files" in parameters:
            files_input = parameters["files"]
            if isinstance(files_input, list) and len(files_input) > 0:
                file_paths: List[str] = []
                for f in files_input:
                    p = self._resolve_file_path(f)
                    if p is None:
                        raise ValueError("Invalid file input: One or more files are missing path or URL")
                    file_paths.append(p)
                determined_file_path = file_paths
        if determined_file_path is None:
            raise ValueError("Missing required parameter: filePath")
        body: Dict[str, Any] = {
            "filePath": determined_file_path,
            "fileType": determined_file_type,
        }
        workspace_id = parameters.get("workspaceId")
        if workspace_id is None and context:
            workspace_id = context.get("workspaceId")
        if workspace_id:
            body["workspaceId"] = workspace_id
        if context:
            workflow_id = context.get("workflowId")
            if workflow_id:
                body["workflowId"] = workflow_id
            execution_id = context.get("executionId")
            if execution_id:
                body["executionId"] = execution_id
        return body

    def _parse_file_parser_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if "results" in result:
            # multi
            file_results: List[Dict[str, Any]] = []
            for file_result in result["results"]:
                fr = file_result.get("output", file_result)
                file_results.append(fr)
            processed_files: List[Dict[str, Any]] = [fr["file"] for fr in file_results if "file" in fr]
            divider = "\n" + "=" * 80 + "\n"
            contents_parts: List[str] = []
            for i, fr in enumerate(file_results):
                part = fr.get("content", "")
                if i < len(file_results) - 1:
                    part += divider
                contents_parts.append(part)
            combined_content = "\n".join(contents_parts)
            output_data: Dict[str, Any] = {
                "files": file_results,
                "combinedContent": combined_content,
            }
            if processed_files:
                output_data["processedFiles"] = processed_files
            return {"success": True, "output": output_data}
        else:
            # single
            file_output = result.get("output", result)
            combined_content = file_output.get("content") or result.get("content", "")
            output_data: Dict[str, Any] = {
                "files": [file_output],
                "combinedContent": combined_content,
            }
            if "file" in file_output:
                output_data["processedFiles"] = [file_output["file"]]
            return {"success": True, "output": output_data}

    def _transform_v3_response(self, response: httpx.Response) -> Dict[str, Any]:
        result = response.json()
        parsed = self._parse_file_parser_response(result)
        output = parsed["output"]
        files = output.get("processedFiles", [])
        if not isinstance(files, list):
            files = []
        return {
            "files": files,
            "combinedContent": output["combinedContent"],
        }

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        headers = {
            "Content-Type": "application/json",
        }
        url = "/api/files/parse"
        try:
            body = self._prepare_body(parameters, context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                if response.status_code in [200, 201, 204]:
                    cleaned = self._transform_v3_response(response)
                    return ToolResult(
                        success=True,
                        output=cleaned["combinedContent"],
                        data=cleaned
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")