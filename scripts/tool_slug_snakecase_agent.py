"""
tool_slug_snakecase_agent.py

One-shot migration agent that normalizes every integration tool.name in
backend/core/tools/integration_tools_v2/ to lowercase snake_case, and keeps
the catalog (`PROVIDER_TOOL_BUNDLES` members + `add(...)` registration lines
in backend/core/tools/catalog.py) in sync.

The Composio-style meta tools (search_integration_tools,
execute_integration_tool, get_tool_schemas) resolve slugs by exact match
against tool.name. Label-case names like "Gmail Read" or
"Add Notion Database Row" make the LLM echo back a normalized snake_case
form which then fails to resolve. This script fixes the root cause in one
pass, so we never need runtime alias maps.

Usage:
    python3 scripts/tool_slug_snakecase_agent.py            # dry run
    python3 scripts/tool_slug_snakecase_agent.py --apply    # write changes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "backend/core/tools/integration_tools_v2"
CATALOG_FILE = REPO_ROOT / "backend/core/tools/catalog.py"

# ---------- snake_case rule ----------

SNAKE_OK_RE = re.compile(r"^[a-z0-9_]+$")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def snake_case(name: str) -> str:
    """Lowercase, replace non-alnum runs with _, strip edges, collapse."""
    if not name:
        return ""
    cleaned = NON_ALNUM_RE.sub("_", name.lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned


def is_snake(name: str) -> bool:
    return bool(name) and SNAKE_OK_RE.fullmatch(name) is not None


# ---------- offender discovery ----------

def enumerate_offenders() -> list[tuple[str, str, str]]:
    """Return [(bundle_name, tool_name, provider_root_class), ...] for every
    integration tool whose runtime name is not already snake_case."""
    sys.path.insert(0, str(REPO_ROOT))
    from backend.core.tools.catalog import PROVIDER_TOOL_BUNDLES, create_tool

    offenders: list[tuple[str, str, str]] = []
    for root, bundle in PROVIDER_TOOL_BUNDLES.items():
        for member in bundle.get("members", set()):
            tool = create_tool(member)
            if tool is None:
                continue
            if not is_snake(tool.name):
                offenders.append((member, tool.name, root))
    return offenders


# ---------- file surgery ----------

NAME_LINE_RE = re.compile(r'^(\s*name\s*=\s*)"([^"\n]+)"\s*$')


def find_tool_file_by_name(old_name: str) -> Optional[Path]:
    """Locate the .py file in integration_tools_v2 that declares name = "<old_name>"."""
    target = f'name = "{old_name}"'
    for py_file in TOOLS_DIR.rglob("*.py"):
        try:
            with py_file.open("r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if target in content:
            return py_file
    return None


def patch_tool_file(path: Path, old_name: str, new_name: str) -> bool:
    """Replace the `name = "old"` line with `name = "new"`. Leaves every other
    occurrence of the string untouched (descriptions, docstrings, etc.)."""
    with path.open("r", encoding="utf-8") as f:
        original = f.read()

    new_lines: list[str] = []
    changed = False
    for line in original.splitlines(keepends=True):
        m = NAME_LINE_RE.match(line.rstrip("\r\n"))
        if m and m.group(2) == old_name and not changed:
            new_lines.append(line.replace(f'"{old_name}"', f'"{new_name}"', 1))
            changed = True
        else:
            new_lines.append(line)

    if changed:
        with path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return changed


def patch_catalog(catalog_text: str, old_name: str, new_name: str) -> tuple[str, int]:
    """Replace the old_name string with new_name across catalog.py.

    Only touches occurrences inside double quotes to avoid touching unrelated
    text. Returns (new_text, replacement_count).
    """
    quoted_old = f'"{old_name}"'
    quoted_new = f'"{new_name}"'
    count = catalog_text.count(quoted_old)
    if count == 0:
        return catalog_text, 0
    return catalog_text.replace(quoted_old, quoted_new), count


# ---------- agent ----------

class SlugSnakeCaseAgent:
    def __init__(self, apply_changes: bool = False):
        self.apply_changes = apply_changes
        self.renames: list[tuple[str, str]] = []        # (old, new)
        self.collisions: list[tuple[str, str, str]] = [] # (old_a, old_b, shared_new)
        self.file_edits: list[Path] = []
        self.catalog_edits: int = 0
        self.missing_files: list[str] = []
        self.unchanged_files: list[tuple[str, Path]] = []

    def plan_renames(self, offenders: list[tuple[str, str, str]]) -> dict[str, str]:
        """Build old→new map. Detect collisions against existing snake names AND
        against each other. Abort if any collision — we refuse to silently merge
        two distinct tools into one slug."""
        sys.path.insert(0, str(REPO_ROOT))
        from backend.core.tools.catalog import PROVIDER_TOOL_BUNDLES, create_tool

        existing_snake: set[str] = set()
        for bundle in PROVIDER_TOOL_BUNDLES.values():
            for member in bundle.get("members", set()):
                tool = create_tool(member)
                if tool and is_snake(tool.name):
                    existing_snake.add(tool.name)

        proposed: dict[str, str] = {}
        used_new: dict[str, str] = {}
        for bundle_name, current_name, _root in offenders:
            new = snake_case(current_name)
            if not new:
                continue
            if new in existing_snake:
                self.collisions.append((current_name, f"<existing>{new}", new))
                continue
            if new in used_new and used_new[new] != current_name:
                self.collisions.append((current_name, used_new[new], new))
                continue
            used_new[new] = current_name
            proposed[current_name] = new
        return proposed

    def apply(self, proposed: dict[str, str]) -> None:
        if not proposed:
            print("Nothing to rename.")
            return

        with CATALOG_FILE.open("r", encoding="utf-8") as f:
            catalog_text = f.read()

        for old_name, new_name in sorted(proposed.items()):
            self.renames.append((old_name, new_name))

            tool_file = find_tool_file_by_name(old_name)
            if tool_file is None:
                self.missing_files.append(old_name)
                print(f"  ! no file found for name = {old_name!r}")
            elif self.apply_changes:
                changed = patch_tool_file(tool_file, old_name, new_name)
                if changed:
                    self.file_edits.append(tool_file)
                else:
                    self.unchanged_files.append((old_name, tool_file))
                    print(f"  ! file located but name line not replaced: {tool_file} ({old_name!r})")

            catalog_text, n = patch_catalog(catalog_text, old_name, new_name)
            self.catalog_edits += n

        if self.apply_changes:
            with CATALOG_FILE.open("w", encoding="utf-8") as f:
                f.write(catalog_text)

    def report(self) -> None:
        print()
        print("=" * 72)
        print(f"Renames planned: {len(self.renames)}")
        for old, new in self.renames:
            print(f"  {old!r:45} -> {new!r}")
        if self.collisions:
            print()
            print(f"COLLISIONS ({len(self.collisions)}) — NOT renamed:")
            for a, b, shared in self.collisions:
                print(f"  both {a!r} and {b!r} would collide on {shared!r}")
        if self.missing_files:
            print()
            print(f"Offenders with no matching file ({len(self.missing_files)}):")
            for n in self.missing_files:
                print(f"  {n!r}")
        if self.unchanged_files:
            print()
            print(f"Files located but name line not matched ({len(self.unchanged_files)}):")
            for old, f in self.unchanged_files:
                print(f"  {old!r} -> {f}")
        print()
        print(f"Tool files edited : {len(self.file_edits)}")
        print(f"catalog.py replacements: {self.catalog_edits}")
        print(f"apply_changes = {self.apply_changes}")
        print("=" * 72)


def verify_clean() -> int:
    offenders = enumerate_offenders()
    print(f"Post-verify offender count: {len(offenders)}")
    for bundle_name, tool_name, root in offenders[:20]:
        print(f"  still bad: bundle={bundle_name!r}  tool.name={tool_name!r}  provider={root}")
    return len(offenders)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this, dry-run only.")
    parser.add_argument("--verify-only", action="store_true", help="Skip renames, just enumerate offenders and exit.")
    args = parser.parse_args()

    print("🔧 Tool Slug Snake-Case Agent")
    print(f"   repo:    {REPO_ROOT}")
    print(f"   tools:   {TOOLS_DIR}")
    print(f"   catalog: {CATALOG_FILE}")
    print(f"   apply:   {args.apply}")

    if args.verify_only:
        return 0 if verify_clean() == 0 else 1

    offenders = enumerate_offenders()
    print(f"\nOffenders found: {len(offenders)}")

    agent = SlugSnakeCaseAgent(apply_changes=args.apply)
    proposed = agent.plan_renames(offenders)
    print(f"Proposed renames: {len(proposed)}")
    if agent.collisions:
        print(f"⚠️  {len(agent.collisions)} collisions detected — they will NOT be renamed:")
        for a, b, shared in agent.collisions:
            print(f"   {a!r} vs {b!r} -> {shared!r}")

    if not proposed:
        print("Nothing to do.")
        return 0

    agent.apply(proposed)
    agent.report()

    if args.apply:
        print("\nVerifying post-state…")
        remaining = verify_clean()
        if remaining > 0:
            print("⚠️  Some offenders remain — inspect output above.")
            return 2
        print("✅ All integration tools now use snake_case names.")
    else:
        print("\nDry-run complete. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
