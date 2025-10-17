"""
Script to aggregate and analyze linter outputs (flake8, pylint, mypy)
for the UserFlagApp project.

Usage:
    python debug_lint.py
"""

import os
import subprocess
from pathlib import Path

###############################
# CONFIG
###############################
ROOT_DIR = Path(__file__).resolve().parent
MODULES = ["src", "apis", "utils"]
REPORT_PATH = ROOT_DIR / "lint_report.txt"

###############################
# UTILITY FUNCTIONS
###############################

def run_cmd(command: list[str], title: str) -> str:
    """Run a shell command and return its output."""
    print(f"\n🔍 Running {title}...")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
            check=False,
        )
        output = result.stdout + result.stderr
        print(output)
        return output
    except FileNotFoundError:
        print(f"⚠️ {title} not found. Did you install it?")
        return ""

###############################
# MAIN EXECUTION
###############################

def main() -> None:
    print("===============================================")
    print("   UserFlagApp — Linter Debug Script")
    print("===============================================\n")

    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    all_output = []

    # Run black check (without modifying)
    all_output.append(run_cmd(["black", "--check", "."], "Black (format check)"))

    # Run isort check
    all_output.append(run_cmd(["isort", "--check-only", "."], "Isort (import order check)"))

    # Run flake8
    all_output.append(run_cmd(["flake8", *MODULES], "Flake8 (PEP8)"))

    # Run pylint
    all_output.append(run_cmd(["pylint", *MODULES], "Pylint (deep analysis)"))

    # Run mypy (type checker)
    all_output.append(run_cmd(["mypy", *MODULES], "Mypy (type checking)"))

    # Write full report
    REPORT_PATH.write_text("\n\n".join(all_output), encoding="utf-8")

    # Extract only critical E/F issues for quick inspection
    print("\n===============================================")
    print("   SUMMARY — Critical Errors (E/F)")
    print("===============================================")
    summary_lines = []
    for line in "\n".join(all_output).splitlines():
        if any(tag in line for tag in [" E", " F"]):
            summary_lines.append(line)
            print(line)
    if not summary_lines:
        print("✅ No critical (E/F) issues found!")

    print(f"\nFull report saved to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
