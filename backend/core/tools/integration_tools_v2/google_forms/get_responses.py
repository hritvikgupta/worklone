from typing import Any, Dict
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleFormsGetResponsesTool(BaseTool):
    name = "google_forms_get_responses"
    description = "Retrieve a single response or list responses from a Google Form"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_FORMS_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_FORMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-forms",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_FORMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _normalize_answer_container(self, container: Any) -> Any:
        if not isinstance(container, dict):
            return container
        answers_list = container.get("answers")
        if not isinstance(answers_list, list):
            return container
        values = []
        for entry in answers_list:
            if isinstance(entry, dict) and "value" in entry:
                values.append(entry["value"])
            else:
                values.append(entry)
        return values[0] if len(values) == 1 else values

    def _normalize_answers(self, answers: Any) -> Dict[str, Any]:
        if not isinstance(answers, dict):
            return {}
        out: Dict[str, Any] = {}
        for question_id, answer_obj in answers.items():
            if isinstance(answer_obj, dict):
                found = False
                for k in answer_obj:
                    if k.lower().endswith("answers"):
                        sub = answer_obj[k]
                        if isinstance(sub, dict) and isinstance(sub.get("answers"), list):
                            out[question_id] = self._normalize_answer_container(sub)
                            found = True
                            break
                if not found:
                    out[question_id] = answer_obj
            else:
                out[question_id] = answer_obj
        return out

    def _normalize_response(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "responseId": r.get("responseId"),
            "createTime": r.get("createTime"),
            "lastSubmittedTime": r.get("lastSubmittedTime"),
            "answers": self._normalize_answers(r.get("answers", {})),
        }

    def _parse_timestamp(self, s: str | None) -> datetime:
        if not s:
            return datetime(1970, 1, 1)
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except ValueError:
            return datetime(1970, 1, 1)

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "formId": {
                    "type": "string",
                    "description": "Google Forms form ID",
                },
                "responseId": {
                    "type": "string",
                    "description": "Response ID - if provided, returns this specific response",
                },
                "pageSize": {
                    "type": "number",
                    "description": "Maximum number of responses to return (service may return fewer). Defaults to 5000.",
                },
            },
            "required": ["formId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        form_id = parameters["formId"]
        response_id = parameters.get("responseId")
        page_size = parameters.get("pageSize")

        url_base = f"https://forms.googleapis.com/v1/forms/{form_id}/responses"
        if response_id:
            url = f"{url_base}/{response_id}"
        else:
            url = url_base
            if page_size is not None:
                url += f"?pageSize={int(page_size)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                try:
                    data = response.json()
                except:
                    if response.status_code == 200:
                        return ToolResult(success=True, output=response.text, data={})
                    else:
                        return ToolResult(success=False, output=response.text, error=response.text)

                if response.status_code != 200:
                    error_msg = data.get("error", {}).get("message", response.text or "Failed to fetch responses")
                    return ToolResult(success=False, output=response.text, error=error_msg)

                if "responses" in data and isinstance(data["responses"], list):
                    responses_list = data["responses"]
                    sorted_responses = sorted(
                        responses_list,
                        key=lambda r: self._parse_timestamp(r.get("lastSubmittedTime") or r.get("createTime")),
                        reverse=True,
                    )
                    normalized = [self._normalize_response(r) for r in sorted_responses]
                    transformed = {
                        "responses": normalized,
                        "raw": data,
                    }
                else:
                    normalized_single = self._normalize_response(data)
                    transformed = {
                        "response": normalized_single,
                        "raw": data,
                    }

                return ToolResult(
                    success=True,
                    output=json.dumps(transformed, default=str),
                    data=transformed,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")