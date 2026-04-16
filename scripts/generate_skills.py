#!/usr/bin/env python3
"""
Generate a workplace skill draft from the internal backend endpoint.

Example:
    python3 scripts/generate_skills.py \
      --title "Personal Assistant Inbox Triage" \
      --description "A reusable workplace skill for reviewing inbound messages, identifying priorities, extracting action items, and preparing structured follow-up outputs." \
      --employee-role "Executive Personal Assistant"
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a skill draft from the internal Worklone skill endpoint."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend base URL. Default: http://localhost:8000",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Skill title to generate.",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Short description of what the skill should cover.",
    )
    parser.add_argument(
        "--employee-role",
        default="",
        help="Optional employee role context for the generator.",
    )
    parser.add_argument(
        "--model",
        default="minimax/minimax-m2.7",
        help="OpenRouter model id. Default: minimax/minimax-m2.7",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print raw JSON only.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    payload = {
        "title": args.title,
        "description": args.description,
        "employee_role": args.employee_role,
        "model": args.model,
    }

    url = f"{args.base_url.rstrip('/')}/api/employees/internal/generate-skill"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        print(f"HTTP {exc.code}: {error_body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return 0

    if args.json_only:
        print(json.dumps(data, indent=2))
        return 0

    print(json.dumps({k: v for k, v in data.items() if k != "skill_markdown"}, indent=2))
    if data.get("skill_markdown"):
        print("\n" + "=" * 80)
        print("SKILL.md")
        print("=" * 80)
        print(data["skill_markdown"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
