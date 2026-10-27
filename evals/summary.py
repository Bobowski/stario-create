"""summary.py [GLOB] -> one row per run with the rubric that matters."""

import json
import os
import sys
from pathlib import Path

pat = sys.argv[1] if len(sys.argv) > 1 else "*"
cols = [
    ("ok", lambda d: d["check_all"]),
    ("fail", lambda d: ",".join(k for k, v in d["check"].items() if not v) or "-"),
    ("tests", lambda d: d.get("tests_passed")),
    ("dirs", lambda d: ",".join(d["feature_dirs"])),
    ("core", lambda d: d["has_core_files"]),
    ("reg", lambda d: d["registered_in_main"]),
    ("page", lambda d: d.get("page_class")),
    ("fact", lambda d: len(d.get("handler_factories", []))),
    ("layers", lambda d: ",".join(d.get("layer_classes", [])) or "-"),
    ("view", lambda d: d.get("view_from_query")),
    ("live", lambda d: d["has_live_route"]),
    ("init", lambda d: d["init_live_retry_always"]),
    ("alive", lambda d: d["c_alive"]),
    ("paints", lambda d: ",".join(d["commands_that_render"]) or "-"),
    ("priv", lambda d: ",".join(d.get("private_posts", [])) or "-"),
    ("store", lambda d: d["store"]),
    ("task", lambda d: d["create_task"]),
    ("ind", lambda d: d["indicator"]),
    ("pres", lambda d: d["preserve_open"]),
    ("globals", lambda d: ",".join(Path(f).name for f in d["module_mutable_state"]) or "-"),
    ("env", lambda d: ",".join(d["environ_outside_config"]) or "-"),
    ("outside", lambda d: ",".join(d["files_outside_features"]) or "-"),
    ("nav", lambda d: d.get("navigate")),
    ("redir", lambda d: d.get("redirect_in_features")),
    ("pkgs", lambda d: ",".join(d.get("non_feature_pkgs", [])) or "-"),
    ("sec", lambda d: d.get("seconds")),
    ("ktok", lambda d: d.get("ktok")),
    (
        "diff",
        lambda d: (
            d["diff"]
            .replace(" files changed", "f")
            .replace(" insertions(+)", "+")
            .replace(" deletions(-)", "-")
        ),
    ),
]
rows = []
runs_dir = Path(os.environ.get("EVAL_DIR", "/tmp/stario-eval")) / "runs"
for f in sorted(runs_dir.glob(f"{pat}/.eval-check.json")):
    try:
        d = json.loads(f.read_text())
    except json.JSONDecodeError:
        rows.append([f.parent.name, "BROKEN JSON"])
        continue
    rows.append([f.parent.name.replace("-swe-2-high", "")] + [str(fn(d)) for _, fn in cols])
head = ["run"] + [c for c, _ in cols]
w = [max(len(r[i]) if i < len(r) else 0 for r in [*rows, head]) for i in range(len(head))]
for r in [head, *rows]:
    print("  ".join(c.ljust(w[i]) for i, c in enumerate(r)))
