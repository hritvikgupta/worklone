"""
Files Router - Authenticated markdown file browser endpoints
"""

from pathlib import Path
from typing import Dict, List, Optional
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from pydantic import BaseModel

from backend.lib.auth.session import get_current_user
from backend.store.file_store import FileStore

router = APIRouter()
file_store = FileStore()

class MarkdownUpdateRequest(BaseModel):
    scope: str
    path: str
    content: str

def _require_user(user):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

def _build_tree_from_paths(files_metadata: List[Dict]) -> List[Dict]:
    """Build a nested tree structure from a flat list of file metadata paths."""
    tree = []
    
    # Use a dictionary to keep track of folder nodes
    folders = {"": {"children": tree}}
    
    for meta in files_metadata:
        path_parts = meta["path"].split("/")
        
        current_path = ""
        current_node = folders[""]
        
        # Build folder structure
        for i, part in enumerate(path_parts):
            is_last = (i == len(path_parts) - 1)
            
            if current_path:
                current_path += "/" + part
            else:
                current_path = part
                
            if current_path not in folders:
                if is_last and meta["type"] == "file":
                    # It's a file
                    node = {
                        "type": "file",
                        "name": meta["name"],
                        "path": meta["path"]
                    }
                    current_node["children"].append(node)
                else:
                    # It's a folder (either explicit or implicit parent)
                    node_name = meta["name"] if is_last else part
                    node = {
                        "type": "folder",
                        "name": node_name,
                        "path": current_path,
                        "children": []
                    }
                    current_node["children"].append(node)
                    folders[current_path] = node
            
            if current_path in folders:
                current_node = folders[current_path]

    return tree

@router.get("/tree")
async def get_markdown_tree(
    scope: str = Query("agent"),
    user=Depends(get_current_user),
):
    """Return a tree of files for the given scope and user."""
    _require_user(user)
    
    files = file_store.list_files(user["id"], scope)
    tree_nodes = _build_tree_from_paths(files)
    
    return {
        "success": True,
        "scope": scope,
        "root_name": "Root",
        "tree": tree_nodes,
    }

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    scope: str = Query("agent"),
    path: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """Upload a file to the user's storage."""
    _require_user(user)
    
    content = await file.read()
    name = file.filename
    # If no path provided, just use the filename
    file_path = path if path else name
    
    updated_meta = file_store.save_file_bytes(
        user["id"], 
        scope, 
        file_path, 
        name, 
        content
    )

    return {
        "success": True,
        "scope": scope,
        "path": updated_meta["path"],
        "name": updated_meta["name"],
    }

@router.get("/raw")
async def get_raw_file(
    scope: str = Query("agent"),
    path: str = Query(...),
    user=Depends(get_current_user),
):
    """Serve the raw file content."""
    _require_user(user)
    
    metadata = file_store.get_file_metadata(user["id"], scope, path)
    if not metadata or metadata["type"] != "file":
        raise HTTPException(status_code=404, detail="File not found")
        
    content = file_store.read_file_bytes(user["id"], scope, path)
    if content is None:
         raise HTTPException(status_code=404, detail="File content not found")

    # Determine content type based on extension
    content_type = "application/octet-stream"
    if path.lower().endswith(".pdf"):
        content_type = "application/pdf"
    elif path.lower().endswith(".md"):
        content_type = "text/markdown"
    elif path.lower().endswith(".txt"):
        content_type = "text/plain"
        
    # urlencode filename for header
    encoded_name = urllib.parse.quote(metadata["name"])

    return Response(
        content=content, 
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename*=utf-8''{encoded_name}"
        }
    )

@router.get("/content")
async def get_markdown_content(
    scope: str = Query("agent"),
    path: str = Query(...),
    user=Depends(get_current_user),
):
    """Return markdown file content for the given scope/path."""
    _require_user(user)
    
    metadata = file_store.get_file_metadata(user["id"], scope, path)
    if not metadata or metadata["type"] != "file":
        raise HTTPException(status_code=404, detail="Markdown file not found")
        
    content = file_store.read_file_content(user["id"], scope, path)
    if content is None:
         raise HTTPException(status_code=404, detail="Markdown file content not found")

    return {
        "success": True,
        "scope": scope,
        "root_name": "Root",
        "path": metadata["path"],
        "name": metadata["name"],
        "content": content,
    }


@router.put("/content")
async def update_markdown_content(
    request: MarkdownUpdateRequest,
    user=Depends(get_current_user),
):
    """Update markdown file content for the given scope/path."""
    _require_user(user)
    
    name = request.path.split("/")[-1]
    
    # Save or update the file content
    updated_meta = file_store.save_file_content(
        user["id"], 
        request.scope, 
        request.path, 
        name, 
        request.content
    )

    return {
        "success": True,
        "scope": request.scope,
        "root_name": "Root",
        "path": updated_meta["path"],
        "name": updated_meta["name"],
        "content": request.content,
    }
