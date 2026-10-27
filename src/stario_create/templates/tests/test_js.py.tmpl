import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALL = re.compile(r"(?<![\w.$])app\.([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*)|(?=\s*\())")


def expressions() -> set[tuple[str, str | None]]:
    calls: set[tuple[str, str | None]] = set()
    for path in (ROOT / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                calls |= {(m[1], m[2]) for m in CALL.finditer(node.value)}
    return calls


def test_every_app_call_has_its_function():
    missing = []
    for name, method in sorted(expressions(), key=str):
        js = ROOT / "static/js" / f"{name}.js"
        text = js.read_text() if js.is_file() else ""
        if not re.search(rf"\bapp\.{name}\s*=", text):
            missing.append(f"app.{name} (static/js/{name}.js)")
        elif method and not re.search(rf"\b{method}\s*[(:]", text):
            missing.append(f"app.{name}.{method}")
    assert not missing, missing
