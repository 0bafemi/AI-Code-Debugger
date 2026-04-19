import logging
import os
import re
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)


def run_tests(fixed_code: str, test_code: str) -> dict:
    """
    Write fixed_code to solution.py and test_code to test_solution.py inside a
    temporary directory, run pytest, and return structured results.

    Test files should import from 'solution' (e.g. `from solution import my_func`).
    The temp directory is deleted automatically after the run.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = os.path.join(tmpdir, "solution.py")
        test_path = os.path.join(tmpdir, "test_solution.py")
        conftest_path = os.path.join(tmpdir, "conftest.py")

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        # Ensure tmpdir is on sys.path so test_solution.py can import solution.py
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write("import sys, os\nsys.path.insert(0, os.path.dirname(__file__))\n")

        logger.info("Verifier: running pytest in %s", tmpdir)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            logger.error("Verifier: pytest timed out after 60 s")
            return {
                "passed": 0,
                "failed": 0,
                "total": 0,
                "output": "Test run timed out after 60 seconds.",
                "success": False,
                "return_code": -1,
            }

        output = result.stdout + result.stderr
        logger.info("Verifier: return code %d", result.returncode)

        passed, failed = _parse_counts(output)

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "output": output,
            "success": result.returncode == 0,
            "return_code": result.returncode,
        }


def _parse_counts(output: str) -> tuple:
    """Extract passed/failed counts from pytest summary line."""
    passed = 0
    failed = 0
    m = re.search(r"(\d+) passed", output)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        failed = int(m.group(1))
    return passed, failed
