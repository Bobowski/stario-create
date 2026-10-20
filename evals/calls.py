"""calls.py RUN_DIR -> the tool calls of one run: name and the key argument. Plus token totals when present."""

import json
import sys
from pathlib import Path

d = json.loads((Path(sys.argv[1]) / ".eval-transcript.md").read_text())
steps = d.get("steps") or d.get("trajectory") or []
n = 0
for s in steps:
    for tc in s.get("tool_calls") or []:
        n += 1
        name = tc.get("function_name") or tc.get("name") or (tc.get("function") or {}).get("name")
        args = tc.get("arguments") or (tc.get("function") or {}).get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"raw": args[:80]}
        key = (
            args.get("file_path")
            or args.get("skill")
            or args.get("command")
            or args.get("pattern")
            or ""
        )
        print(f"{n:3} {name:10} {str(key)[:110]}")
fm = d.get("final_metrics") or {}
print("metrics:", {k: v for k, v in fm.items() if "token" in k or "cost" in k or "steps" in k})
