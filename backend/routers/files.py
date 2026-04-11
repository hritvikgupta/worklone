"""
Files Router - Authenticated markdown file browser endpoints
"""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.routers.auth import get_current_user

router = APIRouter()


class MarkdownUpdateRequest(BaseModel):
    scope: str
    path: str
    content: str

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = PROJECT_ROOT / "agentic-os" if (PROJECT_ROOT / "agentic-os").exists() else PROJECT_ROOT
SHARED_ROOT = PROJECT_ROOT / ".reference" / "sim" if (PROJECT_ROOT / ".reference" / "sim").exists() else PROJECT_ROOT
FILE_ROOTS: Dict[str, Path] = {
    "agent": AGENT_ROOT,
    "shared": SHARED_ROOT,
}

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
}


def _require_user(user):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")


def _get_root(scope: str) -> Path:
    root = FILE_ROOTS.get(scope)
    if not root or not root.exists():
        raise HTTPException(status_code=404, detail="File scope not found")
    return root.resolve()


def _is_allowed_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".md"


def _build_tree(path: Path, root: Path) -> Optional[dict]:
    if path.name in EXCLUDED_DIRS:
        return None

    if path.is_dir():
        children: List[dict] = []
        try:
            entries = sorted(path.iterdir(), key=lambda entry: (entry.is_file(), entry.name.lower()))
        except PermissionError:
            return None

        for child in entries:
            node = _build_tree(child, root)
            if node:
                children.append(node)

        if not children:
            return None

        relative_path = path.relative_to(root)
        return {
            "type": "folder",
            "name": path.name if relative_path.parts else root.name,
            "path": "" if not relative_path.parts else str(relative_path),
            "children": children,
        }

    if _is_allowed_file(path):
        return {
            "type": "file",
            "name": path.name,
            "path": str(path.relative_to(root)),
        }

    return None


def _resolve_file_path(scope: str, relative_path: str) -> Path:
    root = _get_root(scope)
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc

    if not _is_allowed_file(candidate):
        raise HTTPException(status_code=404, detail="Markdown file not found")

    return candidate


@router.get("/tree")
async def get_markdown_tree(
    scope: str = Query("agent"),
    user=Depends(get_current_user),
):
    """Return a tree of markdown files for the given scope."""
    _require_user(user)
    root = _get_root(scope)
    tree = _build_tree(root, root)
    return {
        "success": True,
        "scope": scope,
        "root_name": root.name,
        "tree": tree["children"] if tree else [],
    }


@router.get("/content")
async def get_markdown_content(
    scope: str = Query("agent"),
    path: str = Query(...),
    user=Depends(get_current_user),
):
    """Return markdown file content for the given scope/path."""
    _require_user(user)
    file_path = _resolve_file_path(scope, path)
    root = _get_root(scope)

    return {
        "success": True,
        "scope": scope,
        "root_name": root.name,
        "path": str(file_path.relative_to(root)),
        "name": file_path.name,
        "content": file_path.read_text(encoding="utf-8"),
    }


@router.put("/content")
async def update_markdown_content(
    request: MarkdownUpdateRequest,
    user=Depends(get_current_user),
):
    """Update markdown file content for the given scope/path."""
    _require_user(user)
    file_path = _resolve_file_path(request.scope, request.path)
    root = _get_root(request.scope)
    file_path.write_text(request.content, encoding="utf-8")

    return {
        "success": True,
        "scope": request.scope,
        "root_name": root.name,
        "path": str(file_path.relative_to(root)),
        "name": file_path.name,
        "content": request.content,
    }
