import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from backend.db.database import get_shared_db_path, get_connection

BLOB_STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "blobs"

def _ensure_schema(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_metadata (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            local_blob_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, scope, path)
        )
        """
    )
    conn.commit()

class FileStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = get_shared_db_path(db_path)
        with get_connection(self.db_path) as conn:
            _ensure_schema(conn)
        
        # Ensure blob directory exists
        BLOB_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_file_metadata(self, user_id: str, scope: str, path: str) -> Optional[Dict]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM file_metadata WHERE user_id = ? AND scope = ? AND path = ?",
                (user_id, scope, path)
            ).fetchone()
            return dict(row) if row else None

    def list_files(self, user_id: str, scope: str) -> List[Dict]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM file_metadata WHERE user_id = ? AND scope = ? ORDER BY path",
                (user_id, scope)
            ).fetchall()
            return [dict(row) for row in rows]

    def create_folder(self, user_id: str, scope: str, path: str, name: str) -> Dict:
        now = self._now()
        folder_id = f"folder_{uuid.uuid4().hex}"
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO file_metadata (id, user_id, scope, path, name, type, local_blob_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (folder_id, user_id, scope, path, name, "folder", None, now, now)
            )
            conn.commit()
            
            row = conn.execute("SELECT * FROM file_metadata WHERE id = ?", (folder_id,)).fetchone()
            return dict(row)

    def save_file_content(self, user_id: str, scope: str, path: str, name: str, content: str) -> Dict:
        return self.save_file_bytes(user_id, scope, path, name, content.encode("utf-8"))

    def save_file_bytes(self, user_id: str, scope: str, path: str, name: str, content: bytes) -> Dict:
        now = self._now()
        existing = self.get_file_metadata(user_id, scope, path)
        
        if existing:
            blob_path = existing["local_blob_path"]
            if not blob_path:
                blob_path = str(BLOB_STORAGE_DIR / f"{uuid.uuid4().hex}_{name}")
            
            # Write physical file
            Path(blob_path).write_bytes(content)
            
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE file_metadata 
                    SET updated_at = ?, local_blob_path = ?
                    WHERE id = ?
                    """,
                    (now, blob_path, existing["id"])
                )
                conn.commit()
                row = conn.execute("SELECT * FROM file_metadata WHERE id = ?", (existing["id"],)).fetchone()
                return dict(row)
        else:
            file_id = f"file_{uuid.uuid4().hex}"
            blob_path = str(BLOB_STORAGE_DIR / f"{uuid.uuid4().hex}_{name}")
            
            # Write physical file
            Path(blob_path).write_bytes(content)
            
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO file_metadata (id, user_id, scope, path, name, type, local_blob_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (file_id, user_id, scope, path, name, "file", blob_path, now, now)
                )
                conn.commit()
                row = conn.execute("SELECT * FROM file_metadata WHERE id = ?", (file_id,)).fetchone()
                return dict(row)

    def read_file_content(self, user_id: str, scope: str, path: str) -> Optional[str]:
        bytes_content = self.read_file_bytes(user_id, scope, path)
        if bytes_content is None:
            return None
        return bytes_content.decode("utf-8", errors="replace")
        
    def read_file_bytes(self, user_id: str, scope: str, path: str) -> Optional[bytes]:
        metadata = self.get_file_metadata(user_id, scope, path)
        if not metadata or metadata["type"] != "file" or not metadata["local_blob_path"]:
            return None
            
        try:
            return Path(metadata["local_blob_path"]).read_bytes()
        except FileNotFoundError:
            return None
