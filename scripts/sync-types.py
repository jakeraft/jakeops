#!/usr/bin/env python3
"""Generate frontend TypeScript types from backend Python domain models.

Parses backend model files using the ast module (no imports needed) and writes
a generated TypeScript file that serves as the single source of truth for
shared enum types and interfaces.

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

# --- Enums: (source_file, python_class, ts_type, ts_const) ---
ENUM_MAP: list[tuple[str, str, str, str]] = [
    ("delivery.py", "Phase", "Phase", "PHASES"),
    ("delivery.py", "RunStatus", "RunStatus", "RUN_STATUSES"),
    ("delivery.py", "ExecutorKind", "ExecutorKind", "EXECUTOR_KINDS"),
    ("delivery.py", "Verdict", "Verdict", "VERDICTS"),
    ("delivery.py", "RefRole", "RefRole", "REF_ROLES"),
    ("delivery.py", "RefType", "RefType", "REF_TYPES"),
    ("source.py", "SourceType", "SourceType", "SOURCE_TYPES"),
    ("agent_run.py", "AgentRunMode", "AgentRunMode", "AGENT_RUN_MODES"),
    ("agent_run.py", "AgentRunStatus", "AgentRunStatus", "AGENT_RUN_STATUSES"),
]

# --- Interfaces: (source_file, python_class, ts_name) ---
# Order matters: referenced types must come before referencing types.
INTERFACE_MAP: list[tuple[str, str, str]] = [
    ("delivery.py", "Ref", "Ref"),
    ("delivery.py", "Session", "Session"),
    ("delivery.py", "Plan", "Plan"),
    ("delivery.py", "ExecutionStats", "ExecutionStats"),
    ("delivery.py", "PhaseRun", "PhaseRun"),
    ("agent_run.py", "AgentRun", "AgentRun"),
    ("source.py", "Source", "Source"),
    ("source.py", "SourceCreate", "SourceCreate"),
    ("source.py", "SourceUpdate", "SourceUpdate"),
]

# Python type -> TypeScript type
PRIMITIVE_MAP: dict[str, str] = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "dict": "Record<string, unknown>",
}

# All known generated type names (enums + interfaces) for reference resolution
KNOWN_TYPES: set[str] = set()


def _init_known_types() -> None:
    for _, _, ts_type, _ in ENUM_MAP:
        KNOWN_TYPES.add(ts_type)
    for _, _, ts_name in INTERFACE_MAP:
        KNOWN_TYPES.add(ts_name)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _parse_file(filepath: Path) -> ast.Module:
    source = filepath.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(filepath))


def _find_class(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


# ---------------------------------------------------------------------------
# Enum extraction
# ---------------------------------------------------------------------------

def extract_enum_values(filepath: Path, class_name: str) -> list[str]:
    tree = _parse_file(filepath)
    cls = _find_class(tree, class_name)
    if cls is None:
        print(f"ERROR: Enum '{class_name}' not found in {filepath}", file=sys.stderr)
        sys.exit(1)

    values: list[str] = []
    for item in cls.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                    values.append(item.value.value)
    return values


# ---------------------------------------------------------------------------
# Type annotation -> TypeScript
# ---------------------------------------------------------------------------

def _resolve_annotation(node: ast.expr) -> tuple[str, bool]:
    """Convert a Python type annotation AST node to (ts_type, is_optional).

    Returns the TypeScript type string and whether the field is optional
    (i.e. the annotation includes `| None`).
    """
    # X | Y  (union via bitwise or, Python 3.10+)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Check for X | None pattern
        if isinstance(node.right, ast.Constant) and node.right.value is None:
            inner_type, _ = _resolve_annotation(node.left)
            return inner_type, True
        if isinstance(node.left, ast.Constant) and node.left.value is None:
            inner_type, _ = _resolve_annotation(node.right)
            return inner_type, True
        # General union: X | Y
        left_type, _ = _resolve_annotation(node.left)
        right_type, _ = _resolve_annotation(node.right)
        return f"{left_type} | {right_type}", False

    # list[X]
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        if node.value.id == "list":
            inner_type, _ = _resolve_annotation(node.slice)
            return f"{inner_type}[]", False

    # Simple name
    if isinstance(node, ast.Name):
        name = node.id
        if name in PRIMITIVE_MAP:
            return PRIMITIVE_MAP[name], False
        if name in KNOWN_TYPES:
            return name, False
        # Fallback: unknown type
        return f"unknown /* {name} */", False

    # None literal
    if isinstance(node, ast.Constant) and node.value is None:
        return "null", False

    return "unknown", False


# ---------------------------------------------------------------------------
# Interface extraction
# ---------------------------------------------------------------------------

def extract_interface_fields(filepath: Path, class_name: str) -> list[tuple[str, str, bool]]:
    """Extract fields from a Pydantic BaseModel class.

    Returns list of (field_name, ts_type, is_optional).
    """
    tree = _parse_file(filepath)
    cls = _find_class(tree, class_name)
    if cls is None:
        print(f"ERROR: Model '{class_name}' not found in {filepath}", file=sys.stderr)
        sys.exit(1)

    fields: list[tuple[str, str, bool]] = []
    for item in cls.body:
        if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
            continue

        field_name = item.target.id
        ts_type, is_optional = _resolve_annotation(item.annotation)

        # Field with default value (including None) is optional
        if item.value is not None and not is_optional:
            if isinstance(item.value, ast.Constant) and item.value.value is None:
                is_optional = True
            elif isinstance(item.value, ast.Call):
                # Field(...) or Field(default=None) etc.
                # Check for default=None in keywords
                for kw in item.value.keywords:
                    if kw.arg == "default" and isinstance(kw.value, ast.Constant) and kw.value.value is None:
                        is_optional = True
                        break
                # Field(default_factory=...) means it has a default, so optional from TS perspective
                for kw in item.value.keywords:
                    if kw.arg == "default_factory":
                        # Has a default but not None-optional, keep required
                        break

        fields.append((field_name, ts_type, is_optional))

    return fields


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def generate_typescript() -> str:
    _init_known_types()

    lines: list[str] = [
        "// Auto-generated from backend domain models. DO NOT EDIT.",
        "// Run: python3 scripts/sync-types.py",
        "",
        "// --- Enums ---",
        "",
    ]

    for filename, class_name, ts_type, ts_const in ENUM_MAP:
        filepath = BACKEND_MODELS / filename
        values = extract_enum_values(filepath, class_name)

        union = " | ".join(f'"{v}"' for v in values)
        lines.append(f"export type {ts_type} = {union}")

        items = ", ".join(f'"{v}"' for v in values)
        lines.append(f"export const {ts_const} = [{items}] as const")
        lines.append("")

    lines.append("// --- Interfaces ---")
    lines.append("")

    for filename, class_name, ts_name in INTERFACE_MAP:
        filepath = BACKEND_MODELS / filename
        fields = extract_interface_fields(filepath, class_name)

        lines.append(f"export interface {ts_name} {{")
        for field_name, ts_type, is_optional in fields:
            opt = "?" if is_optional else ""
            lines.append(f"  {field_name}{opt}: {ts_type}")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    content = generate_typescript()
    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
