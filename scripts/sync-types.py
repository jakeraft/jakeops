#!/usr/bin/env python3
"""Generate frontend TypeScript enums from backend Python Enum definitions.

Parses backend model files using the ast module (no imports needed) and writes
a generated TypeScript file that serves as the single source of truth for
shared enum types.

Usage:
    python3 scripts/sync-types.py
    # or from frontend/
    npm run sync-types
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_MODELS = REPO_ROOT / "backend" / "app" / "domain" / "models"
OUTPUT_FILE = REPO_ROOT / "frontend" / "src" / "types.generated.ts"

# (source_file, class_name) -> (ts_type_name, ts_const_name)
ENUM_MAP: list[tuple[str, str, str, str]] = [
    ("delivery.py", "Phase", "Phase", "PHASES"),
    ("delivery.py", "RunStatus", "RunStatus", "RUN_STATUSES"),
    ("delivery.py", "ExecutorKind", "ExecutorKind", "EXECUTOR_KINDS"),
    ("delivery.py", "Verdict", "Verdict", "VERDICTS"),
    ("delivery.py", "RefRole", "RefRole", "REF_ROLES"),
    ("delivery.py", "RefType", "RefType", "REF_TYPES"),
]


def extract_enum_values(filepath: Path, class_name: str) -> list[str]:
    """Extract string values from a Python str Enum class using AST parsing."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        values: list[str] = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        item.value, ast.Constant
                    ):
                        values.append(item.value.value)
        return values

    print(f"ERROR: Enum '{class_name}' not found in {filepath}", file=sys.stderr)
    sys.exit(1)


def generate_typescript() -> str:
    lines: list[str] = [
        "// Auto-generated from backend domain models. DO NOT EDIT.",
        "// Run: python3 scripts/sync-types.py",
        "",
    ]

    for filename, class_name, ts_type, ts_const in ENUM_MAP:
        filepath = BACKEND_MODELS / filename
        values = extract_enum_values(filepath, class_name)

        # type union
        union = " | ".join(f'"{v}"' for v in values)
        lines.append(f"export type {ts_type} = {union}")

        # const array
        items = ", ".join(f'"{v}"' for v in values)
        lines.append(f"export const {ts_const} = [{items}] as const")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    content = generate_typescript()
    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
