"""
test_harness.py — Batch evaluation script.

Runs all test_cases through the full AI pipeline (diagnose -> repair -> verify)
and prints a pass/fail summary table with confidence scores.

Usage:
    python test_harness.py
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from agents import DiagnosisAgent, RepairAgent
from verifier import run_tests

TEST_CASES = [
    {
        "name": "Wrong Comparison Operator",
        "code_file": "test_cases/buggy_comparison.py",
        "test_file": "test_cases/test_buggy_comparison.py",
        "expected_behavior": (
            "is_adult should return True for age >= 18; "
            "is_passing_grade should return True for percentage >= 60"
        ),
    },
    {
        "name": "Off-by-One Error",
        "code_file": "test_cases/buggy_offbyone.py",
        "test_file": "test_cases/test_buggy_offbyone.py",
        "expected_behavior": (
            "first_n_items should return exactly n items; "
            "integers_up_to should include n itself"
        ),
    },
    {
        "name": "Type Mismatch",
        "code_file": "test_cases/buggy_typemismatch.py",
        "test_file": "test_cases/test_buggy_typemismatch.py",
        "expected_behavior": (
            "format_score should convert int to string before concatenating; "
            "stringify_list should convert each int to str before joining"
        ),
    },
    {
        "name": "Scoring Logic Bug",
        "code_file": "test_cases/buggy_scoring.py",
        "test_file": "test_cases/test_buggy_scoring.py",
        "expected_behavior": "Wrong guesses should subtract 5 points, not add them",
    },
]

WIDTH = 65


def run_case(case: dict, diag: DiagnosisAgent, repair: RepairAgent) -> dict:
    code_path = Path(case["code_file"])
    test_path = Path(case["test_file"])

    if not code_path.exists() or not test_path.exists():
        return {
            "name": case["name"],
            "status": "SKIP",
            "bugs": 0,
            "passed": 0,
            "total": 0,
            "confidence": 0.0,
        }

    code = code_path.read_text(encoding="utf-8")
    test_code = test_path.read_text(encoding="utf-8")

    # Stage 1 -- diagnose
    diag_result = diag.diagnose(code, case.get("expected_behavior", ""))
    bugs = diag_result.get("bugs", [])

    # Stage 2 -- first repair attempt
    repair_result = repair.repair(code, bugs)
    fixed_code = repair_result.get("fixed_code") or code

    # Stage 3 -- verify
    verify = run_tests(fixed_code, test_code)
    passed = verify["passed"]
    total = verify["total"] or 1

    if verify["success"]:
        return {
            "name": case["name"],
            "status": "PASS",
            "bugs": len(bugs),
            "passed": verify["passed"],
            "total": verify["total"],
            "confidence": passed / total * 100,
        }

    # Stage 3b -- one retry with test failure context
    retry_repair = repair.retry_repair(code, bugs, verify["output"])
    retry_fixed = retry_repair.get("fixed_code") or fixed_code
    retry_verify = run_tests(retry_fixed, test_code)

    retry_passed = retry_verify["passed"]
    retry_total = retry_verify["total"] or 1
    confidence = retry_passed / retry_total * 100 * 0.7  # penalty for needing retry

    return {
        "name": case["name"],
        "status": "RETRY_PASS" if retry_verify["success"] else "FAIL",
        "bugs": len(bugs),
        "passed": retry_verify["passed"],
        "total": retry_verify["total"],
        "confidence": confidence,
    }


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    print("\n" + "=" * WIDTH)
    print("  AI Code Debugger -- Test Harness")
    print("=" * WIDTH)

    diag = DiagnosisAgent()
    repair = RepairAgent()

    results = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {case['name']} ...", end=" ", flush=True)
        result = run_case(case, diag, repair)
        results.append(result)
        print(result["status"])

    # Summary table
    print("\n" + "=" * WIDTH)
    print("  RESULTS SUMMARY")
    print("=" * WIDTH)
    print(f"{'Case':<30} {'Bugs':<6} {'Tests':<10} {'Status':<12} {'Conf'}")
    print("-" * WIDTH)

    total_pass = 0
    for r in results:
        tests_str = f"{r['passed']}/{r['total']}"
        print(
            f"{r['name']:<30} {r['bugs']:<6} {tests_str:<10} "
            f"{r['status']:<12} {r['confidence']:.0f}%"
        )
        if r["status"] in ("PASS", "RETRY_PASS"):
            total_pass += 1

    avg_conf = sum(r["confidence"] for r in results) / len(results) if results else 0
    print("-" * WIDTH)
    print(f"\nPassed: {total_pass}/{len(results)}   Average confidence: {avg_conf:.0f}%")
    print("=" * WIDTH + "\n")


if __name__ == "__main__":
    main()
