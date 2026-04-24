"""Migration agent for normalizing OAuth provider usage across integration tools.

This script scans backend integration tools for calls to resolve_oauth_connection(...)
and rewrites the provider string to the canonical auth provider for that tool family.

Default mode is dry-run:
    python3 scripts/oauth_tool_migration_agent.py

Apply changes:
    python3 scripts/oauth_tool_migration_agent.py --apply
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.lib.oauth.providers import OAUTH_PROVIDERS  # noqa: E402

INTEGRATION_TOOLS_DIR = REPO_ROOT / "backend/core/tools/integration_tools_v2"

# Families that intentionally share one stored OAuth connection.
AUTH_PROVIDER_ALIASES = {
    "gmail": "google",
    "google_email": "google",
    "google_drive": "google",
    "google_calendar": "google",
}

CALL_PATTERN = re.compile(
    r"resolve_oauth_connection\(\s*(?P<quote>['\"])(?P<provider>[^'\"]+)(?P=quote)",
    re.MULTILINE,
)


@dataclass
class ProviderChange:
    file: Path
    line: int
    current: str
    expected: str


def normalize_provider(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def canonical_provider_for_tool_file(path: Path) -> str:
    folder_provider = normalize_provider(path.parent.name)
    return AUTH_PROVIDER_ALIASES.get(folder_provider, folder_provider)


def should_manage_tool_file(path: Path) -> bool:
    expected = canonical_provider_for_tool_file(path)
    return expected in OAUTH_PROVIDERS


def has_valid_python(source: str, path: Path) -> bool:
    try:
        ast.parse(source, filename=str(path))
        return True
    except SyntaxError:
        return False


def line_number(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def scan_file(path: Path) -> list[ProviderChange]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    expected = canonical_provider_for_tool_file(path)
    changes: list[ProviderChange] = []

    for match in CALL_PATTERN.finditer(source):
        current_raw = match.group("provider")
        current = normalize_provider(current_raw)
        if AUTH_PROVIDER_ALIASES.get(current, current) == expected:
            continue
        changes.append(
            ProviderChange(
                file=path,
                line=line_number(source, match.start("provider")),
                current=current_raw,
                expected=expected,
            )
        )

    return changes


def rewrite_file(path: Path, changes: list[ProviderChange]) -> bool:
    if not changes:
        return False

    source = path.read_text(encoding="utf-8", errors="ignore")
    expected = canonical_provider_for_tool_file(path)

    def replace(match: re.Match[str]) -> str:
        current = normalize_provider(match.group("provider"))
        if AUTH_PROVIDER_ALIASES.get(current, current) == expected:
            return match.group(0)
        quote = match.group("quote")
        return f"resolve_oauth_connection({quote}{expected}{quote}"

    updated = CALL_PATTERN.sub(replace, source)
    if updated == source:
        return False
    if not has_valid_python(updated, path):
        raise RuntimeError(f"Refusing to write invalid Python: {path}")

    path.write_text(updated, encoding="utf-8")
    return True


class OAuthToolMigrationAgent:
    """Scans and optionally fixes OAuth provider strings in integration tools."""

    def __init__(self, root: Path, apply: bool = False, provider: str | None = None):
        self.root = root
        self.apply = apply
        self.provider = normalize_provider(provider) if provider else None

    def iter_tool_files(self) -> list[Path]:
        files = []
        for path in sorted(self.root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if self.provider and normalize_provider(path.parent.name) != self.provider:
                continue
            files.append(path)
        return files

    def run(self) -> int:
        all_changes: list[ProviderChange] = []
        changed_files = 0

        for path in self.iter_tool_files():
            source = path.read_text(encoding="utf-8", errors="ignore")
            if "resolve_oauth_connection(" not in source:
                continue
            if not should_manage_tool_file(path):
                continue
            changes = scan_file(path)
            all_changes.extend(changes)
            if self.apply and rewrite_file(path, changes):
                changed_files += 1

        if not all_changes:
            print("No OAuth provider mismatches found.")
            return 0

        mode = "Applied" if self.apply else "Would update"
        print(f"{mode} {len(all_changes)} OAuth provider reference(s) in {len({c.file for c in all_changes})} file(s):")
        for change in all_changes:
            rel = change.file.relative_to(REPO_ROOT)
            print(f"- {rel}:{change.line}: {change.current!r} -> {change.expected!r}")

        if self.apply:
            print(f"\nChanged files: {changed_files}")
        else:
            print("\nDry run only. Re-run with --apply to write changes.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize OAuth provider strings in integration tools.")
    parser.add_argument("--apply", action="store_true", help="Write changes to tool files.")
    parser.add_argument("--provider", help="Limit to one provider folder, e.g. gmail or slack.")
    args = parser.parse_args()

    agent = OAuthToolMigrationAgent(
        root=INTEGRATION_TOOLS_DIR,
        apply=args.apply,
        provider=args.provider,
    )
    return agent.run()


if __name__ == "__main__":
    raise SystemExit(main())
