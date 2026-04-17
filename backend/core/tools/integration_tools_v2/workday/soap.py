import base64
import xml.sax.saxutils


WORKDAY_SERVICES = {
    "staffing": "Human_Resources",
    "human_resources": "Human_Resources",
    "compensation": "Compensation",
    "recruiting": "Recruiting",
}

DEFAULT_WORKDAY_VERSION = "v45.0"


def build_workday_url(
    tenant_url: str,
    tenant: str,
    *,
    service: str = "human_resources",
    version: str = DEFAULT_WORKDAY_VERSION,
) -> str:
    service_name = WORKDAY_SERVICES.get(service, service)
    return f"{tenant_url.rstrip('/')}/{tenant}/ccx/service/{service_name}/{version}"


def build_basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "text/xml; charset=utf-8",
    }


def xml_escape(value: str | None) -> str:
    return xml.sax.saxutils.escape(value or "")
