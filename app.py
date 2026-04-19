import logging
import os

import streamlit as st

from agents import DiagnosisAgent, PlanningAgent, RepairAgent
from verifier import run_tests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("debugger.log"),
        logging.StreamHandler(),
    ],
)

st.set_page_config(
    page_title="Game Glitch Investigator — AI Debugger",
    page_icon="🔍",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔍 Game Glitch Investigator — AI Code Debugger")
st.caption(
    "Powered by Claude (claude-sonnet-4-6) · "
    "Original project: Number Guessing Game debugger"
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. **Paste** buggy Python code\n"
        "2. Optionally describe expected behavior and/or paste test code\n"
        "3. Click **Run Debugger**\n\n"
        "The AI pipeline will:\n"
        "- Diagnose bugs (type, location, severity)\n"
        "- Repair the code\n"
        "- Verify fixes with pytest\n"
        "- Report a confidence score"
    )
    st.divider()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set.")
    else:
        st.success("API key configured")

# ── Input area ────────────────────────────────────────────────────────────────
col_code, col_meta = st.columns([2, 1])

with col_code:
    code_input = st.text_area(
        "Buggy Python code:",
        height=280,
        placeholder="def my_func():\n    # paste your buggy code here\n    pass",
    )

with col_meta:
    expected_behavior = st.text_input(
        "Expected behavior (optional):",
        placeholder="e.g. should return True for age >= 18",
    )
    test_code_input = st.text_area(
        "Test code (optional):",
        height=190,
        placeholder=(
            "# Tests must import from 'solution'\n"
            "from solution import my_func\n\n"
            "def test_example():\n"
            "    assert my_func(18) is True"
        ),
    )

api_ready = bool(os.environ.get("ANTHROPIC_API_KEY"))
run_clicked = st.button(
    "🚀 Run Debugger",
    type="primary",
    disabled=not code_input or not api_ready,
)

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run_clicked and code_input:
    plan_agent = PlanningAgent()
    diag_agent = DiagnosisAgent()
    repair_agent = RepairAgent()

    # ── Stage 0: Debugging Plan ───────────────────────────────────────────────
    with st.expander("🗺️ Stage 0: Debugging Strategy (Agentic Planning)", expanded=True):
        with st.spinner("Generating debugging plan…"):
            plan = plan_agent.plan(code_input, expected_behavior)

        if "error" in plan:
            st.warning(f"Planning error: {plan['error']}")
        else:
            st.write(f"**Approach:** {plan.get('approach', '')}")
            steps = plan.get("steps", [])
            if steps:
                st.write("**Plan steps:**")
                for s in steps:
                    st.write(
                        f"**Step {s.get('step', '?')} — {s.get('action', '')}**  \n"
                        f"*Why:* {s.get('reasoning', '')}  \n"
                        f"*Expected outcome:* {s.get('expected_outcome', '')}"
                    )
            priority = plan.get("priority_areas", [])
            if priority:
                st.write(f"**Priority areas:** {', '.join(priority)}")
            risk = plan.get("risk_assessment", "")
            if risk:
                st.caption(f"Risk assessment: {risk}")

    # ── Stage 1: Diagnosis ────────────────────────────────────────────────────
    with st.expander("🔎 Stage 1: Bug Diagnosis (RAG-Enhanced)", expanded=True):
        with st.spinner("Analyzing code for bugs…"):
            diagnosis = diag_agent.diagnose(code_input, expected_behavior)

        bugs = diagnosis.get("bugs", [])
        summary = diagnosis.get("summary", "")
        retrieved_patterns = diagnosis.get("_retrieved_patterns", [])

        if retrieved_patterns:
            with st.expander(f"📚 RAG: {len(retrieved_patterns)} pattern(s) retrieved from knowledge base"):
                st.caption("These bug patterns were injected into the diagnosis prompt to improve accuracy.")
                for p in retrieved_patterns:
                    st.write(f"- {p}")

        if "error" in diagnosis:
            st.error(f"Diagnosis error: {diagnosis['error']}")
        elif not bugs:
            st.info(f"No bugs detected. {summary}")
        else:
            st.write(f"**{len(bugs)} bug(s) found.** {summary}")
            for i, bug in enumerate(bugs, 1):
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    bug.get("severity", ""), "⚪"
                )
                st.write(
                    f"{icon} **Bug {i}** — "
                    f"`{bug.get('location', '?')}` | "
                    f"Type: `{bug.get('bug_type', '?')}` | "
                    f"Severity: **{bug.get('severity', '?')}**"
                )
                st.caption(bug.get("description", ""))

    # ── Stage 2: Repair ───────────────────────────────────────────────────────
    fixed_code = code_input
    fixes = []

    with st.expander("🔧 Stage 2: Bug Repair", expanded=True):
        with st.spinner("Generating fixes…"):
            repair_result = repair_agent.repair(code_input, bugs)

        fixed_code = repair_result.get("fixed_code") or code_input
        fixes = repair_result.get("fixes", [])

        if "error" in repair_result:
            st.error(f"Repair error: {repair_result['error']}")
        else:
            if not fixes:
                st.info("No individual fixes returned.")
            for i, fix in enumerate(fixes, 1):
                st.write(f"**Fix {i}:**")
                c1, c2 = st.columns(2)
                with c1:
                    st.code(fix.get("original_snippet", ""), language="python")
                    st.caption("Before")
                with c2:
                    st.code(fix.get("fixed_snippet", ""), language="python")
                    st.caption("After")
                st.write(f"*{fix.get('explanation', '')}*")
                st.divider()

            with st.expander("Fixed code (full)"):
                st.code(fixed_code, language="python")

    # ── Stage 3: Verification ─────────────────────────────────────────────────
    first_result = None
    retry_result = None

    with st.expander("✅ Stage 3: Verification", expanded=True):
        if not test_code_input.strip():
            st.info("No test code provided — skipping verification.")
        else:
            with st.spinner("Running tests on fixed code…"):
                first_result = run_tests(fixed_code, test_code_input)

            if first_result["success"]:
                st.success(
                    f"All tests passed on first attempt! "
                    f"({first_result['passed']}/{first_result['total']})"
                )
            else:
                st.warning(
                    f"Tests failed ({first_result['passed']}/{first_result['total']} passed). "
                    "Retrying with test failure context…"
                )
                with st.spinner("Retrying repair…"):
                    retry_repair = repair_agent.retry_repair(
                        code_input, bugs, first_result["output"]
                    )
                    retry_fixed = retry_repair.get("fixed_code") or fixed_code
                    retry_result = run_tests(retry_fixed, test_code_input)

                if retry_result["success"]:
                    st.success(
                        f"Retry succeeded! "
                        f"({retry_result['passed']}/{retry_result['total']})"
                    )
                    fixed_code = retry_fixed
                else:
                    st.error(
                        f"Retry also failed. "
                        f"({retry_result['passed']}/{retry_result['total']} passed)"
                    )

            with st.expander("Test output"):
                st.code(first_result["output"])
                if retry_result:
                    st.write("**Retry output:**")
                    st.code(retry_result["output"])

    # ── Stage 4: Report & Confidence Score ────────────────────────────────────
    with st.expander("📊 Stage 4: Report & Confidence Score", expanded=True):
        if first_result:
            total = first_result["total"] or 1
            first_rate = first_result["passed"] / total

            if first_result["success"]:
                confidence = first_rate * 100
                label = "first-attempt pass rate"
            elif retry_result:
                retry_total = retry_result["total"] or 1
                confidence = retry_result["passed"] / retry_total * 100 * 0.7
                label = "retry pass rate (x0.7 penalty)"
            else:
                confidence = first_rate * 100 * 0.5
                label = "partial first-attempt (retry failed)"
        else:
            confidence = 50.0
            label = "no tests provided — uncertain"

        st.metric("Confidence Score", f"{confidence:.0f}%", label)
        st.progress(min(confidence / 100, 1.0))

        st.write("### Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Bugs Found", len(bugs))
        c2.metric("Fixes Applied", len(fixes))
        if first_result:
            best = retry_result if retry_result else first_result
            c3.metric("Tests Passed", f"{best['passed']}/{best['total']}")
