"""RAG module: retrieves relevant Python bug patterns to augment diagnosis prompts."""
import json
import re
from pathlib import Path

_PATTERNS_FILE = Path(__file__).parent / "bug_patterns.json"


class BugPatternRetriever:
    """Retrieves relevant Python bug patterns from a local knowledge base."""

    def __init__(self):
        with open(_PATTERNS_FILE, encoding="utf-8") as fh:
            self.patterns = json.load(fh)

    def retrieve(self, code: str, n: int = 3) -> list:
        """Return the top-n patterns most relevant to the given code snippet."""
        tokens = set(re.findall(r"[a-zA-Z_]\w*|[+\-/%<>=!]+", code.lower()))
        scored = []
        for pattern in self.patterns:
            score = sum(1 for kw in pattern["keywords"] if kw.lower() in tokens)
            if score > 0:
                scored.append((score, pattern))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[:n]]

    def format_for_prompt(self, patterns: list) -> str:
        """Format retrieved patterns as a context block for injection into a prompt."""
        if not patterns:
            return ""
        lines = ["=== Relevant Bug Patterns from Knowledge Base ==="]
        for p in patterns:
            lines.append(f"\n[{p['name']} — {p['bug_type']}]")
            lines.append(p["description"])
            if p.get("examples"):
                ex = p["examples"][0]
                lines.append(f"  Buggy:  {ex['buggy']}")
                lines.append(f"  Fixed:  {ex['fixed']}")
            lines.append(f"  Hint: {p['fix_hint']}")
        lines.append("\n=================================================")
        return "\n".join(lines)
