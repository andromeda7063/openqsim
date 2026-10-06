#!/usr/bin/env python3
"""Requirements Traceability Report Generator.

Parses docs/requirements.md for FR, NFR, and LC requirements and correlates them
with @pytest.mark.req markers collected across all project test suites without
executing tests.

Generates docs/traceability-report.md and prints summary to stdout.
"""

from __future__ import annotations

import io
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest


class ReqMarkerCollector:
    """Pytest plugin collecting @pytest.mark.req markers during collection."""

    def __init__(self) -> None:
        self.req_to_tests: dict[str, list[str]] = defaultdict(list)
        self.collected_test_count = 0

    def pytest_collection_modifyitems(
        self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        self.collected_test_count = len(items)
        for item in items:
            for mark in item.iter_markers("req"):
                for arg in mark.args:
                    if isinstance(arg, str):
                        self.req_to_tests[arg].append(item.nodeid)


def parse_requirements(requirements_path: Path) -> dict[str, dict[str, str]]:
    """Parse FR, NFR, and LC definitions from requirements.md."""
    text = requirements_path.read_text(encoding="utf-8")
    requirements: dict[str, dict[str, str]] = {}

    # 1. Parse table rows: ID | Requirement text | Priority
    # Matches patterns like:
    # FR-1.1 The system shall allow the user to create a new empty circuit. High
    table_pattern = re.compile(
        r"^\s*(FR-\d+\.\d+|NFR-\d+\.\d+)\b(.*?)(High|Medium|Low)\s*$",
        re.MULTILINE,
    )
    for match in table_pattern.finditer(text):
        req_id = match.group(1).strip()
        desc = re.sub(r"\s+", " ", match.group(2).strip())
        priority = match.group(3).strip()
        requirements[req_id] = {
            "id": req_id,
            "description": desc,
            "priority": priority,
            "type": "FR" if req_id.startswith("FR-") else "NFR",
        }

    # 2. Parse LC rules: **LC-n.** Description
    lc_pattern = re.compile(r"\*\*LC-(\d+)\.\*\*\s*(.*?)(?=\n\n|\n\*\*LC-|\Z)", re.DOTALL)
    for match in lc_pattern.finditer(text):
        lc_num = match.group(1).strip()
        req_id = f"LC-{lc_num}"
        raw_desc = match.group(2).strip()
        desc = re.sub(r"\s+", " ", raw_desc)
        requirements[req_id] = {
            "id": req_id,
            "description": desc,
            "priority": "High",
            "type": "LC",
        }

    return requirements


def collect_test_markers(test_dirs: list[str]) -> tuple[dict[str, list[str]], int]:
    """Collect @pytest.mark.req markers using pytest collection hook."""
    collector = ReqMarkerCollector()
    # Suppress pytest stdout during collection
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        pytest.main(["--collect-only", "-q", *test_dirs], plugins=[collector])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return dict(collector.req_to_tests), collector.collected_test_count


def generate_report(
    requirements: dict[str, dict[str, str]],
    req_to_tests: dict[str, list[str]],
    test_count: int,
    output_path: Path,
) -> None:
    """Generate Markdown traceability report."""
    total_reqs = len(requirements)
    high_reqs = [r for r, d in requirements.items() if d["priority"] == "High"]
    med_reqs = [r for r, d in requirements.items() if d["priority"] == "Medium"]

    high_covered = [r for r in high_reqs if r in req_to_tests and len(req_to_tests[r]) > 0]
    med_covered = [r for r in med_reqs if r in req_to_tests and len(req_to_tests[r]) > 0]
    all_covered = [r for r in requirements if r in req_to_tests and len(req_to_tests[r]) > 0]

    high_missing = [r for r in high_reqs if r not in req_to_tests or not req_to_tests[r]]
    med_missing = [r for r in med_reqs if r not in req_to_tests or not req_to_tests[r]]

    lines: list[str] = [
        "# Requirements Traceability Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Total Requirements Defined**: {total_reqs}",
        f"  - **High Priority (FR, NFR, LC)**: {len(high_reqs)}",
        f"  - **Medium Priority**: {len(med_reqs)}",
        f"- **Total Tests Collected**: {test_count}",
        f"- **Requirements Covered**: {len(all_covered)} / {total_reqs} ({len(all_covered) / total_reqs * 100:.1f}%)",
        f"- **High-Priority Coverage**: {len(high_covered)} / {len(high_reqs)} ({len(high_covered) / len(high_reqs) * 100:.1f}%)",
        f"- **Medium-Priority Coverage**: {len(med_covered)} / {len(med_reqs)} ({len(med_covered) / len(med_reqs) * 100:.1f}%)",
        "",
        "## 2. Coverage Gaps",
        "",
        "### High-Priority Requirements with NO Test",
        "",
    ]

    if high_missing:
        lines.append(
            f"**WARNING: {len(high_missing)} High-priority requirements lack automated test coverage:**"
        )
        lines.append("")
        for req_id in sorted(high_missing):
            req_info = requirements[req_id]
            lines.append(f"- **{req_id}**: {req_info['description']}")
        lines.append("")
    else:
        lines.append(
            "**None.** All High-priority functional requirements, non-functional requirements, "
            "and lifecycle rules (100%) have automated test coverage."
        )
        lines.append("")

    lines.append("### Medium-Priority Requirements with NO Test")
    lines.append("")
    if med_missing:
        for req_id in sorted(med_missing):
            req_info = requirements[req_id]
            lines.append(f"- **{req_id}**: {req_info['description']}")
        lines.append("")
    else:
        lines.append(
            "**None.** All Medium-priority requirements (100%) have automated test coverage."
        )
        lines.append("")

    lines.extend(
        [
            "## 3. Full Traceability Matrix",
            "",
            "| Requirement ID | Priority | Description | Test Count | Covering Tests |",
            "|---|---|---|---|---|",
        ]
    )

    def sort_key(item: str) -> tuple[int, int, str]:
        # Sort by type (FR, NFR, LC), then numerical parts
        prefix, _, rest = item.partition("-")
        prio_order = {"FR": 1, "NFR": 2, "LC": 3}.get(prefix, 4)
        if "." in rest:
            maj, min_ = rest.split(".", 1)
            return (prio_order, int(maj), min_)
        if rest.isdigit():
            return (prio_order, int(rest), "")
        return (prio_order, 999, rest)

    for req_id in sorted(requirements.keys(), key=sort_key):
        req_info = requirements[req_id]
        prio = req_info["priority"]
        desc = req_info["description"]
        # Escape pipe symbols in descriptions
        clean_desc = desc.replace("|", "\\|")
        if len(clean_desc) > 80:
            clean_desc = clean_desc[:77] + "..."

        tests = req_to_tests.get(req_id, [])
        test_cnt = len(tests)
        if test_cnt == 0:
            test_str = "*None*"
        elif test_cnt <= 3:
            # Short list
            test_str = "<br>".join(f"`{t}`" for t in tests)
        else:
            test_str = f"{test_cnt} tests (e.g. `{tests[0]}`<br>`{tests[1]}`<br>`{tests[2]}` ...)"

        lines.append(f"| **{req_id}** | {prio} | {clean_desc} | {test_cnt} | {test_str} |")

    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    req_file = repo_root / "docs" / "requirements.md"
    output_file = repo_root / "docs" / "traceability-report.md"

    if not req_file.exists():
        print(f"Error: Requirements file not found: {req_file}", file=sys.stderr)
        return 1

    requirements = parse_requirements(req_file)
    test_dirs = ["libqsim/tests", "qsim-gui/tests", "tests/acceptance"]
    req_to_tests, test_count = collect_test_markers(test_dirs)

    generate_report(requirements, req_to_tests, test_count, output_file)

    high_reqs = [r for r, d in requirements.items() if d["priority"] == "High"]
    high_missing = [r for r in high_reqs if r not in req_to_tests or not req_to_tests[r]]

    print("==================================================")
    print("TRACEABILITY REPORT SUMMARY")
    print("==================================================")
    print(f"Total Requirements Parsed: {len(requirements)}")
    print(f"Total Tests Collected:     {test_count}")
    print(f"High-Priority Requirements: {len(high_reqs)}")
    print(f"High-Priority Missing:      {len(high_missing)}")
    if high_missing:
        print(f"High-Priority Gaps: {high_missing}")
    else:
        print("High-Priority Gaps: NONE (100% covered)")
    print(f"Traceability Report Written: {output_file}")
    print("==================================================")

    return 0 if not high_missing else 2


if __name__ == "__main__":
    sys.exit(main())
