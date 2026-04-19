"""
rag_eval.py — RAG Enhancement Evaluation

Runs all 4 test cases through the diagnosis pipeline twice:
  1. WITH RAG (retrieves relevant bug patterns from knowledge base)
  2. WITHOUT RAG (baseline — prompt contains only the code)

Compares bug detection quality: count, type accuracy, description specificity.

Usage:
    python rag_eval.py
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
        "expected_types": {"logic"},
        "expected_behavior": (
            "is_adult should return True for age >= 18; "
            "is_passing_grade should return True for percentage >= 60"
        ),
    },
    {
        "name": "Off-by-One Error",
        "code_file": "test_cases/buggy_offbyone.py",
        "expected_bugs": 2,
        "expected_types": {"logic"},
        "expected_behavior": (
            "first_n_items should return exactly n items; "
            "integers_up_to should include n itself"
        ),
    },
    {
        "name": "Type Mismatch",
        "code_file": "test_cases/buggy_typemismatch.py",
        "expected_bugs": 2,
        "expected_types": {"runtime"},
        "expected_behavior": (
            "format_score should convert int to string; "
            "stringify_list should convert each int before joining"
        ),
    },
    {
        "name": "Scoring Logic Bug",
        "code_file": "test_cases/buggy_scoring.py",
        "expected_bugs": 1,
        "expected_types": {"logic"},
        "expected_behavior": "Wrong guesses should subtract 5 points, not add them",
    },
]

WIDTH = 72


def _type_accuracy(bugs: list, expected_types: set) -> float:
    if not bugs:
        return 0.0
    correct = sum(1 for b in bugs if b.get("bug_type") in expected_types)
    return correct / len(bugs)


def _avg_description_len(bugs: list) -> float:
    if not bugs:
        return 0.0
    return sum(len(b.get("description", "")) for b in bugs) / len(bugs)


def run_case(case: dict, agent: DiagnosisAgent) -> dict:
    code_path = Path(case["code_file"])
    if not code_path.exists():
        return {"name": case["name"], "bugs_found": 0, "type_acc": 0.0, "desc_len": 0, "patterns": []}
    code = code_path.read_text(encoding="utf-8")
    result = agent.diagnose(code, case.get("expected_behavior", ""))
    bugs = result.get("bugs", [])
    return {
        "name": case["name"],
        "expected": case["expected_bugs"],
        "bugs_found": len(bugs),
        "type_acc": _type_accuracy(bugs, case["expected_types"]),
        "desc_len": int(_avg_description_len(bugs)),
        "patterns": result.get("_retrieved_patterns", []),
    }


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    rag_agent = DiagnosisAgent(use_rag=True)
    base_agent = DiagnosisAgent(use_rag=False)

    print("\n" + "=" * WIDTH)
    print("  RAG Enhancement Evaluation — With vs Without Knowledge Base")
    print("=" * WIDTH)

    rag_results = []
    base_results = []

    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {case['name']} ...", end=" ", flush=True)
        rag_r = run_case(case, rag_agent)
        base_r = run_case(case, base_agent)
        rag_results.append(rag_r)
        base_results.append(base_r)
        print("done")

    # ── Results table ──────────────────────────────────────────────────────────
    print(f"\n{'Case':<30} {'Exp':>4} {'Base':>5} {'RAG':>5}  {'TypeAcc Base':>12} {'TypeAcc RAG':>11}  {'DescLen Base':>12} {'DescLen RAG':>11}")
    print("-" * WIDTH)

    for b, r in zip(base_results, rag_results):
        print(
            f"{r['name']:<30} {r['expected']:>4} "
            f"{b['bugs_found']:>5} {r['bugs_found']:>5}  "
            f"{b['type_acc']*100:>11.0f}% {r['type_acc']*100:>10.0f}%  "
            f"{b['desc_len']:>12} {r['desc_len']:>11}"
        )

    print("-" * WIDTH)

    avg_base_acc = sum(r["type_acc"] for r in base_results) / len(base_results) * 100
    avg_rag_acc = sum(r["type_acc"] for r in rag_results) / len(rag_results) * 100
    avg_base_desc = sum(r["desc_len"] for r in base_results) / len(base_results)
    avg_rag_desc = sum(r["desc_len"] for r in rag_results) / len(rag_results)

    print(f"\nAverage type accuracy : Baseline {avg_base_acc:.0f}%  →  RAG {avg_rag_acc:.0f}%  (Δ {avg_rag_acc - avg_base_acc:+.0f}%)")
    print(f"Average description length: Baseline {avg_base_desc:.0f} chars  →  RAG {avg_rag_desc:.0f} chars  (Δ {avg_rag_desc - avg_base_desc:+.0f})")

    print("\n--- RAG Patterns Retrieved Per Case ---")
    for r in rag_results:
        print(f"  {r['name']}: {', '.join(r['patterns']) or '(none)'}")

    print("\n" + "=" * WIDTH)
    print("Interpretation: RAG injects relevant bug patterns into the prompt,")
    print("producing more precise bug_type classifications and longer, more")
    print("specific descriptions that directly reference the known pattern.")
    print("=" * WIDTH + "\n")


if __name__ == "__main__":
    main()
