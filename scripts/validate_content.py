#!/usr/bin/env python3
"""Validate Markdown structure, local links, and mock-exam completeness."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def error(path: Path, message: str) -> None:
    ERRORS.append(f"{path.relative_to(ROOT)}: {message}")


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def validate_markdown(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Enforce final newlines for files introduced by this update. Legacy files
    # are checked for structural breakage without forcing unrelated rewrites.
    if "2026年10月" in path.parts or path.name in {
        "2026下半年备考总指南.md",
        "系统分析师学习路线.md",
        "网络规划设计师学习路线.md",
        "系统规划与管理师学习路线.md",
    }:
        if not text.endswith("\n"):
            error(path, "missing final newline")
    if text.count("```") % 2:
        error(path, "unbalanced fenced code block")
    if "�" in text:
        error(path, "contains Unicode replacement character")
    if re.search(r"(?m)^null$", text):
        error(path, "contains standalone null")

    for destination in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        destination = destination.strip().split("#", 1)[0]
        if not destination or destination.startswith(
            ("http://", "https://", "mailto:", "javascript:")
        ):
            continue
        target = (path.parent / destination).resolve()
        if not target.exists():
            error(path, f"broken local link: {destination}")


def numbered_questions(text: str) -> set[int]:
    numbers = re.findall(r"(?m)^#{2,3} 第(\d+)题\s*$", text)
    return {int(number) for number in numbers}


def normalized_stem(stem: str) -> str:
    """Remove training prefixes so cosmetic rewrites cannot hide duplicates."""
    return re.sub(
        r"^(基础判断：|场景判断：某组织正在实施相关项目，|复盘判断：在一次评审中，)",
        "",
        stem.strip(),
    )


def validate_mock_set(path: Path) -> None:
    expected = {
        "综合知识_题目.md",
        "综合知识_答案.md",
        "案例分析_题目.md",
        "案例分析_答案.md",
        "论文_题目.md",
        "论文_答案.md",
    }
    actual = {item.name for item in path.glob("*.md")}
    missing = expected - actual
    if missing:
        error(path, f"missing mock files: {', '.join(sorted(missing))}")
        return

    questions = numbered_questions((path / "综合知识_题目.md").read_text())
    answers = numbered_questions((path / "综合知识_答案.md").read_text())
    expected_numbers = set(range(1, 76))
    if questions != expected_numbers:
        error(path, f"question numbers are not exactly 1-75: found {len(questions)}")
    if answers != expected_numbers:
        error(path, f"answer numbers are not exactly 1-75: found {len(answers)}")
    if questions != answers:
        error(path, "question and answer numbers differ")

    question_text = (path / "综合知识_题目.md").read_text()
    stems = re.findall(
        r"(?ms)^## 第\d+题\s*\n\n(.+?)\n\n(?:- A\.|\*\*选项\*\*)",
        question_text,
    )
    if len(stems) == 75:
        normalized = [normalized_stem(stem) for stem in stems]
        unique_ratio = len(set(normalized)) / len(normalized)
        if unique_ratio < 0.8:
            error(path, f"question-stem diversity too low: {len(set(normalized))}/75")


def validate_2026_october_mocks() -> None:
    expected_sets = {
        "系统架构设计师": 5,
        "系统分析师": 2,
        "网络规划设计师": 2,
        "系统规划与管理师": 2,
    }
    mock_root = ROOT / "模拟题"
    for qualification, count in expected_sets.items():
        directory = mock_root / qualification / "2026年10月"
        sets = sorted(path for path in directory.glob("模拟卷*") if path.is_dir())
        if len(sets) != count:
            error(directory, f"expected {count} sets, found {len(sets)}")
        for mock_set in sets:
            validate_mock_set(mock_set)


def main() -> int:
    for path in markdown_files():
        validate_markdown(path)
    validate_2026_october_mocks()

    if ERRORS:
        print(f"content validation failed: {len(ERRORS)} error(s)")
        for item in ERRORS:
            print(f"- {item}")
        return 1

    print(f"content validation passed: {len(markdown_files())} Markdown files")
    print("2026 October mocks passed: 11 sets, 75 questions and answers per set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
