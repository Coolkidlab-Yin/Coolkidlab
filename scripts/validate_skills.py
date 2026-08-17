#!/usr/bin/env python3
"""Validate Coolkidlab marketplace structure and learning-readiness.

The validator intentionally uses only Python's standard library so contributors
and CI can run it before installing any plugin-specific dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = DEFAULT_ROOT
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
EVALS_PATH = ROOT / "evals" / "skill-scenarios.json"
MAX_CANDIDATE_FILE_BYTES = 2 * 1024 * 1024
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
LOCAL_LINK = re.compile(
    r"\[[^\]]+\]\(\s*(?:<([^>]+)>|((?!https?://|mailto:|#)[^)\s]+))"
    r"(?:\s+['\"][^'\"]+['\"])?\s*\)"
)
# 500 行是預設上限。豁免名單:SKILL.md 本身就是對外產品本體的 skill,
# 放行到「個別上限」而不是無條件——超過個別上限照樣紅燈,理由必須寫在這裡。
LINE_BUDGETS = {
    # trip-guide 的 SKILL.md 同時是「手機貼文模式」的完整產品:
    # 使用者只拿得到這一份,內容下放 references 等於精簡版缺料。
    # 2026-08-17 本人裁定放寬,而非瘦身。
    "trip-guide": 800,
}

QUALITY_CHECKS = {
    "Agent 引導邊界": re.compile(
        r"(?:引導邊界|定位[:：].*(?:引導|骨架|判斷框架|Agent))"
    ),
    "開始前的輸入或執行契約": re.compile(r"(?:開始前|執行契約|準備|輸入)"),
    "明確產出": re.compile(r"(?:產出|輸出|會得到)"),
    "完成或驗收定義": re.compile(r"(?:完成定義|完成檢查|驗收|成功判準|檢查點)"),
    "限制或安全邊界": re.compile(r"(?:侷限|限制|安全|紅線|隱私)"),
    "來源與時效": re.compile(r"(?:來源|參考|時效)"),
}


class ValidationInputError(OSError):
    """Candidate input is missing, unsafe, not regular, or too large."""


def validate_candidate_file(path: Path) -> Path:
    """Reject symlinks, escapes, special files and oversized untrusted inputs."""
    root = ROOT.resolve()
    absolute = Path(os.path.abspath(path))
    if not absolute.is_relative_to(root):
        raise ValidationInputError(f"path escapes validation root: {path}")

    current = root
    for part in absolute.relative_to(root).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise ValidationInputError(f"cannot stat candidate path: {path}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationInputError(f"symlink is not allowed in candidate input: {path}")

    metadata = absolute.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValidationInputError(f"candidate input is not a regular file: {path}")
    if metadata.st_size > MAX_CANDIDATE_FILE_BYTES:
        raise ValidationInputError(
            f"candidate input exceeds {MAX_CANDIDATE_FILE_BYTES} bytes: {path}"
        )
    resolved = absolute.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValidationInputError(f"resolved candidate path escapes validation root: {path}")
    return resolved


def validate_candidate_directory(path: Path) -> Path:
    """Reject directory symlinks and escapes before enumerating untrusted entries."""
    root = ROOT.resolve()
    absolute = Path(os.path.abspath(path))
    if not absolute.is_relative_to(root):
        raise ValidationInputError(f"directory escapes validation root: {path}")
    current = root
    for part in absolute.relative_to(root).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise ValidationInputError(f"cannot stat candidate directory: {path}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationInputError(f"symlink is not allowed in candidate directory: {path}")
    if not stat.S_ISDIR(absolute.lstat().st_mode):
        raise ValidationInputError(f"candidate path is not a directory: {path}")
    resolved = absolute.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValidationInputError(f"resolved candidate directory escapes validation root: {path}")
    return resolved


def read_candidate_text(path: Path) -> str:
    safe_path = validate_candidate_file(path)
    return safe_path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read_candidate_text(path))


def configure_root(root: Path) -> None:
    """Point all validation at a candidate tree without importing or executing it."""
    global ROOT, MARKETPLACE_PATH, EVALS_PATH
    ROOT = root.resolve()
    MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
    EVALS_PATH = ROOT / "evals" / "skill-scenarios.json"


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    block = lines[1:end]
    result: dict[str, str] = {}
    current_key: str | None = None
    for line in block:
        match = re.match(r"^([a-zA-Z][\w-]*):\s*(.*)$", line)
        if match:
            current_key = match.group(1)
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            elif len(value) >= 2 and value[0] == value[-1] == "'":
                value = value[1:-1].replace("''", "'")
            result[current_key] = "" if value in {">", "|"} else value
        elif current_key and line.startswith((" ", "\t")):
            result[current_key] = f"{result[current_key]} {line.strip()}".strip()
    return result


def markdown_sections(text: str) -> list[tuple[str, str]]:
    """Return real level 2-3 headings and their non-fenced section bodies."""
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    current: tuple[str, list[str]] | None = None
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if heading:
            current = (heading.group(1), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    return [(heading, "\n".join(body).strip()) for heading, body in sections]


def validate_local_links(markdown_path: Path, errors: list[str]) -> None:
    try:
        text = read_candidate_text(markdown_path)
    except (OSError, UnicodeError) as exc:
        try:
            label = markdown_path.relative_to(ROOT)
        except ValueError:
            label = markdown_path
        errors.append(f"{label}: cannot read Markdown as UTF-8: {exc}")
        return
    allowed_root = ROOT
    if "plugins" in markdown_path.parts:
        for parent in markdown_path.parents:
            if (parent / ".claude-plugin" / "plugin.json").is_file():
                allowed_root = parent
                break
    for angle_target, plain_target in LOCAL_LINK.findall(text):
        raw_target = angle_target or plain_target
        raw_target = urllib.parse.unquote(raw_target)
        if raw_target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = raw_target.split("#", 1)[0]
        if not target or target.startswith(("/", "\\")):
            continue
        resolved = (markdown_path.parent / target).resolve()
        if not resolved.is_relative_to(allowed_root):
            errors.append(
                f"{markdown_path.relative_to(ROOT)}: local link escapes its distributable root -> {raw_target}"
            )
            continue
        if not resolved.exists():
            errors.append(f"{markdown_path.relative_to(ROOT)}: broken local link -> {raw_target}")


def validate_python(scripts: list[Path], errors: list[str], run_help: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="coolkidlab-validate-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, script in enumerate(scripts):
            label = script.relative_to(ROOT)
            try:
                safe_script = validate_candidate_file(script)
                py_compile.compile(
                    str(safe_script),
                    cfile=str(temp_root / f"{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as exc:
                errors.append(f"{label}: Python compile failed: {exc.msg}")
                continue
            except (OSError, UnicodeError) as exc:
                errors.append(f"{label}: unsafe or unreadable Python input: {exc}")
                continue

            if not run_help:
                continue
            try:
                completed = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=script.parent,
                    capture_output=True,
                    timeout=20,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                errors.append(f"{label}: --help could not run: {exc}")
                continue
            if completed.returncode != 0:
                raw_detail = completed.stderr or completed.stdout
                detail = raw_detail.decode("utf-8", errors="replace").strip().splitlines()
                errors.append(f"{label}: --help exited {completed.returncode}: {detail[:1]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Coolkidlab plugin marketplace")
    parser.add_argument(
        "--runtime-smoke",
        action="store_true",
        help="also execute each bundled Python script with --help; use only on trusted code",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="candidate repository root; the validator itself may live in a separate trusted checkout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.root.is_symlink() or not args.root.is_dir():
        print(f"ERROR: validation root is not a directory: {args.root}", file=sys.stderr)
        return 1
    configure_root(args.root)
    if args.runtime_smoke and ROOT != DEFAULT_ROOT.resolve():
        print("ERROR: --runtime-smoke cannot execute a separate candidate root", file=sys.stderr)
        return 1
    errors: list[str] = []
    warnings: list[str] = []

    try:
        marketplace = load_json(MARKETPLACE_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {MARKETPLACE_PATH}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(marketplace, dict):
        print("ERROR: marketplace root must be a JSON object", file=sys.stderr)
        return 1

    marketplace_description = marketplace.get("description")
    if not isinstance(marketplace_description, str) or not marketplace_description.strip():
        errors.append(".claude-plugin/marketplace.json: marketplace description is required")

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        errors.append(".claude-plugin/marketplace.json: plugins must be a non-empty list")
        entries = []

    seen_names: set[str] = set()
    skill_count = 0
    python_scripts: list[Path] = []
    try:
        plugins_root = validate_candidate_directory(ROOT / "plugins")
    except OSError as exc:
        errors.append(f"plugins: unsafe or unreadable directory: {exc}")
        plugins_root = ROOT / "plugins"
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("marketplace plugin entries must be JSON objects")
            continue
        name = entry.get("name")
        source = entry.get("source")
        description = entry.get("description")
        if not isinstance(name, str):
            errors.append(f"marketplace plugin name must be a string: {name!r}")
            continue
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(f"marketplace plugin name is not kebab-case: {name!r}")
        if name in seen_names:
            errors.append(f"duplicate marketplace plugin name: {name}")
        seen_names.add(name)
        if not isinstance(source, str) or not source.startswith("./plugins/"):
            errors.append(f"{name}: source must stay inside ./plugins/")
            continue
        if not isinstance(description, str) or len(description.strip()) < 20:
            errors.append(f"{name}: marketplace description is missing or too vague")

        plugin_candidate = ROOT / source
        try:
            plugin_root = validate_candidate_directory(plugin_candidate)
        except OSError as exc:
            errors.append(f"{name}: unsafe or unreadable plugin directory: {exc}")
            continue
        if not plugin_root.is_relative_to(plugins_root) or plugin_root == plugins_root:
            errors.append(f"{name}: resolved source escapes ./plugins/: {source}")
            continue
        manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
        try:
            manifest = load_json(manifest_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{manifest_path.relative_to(ROOT)}: invalid JSON: {exc}")
            continue
        if not isinstance(manifest, dict):
            errors.append(f"{manifest_path.relative_to(ROOT)}: root must be a JSON object")
            continue

        manifest_name = manifest.get("name")
        manifest_description = manifest.get("description")
        if not isinstance(manifest_name, str) or manifest_name != name:
            errors.append(f"{name}: manifest name does not match marketplace entry")
        if not isinstance(manifest_description, str) or len(manifest_description.strip()) < 20:
            errors.append(f"{name}: plugin.json description is missing or too vague")
        version = manifest.get("version", "")
        if not isinstance(version, str) or not SEMVER.fullmatch(version):
            errors.append(f"{name}: plugin.json needs a semantic version, got {version!r}")
        if manifest.get("license") != "MIT":
            errors.append(f"{name}: plugin.json license must be MIT")

        skill_path = plugin_root / "skills" / name / "SKILL.md"
        skill_count += 1
        try:
            skill_text = read_candidate_text(skill_path)
        except (OSError, UnicodeError) as exc:
            errors.append(f"{skill_path.relative_to(ROOT)}: cannot read SKILL.md as UTF-8: {exc}")
            continue
        metadata = frontmatter(skill_text)
        if metadata.get("name") != name:
            errors.append(f"{skill_path.relative_to(ROOT)}: frontmatter name must be {name}")
        if len(metadata.get("description", "").strip()) < 40:
            errors.append(f"{skill_path.relative_to(ROOT)}: description is missing or too vague")
        line_count = len(skill_text.splitlines())
        line_budget = LINE_BUDGETS.get(name, 500)
        if line_count > line_budget:
            errors.append(f"{skill_path.relative_to(ROOT)}: {line_count} lines exceeds the {line_budget}-line target")
        sections = markdown_sections(skill_text)
        for label, pattern in QUALITY_CHECKS.items():
            matching_bodies = [body for heading, body in sections if pattern.search(heading)]
            if not matching_bodies:
                errors.append(f"{skill_path.relative_to(ROOT)}: missing quality section: {label}")
            elif not any(len(re.sub(r"\s+", "", body)) >= 20 for body in matching_bodies):
                errors.append(f"{skill_path.relative_to(ROOT)}: quality section is empty or too thin: {label}")
        # (?<!-)/(?!-):CLI 旗標名(--todo)不是待辦標記,別誤報。
        if re.search(r"(?<!-)\b(?:TODO|TBD)\b(?!-)", skill_text, re.IGNORECASE):
            warnings.append(f"{skill_path.relative_to(ROOT)}: contains TODO/TBD")
        validate_local_links(skill_path, errors)

        scripts_dir = plugin_root / "skills" / name / "scripts"
        if os.path.lexists(scripts_dir):
            try:
                safe_scripts_dir = validate_candidate_directory(scripts_dir)
            except OSError as exc:
                errors.append(f"{scripts_dir.relative_to(ROOT)}: unsafe scripts directory: {exc}")
            else:
                python_scripts.extend(
                    child for child in safe_scripts_dir.iterdir() if child.name.endswith(".py")
                )

    if skill_count != len(entries):
        errors.append(f"marketplace declares {len(entries)} plugins but only {skill_count} valid skills were found")

    try:
        eval_data = load_json(EVALS_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"evals/skill-scenarios.json: cannot load eval scenarios: {exc}")
        eval_data = {}
    if not isinstance(eval_data, dict):
        errors.append("evals/skill-scenarios.json: root must be a JSON object")
        scenarios = []
    else:
        scenarios = eval_data.get("scenarios", [])
    if not isinstance(scenarios, list):
        errors.append("evals/skill-scenarios.json: scenarios must be a list")
        scenarios = []
    eval_coverage: dict[str, set[bool]] = {name: set() for name in seen_names}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("evals/skill-scenarios.json: each scenario must be an object")
            continue
        scenario_name = scenario.get("skill_name")
        should_trigger = scenario.get("should_trigger")
        if not isinstance(scenario_name, str):
            errors.append(f"evals/skill-scenarios.json: skill_name must be a string: {scenario_name!r}")
            continue
        if scenario_name not in seen_names:
            errors.append(f"evals/skill-scenarios.json: unknown skill_name {scenario_name!r}")
            continue
        if not isinstance(should_trigger, bool):
            errors.append(f"{scenario_name}: eval should_trigger must be true or false")
            continue
        prompt = scenario.get("prompt")
        if not isinstance(prompt, str) or len(prompt.strip()) < 20:
            errors.append(f"{scenario_name}: eval prompt is missing or unrealistically short")
        if should_trigger:
            criteria = scenario.get("success_criteria")
            if not isinstance(criteria, list) or not criteria or not all(
                isinstance(item, str) and item.strip() for item in criteria
            ):
                errors.append(f"{scenario_name}: trigger eval needs non-empty success_criteria")
        else:
            expected_route = scenario.get("expected_route")
            if not isinstance(expected_route, str) or len(expected_route.strip()) < 10:
                errors.append(f"{scenario_name}: near-miss eval needs a concrete expected_route")
        eval_coverage[scenario_name].add(should_trigger)
    for name, coverage in eval_coverage.items():
        if coverage != {False, True}:
            errors.append(f"{name}: evals need at least one trigger and one near-miss scenario")

    for markdown_path in (ROOT / "README.md", ROOT / "CONTRIBUTING.md"):
        validate_local_links(markdown_path, errors)

    python_scripts.sort()
    validate_python(python_scripts, errors, run_help=args.runtime_smoke)

    print(f"Validated {skill_count} skills and {len(python_scripts)} Python scripts.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    print("All marketplace checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
