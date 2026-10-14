"""Check a demo scene file against the app's code, before recording.

A recording takes several minutes and calls a paid AI model. A single typo in a
button label ("Start Interview" instead of "Start interview") would only fail
halfway through. This script catches that in a second, by checking that every
button, tab, label and dropdown option named in scenes.json actually appears as
a string in the app's Python code.

Usage:
    python scripts/check_scenes.py --scenes demo/scenes.json --app-dir .

Exit code 0 means everything was found; 1 means at least one error.
This file is identical in every project: only demo/scenes.json changes.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# The action types the recorder understands, and the fields each one needs.
# Keep this in sync with ACTIONS in record_demo.py.
REQUIRED_FIELDS = {
    "click_button": ["label"],
    "click_tab": ["label"],
    "select": ["label", "option"],
    "fill": ["label", "text"],
    "type_chat": ["text"],
    "scroll_to": ["text"],
    "wait_text": ["text"],
    "wait_gone": ["text"],
    "pause": ["ms"],
}

# Only waits can be cut: cutting during a click would cut the click itself.
CUTTABLE = {"wait_text", "wait_gone"}

# Folders that hold no app code, so their strings shouldn't count as "found".
SKIP_DIRS = {
    ".venv",
    "venv",
    "env",
    ".git",
    "__pycache__",
    "node_modules",
    "scripts",
    "demo",
}

# Scene ids become file names (voice clips, failure screenshots).
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def collect_string_literals(app_dir: Path) -> set[str]:
    """Return every string constant written in the app's .py files.

    We parse the code with Python's own parser (ast) instead of searching the
    text with regular expressions, so quotes, escapes and implicitly joined
    strings ("Start " "interview") are all handled correctly.
    """
    literals: set[str] = set()
    for path in app_dir.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.relative_to(app_dir).parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as error:
            print(f"  ! Could not read {path}: {error}")
            continue
        for node in ast.walk(tree):
            # Plain strings, and the fixed parts of f-strings, are both Constants.
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)
    return literals


def found_exact(text: str, literals: set[str]) -> bool:
    """True if `text` is written in the code as a complete string.

    Labels must match exactly, because Streamlit shows them exactly as written.
    We ignore leading/trailing spaces and a trailing "..." (used by spinners).
    """
    wanted = text.strip()
    return any(
        lit.strip().rstrip(".").strip() == wanted.rstrip(".").strip()
        for lit in literals
    )


def found_part(text: str, literals: set[str]) -> bool:
    """True if `text` appears inside any string in the code (case-insensitive).

    Used for dropdown options and wait texts, which may be part of a longer
    string, and for options the recorder filters by typing only part of.
    """
    wanted = text.strip().lower()
    return any(wanted in lit.lower() for lit in literals)


def check(scenes_path: Path, app_dir: Path) -> tuple[list[str], list[str]]:
    """Check the scene file. Returns (errors, warnings).

    Errors stop a recording; warnings are things worth a look but often fine,
    such as waiting for text that the AI will write (and so isn't in the code).
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = json.loads(scenes_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"Cannot read {scenes_path}: {error}"], []

    literals = collect_string_literals(app_dir)
    if not literals:
        errors.append(f"No Python code found in {app_dir}")

    # ----- The app block -----
    app = data.get("app", {})
    entry = app.get("entry", "app.py")
    if not (app_dir / entry).exists():
        errors.append(f"app.entry: {entry} doesn't exist in {app_dir}")
    if not isinstance(app.get("env", {}), dict):
        errors.append("app.env must be an object of NAME: value pairs")
    ready = app.get("ready_text")
    if not ready:
        errors.append(
            "app.ready_text is missing: the recorder waits for it before starting"
        )
    elif not found_part(ready, literals):
        errors.append(f'app.ready_text "{ready}" doesn\'t appear in the app code')

    # ----- The scenes -----
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
        return errors, warnings

    seen_ids: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        sid = scene.get("id", f"#{index}")
        where = f"scene {sid}"

        if "id" not in scene:
            errors.append(f"{where}: missing id")
        elif not SAFE_ID.match(sid):
            errors.append(f"{where}: id may only use letters, numbers, - and _")
        elif sid in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(sid)

        for field in ("caption", "voice"):
            if not str(scene.get(field, "")).strip():
                errors.append(f"{where}: missing {field}")

        for number, action in enumerate(scene.get("actions", []), start=1):
            atype = action.get("type")
            at = f"{where}, action {number} ({atype})"

            if atype not in REQUIRED_FIELDS:
                errors.append(
                    f"{at}: unknown type. Use one of: {', '.join(REQUIRED_FIELDS)}"
                )
                continue
            missing = [f for f in REQUIRED_FIELDS[atype] if f not in action]
            if missing:
                errors.append(f"{at}: missing {', '.join(missing)}")
                continue
            if action.get("cut") and atype not in CUTTABLE:
                errors.append(f"{at}: cut only works on wait_text and wait_gone")

            # Labels the user clicks or types into must exist exactly.
            if atype in ("click_button", "click_tab", "select", "fill"):
                if not found_exact(action["label"], literals):
                    errors.append(
                        f'{at}: label "{action["label"]}" not found in the app code'
                    )

            # Dropdown options: the recorder types part of the option to filter,
            # so we only need that part to appear somewhere. Options built from
            # data at runtime can be marked "dynamic": true to skip the check.
            if atype == "select" and not action.get("dynamic"):
                if not found_part(action["option"], literals):
                    errors.append(
                        f'{at}: option "{action["option"]}" not found in the app code '
                        '(add "dynamic": true if the options come from data)'
                    )

            if atype == "type_chat" and action.get("placeholder"):
                if not found_exact(action["placeholder"], literals):
                    errors.append(
                        f'{at}: chat placeholder "{action["placeholder"]}" not found'
                    )

            # Waits and scrolls often target AI-written text, which can't be in
            # the code. That's fine, so it's only a warning.
            if atype in ("wait_text", "wait_gone", "scroll_to"):
                if not found_part(action["text"], literals):
                    warnings.append(
                        f'{at}: "{action["text"]}" isn\'t in the code '
                        "(fine if the AI writes it)"
                    )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scenes", default="demo/scenes.json", type=Path)
    parser.add_argument("--app-dir", default=".", type=Path)
    args = parser.parse_args()

    errors, warnings = check(args.scenes, args.app_dir.resolve())

    for warning in warnings:
        print(f"  ~ {warning}")
    for error in errors:
        print(f"  x {error}")
    if errors:
        print(
            f"\n{len(errors)} error(s): fix scenes.json (or the app) before recording."
        )
        return 1
    print(f"\nScene file OK ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
