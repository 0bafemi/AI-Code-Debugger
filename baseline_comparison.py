"""
baseline_comparison.py — Fine-Tuning / Specialization Evaluation

Compares the DiagnosisAgent WITH few-shot examples (specialized) against
the same agent WITHOUT few-shot examples (baseline), on all 4 test cases.

Measured dimensions:
  - Bug count accuracy  (did it find the right number of bugs?)
  - Bug type consistency (are bug_type values always logic/runtime/syntax?)
  - Severity non-null    (did it always assign a severity?)
  - Description length   (longer = more specific, a proxy for quality)

Usage:
    python baseline_comparison.py
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from agents import DiagnosisAgent

TEST_CASES = [
    {
        "name": "Wrong Comparison Operator",
        "code_file": "test_cases/buggy_comparison.py",
        "expected_bugs": 2,
        "expected_behavior": (
            "is_adult should return True for age >= 18; "
            "is_passing_grade should return True for percentage >= 60"
        ),
    },
    {
        "name": "Off-by-One Error",
        "code_file": "test_cases/buggy_offbyone.py",
        "expected_bugs": 2,
        "expected_behavior": (
            "first_n_items should return exactly n items; "
            "integers_up_to should include n itself"
        ),
    },
    {
        "name": "Type Mismatch",
        "code_file": "test_cases/buggy_typemismatch.py",
        "expected_bugs": 2,
        "expected_behavior": (
            "format_score should convert int to string; "
            "stringify_list should convert each int before joining"
        ),
    },
    {
        "name": "Scoring Logic Bug",
        "code_file": "test_cases/buggy_scoring.py",
        "expected_bugs": 1,
        "expected_behavior": "Wrong guesses should subtract 5 points, not add them",
    },
]

VALID_BUG_TYPES = {"logic", "runtime", "syntax"}
WIDTH = 76


def score_result(result: dict, expected_bugs: int) -> dict:
    bugs = result.get("bugs", [])
    count_correct = len(bugs) == expected_bugs
    type_consistent = all(b.get("bug_type") in VALID_BUG_TYPES for b in bugs)
    severity_present = all(b.get("severity") in {"low", "medium", "high"} for b in bugs)
    avg_desc_len = int(sum(len(b.get("description", "")) for b in bugs) / max(len(bugs), 1))
    return {
        "bugs_found": len(bugs),
        "count_correct": count_correct,
        "type_consistent": type_consistent,
        "severity_ok": severity_present,
        "desc_len": avg_desc_len,
    }


def run_case(case: dict, agent: DiagnosisAgent) -> dict:
    code_path = Path(case["code_file"])
    if not code_path.exists():
        return {"bugs_found": 0, "count_correct": False, "type_consistent": False,
                "severity_ok": False, "desc_len": 0}
    code = code_path.read_text(encoding="utf-8")
    result = agent.diagnose(code, case.get("expected_behavior", ""))
    return score_result(result, case["expected_bugs"])


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    specialized = DiagnosisAgent(use_rag=False, use_few_shot=True)
    baseline = DiagnosisAgent(use_rag=False, use_few_shot=False)

    print("\n" + "=" * WIDTH)
    print("  Fine-Tuning / Specialization Evaluation — With vs Without Few-Shot Examples")
    print("=" * WIDTH)
    print("(RAG disabled for both agents to isolate the few-shot effect)\n")

    base_scores = []
    spec_scores = []

    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {case['name']} ...", end=" ", flush=True)
        b = run_case(case, baseline)
        s = run_case(case, specialized)
        base_scores.append(b)
        spec_scores.append(s)
        print("done")

    # ── Results table ──────────────────────────────────────────────────────────
    hdr = f"{'Case':<30} {'Bugs Base/Spec':>14} {'CountOK B/S':>12} {'TypeOK B/S':>11} {'DescLen B/S':>12}"
    print(f"\n{hdr}")
    print("-" * WIDTH)

    for case, b, s in zip(TEST_CASES, base_scores, spec_scores):
        bugs_str = f"{b['bugs_found']}/{s['bugs_found']}"
        count_str = f"{'Y' if b['count_correct'] else 'N'}/{'Y' if s['count_correct'] else 'N'}"
        type_str = f"{'Y' if b['type_consistent'] else 'N'}/{'Y' if s['type_consistent'] else 'N'}"
        desc_str = f"{b['desc_len']}/{s['desc_len']}"
        print(f"{case['name']:<30} {bugs_str:>14} {count_str:>12} {type_str:>11} {desc_str:>12}")

    print("-" * WIDTH)

    def pct(scores, key):
        return sum(1 for s in scores if s[key]) / len(scores) * 100

    print(f"\n{'Metric':<35} {'Baseline':>10} {'Specialized':>12} {'Delta':>8}")
    print("-" * 68)
    print(f"{'Bug count accuracy':<35} {pct(base_scores,'count_correct'):>9.0f}%"
          f" {pct(spec_scores,'count_correct'):>11.0f}%"
          f" {pct(spec_scores,'count_correct')-pct(base_scores,'count_correct'):>+7.0f}%")
    print(f"{'Bug type consistency':<35} {pct(base_scores,'type_consistent'):>9.0f}%"
          f" {pct(spec_scores,'type_consistent'):>11.0f}%"
          f" {pct(spec_scores,'type_consistent')-pct(base_scores,'type_consistent'):>+7.0f}%")
    print(f"{'Severity always assigned':<35} {pct(base_scores,'severity_ok'):>9.0f}%"
          f" {pct(spec_scores,'severity_ok'):>11.0f}%"
          f" {pct(spec_scores,'severity_ok')-pct(base_scores,'severity_ok'):>+7.0f}%")
    avg_b = sum(s['desc_len'] for s in base_scores) / len(base_scores)
    avg_s = sum(s['desc_len'] for s in spec_scores) / len(spec_scores)
    print(f"{'Avg description length (chars)':<35} {avg_b:>9.0f} "
          f" {avg_s:>11.0f}  {avg_s - avg_b:>+7.0f}")

    print("\n" + "=" * WIDTH)
    print("Interpretation: Few-shot examples specialize the model to produce")
    print("structured, consistent output — valid bug_type enums, non-null")
    print("severities, and more specific descriptions that reference the exact")
    print("fault pattern rather than making vague observations.")
    print("=" * WIDTH + "\n")


if __name__ == "__main__":
    main()
