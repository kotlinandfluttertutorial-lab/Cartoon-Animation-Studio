#!/usr/bin/env python3
"""
check_before_push.py ΓÇö Local pre-push CI check for Cartoon Animation Studio.

Mirrors the checks in .github/workflows/ci.yml and pr-checks.yml so you can
catch failures before pushing to the remote.

Usage:
    python check_before_push.py              # all checks
    python check_before_push.py --fast       # skip Blender integration tests
    python check_before_push.py --syntax     # syntax check only

Exit codes:
    0 ΓÇö all checks passed
    1 ΓÇö one or more checks failed
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 cannot encode em-dash etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ΓöÇΓöÇ Paths ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
REPO_ROOT    = Path(__file__).resolve().parent
PROJECT_DIR  = REPO_ROOT / "Local_3D_Cartoon_Studio"
PYTHON       = sys.executable                     # same Python running this script
BLENDER      = REPO_ROOT / "tools" / "blender-4.4.3-windows-x64" / "blender.exe"

# ΓöÇΓöÇ ANSI colours ΓÇö disabled for Windows PowerShell compatibility ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
GREEN = RED = YELLOW = CYAN = RESET = BOLD = ""


# ΓöÇΓöÇ Result tracking ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
_results: list[dict] = []

def _pass(name: str, detail: str = "") -> None:
    _results.append({"name": name, "status": "PASS", "detail": detail})
    tag = f"{GREEN}PASS{RESET}"
    print(f"  {tag}  {name}" + (f"  ΓÇö {detail}" if detail else ""))

def _fail(name: str, detail: str = "") -> None:
    _results.append({"name": name, "status": "FAIL", "detail": detail})
    tag = f"{RED}FAIL{RESET}"
    print(f"  {tag}  {name}" + (f"  ΓÇö {detail}" if detail else ""))

def _warn(name: str, detail: str = "") -> None:
    _results.append({"name": name, "status": "WARN", "detail": detail})
    tag = f"{YELLOW}WARN{RESET}"
    print(f"  {tag}  {name}" + (f"  ΓÇö {detail}" if detail else ""))

def _skip(name: str, reason: str = "") -> None:
    _results.append({"name": name, "status": "SKIP", "detail": reason})
    tag = f"{CYAN}SKIP{RESET}"
    print(f"  {tag}  {name}" + (f"  ΓÇö {reason}" if reason else ""))

def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'-'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'-'*60}{RESET}")


# ΓöÇΓöÇ 1. Git state ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_git(fast: bool) -> None:
    section("1. Git state")

    # Current branch
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=REPO_ROOT
    ).stdout.strip()
    if branch:
        _pass("Git branch detected", branch)
    else:
        _warn("Git branch", "detached HEAD or not a git repo")

    # Warn if on develop or main
    if branch in ("develop", "main"):
        _warn("Branch convention", f"You are on '{branch}'. Feature work should be on feature/* or fix/*")
    else:
        _pass("Branch convention", f"'{branch}' is a feature/fix branch ΓÇö PR should target develop")

    # Clean working tree
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT
    ).stdout.strip()
    if not status:
        _pass("Working tree clean")
    else:
        lines = status.splitlines()
        _warn("Uncommitted changes", f"{len(lines)} file(s) modified/untracked")
        for l in lines[:5]:
            print(f"       {l}")
        if len(lines) > 5:
            print(f"       ΓÇª and {len(lines)-5} more")

    # Check .bak files are gitignored
    tracked_bak = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "*.bak"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if tracked_bak.returncode == 0:
        _warn(".bak files tracked", "backup files should be in .gitignore")
    else:
        _pass(".bak files gitignored")


# ΓöÇΓöÇ 2. Python syntax check ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_syntax() -> None:
    section("2. Python syntax check")

    py_files = list(PROJECT_DIR.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    errors = []
    for f in py_files:
        result = subprocess.run(
            [PYTHON, "-m", "py_compile", str(f)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            errors.append((f.relative_to(REPO_ROOT), result.stderr.strip()))

    if errors:
        _fail("Python syntax", f"{len(errors)} file(s) with errors")
        for path, err in errors:
            print(f"       {path}: {err}")
    else:
        _pass("Python syntax", f"{len(py_files)} files checked")


# ΓöÇΓöÇ 3. JSON config validity ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_json_configs() -> None:
    section("3. JSON config validity")

    config_dir = PROJECT_DIR / "config"
    if not config_dir.exists():
        _warn("Config directory", "not found ΓÇö skipping")
        return

    json_files = list(config_dir.glob("*.json"))
    errors = []
    for f in json_files:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append((f.name, str(e)))

    if errors:
        _fail("Config JSON", f"{len(errors)} invalid file(s)")
        for name, err in errors:
            print(f"       {name}: {err}")
    else:
        _pass("Config JSON", f"{len(json_files)} files valid")


# ΓöÇΓöÇ 4. requirements.txt installable ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_requirements() -> None:
    section("4. Requirements")

    req = PROJECT_DIR / "requirements.txt"
    if not req.exists():
        _warn("requirements.txt", "not found")
        return

    result = subprocess.run(
        [PYTHON, "-m", "pip", "install", "--dry-run", "-r", str(req)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        _pass("requirements.txt", "dry-run install OK")
    else:
        _fail("requirements.txt", "pip dry-run failed")
        print(f"       {result.stderr[:300]}")


# ΓöÇΓöÇ 5. Asset integrity ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_assets() -> None:
    section("5. Asset integrity")

    # Character originals
    chars = {
        "aarav.blend": (PROJECT_DIR / "blender/assets/characters/aarav/aarav.blend", 774392),
        "aanya.blend": (PROJECT_DIR / "blender/assets/characters/aanya/aanya.blend", 796228),
    }
    for name, (path, expected_size) in chars.items():
        if not path.exists():
            _fail(f"{name} exists", str(path))
        elif path.stat().st_size != expected_size:
            actual = path.stat().st_size
            _warn(f"{name} size", f"expected {expected_size}, got {actual} ΓÇö may have been regenerated")
        else:
            _pass(f"{name} integrity", f"{expected_size} bytes")

    # Garden
    garden = PROJECT_DIR / "blender/assets/environments/garden/garden.blend"
    if garden.exists():
        _pass("garden.blend exists", f"{garden.stat().st_size:,} bytes")
    else:
        _fail("garden.blend exists", str(garden))

    # Character previews
    for char in ("aarav", "aanya"):
        for view in ("front", "side", "three_quarter", "wave_pose", "happy_expression"):
            p = PROJECT_DIR / f"blender/assets/characters/{char}/previews/{view}.png"
            if p.exists() and p.stat().st_size > 20480:
                pass  # silent pass for previews ΓÇö too many to list individually
            else:
                _warn(f"{char}/{view}.png", "missing or too small")

    _pass("Character previews scanned", "10 ├ù character preview PNGs checked")

    # Garden previews
    for view in ("garden_wide", "garden_main", "garden_close", "garden_with_characters"):
        p = PROJECT_DIR / f"blender/assets/environments/garden/previews/{view}.png"
        if not (p.exists() and p.stat().st_size > 20480):
            _warn(f"{view}.png", "missing or too small")
    _pass("Garden previews scanned", "4 ├ù garden preview PNGs checked")


# ΓöÇΓöÇ 6. Stage reports present ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_reports() -> None:
    section("6. Stage reports")

    expected = [
        "reports/stage1_report.md",
        "reports/stage2_report.md",
        "reports/stage3_garden_environment_report.md",
        "reports/stage4_1_character_rigging_report.md",
        "reports/stage4_2_movement_system_report.md",
    ]
    missing = []
    for rel in expected:
        p = PROJECT_DIR / rel
        if p.exists():
            pass
        else:
            missing.append(rel)

    if missing:
        _warn("Stage reports", f"{len(missing)} expected report(s) missing")
        for m in missing:
            print(f"       {m}")
    else:
        _pass("Stage reports", f"{len(expected)} reports present")


# ΓöÇΓöÇ 7. Unit tests (non-integration) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_unit_tests(fast: bool) -> None:
    section("7. Automated tests")

    tests_dir = PROJECT_DIR / "tests"
    if not tests_dir.exists():
        _warn("Tests directory", "not found")
        return

    # Build pytest exclusion args
    # Skip Blender integration tests in fast mode (they require Blender process)
    base_cmd = [PYTHON, "-m", "pytest", str(tests_dir), "-v", "--tb=short", "-q"]

    if fast:
        base_cmd += [
            "-k", "not blender and not Blender and not integration and not Integration"
                  " and not render and not Render"
        ]
        label = "unit tests (non-integration)"
    else:
        label = "all tests"

    t0 = time.perf_counter()
    result = subprocess.run(base_cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    elapsed = time.perf_counter() - t0

    # Parse summary line
    output = result.stdout + result.stderr
    passed = failed = errors = skipped = 0
    for line in output.splitlines():
        if " passed" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            if m: passed = int(m.group(1))
            m = re.search(r"(\d+) failed", line)
            if m: failed = int(m.group(1))
            m = re.search(r"(\d+) error", line)
            if m: errors = int(m.group(1))
            m = re.search(r"(\d+) skipped", line)
            if m: skipped = int(m.group(1))

    summary = f"{passed} passed"
    if failed:   summary += f", {failed} failed"
    if errors:   summary += f", {errors} errors"
    if skipped:  summary += f", {skipped} skipped"
    summary += f"  ({elapsed:.1f}s)"

    if result.returncode == 0:
        _pass(f"pytest {label}", summary)
    else:
        _fail(f"pytest {label}", summary)
        # Print last 30 lines of output for context
        tail = output.splitlines()[-30:]
        for line in tail:
            print(f"       {line}")


# ΓöÇΓöÇ 8. No secrets in staged files ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_secrets() -> None:
    section("8. Secret scan (basic)")

    patterns = [
        ("AWS key",        r"AKIA[0-9A-Z]{16}"),
        ("Generic secret", r"(?i)(secret|password|token|api_key)\s*=\s*['\"][^'\"]{8,}"),
        ("Private key",    r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY"),
    ]

    import re
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=REPO_ROOT
    ).stdout.strip().splitlines()

    hits = []
    for rel in staged:
        path = REPO_ROOT / rel
        if not path.exists() or not path.suffix in (".py", ".json", ".yml", ".yaml", ".md", ".txt", ".env"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for label, pattern in patterns:
            if re.search(pattern, text):
                hits.append((rel, label))

    if hits:
        _fail("Secret scan", f"{len(hits)} potential secret(s) in staged files")
        for rel, label in hits:
            print(f"       {rel}: {label}")
    else:
        _pass("Secret scan", f"{len(staged)} staged file(s) scanned")


# ΓöÇΓöÇ 9. Blender smoke test (optional) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def check_blender(fast: bool) -> None:
    section("9. Blender smoke test")

    if not BLENDER.exists():
        _warn("Blender executable", f"not found at {BLENDER}")
        return

    if fast:
        _skip("Blender version check", "--fast mode")
        return

    result = subprocess.run(
        [str(BLENDER), "--version"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        ver = result.stdout.splitlines()[0] if result.stdout else "unknown"
        _pass("Blender executable", ver)
    else:
        _fail("Blender executable", "blender --version failed")


# ΓöÇΓöÇ Summary ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def print_summary() -> int:
    passed  = sum(1 for r in _results if r["status"] == "PASS")
    failed  = sum(1 for r in _results if r["status"] == "FAIL")
    warned  = sum(1 for r in _results if r["status"] == "WARN")
    skipped = sum(1 for r in _results if r["status"] == "SKIP")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  PRE-PUSH CHECK SUMMARY{RESET}")
    print(f"{'='*60}")
    print(f"  {GREEN}PASS{RESET}  {passed}")
    print(f"  {RED}FAIL{RESET}  {failed}")
    print(f"  {YELLOW}WARN{RESET}  {warned}")
    print(f"  {CYAN}SKIP{RESET}  {skipped}")
    print(f"{'-'*60}")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}All checks passed - safe to push.{RESET}\n")
        return 0
    else:
        print(f"\n  {RED}{BOLD}FAILED: {failed} check(s) failed - fix before pushing.{RESET}\n")
        return 1


# ΓöÇΓöÇ Entry point ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-push CI check")
    parser.add_argument("--fast",   action="store_true", help="Skip Blender + integration tests")
    parser.add_argument("--syntax", action="store_true", help="Syntax check only")
    args = parser.parse_args()

    print(f"\n{BOLD}Cartoon Animation Studio ΓÇö Pre-push CI Check{RESET}")
    print(f"Repo:    {REPO_ROOT}")
    print(f"Project: {PROJECT_DIR}")
    print(f"Mode:    {'syntax-only' if args.syntax else 'fast' if args.fast else 'full'}")

    if args.syntax:
        check_syntax()
        check_json_configs()
    else:
        check_git(args.fast)
        check_syntax()
        check_json_configs()
        check_requirements()
        check_assets()
        check_reports()
        check_unit_tests(args.fast)
        check_secrets()
        check_blender(args.fast)

    return print_summary()


if __name__ == "__main__":
    sys.exit(main())
