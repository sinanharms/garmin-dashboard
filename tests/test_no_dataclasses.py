import ast
from pathlib import Path


def test_application_source_has_no_dataclass_imports_or_decorators() -> None:
    source_root = Path(__file__).parents[1] / "src/garmin_dashboard"
    violations: list[str] = []

    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "dataclasses":
                violations.append(f"{path}: dataclasses import")
            elif isinstance(node, ast.Import) and any(alias.name == "dataclasses" for alias in node.names):
                violations.append(f"{path}: dataclasses import")
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    target = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if isinstance(target, ast.Name) and target.id == "dataclass":
                        violations.append(f"{path}: @dataclass")
                    elif isinstance(target, ast.Attribute) and target.attr == "dataclass":
                        violations.append(f"{path}: @*.dataclass")

    assert not violations, "\n".join(violations)
