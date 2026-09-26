# ai-generated: 100% - Codex wrote the pytest runner and accurate summary reporting.
import sys
from pathlib import Path
import pytest

class Counts:
    def __init__(self):
        self.passed = 0
        self.failed = 0
    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.passed:
            self.passed += 1
        if report.failed:
            self.failed += 1
    def pytest_collectreport(self, report):
        if report.failed:
            self.failed += 1

if __name__ == "__main__":
    counts = Counts()
    code = pytest.main([str(Path(__file__).with_name("test_api.py")), "-q", "-p", "no:cacheprovider"], plugins=[counts])
    failures = counts.failed if code == 0 else max(1, counts.failed)
    print(f"ITSMLAB-TESTS: passed={counts.passed} failed={failures}", flush=True)
    sys.exit(int(code))
