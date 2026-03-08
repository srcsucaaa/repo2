#!/usr/bin/env python3
"""Flatten a local codebase into a Markdown string for LLM context."""

from __future__ import annotations

import argparse
import locale
import os
import subprocess
import sys
from pathlib import Path

EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
ENCODINGS = ("utf-8", "utf-8-sig", locale.getpreferredencoding(False) or "utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pack a local directory into a single Markdown context string."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target directory to pack. Defaults to the current directory.",
    )
    return parser.parse_args()


def guess_language(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".json": "json",
        ".md": "markdown",
        ".sh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".html": "html",
        ".css": "css",
        ".xml": "xml",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".sql": "sql",
    }.get(suffix, "")


def read_text_file(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in data:
        return None

    for encoding in ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    text = data.decode("latin-1")
    printable = sum(ch.isprintable() or ch in "\n\r\t" for ch in text)
    if text and printable / len(text) >= 0.95:
        return text
    return None


def build_markdown(root: Path) -> str:
    sections: list[str] = []

    for current_root, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for filename in sorted(files):
            file_path = Path(current_root) / filename
            rel_path = file_path.relative_to(root)
            content = read_text_file(file_path)
            if content is None:
                continue

            language = guess_language(rel_path)
            sections.append(
                f"## `{rel_path.as_posix()}`\n"
                f"```{language}\n{content}\n```\n"
            )

    return "\n".join(sections).rstrip() + "\n"


def load_pyperclip():
    try:
        import pyperclip  # type: ignore

        return pyperclip
    except ImportError:
        pass

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyperclip"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import pyperclip  # type: ignore

        return pyperclip
    except Exception:
        return None


def main() -> int:
    args = parse_args()
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory.", file=sys.stderr)
        return 1

    markdown = build_markdown(root)
    total_chars = len(markdown)
    output = f"{markdown}\nTotal characters: {total_chars}\n"

    sys.stdout.write(output)

    pyperclip = load_pyperclip()
    if pyperclip is None:
        print("Clipboard copy unavailable; printed to terminal only.", file=sys.stderr)
        return 0

    try:
        pyperclip.copy(output)
        print("Copied packed context to clipboard.", file=sys.stderr)
    except pyperclip.PyperclipException:
        print("Clipboard copy failed; printed to terminal only.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
