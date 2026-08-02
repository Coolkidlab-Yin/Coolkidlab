from __future__ import annotations

import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_skills.py"
    spec = importlib.util.spec_from_file_location("validate_skills_test_target", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


class ValidatorRobustnessTests(unittest.TestCase):
    def test_guidance_boundary_is_a_required_quality_heading(self) -> None:
        pattern = VALIDATOR.QUALITY_CHECKS["Agent 引導邊界"]
        headings = [heading for heading, _ in VALIDATOR.markdown_sections(
            "## 定位：提供骨架，由 Agent 補完\n\n說明現場判斷。\n"
        )]
        self.assertTrue(any(pattern.search(heading) for heading in headings))
        body_only = VALIDATOR.markdown_sections(
            "## 一般說明\n\n這裡提到引導邊界，但標題沒有表達。\n"
        )
        self.assertFalse(any(pattern.search(heading) for heading, _ in body_only))

    def test_frontmatter_requires_an_exact_closing_delimiter(self) -> None:
        malformed = "---\nname: example\ndescription: long enough description\n---oops\n# Body\n"
        self.assertEqual({}, VALIDATOR.frontmatter(malformed))

    def test_frontmatter_accepts_quoted_scalar_metadata(self) -> None:
        quoted = '---\nname: "example-skill"\ndescription: \'A useful skill description\'\n---\n'
        self.assertEqual(
            {"name": "example-skill", "description": "A useful skill description"},
            VALIDATOR.frontmatter(quoted),
        )

    def test_candidate_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "README.md"
            candidate.write_text("candidate", encoding="utf-8")
            real_lstat = Path.lstat

            def simulated_lstat(path: Path):
                if path == candidate:
                    return mock.Mock(st_mode=stat.S_IFLNK)
                return real_lstat(path)

            try:
                VALIDATOR.configure_root(root)
                with (
                    mock.patch.object(Path, "lstat", autospec=True, side_effect=simulated_lstat),
                    self.assertRaises(VALIDATOR.ValidationInputError),
                ):
                    VALIDATOR.validate_candidate_file(candidate)
            finally:
                VALIDATOR.configure_root(VALIDATOR.DEFAULT_ROOT)

    def test_oversized_candidate_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "large.md"
            candidate.write_bytes(b"x" * 11)
            try:
                VALIDATOR.configure_root(root)
                with (
                    mock.patch.object(VALIDATOR, "MAX_CANDIDATE_FILE_BYTES", 10),
                    self.assertRaises(VALIDATOR.ValidationInputError),
                ):
                    VALIDATOR.validate_candidate_file(candidate)
            finally:
                VALIDATOR.configure_root(VALIDATOR.DEFAULT_ROOT)

    def test_non_string_json_fields_report_errors_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".claude-plugin").mkdir()
            (root / "evals").mkdir()
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(
                    {
                        "description": 7,
                        "plugins": [
                            {"name": ["not", "a", "string"], "source": "./plugins/x", "description": 9}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "evals" / "skill-scenarios.json").write_text(
                json.dumps({"scenarios": [{"skill_name": ["bad"], "should_trigger": True, "prompt": 1}]}),
                encoding="utf-8",
            )
            (root / "README.md").write_text("# README\n", encoding="utf-8")
            (root / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")

            argv = ["validate_skills.py", "--root", str(root)]
            try:
                with mock.patch.object(sys, "argv", argv):
                    self.assertEqual(1, VALIDATOR.main())
            finally:
                VALIDATOR.configure_root(VALIDATOR.DEFAULT_ROOT)


if __name__ == "__main__":
    unittest.main()
