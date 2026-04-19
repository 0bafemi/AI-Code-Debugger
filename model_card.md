# Model Card — Game Glitch Investigator AI Debugger

## System Overview

**Task:** Automated Python bug diagnosis, repair, and verification  
**Model:** Claude (claude-sonnet-4-6) via Anthropic API  
**Original project:** Game Glitch Investigator number guessing game (Modules 1–3)

---

## Limitations and Biases

- **Language scope:** Python only — untested on other languages.
- **Bug type bias:** Performs best on logic and runtime bugs. Syntax errors in
  large files are harder to localize precisely.
- **False positives:** Claude occasionally flags idiomatic Python patterns as
  bugs when they are intentional. Without an explicit expected-behavior
  description, the model has no way to distinguish style from correctness.
- **Context window:** Very large code files may exceed effective reasoning
  capacity, leading to incomplete or truncated diagnoses.
- **Test dependency:** The confidence score is only meaningful when test code is
  provided. Without tests, it defaults to 50% regardless of repair quality.

---

## Potential Misuse and Safeguards

**Potential misuse:**
- Submitting fully AI-repaired code as original work without disclosure.
- Using the system to "clean up" obfuscated or malicious code in a way that
  makes it harder to detect.

**Safeguards implemented:**
- All API calls (inputs and outputs) are logged to `debugger.log` for
  auditability.
- The system returns structured before/after diffs so humans can review every
  proposed change before accepting it.
- Code is only executed inside an isolated temporary directory during pytest
  runs; temp files are deleted immediately afterward.
- No fixed code is written to the project directory automatically.

---

## Testing Results

| Test Case | Status | Confidence |
|---|---|---|
| Wrong Comparison Operator | PASS | 100% |
| Off-by-One Error | PASS | 100% |
| Type Mismatch | PASS | 100% |
| Scoring Logic Bug | PASS | 100% |

**What surprised me:** When the test code used slightly different import paths
than expected, the model's retry was able to infer the problem from pytest's
error output and correct its fix — showing genuine reasoning, not just pattern
matching. I also expected more false positives on the comparison operator tests
(since `>` is valid Python), but the model consistently identified the intent
mismatch when given expected-behavior context.

---

## AI Collaboration Reflection

**Helpful suggestion:** When designing the retry mechanism, the AI suggested
passing the full pytest output (including stack traces) as context for the retry
prompt, rather than just the pass/fail count. This was the right call — the
failure message text lets the model understand *what* broke, not just *that* it
broke, leading to more targeted second-attempt fixes.

**Flawed suggestion:** During early design of `verifier.py`, the AI suggested
using Python's built-in `unittest` runner instead of pytest subprocess isolation,
arguing it would avoid a subprocess call. While technically valid, this would
have broken compatibility with user-provided pytest-style tests (fixtures,
parametrize, etc.) and conflicted with the project's existing test
infrastructure. I rejected this suggestion and kept pytest with temp-directory
isolation.

---

## What This Project Taught Me About AI

Building this system taught me that AI reliability is not binary. The same
model that perfectly identifies a scoring sign error can hallucinate an "issue"
with a correct comparison operator. Structured prompts with explicit output
schemas dramatically reduced variability, but did not eliminate it. The test
harness was essential: running the pipeline against known-buggy inputs provided
concrete pass/fail evidence rather than subjective impressions.

Most importantly, treating the AI as a teammate whose suggestions I evaluate
critically — accepting the pytest-output idea, rejecting the unittest idea —
produced better results than either blindly following or ignoring its
recommendations.
