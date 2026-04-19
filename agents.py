import json
import logging
import os

import anthropic

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


class DiagnosisAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = MODEL

    def diagnose(self, code: str, expected_behavior: str = "") -> dict:
        """Analyze code and return a structured list of bugs."""
        logger.info("DiagnosisAgent: analyzing %d chars of code", len(code))

        user_content = f"Analyze this Python code for bugs:\n\n```python\n{code}\n```"
        if expected_behavior.strip():
            user_content += f"\n\nExpected behavior: {expected_behavior}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": DIAGNOSIS_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            logger.info("DiagnosisAgent: response received (%d chars)", len(raw))
            result = _parse_json(raw)
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
