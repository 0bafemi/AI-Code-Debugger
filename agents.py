import json
import logging
import os

import anthropic

try:
    from rag import BugPatternRetriever
    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert Python debugger. Analyze the provided Python code and identify all bugs.

Return your response as a JSON object with EXACTLY this structure — no markdown fences, no extra text:
{
  "bugs": [
    {
      "location": "function name or approximate line number",
      "bug_type": "syntax|logic|runtime",
      "description": "clear, specific description of the bug",
      "severity": "low|medium|high"
    }
  ],
  "summary": "brief overall assessment"
}

If no bugs are found, return: {"bugs": [], "summary": "No bugs detected."}"""

_FEW_SHOT_EXAMPLES = """

### Specialization Examples (few-shot)

Example 1 — Boundary comparison bug:
Code: def is_adult(age): return age > 18
Expected: should return True for age 18 and above
Output: {"bugs": [{"location": "is_adult", "bug_type": "logic", "description": "Uses strict > instead of >=, so age exactly 18 incorrectly returns False — the boundary value is excluded", "severity": "medium"}], "summary": "One logic bug: strict inequality excludes the boundary case."}

Example 2 — Type mismatch in concatenation:
Code: def fmt(score): return score + "%"
Output: {"bugs": [{"location": "fmt", "bug_type": "runtime", "description": "Cannot concatenate int and str with +; score must be wrapped in str() or an f-string", "severity": "high"}], "summary": "One runtime TypeError: integer cannot be concatenated to a string."}

Example 3 — Off-by-one in slice:
Code: def first_n(lst, n): return lst[:n-1]
Expected: should return exactly n elements
Output: {"bugs": [{"location": "first_n", "bug_type": "logic", "description": "Slice [:n-1] returns only n-1 elements due to off-by-one error; should be [:n] to return exactly n", "severity": "medium"}], "summary": "One logic bug: off-by-one in slice endpoint."}

Example 4 — Wrong arithmetic sign:
Code: def update_score(score, outcome):\n    if outcome == 'wrong':\n        return score + 5
Expected: wrong guesses should penalize the player
Output: {"bugs": [{"location": "update_score", "bug_type": "logic", "description": "Returns score + 5 on wrong guess instead of score - 5; addition rewards incorrect answers instead of penalizing them", "severity": "high"}], "summary": "One logic bug: wrong arithmetic sign turns a penalty into a reward."}"""

REPAIR_SYSTEM_PROMPT = """You are an expert Python developer. Fix the provided buggy Python code based on the identified bugs.

Return your response as a JSON object with EXACTLY this structure — no markdown fences, no extra text:
{
  "fixed_code": "the complete corrected Python code as a string",
  "fixes": [
    {
      "original_snippet": "the exact buggy code snippet",
      "fixed_snippet": "the corrected replacement",
      "explanation": "plain English explanation of what changed and why"
    }
  ]
}"""


PLANNING_SYSTEM_PROMPT = """You are an expert debugging strategist. Given buggy Python code, produce a structured multi-step debugging plan BEFORE any fixes are attempted. This plan makes the reasoning process observable.

Return your response as a JSON object with EXACTLY this structure — no markdown fences, no extra text:
{
  "approach": "1-2 sentence overall debugging strategy",
  "steps": [
    {
      "step": 1,
      "action": "what to examine or do in this step",
      "reasoning": "why this step is necessary",
      "expected_outcome": "what you expect to discover or achieve"
    }
  ],
  "priority_areas": ["list of functions or code regions to focus on first"],
  "risk_assessment": "potential complications that could make repair tricky"
}

Rules:
- Provide 3-5 planning steps.
- Every string value must be on a single line — no newlines, no code snippets inside field values.
- Do not include code examples inside any JSON field."""


def _parse_json(text: str) -> dict:
    """Parse JSON from an API response, stripping markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end]).strip()
    return json.loads(text)


class PlanningAgent:
    """Stage 0: generates an observable multi-step debugging plan before diagnosis."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = MODEL

    def plan(self, code: str, expected_behavior: str = "") -> dict:
        logger.info("PlanningAgent: creating plan for %d chars", len(code))
        user_content = f"Create a debugging plan for this Python code:\n\n```python\n{code}\n```"
        if expected_behavior.strip():
            user_content += f"\n\nExpected behavior: {expected_behavior}"
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": PLANNING_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            result = _parse_json(raw)
            logger.info("PlanningAgent: plan with %d steps", len(result.get("steps", [])))
            return result
        except json.JSONDecodeError as e:
            logger.error("PlanningAgent: JSON parse error: %s", e)
            return {"approach": "Standard systematic debugging.", "steps": [], "error": str(e)}
        except anthropic.APIError as e:
            logger.error("PlanningAgent: API error: %s", e)
            return {"approach": "", "steps": [], "error": str(e)}


class DiagnosisAgent:
    def __init__(self, use_rag: bool = True, use_few_shot: bool = True):
        self.client = anthropic.Anthropic()
        self.model = MODEL
        self.retriever = BugPatternRetriever() if (use_rag and _RAG_AVAILABLE) else None
        self._system_prompt = DIAGNOSIS_SYSTEM_PROMPT + (_FEW_SHOT_EXAMPLES if use_few_shot else "")

    def diagnose(self, code: str, expected_behavior: str = "") -> dict:
        """Analyze code and return a structured list of bugs."""
        logger.info("DiagnosisAgent: analyzing %d chars of code", len(code))

        retrieved = []
        if self.retriever:
            retrieved = self.retriever.retrieve(code)
            logger.info("DiagnosisAgent: retrieved %d RAG patterns", len(retrieved))

        user_content = f"Analyze this Python code for bugs:\n\n```python\n{code}\n```"
        if expected_behavior.strip():
            user_content += f"\n\nExpected behavior: {expected_behavior}"
        if retrieved and self.retriever:
            rag_context = self.retriever.format_for_prompt(retrieved)
            user_content += f"\n\n{rag_context}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": self._system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            logger.info("DiagnosisAgent: response received (%d chars)", len(raw))
            result = _parse_json(raw)
            result["_retrieved_patterns"] = [p["name"] for p in retrieved]
            logger.info("DiagnosisAgent: found %d bug(s)", len(result.get("bugs", [])))
            return result

        except json.JSONDecodeError as e:
            logger.error("DiagnosisAgent: JSON parse error: %s", e)
            return {"bugs": [], "summary": "Failed to parse diagnosis response.", "error": str(e)}
        except anthropic.APIError as e:
            logger.error("DiagnosisAgent: API error: %s", e)
            return {"bugs": [], "summary": "API error during diagnosis.", "error": str(e)}


class RepairAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = MODEL

    def repair(self, code: str, bugs: list) -> dict:
        """Propose fixes for the identified bugs."""
        logger.info("RepairAgent: repairing code with %d known bug(s)", len(bugs))
        return self._call_api(self._build_prompt(code, bugs))

    def retry_repair(self, code: str, bugs: list, test_failure_output: str) -> dict:
        """Retry repair using pytest failure output as additional context."""
        logger.info("RepairAgent: retrying repair with test failure context")
        prompt = (
            f"{self._build_prompt(code, bugs)}\n\n"
            f"A previous fix attempt failed the tests. pytest output:\n"
            f"```\n{test_failure_output}\n```\n"
            "Address both the identified bugs AND the test failures shown above."
        )
        return self._call_api(prompt)

    def _build_prompt(self, code: str, bugs: list) -> str:
        bugs_json = json.dumps(bugs, indent=2)
        return (
            f"Fix this Python code based on the identified bugs.\n\n"
            f"Original code:\n```python\n{code}\n```\n\n"
            f"Bugs to fix:\n{bugs_json}"
        )

    def _call_api(self, user_content: str) -> dict:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": REPAIR_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            logger.info("RepairAgent: response received (%d chars)", len(raw))
            result = _parse_json(raw)
            logger.info("RepairAgent: applied %d fix(es)", len(result.get("fixes", [])))
            return result

        except json.JSONDecodeError as e:
            logger.error("RepairAgent: JSON parse error: %s", e)
            return {"fixed_code": "", "fixes": [], "error": str(e)}
        except anthropic.APIError as e:
            logger.error("RepairAgent: API error: %s", e)
            return {"fixed_code": "", "fixes": [], "error": str(e)}
